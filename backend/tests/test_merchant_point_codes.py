from decimal import Decimal

from django.test import TestCase

from apps.merchants.models import MerchantPointCode
from apps.merchants.services import (
    point_code_content,
    point_code_payment_preview,
    scan_point_code,
)
from apps.points.models import PointAccount, PointExchangeRule, PointRecord
from apps.points.services import add_points
from shared.exceptions import BusinessError
from tests.helpers import admin_auth_header, auth_header, create_member, create_merchant


class MerchantPointCodeServiceTests(TestCase):
    def setUp(self):
        self.member = create_member()
        self.merchant = create_merchant()
        PointExchangeRule.objects.create(points_per_yuan=100, is_active=True)
        self.point_code = MerchantPointCode.objects.create(
            merchant=self.merchant,
            points=50,
            code="test-code-token",
            is_active=True,
            remark="测试固定码",
        )

    def test_scan_point_code_deducts_fixed_points(self):
        add_points(self.member, 200, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        record = scan_point_code(self.member, self.point_code.code, request_no="scan-001")

        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 150)
        self.assertEqual(record.source_type, PointRecord.SourceType.MERCHANT_PAYMENT)
        self.assertEqual(record.merchant, self.merchant)
        self.assertEqual(record.amount, -50)
        self.assertEqual(record.yuan_amount, Decimal("0.50"))
        self.assertEqual(record.request_no, "scan-001")
        self.assertEqual(record.balance_after, 150)
        self.assertIn("固定码", record.reason)

    def test_scan_point_code_is_idempotent(self):
        add_points(self.member, 200, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        first = scan_point_code(self.member, self.point_code.code, request_no="same-req")
        second = scan_point_code(self.member, self.point_code.code, request_no="same-req")

        self.assertEqual(first.id, second.id)
        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 150)
        self.assertEqual(PointRecord.objects.filter(source_type=PointRecord.SourceType.MERCHANT_PAYMENT).count(), 1)

    def test_scan_point_code_without_request_no_allows_multiple(self):
        add_points(self.member, 200, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        first = scan_point_code(self.member, self.point_code.code)
        second = scan_point_code(self.member, self.point_code.code)

        self.assertNotEqual(first.id, second.id)
        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 100)

    def test_scan_point_code_rejects_insufficient_balance(self):
        add_points(self.member, 30, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        with self.assertRaisesRegex(BusinessError, "积分余额不足"):
            scan_point_code(self.member, self.point_code.code)

    def test_scan_point_code_rejects_inactive_code(self):
        self.point_code.is_active = False
        self.point_code.save(update_fields=["is_active"])
        add_points(self.member, 200, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        with self.assertRaisesRegex(BusinessError, "固定积分码已停用"):
            scan_point_code(self.member, self.point_code.code)

    def test_scan_point_code_rejects_unknown_code(self):
        add_points(self.member, 200, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        with self.assertRaisesRegex(BusinessError, "固定积分码不存在"):
            scan_point_code(self.member, "nonexistent-code")

    def test_scan_point_code_rejects_inactive_merchant(self):
        self.merchant.is_active = False
        self.merchant.save(update_fields=["is_active"])
        add_points(self.member, 200, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        with self.assertRaisesRegex(BusinessError, "商户已停用"):
            scan_point_code(self.member, self.point_code.code)

    def test_point_code_payment_preview_returns_info(self):
        add_points(self.member, 120, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        preview = point_code_payment_preview(self.member, self.point_code.code)

        self.assertEqual(preview["code"], self.point_code.code)
        self.assertEqual(preview["merchant_id"], self.merchant.id)
        self.assertEqual(preview["merchant_name"], self.merchant.name)
        self.assertEqual(preview["points"], 50)
        self.assertEqual(preview["points_per_yuan"], 100)
        self.assertEqual(preview["yuan_amount"], "0.50")
        self.assertEqual(preview["balance"], 120)

    def test_point_code_content_format(self):
        content = point_code_content("abc123")
        self.assertEqual(content, "street-service://merchant-point-pay?code=abc123")


class MerchantPointCodeApiTests(TestCase):
    def setUp(self):
        self.member = create_member()
        self.merchant = create_merchant()
        PointExchangeRule.objects.create(points_per_yuan=100, is_active=True)
        self.point_code = MerchantPointCode.objects.create(
            merchant=self.merchant,
            points=50,
            code="api-code-token",
            is_active=True,
        )
        self.member_headers = auth_header("member", self.member.openid)

    def test_preview_api_returns_code_info(self):
        add_points(self.member, 100, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        response = self.client.get(
            f"/api/merchants/point-codes/{self.point_code.code}",
            **self.member_headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["points"], 50)
        self.assertEqual(data["yuan_amount"], "0.50")
        self.assertEqual(data["balance"], 100)

    def test_scan_api_deducts_points(self):
        add_points(self.member, 100, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        response = self.client.post(
            f"/api/merchants/point-codes/{self.point_code.code}/scan",
            {"request_no": "api-scan-001"},
            content_type="application/json",
            **self.member_headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["points"], 50)
        self.assertEqual(data["yuan_amount"], "0.50")
        self.assertEqual(data["balance_after"], 50)
        self.assertEqual(data["merchant_id"], self.merchant.id)

    def test_scan_api_idempotent_with_request_no(self):
        add_points(self.member, 200, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        first = self.client.post(
            f"/api/merchants/point-codes/{self.point_code.code}/scan",
            {"request_no": "dup-req"},
            content_type="application/json",
            **self.member_headers,
        )
        second = self.client.post(
            f"/api/merchants/point-codes/{self.point_code.code}/scan",
            {"request_no": "dup-req"},
            content_type="application/json",
            **self.member_headers,
        )

        self.assertEqual(first.json()["data"]["id"], second.json()["data"]["id"])
        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 150)

    def test_scan_api_rejects_insufficient_balance(self):
        add_points(self.member, 30, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        response = self.client.post(
            f"/api/merchants/point-codes/{self.point_code.code}/scan",
            content_type="application/json",
            **self.member_headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("积分余额不足", response.json()["message"])

    def test_scan_api_rejects_unknown_code(self):
        response = self.client.post(
            "/api/merchants/point-codes/nonexistent/scan",
            content_type="application/json",
            **self.member_headers,
        )

        self.assertEqual(response.status_code, 404)

    def test_scan_api_requires_auth(self):
        response = self.client.post(
            f"/api/merchants/point-codes/{self.point_code.code}/scan",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)


class AdminMerchantPointCodeApiTests(TestCase):
    def setUp(self):
        self.merchant = create_merchant()
        self.admin_headers = admin_auth_header()

    def test_create_point_code(self):
        response = self.client.post(
            "/api/admin/merchants/point-codes",
            {"merchant_id": self.merchant.id, "points": 100, "remark": "100积分码"},
            content_type="application/json",
            **self.admin_headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["merchant_id"], self.merchant.id)
        self.assertEqual(data["points"], 100)
        self.assertTrue(data["code"])
        self.assertIn("merchant-point-pay", data["code_content"])
        self.assertTrue(data["is_active"])

    def test_list_point_codes(self):
        MerchantPointCode.objects.create(merchant=self.merchant, points=50, code="list-1")
        MerchantPointCode.objects.create(merchant=self.merchant, points=100, code="list-2", is_active=False)

        response = self.client.get(
            "/api/admin/merchants/point-codes",
            **self.admin_headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 2)

    def test_list_point_codes_filter_by_active(self):
        MerchantPointCode.objects.create(merchant=self.merchant, points=50, code="active-1")
        MerchantPointCode.objects.create(merchant=self.merchant, points=100, code="inactive-1", is_active=False)

        response = self.client.get(
            "/api/admin/merchants/point-codes",
            {"is_active": "true"},
            **self.admin_headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["code"], "active-1")

    def test_list_point_codes_filter_by_merchant(self):
        other = create_merchant(openid="other-m", name="其他商户")
        MerchantPointCode.objects.create(merchant=self.merchant, points=50, code="m1")
        MerchantPointCode.objects.create(merchant=other, points=100, code="m2")

        response = self.client.get(
            "/api/admin/merchants/point-codes",
            {"merchant_id": self.merchant.id},
            **self.admin_headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["code"], "m1")

    def test_get_point_code_detail(self):
        code = MerchantPointCode.objects.create(merchant=self.merchant, points=80, code="detail-1", remark="备注")

        response = self.client.get(
            f"/api/admin/merchants/point-codes/{code.id}",
            **self.admin_headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["points"], 80)
        self.assertEqual(data["remark"], "备注")

    def test_update_point_code(self):
        code = MerchantPointCode.objects.create(merchant=self.merchant, points=50, code="update-1")

        response = self.client.patch(
            f"/api/admin/merchants/point-codes/{code.id}",
            {"points": 200, "remark": "已更新"},
            content_type="application/json",
            **self.admin_headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["points"], 200)
        self.assertEqual(data["remark"], "已更新")

    def test_update_point_code_rejects_zero_points(self):
        code = MerchantPointCode.objects.create(merchant=self.merchant, points=50, code="zero-1")

        response = self.client.patch(
            f"/api/admin/merchants/point-codes/{code.id}",
            {"points": 0},
            content_type="application/json",
            **self.admin_headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("固定积分值必须大于 0", response.json()["message"])

    def test_set_point_code_status(self):
        code = MerchantPointCode.objects.create(merchant=self.merchant, points=50, code="status-1")

        response = self.client.post(
            f"/api/admin/merchants/point-codes/{code.id}/status",
            {"is_active": False},
            content_type="application/json",
            **self.admin_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["data"]["is_active"])

    def test_delete_point_code(self):
        code = MerchantPointCode.objects.create(merchant=self.merchant, points=50, code="delete-1")

        response = self.client.delete(
            f"/api/admin/merchants/point-codes/{code.id}",
            **self.admin_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(MerchantPointCode.objects.filter(pk=code.id).exists())

    def test_create_rejects_inactive_merchant(self):
        inactive = create_merchant(openid="inactive-m", name="停用商户", is_active=False)

        response = self.client.post(
            "/api/admin/merchants/point-codes",
            {"merchant_id": inactive.id, "points": 50},
            content_type="application/json",
            **self.admin_headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("商户已停用", response.json()["message"])

    def test_create_rejects_invalid_points(self):
        response = self.client.post(
            "/api/admin/merchants/point-codes",
            {"merchant_id": self.merchant.id, "points": 0},
            content_type="application/json",
            **self.admin_headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("固定积分值必须大于 0", response.json()["message"])

    def test_admin_apis_require_auth(self):
        response = self.client.get("/api/admin/merchants/point-codes")
        self.assertEqual(response.status_code, 401)

from decimal import Decimal

from django.test import TestCase

from apps.merchants.services import fixed_code_data, merchant_payment_info, merchant_point_record_data, pay_merchant_with_points
from apps.points.models import PointAccount, PointExchangeRule, PointRecord
from apps.points.services import add_points
from shared.exceptions import BusinessError
from tests.helpers import auth_header, create_member, create_merchant


class MerchantPointPaymentFlowTests(TestCase):
    def setUp(self):
        self.member = create_member()
        self.merchant = create_merchant()
        self.other_merchant = create_merchant(openid="other-merchant", name="其他商户")
        PointExchangeRule.objects.create(points_per_yuan=100, is_active=True)

    def test_pay_merchant_with_points_deducts_balance_and_records_metadata(self):
        add_points(self.member, 150, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        record = pay_merchant_with_points(self.member, self.merchant, 100, request_no="pay-001")

        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 50)
        self.assertEqual(record.source_type, PointRecord.SourceType.MERCHANT_PAYMENT)
        self.assertEqual(record.merchant, self.merchant)
        self.assertEqual(record.amount, -100)
        self.assertEqual(record.yuan_amount, Decimal("1.00"))
        self.assertEqual(record.request_no, "pay-001")
        self.assertEqual(record.balance_after, 50)

    def test_pay_merchant_rejects_inactive_insufficient_and_missing_rule(self):
        inactive = create_merchant(openid="inactive-merchant", name="停用商户", is_active=False)
        add_points(self.member, 50, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        with self.assertRaisesRegex(BusinessError, "商户已停用"):
            pay_merchant_with_points(self.member, inactive, 10)

        with self.assertRaisesRegex(BusinessError, "积分余额不足"):
            pay_merchant_with_points(self.member, self.merchant, 100)

        PointExchangeRule.objects.update(is_active=False)
        with self.assertRaisesRegex(BusinessError, "积分兑换比例未配置"):
            pay_merchant_with_points(self.member, self.merchant, 10)

    def test_pay_merchant_request_no_is_idempotent(self):
        add_points(self.member, 200, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        first = pay_merchant_with_points(self.member, self.merchant, 100, request_no="same-req")
        second = pay_merchant_with_points(self.member, self.merchant, 100, request_no="same-req")

        self.assertEqual(first.id, second.id)
        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 100)
        self.assertEqual(PointRecord.objects.filter(source_type=PointRecord.SourceType.MERCHANT_PAYMENT).count(), 1)

    def test_fixed_code_and_payment_info_services(self):
        add_points(self.member, 120, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        fixed_code = fixed_code_data(self.merchant)
        payment_info = merchant_payment_info(self.member, self.merchant)

        self.assertEqual(fixed_code["merchant_id"], self.merchant.id)
        self.assertIn(str(self.merchant.id), fixed_code["code_content"])
        self.assertEqual(payment_info["merchant_id"], self.merchant.id)
        self.assertEqual(payment_info["points_per_yuan"], 100)
        self.assertEqual(payment_info["balance"], 120)

    def test_merchant_payment_api_flow(self):
        add_points(self.member, 150, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        member_headers = auth_header("member", self.member.openid)
        merchant_headers = auth_header("merchant", self.merchant.openid)

        info_response = self.client.get(f"/api/merchants/{self.merchant.id}/payment-info", **member_headers)
        pay_response = self.client.post(
            f"/api/merchants/{self.merchant.id}/point-payments",
            {"points": 100, "request_no": "api-pay-001"},
            content_type="application/json",
            **member_headers,
        )
        fixed_code_response = self.client.get("/api/merchant/fixed-code", **merchant_headers)
        records_response = self.client.get("/api/merchant/point-records", **merchant_headers)

        self.assertEqual(info_response.status_code, 200)
        self.assertEqual(info_response.json()["data"]["points_per_yuan"], 100)
        self.assertEqual(pay_response.status_code, 200)
        self.assertEqual(pay_response.json()["data"]["points"], 100)
        self.assertEqual(pay_response.json()["data"]["yuan_amount"], "1.00")
        self.assertEqual(pay_response.json()["data"]["balance_after"], 50)
        self.assertEqual(fixed_code_response.status_code, 200)
        self.assertIn(str(self.merchant.id), fixed_code_response.json()["data"]["code_content"])
        self.assertEqual(records_response.status_code, 200)
        self.assertEqual(records_response.json()["data"]["total"], 1)
        self.assertEqual(records_response.json()["data"]["items"][0]["merchant_id"], self.merchant.id)

    def test_merchant_point_records_only_include_current_merchant(self):
        add_points(self.member, 300, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        own_record = pay_merchant_with_points(self.member, self.merchant, 100, request_no="own")
        pay_merchant_with_points(self.member, self.other_merchant, 100, request_no="other")

        headers = auth_header("merchant", self.merchant.openid)
        response = self.client.get("/api/merchant/point-records", **headers)

        self.assertEqual(response.status_code, 200)
        items = response.json()["data"]["items"]
        self.assertEqual([item["id"] for item in items], [own_record.id])

    def test_openapi_does_not_publish_old_mall_routes(self):
        response = self.client.get("/api/openapi.json")

        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        self.assertNotIn("/api/merchant-products", paths)
        self.assertNotIn("/api/product-redemptions", paths)
        self.assertNotIn("/api/merchant/redemptions", paths)

    def test_merchant_point_record_data_masks_member(self):
        add_points(self.member, 150, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        record = pay_merchant_with_points(self.member, self.merchant, 100, request_no="mask")

        data = merchant_point_record_data(record)

        self.assertEqual(data["member_name_masked"], "测*")
        self.assertEqual(data["member_phone_masked"], "138****0000")

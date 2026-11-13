from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.utils import timezone

from apps.merchants.models import Merchant, MerchantSettlement
from apps.points.models import PointRecord
from tests.helpers import admin_auth_header, create_admin_user, create_member


class AdminPortalMerchantsApiTests(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.headers = admin_auth_header(self.admin)
        self.member = create_member(nickname="支付用户", phone="13800001111")

    def test_merchant_lifecycle_payment_summary_and_settlement_processing(self):
        create_response = self.client.post(
            "/api/admin/merchants",
            {"openid": "merchant-openid", "name": "便民超市", "contact_name": "王店长", "phone": "13900000000", "address": "社区中心", "is_active": True},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(create_response.status_code, 200)
        merchant_id = create_response.json()["data"]["id"]
        merchant = Merchant.objects.get(pk=merchant_id)
        PointRecord.objects.create(
            member=self.member,
            merchant=merchant,
            amount=-200,
            change_type=PointRecord.ChangeType.EXPENSE,
            source_type=PointRecord.SourceType.MERCHANT_PAYMENT,
            reason="商户支付",
            yuan_amount=Decimal("2.00"),
            request_no="req-1",
        )

        list_response = self.client.get("/api/admin/merchants?keyword=便民", **self.headers)
        fixed_code = self.client.get(f"/api/admin/merchants/{merchant_id}/fixed-code", **self.headers)
        status_response = self.client.post(
            f"/api/admin/merchants/{merchant_id}/status",
            {"is_active": False},
            content_type="application/json",
            **self.headers,
        )
        records_response = self.client.get("/api/admin/merchants/point-records?keyword=req-1", **self.headers)
        settlement_response = self.client.post(
            "/api/admin/merchants/settlements/generate",
            {
                "merchant_id": merchant_id,
                "period_type": "month",
                "period_label": "2026-07",
                "date_from": timezone.localdate().isoformat(),
                "date_to": timezone.localdate().isoformat(),
            },
            content_type="application/json",
            **self.headers,
        )
        settlement_id = settlement_response.json()["data"]["id"]
        process_response = self.client.post(
            f"/api/admin/merchants/settlements/{settlement_id}/process",
            {"processor_name": "管理员", "remark": "已结清"},
            content_type="application/json",
            **self.headers,
        )
        refresh_processed = self.client.post(
            "/api/admin/merchants/settlements/generate",
            {
                "merchant_id": merchant_id,
                "period_type": "month",
                "period_label": "2026-07",
                "date_from": timezone.localdate().isoformat(),
                "date_to": timezone.localdate().isoformat(),
            },
            content_type="application/json",
            **self.headers,
        )
        delete_response = self.client.delete(f"/api/admin/merchants/{merchant_id}", **self.headers)

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["data"]["total"], 1)
        self.assertEqual(fixed_code.status_code, 200)
        self.assertIn(str(merchant_id), fixed_code.json()["data"]["code_content"])
        self.assertEqual(status_response.status_code, 200)
        self.assertFalse(status_response.json()["data"]["is_active"])
        self.assertEqual(records_response.status_code, 200)
        self.assertEqual(records_response.json()["data"]["summary"]["record_count"], 1)
        self.assertEqual(records_response.json()["data"]["summary"]["total_points"], 200)
        self.assertEqual(settlement_response.status_code, 200)
        self.assertEqual(settlement_response.json()["data"]["total_points"], 200)
        self.assertEqual(process_response.status_code, 200)
        self.assertEqual(process_response.json()["data"]["status"], "processed")
        self.assertEqual(refresh_processed.status_code, 400)
        self.assertIn("已处理", refresh_processed.json()["message"])
        self.assertEqual(delete_response.status_code, 200)
        self.assertTrue(delete_response.json()["data"]["deleted"])
        merchant = Merchant.objects.get(pk=merchant_id)
        self.assertIsNotNone(merchant.deleted_at)
        self.assertTrue(PointRecord.objects.filter(merchant_id=merchant_id).exists())
        self.assertTrue(MerchantSettlement.objects.filter(merchant_id=merchant_id).exists())

    def test_merchant_openid_must_be_unique(self):
        Merchant.objects.create(openid="dup-openid", name="已有商户")
        response = self.client.post(
            "/api/admin/merchants",
            {"openid": "dup-openid", "name": "重复商户"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)


class AdminPortalMerchantAccountTests(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.headers = admin_auth_header(self.admin)

    def test_merchant_create_with_username_password_then_password_login(self):
        create_response = self.client.post(
            "/api/admin/merchants",
            {
                "openid": "merchant-openid",
                "username": "merchant_a",
                "password": "merchant123456",
                "name": "便民超市",
                "contact_name": "王店长",
                "phone": "13900000000",
                "is_active": True,
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(create_response.status_code, 200)
        data = create_response.json()["data"]
        self.assertEqual(data["username"], "merchant_a")

        login_response = self.client.post(
            "/api/merchant/auth/login",
            {"username": "merchant_a", "password": "merchant123456"},
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()["data"]["merchant"]["username"], "merchant_a")

    def test_merchant_create_username_without_password_rejected(self):
        response = self.client.post(
            "/api/admin/merchants",
            {"openid": "merchant-openid", "username": "merchant_a", "name": "便民超市"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("密码", response.json()["message"])

    def test_merchant_create_username_must_be_unique(self):
        Merchant.objects.create(openid="dup-openid", username="merchant_a", name="已有商户")
        response = self.client.post(
            "/api/admin/merchants",
            {"openid": "merchant-openid", "username": "merchant_a", "password": "merchant123456", "name": "重复商户"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("用户名", response.json()["message"])

    def test_merchant_password_reset_endpoint(self):
        Merchant.objects.create(
            openid="merchant-openid",
            username="merchant_a",
            password=make_password("merchant123456"),
            name="便民超市",
        )
        merchant = Merchant.objects.get(username="merchant_a")

        reset_response = self.client.post(
            f"/api/admin/merchants/{merchant.id}/password",
            {"password": "newpass123456"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(reset_response.status_code, 200)
        self.assertTrue(reset_response.json()["data"]["password_reset"])

        old_login = self.client.post(
            "/api/merchant/auth/login",
            {"username": "merchant_a", "password": "merchant123456"},
            content_type="application/json",
        )
        self.assertEqual(old_login.status_code, 400)

        new_login = self.client.post(
            "/api/merchant/auth/login",
            {"username": "merchant_a", "password": "newpass123456"},
            content_type="application/json",
        )
        self.assertEqual(new_login.status_code, 200)

    def test_merchant_password_reset_requires_username(self):
        merchant = Merchant.objects.create(openid="merchant-openid", name="无用户名商户")
        response = self.client.post(
            f"/api/admin/merchants/{merchant.id}/password",
            {"password": "newpass123456"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("用户名", response.json()["message"])

    def test_merchant_password_reset_too_short(self):
        merchant = Merchant.objects.create(
            openid="merchant-openid",
            username="merchant_a",
            password=make_password("merchant123456"),
            name="便民超市",
        )
        response = self.client.post(
            f"/api/admin/merchants/{merchant.id}/password",
            {"password": "short"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("至少 6 位", response.json()["message"])

    def test_merchant_soft_delete_archives_identity_and_hides_from_list(self):
        merchant = Merchant.objects.create(
            openid="merchant-openid",
            username="13900000999",
            password=make_password("000000"),
            name="待删除商户",
            phone="13900000999",
            audit_status=Merchant.AuditStatus.APPROVED,
            is_active=True,
        )

        response = self.client.delete(f"/api/admin/merchants/{merchant.id}?reason=停止合作", **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["deleted"])

        merchant.refresh_from_db()
        self.assertIsNotNone(merchant.deleted_at)
        self.assertFalse(merchant.is_active)
        self.assertEqual(merchant.deleted_username, "13900000999")
        self.assertEqual(merchant.deleted_phone, "13900000999")
        self.assertEqual(merchant.deleted_by_id, self.admin.id)
        self.assertEqual(merchant.delete_reason, "停止合作")
        self.assertEqual(merchant.username, f"deleted_{merchant.id}")
        self.assertEqual(merchant.phone, f"deleted_{merchant.id}")

        list_response = self.client.get("/api/admin/merchants?keyword=待删除商户", **self.headers)
        self.assertEqual(list_response.json()["data"]["total"], 0)

        # 原账号无法再登录
        login_response = self.client.post(
            "/api/merchant/auth/login",
            {"username": "13900000999", "password": "000000"},
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 400)

        # 原手机号可以重新建档
        again = self.client.post(
            "/api/admin/merchants",
            {"name": "新商户", "phone": "13900000999", "username": "13900000999", "password": "000000"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(again.status_code, 200)

        # 重复删除返回错误
        repeat = self.client.delete(f"/api/admin/merchants/{merchant.id}", **self.headers)
        self.assertEqual(repeat.status_code, 400)
        self.assertIn("已删除", repeat.json()["message"])

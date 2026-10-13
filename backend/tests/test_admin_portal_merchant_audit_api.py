from django.test import TestCase

from apps.merchants.models import Merchant
from tests.helpers import admin_auth_header, create_admin_user


class AdminPortalMerchantAuditApiTests(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.headers = admin_auth_header(self.admin)

    def _register_merchant(self, phone: str = "13700000001", community: str = "幸福社区") -> Merchant:
        response = self.client.post(
            "/api/merchant/auth/register",
            {
                "shop_name": "便民小卖部",
                "shop_address": "幸福街道 1 号",
                "service_content": "日用百货",
                "community": community,
                "merchant_nature": "个体工商户",
                "contact_name": "王店长",
                "contact_phone": phone,
                "business_hours": "08:30-18:20",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        return Merchant.objects.get(phone=phone)

    def test_pending_merchant_list_shows_registration_fields(self):
        self._register_merchant()

        response = self.client.get("/api/admin/merchants?audit_status=pending", **self.headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["total"], 1)
        item = response.json()["data"]["items"][0]
        self.assertEqual(item["audit_status"], "pending")
        self.assertEqual(item["community"], "幸福社区")
        self.assertEqual(item["merchant_nature"], "个体工商户")
        self.assertEqual(item["business_hours"], "08:30-18:20")
        self.assertFalse(item["is_active"])

    def test_merchant_list_filters_by_audit_status_and_community_keyword(self):
        merchant = self._register_merchant(community="幸福社区")
        self._register_merchant(phone="13700000002", community="另外一个社区")

        by_keyword = self.client.get("/api/admin/merchants?keyword=幸福社区", **self.headers)
        by_status = self.client.get("/api/admin/merchants?audit_status=approved", **self.headers)

        self.assertEqual(by_keyword.json()["data"]["total"], 1)
        self.assertEqual(by_keyword.json()["data"]["items"][0]["id"], merchant.id)
        self.assertEqual(by_status.json()["data"]["total"], 0)

    def test_approve_merchant_activates_account(self):
        merchant = self._register_merchant()

        response = self.client.post(
            f"/api/admin/merchants/{merchant.id}/audit",
            {"action": "approve", "remark": "资料完整"},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        merchant.refresh_from_db()
        self.assertEqual(merchant.audit_status, Merchant.AuditStatus.APPROVED)
        self.assertEqual(merchant.audit_remark, "资料完整")
        self.assertTrue(merchant.is_active)

    def test_reject_merchant_requires_remark_and_deactivates_account(self):
        merchant = self._register_merchant()

        missing_remark = self.client.post(
            f"/api/admin/merchants/{merchant.id}/audit",
            {"action": "reject", "remark": ""},
            content_type="application/json",
            **self.headers,
        )
        rejected = self.client.post(
            f"/api/admin/merchants/{merchant.id}/audit",
            {"action": "reject", "remark": "店铺地址不完整"},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(missing_remark.status_code, 400)
        self.assertEqual(missing_remark.json()["message"], "驳回必须填写审核意见")
        self.assertEqual(rejected.status_code, 200)
        merchant.refresh_from_db()
        self.assertEqual(merchant.audit_status, Merchant.AuditStatus.REJECTED)
        self.assertEqual(merchant.audit_remark, "店铺地址不完整")
        self.assertFalse(merchant.is_active)

    def test_audit_rejects_unknown_action_and_missing_merchant(self):
        merchant = self._register_merchant()

        invalid_action = self.client.post(
            f"/api/admin/merchants/{merchant.id}/audit",
            {"action": "maybe", "remark": ""},
            content_type="application/json",
            **self.headers,
        )
        missing = self.client.post(
            "/api/admin/merchants/999999/audit",
            {"action": "approve", "remark": ""},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(invalid_action.status_code, 400)
        self.assertEqual(invalid_action.json()["message"], "审核动作不支持")
        self.assertEqual(missing.status_code, 404)

    def test_admin_created_merchant_is_approved_with_new_fields(self):
        response = self.client.post(
            "/api/admin/merchants",
            {
                "name": "后台商户",
                "contact_name": "管理员",
                "phone": "13700000003",
                "community": "后台社区",
                "merchant_nature": "国有企业",
                "is_active": True,
            },
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["audit_status"], "approved")
        self.assertEqual(data["community"], "后台社区")
        self.assertEqual(data["merchant_nature"], "国有企业")

    def test_admin_merchant_phone_must_be_unique(self):
        self._register_merchant(phone="13700000004")

        create_conflict = self.client.post(
            "/api/admin/merchants",
            {"name": "重复手机号商户", "phone": "13700000004"},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(create_conflict.status_code, 400)
        self.assertEqual(create_conflict.json()["message"], "该手机号已被其他商户使用")

    def test_admin_update_merchant_community_and_phone_syncs_username(self):
        merchant = self._register_merchant(phone="13700000005")

        response = self.client.patch(
            f"/api/admin/merchants/{merchant.id}",
            {"community": "新社区", "merchant_nature": "连锁门店", "phone": "13700000006"},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        merchant.refresh_from_db()
        self.assertEqual(merchant.community, "新社区")
        self.assertEqual(merchant.merchant_nature, "连锁门店")
        self.assertEqual(merchant.phone, "13700000006")
        self.assertEqual(merchant.username, "13700000006")

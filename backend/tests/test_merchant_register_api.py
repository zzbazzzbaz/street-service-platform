from unittest.mock import patch

from django.contrib.auth.hashers import check_password, make_password
from django.test import TestCase

from apps.merchants.models import Merchant
from shared.auth import issue_token
from tests.helpers import admin_auth_header, create_admin_user, create_merchant


def _register_payload(**overrides) -> dict:
    payload = {
        "shop_name": "便民小卖部",
        "shop_address": "幸福街道 1 号",
        "service_content": "日用百货、饮料零食",
        "community": "幸福社区",
        "merchant_nature": "个体工商户",
        "contact_name": "王店长",
        "contact_phone": "13712345678",
        "business_hours": "08:30-18:20",
    }
    payload.update(overrides)
    return payload


class MerchantRegisterApiTests(TestCase):
    def test_register_creates_pending_merchant_and_returns_login(self):
        response = self.client.post("/api/merchant/auth/register", _register_payload(), content_type="application/json")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertTrue(data["need_audit"])
        self.assertTrue(data["access_token"])
        self.assertEqual(data["merchant"]["audit_status"], "pending")
        self.assertFalse(data["merchant"]["is_active"])
        self.assertEqual(data["merchant"]["community"], "幸福社区")
        self.assertEqual(data["merchant"]["merchant_nature"], "个体工商户")

        merchant = Merchant.objects.get(phone="13712345678")
        self.assertEqual(merchant.name, "便民小卖部")
        self.assertEqual(merchant.username, "13712345678")
        self.assertTrue(check_password("000000", merchant.password))
        self.assertEqual(merchant.audit_status, Merchant.AuditStatus.PENDING)
        self.assertIsNone(merchant.openid)

    def test_registered_merchant_can_open_status_page(self):
        response = self.client.post("/api/merchant/auth/register", _register_payload(), content_type="application/json")
        token = response.json()["data"]["access_token"]

        me_response = self.client.get("/api/merchant/me", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["data"]["audit_status"], "pending")
        self.assertFalse(me_response.json()["data"]["is_active"])

    def test_registered_merchant_workbench_is_blocked(self):
        response = self.client.post("/api/merchant/auth/register", _register_payload(), content_type="application/json")
        token = response.json()["data"]["access_token"]
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

        paths = [
            "/api/merchant/fixed-code",
            "/api/merchant/point-codes",
            "/api/merchant/point-records",
            "/api/merchant/settlements",
        ]
        for path in paths:
            with self.subTest(path=path):
                blocked = self.client.get(path, **headers)
                self.assertEqual(blocked.status_code, 403)
                self.assertEqual(blocked.json()["message"], "商户资料审核中，请等待审核")

    def test_register_requires_all_fields(self):
        response = self.client.post("/api/merchant/auth/register", {"shop_name": "小卖部"}, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], 40000)

    def test_register_validates_fields(self):
        cases = [
            ({"shop_name": ""}, "店铺名称不能为空"),
            ({"shop_name": "店" * 101}, "店铺名称最多 100 字"),
            ({"shop_address": ""}, "店铺地址不能为空"),
            ({"service_content": ""}, "服务内容不能为空"),
            ({"community": ""}, "所属社区不能为空"),
            ({"merchant_nature": ""}, "商户性质不能为空"),
            ({"contact_name": ""}, "联系人不能为空"),
            ({"contact_phone": "12345"}, "手机号格式不正确"),
            ({"business_hours": "8:30-18:20"}, "营业时间格式必须为 HH:MM-HH:MM"),
            ({"business_hours": "18:20-08:30"}, "营业时间结束时间必须晚于开始时间"),
            ({"business_hours": "09:00-09:00"}, "营业时间结束时间必须晚于开始时间"),
        ]
        for overrides, message in cases:
            with self.subTest(overrides=overrides):
                response = self.client.post(
                    "/api/merchant/auth/register",
                    _register_payload(**overrides),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["message"], message)

    def test_register_rejects_duplicate_phone(self):
        Merchant.objects.create(openid="existing-openid", name="已存在商户", phone="13712345678")

        response = self.client.post("/api/merchant/auth/register", _register_payload(), content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "该手机号已注册")

    def test_registered_merchant_can_login_with_initial_password(self):
        self.client.post("/api/merchant/auth/register", _register_payload(), content_type="application/json")

        response = self.client.post(
            "/api/merchant/auth/login",
            {"username": "13712345678", "password": "000000"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["merchant"]["audit_status"], "pending")


class MerchantAuditGateApiTests(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.headers = admin_auth_header(self.admin)

    def _register_merchant(self, phone: str = "13700000001") -> Merchant:
        response = self.client.post(
            "/api/merchant/auth/register",
            _register_payload(contact_phone=phone),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        return Merchant.objects.get(phone=phone)

    def _merchant_token(self, merchant: Merchant) -> str:
        token, _ = issue_token(
            subject_type="merchant",
            openid=merchant.openid or "",
            subject_id=merchant.pk,
        )
        return token

    def _login(self, phone: str) -> dict:
        return self.client.post(
            "/api/merchant/auth/login",
            {"username": phone, "password": "000000"},
            content_type="application/json",
        )

    def _approve(self, merchant: Merchant) -> None:
        response = self.client.post(
            f"/api/admin/merchants/{merchant.id}/audit",
            {"action": "approve", "remark": "资料完整"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)

    def _reject(self, merchant: Merchant, remark: str = "店铺地址不完整") -> None:
        response = self.client.post(
            f"/api/admin/merchants/{merchant.id}/audit",
            {"action": "reject", "remark": remark},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)

    def test_approved_merchant_can_use_workbench(self):
        merchant = self._register_merchant()
        self._approve(merchant)

        login = self._login("13700000001")
        token = login.json()["data"]["access_token"]
        fixed_code = self.client.get("/api/merchant/fixed-code", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.json()["data"]["merchant"]["is_active"])
        self.assertEqual(fixed_code.status_code, 200)
        self.assertIn("merchant_id", fixed_code.json()["data"])

    def test_rejected_merchant_can_login_and_see_reason_then_resubmit(self):
        merchant = self._register_merchant()
        self._reject(merchant, "营业时间不完整")

        login = self._login("13700000001")
        self.assertEqual(login.status_code, 200)
        token = login.json()["data"]["access_token"]
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

        me = self.client.get("/api/merchant/me", **headers)
        self.assertEqual(me.json()["data"]["audit_status"], "rejected")
        self.assertEqual(me.json()["data"]["audit_remark"], "营业时间不完整")

        blocked = self.client.get("/api/merchant/fixed-code", **headers)
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.json()["message"], "商户资料未通过审核，请联系街道工作人员")

        resubmit = self.client.post(
            "/api/merchant/register-info",
            _register_payload(shop_name="便民小卖部（新）", shop_address="幸福街道 2 号", business_hours="09:00-20:00"),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(resubmit.status_code, 200)
        self.assertEqual(resubmit.json()["data"]["audit_status"], "pending")
        self.assertEqual(resubmit.json()["data"]["audit_remark"], "")
        self.assertEqual(resubmit.json()["data"]["name"], "便民小卖部（新）")

        blocked_again = self.client.get("/api/merchant/fixed-code", **headers)
        self.assertEqual(blocked_again.json()["message"], "商户资料审核中，请等待审核")

    def test_rejected_merchant_without_username_gets_login_name_on_resubmit(self):
        merchant = create_merchant(
            openid="rejected-merchant-openid",
            phone="13700000007",
            username=None,
            audit_status=Merchant.AuditStatus.REJECTED,
        )

        response = self.client.post(
            "/api/merchant/register-info",
            _register_payload(contact_phone=""),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self._merchant_token(merchant)}",
        )

        self.assertEqual(response.status_code, 200)
        merchant.refresh_from_db()
        self.assertEqual(merchant.username, "13700000007")
        self.assertEqual(merchant.audit_status, Merchant.AuditStatus.PENDING)

    def test_pending_merchant_cannot_resubmit(self):
        self._register_merchant()
        token = self._login("13700000001").json()["data"]["access_token"]

        response = self.client.post(
            "/api/merchant/register-info",
            _register_payload(),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "资料审核中，请等待审核结果")

    def test_approved_merchant_cannot_resubmit(self):
        merchant = self._register_merchant()
        self._approve(merchant)
        token = self._merchant_token(merchant)

        response = self.client.post(
            "/api/merchant/register-info",
            _register_payload(),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "审核已通过，如需修改资料请联系街道工作人员")

    def test_disabled_approved_merchant_is_blocked(self):
        merchant = create_merchant(
            openid="disabled-openid",
            username="13900000009",
            password=make_password("000000"),
            is_active=False,
        )
        token = self._merchant_token(merchant)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

        me = self.client.get("/api/merchant/me", **headers)
        self.assertEqual(me.status_code, 403)
        self.assertEqual(me.json()["message"], "当前账号已停用")

        password_change = self.client.post(
            "/api/merchant/password",
            {"current_password": "000000", "new_password": "newPass123"},
            content_type="application/json",
            **headers,
        )
        self.assertEqual(password_change.status_code, 403)
        self.assertEqual(password_change.json()["message"], "当前账号已停用")

        login = self._login("13900000009")
        self.assertEqual(login.status_code, 403)
        self.assertEqual(login.json()["message"], "当前账号已停用")

    def test_wechat_phone_login_allows_pending_merchant(self):
        merchant = self._register_merchant()
        self.assertEqual(merchant.audit_status, Merchant.AuditStatus.PENDING)

        with (
            patch("apps.merchants.services.wechat_code_to_openid", return_value="wx-pending-openid"),
            patch("apps.merchants.services.wechat_phone_code_to_phone", return_value="13700000001"),
        ):
            response = self.client.post(
                "/api/merchant/auth/wechat-phone-login",
                {"login_code": "wx-code", "phone_code": "wx-phone-code"},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["merchant"]["audit_status"], "pending")

    def test_wechat_phone_login_rejects_phone_bound_to_other_merchant(self):
        self._register_merchant()
        other = create_merchant(openid="other-merchant-openid")

        with (
            patch("apps.merchants.services.wechat_code_to_openid", return_value=other.openid),
            patch("apps.merchants.services.wechat_phone_code_to_phone", return_value="13700000001"),
        ):
            response = self.client.post(
                "/api/merchant/auth/wechat-phone-login",
                {"login_code": "wx-code", "phone_code": "wx-phone-code"},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["message"], "该微信已绑定其他商户账号")

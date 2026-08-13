from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.test import TestCase, override_settings

from apps.members.models import Member
from apps.merchants.models import Merchant
from shared.auth import issue_token, parse_token


class AuthApiTests(TestCase):
    def test_health_endpoint_returns_unified_success(self):
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"code": 0, "message": "success", "data": {"status": "ok"}})

    def test_wechat_login_accepts_openid_for_dev_login(self):
        response = self.client.post("/api/auth/wechat-login", {"openid": "member-openid"}, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], 0)
        self.assertEqual(payload["data"]["token_type"], "Bearer")
        self.assertEqual(payload["data"]["member"]["openid"], "member-openid")
        self.assertEqual(payload["data"]["member"]["identity_type"], "normal_user")
        self.assertEqual(payload["data"]["member"]["audit_status"], "none")
        self.assertEqual(payload["data"]["member"]["audit_remark"], "")
        self.assertTrue(Member.objects.filter(openid="member-openid").exists())

    def test_wechat_login_validation_error_uses_unified_response(self):
        response = self.client.post("/api/auth/wechat-login", {}, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["code"], 40000)
        self.assertIn("message", payload)
        self.assertIn("errors", payload)

    def test_merchant_wechat_login_accepts_openid_for_dev_login(self):
        response = self.client.post(
            "/api/merchant/auth/wechat-login",
            {"openid": "merchant-openid"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], 0)
        self.assertEqual(payload["data"]["token_type"], "Bearer")
        self.assertEqual(payload["data"]["merchant"]["openid"], "merchant-openid")
        self.assertTrue(Merchant.objects.filter(openid="merchant-openid").exists())

    @override_settings(WECHAT_MINIAPP_APPID="", WECHAT_MINIAPP_SECRET="")
    def test_merchant_wechat_login_placeholder_reports_missing_config(self):
        response = self.client.post(
            "/api/merchant/auth/wechat-login",
            {"code": "wx-code"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], 40000)
        self.assertIn("未配置", response.json()["message"])

    def test_member_wechat_phone_login_requires_phone_code(self):
        response = self.client.post(
            "/api/auth/wechat-phone-login",
            {"login_code": "wx-login-code"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "缺少手机号授权 code")

    @override_settings(WECHAT_MINIAPP_APPID="", WECHAT_MINIAPP_SECRET="")
    def test_member_wechat_phone_login_reports_missing_config(self):
        response = self.client.post(
            "/api/auth/wechat-phone-login",
            {"login_code": "wx-login-code", "phone_code": "wx-phone-code"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "微信手机号登录未配置")

    @override_settings(WECHAT_MINIAPP_APPID="appid", WECHAT_MINIAPP_SECRET="secret")
    def test_member_wechat_phone_login_uses_wechat_phone_and_openid_when_configured(self):
        with (
            patch("apps.members.services.wechat_code_to_openid", return_value="wx-openid") as openid_mock,
            patch("apps.members.services.wechat_phone_code_to_phone", return_value="13812345678") as phone_mock,
        ):
            response = self.client.post(
                "/api/auth/wechat-phone-login",
                {"login_code": "login-code", "phone_code": "phone-code"},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["member"]["openid"], "wx-openid")
        self.assertEqual(data["member"]["phone"], "13812345678")
        self.assertTrue(Member.objects.filter(openid="wx-openid", phone="13812345678").exists())
        openid_mock.assert_called_once_with("login-code")
        phone_mock.assert_called_once_with("phone-code")

    def test_merchant_wechat_phone_login_requires_phone_code(self):
        response = self.client.post(
            "/api/merchant/auth/wechat-phone-login",
            {"login_code": "wx-login-code"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "缺少手机号授权 code")

    @override_settings(WECHAT_MINIAPP_APPID="", WECHAT_MINIAPP_SECRET="")
    def test_merchant_wechat_phone_login_reports_missing_config(self):
        response = self.client.post(
            "/api/merchant/auth/wechat-phone-login",
            {"login_code": "wx-login-code", "phone_code": "wx-phone-code"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "商户微信手机号登录未配置")

    @override_settings(WECHAT_MINIAPP_APPID="appid", WECHAT_MINIAPP_SECRET="secret")
    def test_merchant_wechat_phone_login_matches_active_merchant_by_phone(self):
        merchant = Merchant.objects.create(openid="old-merchant-openid", name="测试商户", phone="13912345678", is_active=True)
        with (
            patch("apps.merchants.services.wechat_code_to_openid", return_value="new-merchant-openid") as openid_mock,
            patch("apps.merchants.services.wechat_phone_code_to_phone", return_value="13912345678") as phone_mock,
        ):
            response = self.client.post(
                "/api/merchant/auth/wechat-phone-login",
                {"login_code": "login-code", "phone_code": "phone-code"},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["merchant"]["id"], merchant.id)
        self.assertEqual(data["merchant"]["openid"], "new-merchant-openid")
        merchant.refresh_from_db()
        self.assertEqual(merchant.openid, "new-merchant-openid")
        openid_mock.assert_called_once_with("login-code")
        phone_mock.assert_called_once_with("phone-code")

    @override_settings(WECHAT_MINIAPP_APPID="appid", WECHAT_MINIAPP_SECRET="secret")
    def test_merchant_wechat_phone_login_rejects_unmatched_phone(self):
        with (
            patch("apps.merchants.services.wechat_code_to_openid", return_value="new-merchant-openid"),
            patch("apps.merchants.services.wechat_phone_code_to_phone", return_value="13912345678"),
        ):
            response = self.client.post(
                "/api/merchant/auth/wechat-phone-login",
                {"login_code": "login-code", "phone_code": "phone-code"},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["message"], "商户账号不存在或未启用")

    def test_merchant_test_login_endpoint_is_removed(self):
        response = self.client.post(
            "/api/merchant/auth/test-login",
            {"openid": "merchant-openid"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)

    def test_member_me_requires_token(self):
        response = self.client.get("/api/members/me")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], 40102)

    def test_member_me_rejects_merchant_token(self):
        Merchant.objects.create(openid="merchant-openid", name="测试商户")
        token, _ = issue_token(subject_type="merchant", openid="merchant-openid")

        response = self.client.get("/api/members/me", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], 40301)

    def test_disabled_member_returns_403(self):
        Member.objects.create(openid="member-openid", is_active=False)
        token, _ = issue_token(subject_type="member", openid="member-openid")

        response = self.client.get("/api/members/me", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], 40301)

    def test_expired_token_returns_40101(self):
        token, _ = issue_token(subject_type="member", openid="member-openid")
        identity = parse_token(token)
        expired_token, _ = issue_token(subject_type="member", openid=identity.openid)
        from shared import auth as auth_module

        payload = auth_module._decode_jwt(expired_token)
        payload["exp"] = 1
        expired_token = auth_module._encode_jwt(payload)

        response = self.client.get("/api/members/me", HTTP_AUTHORIZATION=f"Bearer {expired_token}")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], 40101)

    def test_member_me_exposes_audit_fields(self):
        Member.objects.create(
            openid="member-openid",
            real_name="李建国",
            identity_type=Member.IdentityType.COURIER,
            audit_status=Member.AuditStatus.APPROVED,
            audit_remark="审核通过",
        )
        token, _ = issue_token(subject_type="member", openid="member-openid")

        response = self.client.get("/api/members/me", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["real_name"], "李建国")
        self.assertEqual(data["identity_type"], "courier")
        self.assertEqual(data["audit_status"], "approved")
        self.assertEqual(data["audit_remark"], "审核通过")

    def test_member_profile_updates_current_member(self):
        Member.objects.create(openid="member-openid")
        token, _ = issue_token(subject_type="member", openid="member-openid")

        response = self.client.post(
            "/api/members/profile",
            {"nickname": "张三", "phone": "13800000000"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"]["nickname"], "张三")
        self.assertEqual(payload["data"]["phone"], "13800000000")

    def test_merchant_me_requires_merchant_token(self):
        Member.objects.create(openid="member-openid")
        token, _ = issue_token(subject_type="member", openid="member-openid")

        response = self.client.get("/api/merchant/me", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], 40301)

    def test_disabled_merchant_returns_403(self):
        Merchant.objects.create(openid="merchant-openid", name="测试商户", is_active=False)
        token, _ = issue_token(subject_type="merchant", openid="merchant-openid")

        response = self.client.get("/api/merchant/me", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], 40301)

    @override_settings(WECHAT_MINIAPP_APPID="", WECHAT_MINIAPP_SECRET="")
    def test_wechat_login_placeholder_reports_missing_config(self):
        response = self.client.post("/api/auth/wechat-login", {"code": "wx-code"}, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], 40000)
        self.assertIn("未配置", response.json()["message"])

    def test_member_test_login_endpoint_is_removed(self):
        response = self.client.post("/api/auth/test-login", {"openid": "member-openid"}, content_type="application/json")

        self.assertEqual(response.status_code, 404)


class MerchantPasswordLoginTests(TestCase):
    def make_merchant(self, **kwargs):
        defaults = {
            "openid": "account:merchant-a",
            "username": "merchant_a",
            "password": make_password("merchant123456"),
            "name": "账号登录商户",
            "is_active": True,
        }
        defaults.update(kwargs)
        return Merchant.objects.create(**defaults)

    def test_merchant_password_login_success(self):
        self.make_merchant()
        response = self.client.post(
            "/api/merchant/auth/login",
            {"username": "merchant_a", "password": "merchant123456"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], 0)
        data = payload["data"]
        self.assertEqual(data["token_type"], "Bearer")
        self.assertTrue(data["access_token"])
        self.assertEqual(data["merchant"]["username"], "merchant_a")
        self.assertEqual(data["merchant"]["name"], "账号登录商户")
        # token 可访问商户端业务接口
        me = self.client.get("/api/merchant/me", HTTP_AUTHORIZATION=f"Bearer {data['access_token']}")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["data"]["username"], "merchant_a")

    def test_merchant_password_login_wrong_password(self):
        self.make_merchant()
        response = self.client.post(
            "/api/merchant/auth/login",
            {"username": "merchant_a", "password": "wrong-password"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["code"], 40000)
        self.assertEqual(payload["message"], "用户名或密码错误")

    def test_merchant_password_login_unknown_user(self):
        response = self.client.post(
            "/api/merchant/auth/login",
            {"username": "no-such-merchant", "password": "merchant123456"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], 40000)

    def test_merchant_password_login_empty_fields(self):
        self.make_merchant()
        response = self.client.post(
            "/api/merchant/auth/login",
            {"username": "", "password": ""},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], 40000)

    def test_merchant_password_login_disabled_account(self):
        self.make_merchant(is_active=False)
        response = self.client.post(
            "/api/merchant/auth/login",
            {"username": "merchant_a", "password": "merchant123456"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        payload = response.json()
        self.assertEqual(payload["code"], 40301)
        self.assertEqual(payload["message"], "当前账号已停用")

    def test_merchant_password_login_missing_password_hash(self):
        Merchant.objects.create(openid="account:merchant-b", username="merchant_b", name="无密码商户")
        response = self.client.post(
            "/api/merchant/auth/login",
            {"username": "merchant_b", "password": "whatever123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], 40000)

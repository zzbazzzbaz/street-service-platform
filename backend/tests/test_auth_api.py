from django.test import TestCase

from apps.members.models import Member
from apps.merchants.models import Merchant
from shared.auth import issue_token


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

    def test_merchant_wechat_login_placeholder_reports_missing_config(self):
        response = self.client.post(
            "/api/merchant/auth/wechat-login",
            {"code": "wx-code"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], 40000)
        self.assertIn("未配置", response.json()["message"])

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
        self.assertEqual(response.json()["code"], 40001)

    def test_member_me_rejects_merchant_token(self):
        Merchant.objects.create(openid="merchant-openid", name="测试商户")
        token, _ = issue_token(subject_type="merchant", openid="merchant-openid")

        response = self.client.get("/api/members/me", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], 40001)

    def test_disabled_member_returns_403(self):
        Member.objects.create(openid="member-openid", is_active=False)
        token, _ = issue_token(subject_type="member", openid="member-openid")

        response = self.client.get("/api/members/me", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], 40002)

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

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], 40001)

    def test_disabled_merchant_returns_403(self):
        Merchant.objects.create(openid="merchant-openid", name="测试商户", is_active=False)
        token, _ = issue_token(subject_type="merchant", openid="merchant-openid")

        response = self.client.get("/api/merchant/me", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], 40002)

    def test_wechat_login_placeholder_reports_missing_config(self):
        response = self.client.post("/api/auth/wechat-login", {"code": "wx-code"}, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], 40000)
        self.assertIn("未配置", response.json()["message"])

    def test_member_test_login_endpoint_is_removed(self):
        response = self.client.post("/api/auth/test-login", {"openid": "member-openid"}, content_type="application/json")

        self.assertEqual(response.status_code, 404)

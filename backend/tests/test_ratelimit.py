from django.core.cache import cache
from django.test import TestCase, override_settings

from tests.helpers import auth_header, create_member, create_merchant


@override_settings(RATELIMIT_ENABLE=True)
class RateLimitLoginTests(TestCase):
    def setUp(self):
        cache.clear()
    def test_admin_login_rate_limited_after_5_attempts(self):
        for _ in range(5):
            response = self.client.post(
                "/api/admin/auth/login",
                {"username": "admin", "password": "wrong"},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)

        response = self.client.post(
            "/api/admin/auth/login",
            {"username": "admin", "password": "wrong"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["code"], 42900)

    def test_member_wechat_login_rate_limited_after_5_attempts(self):
        for _ in range(5):
            response = self.client.post(
                "/api/auth/wechat-login",
                {"openid": "test-rate-limit"},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/auth/wechat-login",
            {"openid": "test-rate-limit-6"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 429)


@override_settings(RATELIMIT_ENABLE=True)
class RateLimitPaymentTests(TestCase):
    def setUp(self):
        cache.clear()
        from apps.points.models import PointExchangeRule, PointRecord
        from apps.points.services import add_points

        self.member = create_member()
        self.merchant = create_merchant()
        PointExchangeRule.objects.create(points_per_yuan=100, is_active=True)
        add_points(self.member, 10000, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        self.headers = auth_header("member", self.member.openid)

    def test_point_payment_rate_limited_after_20_requests(self):
        for i in range(20):
            merchant = create_merchant(openid=f"rate-merchant-{i}", name=f"限速商户{i}")
            response = self.client.post(
                f"/api/merchants/{merchant.id}/point-payments",
                {"points": 1, "request_no": f"req-{i}"},
                content_type="application/json",
                **self.headers,
            )
            self.assertEqual(response.status_code, 200)

        response = self.client.post(
            f"/api/merchants/{self.merchant.id}/point-payments",
            {"points": 1, "request_no": "req-overflow"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 429)


class RateLimitDisabledByDefaultTests(TestCase):
    def test_rate_limit_disabled_in_test_settings(self):
        from django.conf import settings
        self.assertFalse(settings.RATELIMIT_ENABLE)

    def test_admin_login_not_limited_when_disabled(self):
        for _ in range(10):
            response = self.client.post(
                "/api/admin/auth/login",
                {"username": "admin", "password": "wrong"},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)

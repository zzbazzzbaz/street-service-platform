from django.test import TestCase

from apps.points.models import PointAccount, PointExchangeRule, PointRecord
from tests.helpers import admin_auth_header, create_admin_user, create_member


class AdminPortalPointsApiTests(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.headers = admin_auth_header(self.admin)
        self.member = create_member()

    def test_point_readonly_views_manual_adjustment_and_exchange_rules(self):
        adjustment_response = self.client.post(
            "/api/admin/points/manual-adjustments",
            {"member_id": self.member.id, "amount": 20, "reason": "补发积分"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(adjustment_response.status_code, 200)
        adjustment_id = adjustment_response.json()["data"]["id"]
        record = PointRecord.objects.get(source_type=PointRecord.SourceType.MANUAL)
        self.assertEqual(record.operator_id, self.admin.id)
        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 20)

        accounts = self.client.get("/api/admin/points/accounts", **self.headers)
        account_detail = self.client.get(f"/api/admin/points/accounts/{PointAccount.objects.get(member=self.member).id}", **self.headers)
        records = self.client.get("/api/admin/points/records", **self.headers)
        record_detail = self.client.get(f"/api/admin/points/records/{record.id}", **self.headers)
        adjustment_detail = self.client.get(f"/api/admin/points/manual-adjustments/{adjustment_id}", **self.headers)
        direct_record_create = self.client.post("/api/admin/points/records", {}, content_type="application/json", **self.headers)

        self.assertEqual(accounts.status_code, 200)
        self.assertEqual(account_detail.status_code, 200)
        self.assertEqual(records.status_code, 200)
        self.assertEqual(record_detail.status_code, 200)
        self.assertEqual(adjustment_detail.status_code, 200)
        self.assertEqual(direct_record_create.status_code, 405)

        old_rule = PointExchangeRule.objects.create(points_per_yuan=50, is_active=True)
        new_rule_response = self.client.post(
            "/api/admin/points/exchange-rules",
            {"points_per_yuan": 100, "is_active": True},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(new_rule_response.status_code, 200)
        old_rule.refresh_from_db()
        self.assertFalse(old_rule.is_active)

    def test_manual_adjustment_requires_reason(self):
        response = self.client.post(
            "/api/admin/points/manual-adjustments",
            {"member_id": self.member.id, "amount": 20, "reason": ""},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("原因", response.json()["message"])

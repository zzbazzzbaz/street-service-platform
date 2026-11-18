from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.activities.models import Activity, ActivityCheckin
from apps.civic_feedbacks.models import CivicFeedback
from apps.elder_services.models import ElderCareRelation, ElderServiceFeedback, ElderServiceTask
from apps.members.models import Member
from apps.merchants.models import Merchant, MerchantSettlement
from apps.points.models import PointRecord
from apps.problem_feedbacks.models import ProblemFeedback
from apps.reports.models import Report
from shared import auth as auth_module
from shared.auth import issue_token


User = get_user_model()


class AdminPortalAuthApiTests(TestCase):
    def create_admin(self, **kwargs):
        defaults = {
            "username": "admin",
            "password": "admin123456",
            "is_backend_manager": True,
            "is_active": True,
        }
        defaults.update(kwargs)
        password = defaults.pop("password")
        user = User.objects.create_user(**defaults)
        user.set_password(password)
        user.save()
        return user

    def admin_login(self, username="admin", password="admin123456"):
        return self.client.post(
            "/api/admin/auth/login",
            {"username": username, "password": password},
            content_type="application/json",
        )

    def test_admin_login_returns_admin_token_and_profile(self):
        admin = self.create_admin(email="admin@example.com")

        response = self.admin_login()

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["token_type"], "Bearer")
        self.assertGreater(data["expires_in"], 0)
        self.assertEqual(data["admin"]["id"], admin.id)
        self.assertEqual(data["admin"]["username"], "admin")
        self.assertTrue(data["admin"]["is_staff"])
        self.assertTrue(data["admin"]["is_backend_manager"])
        self.assertTrue(data["access_token"])
        admin.refresh_from_db()
        self.assertIsNotNone(admin.last_login)

    def test_admin_login_rejects_non_backend_manager(self):
        User.objects.create_user(username="staff", password="admin123456", is_staff=True)

        response = self.client.post(
            "/api/admin/auth/login",
            {"username": "staff", "password": "admin123456"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], 40301)

    def test_admin_me_requires_admin_token(self):
        response = self.client.get("/api/admin/auth/me")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], 40102)

    def test_admin_me_rejects_member_token(self):
        Member.objects.create(openid="member-openid")
        token, _ = issue_token(subject_type="member", openid="member-openid")

        response = self.client.get("/api/admin/auth/me", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], 40301)

    def test_admin_me_rejects_expired_admin_token(self):
        admin = self.create_admin()
        expired_token = auth_module._encode_jwt(
            {
                "subject_type": "admin",
                "user_id": admin.id,
                "iat": 1,
                "exp": 1,
            }
        )

        response = self.client.get("/api/admin/auth/me", HTTP_AUTHORIZATION=f"Bearer {expired_token}")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], 40101)

    def test_admin_me_rejects_disabled_admin(self):
        admin = self.create_admin()
        login = self.admin_login()
        token = login.json()["data"]["access_token"]
        admin.is_active = False
        admin.save(update_fields=["is_active"])

        response = self.client.get("/api/admin/auth/me", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], 40301)

    def test_admin_me_returns_current_admin(self):
        admin = self.create_admin()
        token = self.admin_login().json()["data"]["access_token"]

        response = self.client.get("/api/admin/auth/me", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["id"], admin.id)
        self.assertEqual(data["username"], "admin")
        self.assertTrue(data["is_staff"])
        self.assertTrue(data["is_backend_manager"])

    def test_admin_enums_returns_current_choice_values(self):
        self.create_admin()
        token = self.admin_login().json()["data"]["access_token"]

        response = self.client.get("/api/admin/enums", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertIn({"value": "pending", "label": "待审核"}, data["member_audit_statuses"])
        self.assertIn({"value": "男", "label": "男"}, data["member_genders"])
        self.assertIn({"value": "顺丰快递", "label": "顺丰快递"}, data["member_occupations"])
        self.assertIn({"value": "pending", "label": "待审核"}, data["merchant_audit_statuses"])
        self.assertIn({"value": "article", "label": "图文文章"}, data["learning_content_types"])
        self.assertIn({"value": "safety_hazard", "label": "安全隐患"}, data["report_category_codes"])
        self.assertIn({"value": "merchant_payment", "label": "商户积分支付"}, data["point_source_types"])
        self.assertIn({"value": "processed", "label": "已处理"}, data["merchant_settlement_statuses"])

    def test_admin_dashboard_summary_counts_pending_work(self):
        self.create_admin()
        token = self.admin_login().json()["data"]["access_token"]
        member = Member.objects.create(
            openid="member-openid",
            nickname="测试用户",
            audit_status=Member.AuditStatus.PENDING,
        )
        report = Report.objects.create(member=member, title="路灯坏了")
        CivicFeedback.objects.create(member=member, title="建议", content="内容")
        ProblemFeedback.objects.create(member=member, title="问题", content="内容")
        activity = Activity.objects.create(
            title="活动",
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=2),
        )
        ActivityCheckin.objects.create(member=member, activity=activity)
        relation = ElderCareRelation.objects.create(member=member, elder_name="刘阿姨", elder_address="幸福小区")
        task = ElderServiceTask.objects.create(title="助老任务", relation=relation)
        ElderServiceFeedback.objects.create(member=member, relation=relation, task=task, content="已完成")
        merchant = Merchant.objects.create(openid="merchant-openid", name="便民超市")
        PointRecord.objects.create(
            member=member,
            merchant=merchant,
            amount=-100,
            change_type=PointRecord.ChangeType.EXPENSE,
            source_type=PointRecord.SourceType.MERCHANT_PAYMENT,
            reason="商户支付",
        )
        MerchantSettlement.objects.create(
            merchant=merchant,
            period_type=MerchantSettlement.PeriodType.MONTH,
            period_label="2026-07",
            date_from=timezone.localdate(),
            date_to=timezone.localdate(),
        )
        Report.objects.create(member=member, title="已处理", status=Report.Status.APPROVED)

        response = self.client.get("/api/admin/dashboard/summary", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["data"],
            {
                "total_merchants": 0,
                "total_members": 0,
                "pending_member_audits": 1,
                "pending_merchant_audits": 0,
                "pending_reports": 1,
                "pending_civic_feedbacks": 1,
                "pending_problem_feedbacks": 1,
                "pending_activity_checkins": 1,
                "pending_elder_service_feedbacks": 1,
                "today_merchant_payment_count": 1,
                "today_merchant_payment_points": 100,
                "pending_merchant_settlements": 1,
            },
        )

    def test_admin_dashboard_summary_counts_approved_active_totals(self):
        self.create_admin()
        token = self.admin_login().json()["data"]["access_token"]
        Member.objects.create(openid="approved-member", audit_status=Member.AuditStatus.APPROVED, is_active=True)
        Member.objects.create(openid="disabled-member", audit_status=Member.AuditStatus.APPROVED, is_active=False)
        Member.objects.create(openid="pending-member", audit_status=Member.AuditStatus.PENDING, is_active=True)
        Member.objects.create(
            openid="deleted-member",
            audit_status=Member.AuditStatus.APPROVED,
            is_active=True,
            deleted_at=timezone.now(),
        )
        Merchant.objects.create(openid="approved-merchant", name="有效商户", audit_status=Merchant.AuditStatus.APPROVED, is_active=True)
        Merchant.objects.create(openid="disabled-merchant", name="停用商户", audit_status=Merchant.AuditStatus.APPROVED, is_active=False)
        Merchant.objects.create(openid="pending-merchant", name="待审核商户", audit_status=Merchant.AuditStatus.PENDING, is_active=True)
        Merchant.objects.create(
            openid="deleted-merchant",
            name="已删除商户",
            audit_status=Merchant.AuditStatus.APPROVED,
            is_active=True,
            deleted_at=timezone.now(),
        )

        response = self.client.get("/api/admin/dashboard/summary", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total_members"], 1)
        self.assertEqual(data["total_merchants"], 1)

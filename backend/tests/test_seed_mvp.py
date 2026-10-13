from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.activities.models import Activity, ActivityCheckin, ActivitySignup
from apps.civic_feedbacks.models import CivicFeedback
from apps.elder_services.models import ElderCareRelation, ElderServiceFeedback, ElderServiceTask
from apps.learning.models import LearningContent, LearningRecord
from apps.members.models import Member
from apps.merchants.models import Merchant, MerchantSettlement
from apps.points.models import PointAccount, PointExchangeRule, PointRecord
from apps.problem_feedbacks.models import ProblemFeedback
from apps.reports.models import Report


class SeedMvpCommandTests(TestCase):
    def test_seed_mvp_creates_frontend_dev_accounts_with_business_data(self):
        call_command("seed_mvp", stdout=StringIO())

        member = Member.objects.get(openid="test-openid")
        merchant = Merchant.objects.get(openid="merchant-openid")
        admin = get_user_model().objects.get(username="admin")

        self.assertTrue(admin.is_active)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_backend_manager)
        self.assertTrue(member.is_active)
        self.assertEqual(member.audit_status, Member.AuditStatus.APPROVED)
        self.assertEqual(member.occupation, Member.Occupation.SF)
        self.assertTrue(Member.objects.filter(audit_status=Member.AuditStatus.PENDING).exists())
        self.assertTrue(merchant.is_active)
        self.assertEqual(merchant.audit_status, Merchant.AuditStatus.APPROVED)
        self.assertGreaterEqual(LearningContent.objects.filter(is_active=True).count(), 2)
        self.assertTrue(LearningRecord.objects.filter(member=member, is_completed=True).exists())
        self.assertTrue(Activity.objects.filter(status=Activity.Status.PUBLISHED).exists())
        self.assertTrue(ActivitySignup.objects.filter(member=member).exists())
        self.assertTrue(ActivityCheckin.objects.filter(member=member, status=ActivityCheckin.Status.PENDING).exists())
        self.assertTrue(ElderCareRelation.objects.filter(member=member, is_active=True).exists())
        self.assertTrue(ElderServiceTask.objects.filter(status=ElderServiceTask.Status.PUBLISHED).exists())
        self.assertTrue(ElderServiceFeedback.objects.filter(member=member, status=ElderServiceFeedback.Status.PENDING).exists())
        self.assertTrue(Report.objects.filter(member=member, status=Report.Status.PENDING, image_urls__0__isnull=False).exists())
        self.assertTrue(CivicFeedback.objects.filter(member=member, status=CivicFeedback.Status.SUBMITTED).exists())
        self.assertTrue(ProblemFeedback.objects.filter(member=member, status=ProblemFeedback.Status.SUBMITTED).exists())
        self.assertTrue(MerchantSettlement.objects.filter(merchant=merchant).exists())
        self.assertTrue(PointExchangeRule.objects.filter(points_per_yuan=100, is_active=True).exists())
        self.assertTrue(
            PointRecord.objects.filter(
                member=member,
                source_type=PointRecord.SourceType.MERCHANT_PAYMENT,
                merchant=merchant,
                amount=-100,
            ).exists()
        )
        self.assertGreater(PointAccount.objects.get(member=member).balance, 0)
        self.assertTrue(PointRecord.objects.filter(member=member).exists())

    def test_seed_mvp_is_idempotent_for_frontend_dev_data(self):
        call_command("seed_mvp", stdout=StringIO())
        first_counts = {
            "members": Member.objects.count(),
            "merchants": Merchant.objects.count(),
            "contents": LearningContent.objects.count(),
            "records": LearningRecord.objects.count(),
            "activities": Activity.objects.count(),
            "signups": ActivitySignup.objects.count(),
            "checkins": ActivityCheckin.objects.count(),
            "tasks": ElderServiceTask.objects.count(),
            "relations": ElderCareRelation.objects.count(),
            "feedbacks": ElderServiceFeedback.objects.count(),
            "reports": Report.objects.count(),
            "civic_feedbacks": CivicFeedback.objects.count(),
            "problem_feedbacks": ProblemFeedback.objects.count(),
            "merchant_settlements": MerchantSettlement.objects.count(),
            "exchange_rules": PointExchangeRule.objects.count(),
            "merchant_payments": PointRecord.objects.filter(source_type=PointRecord.SourceType.MERCHANT_PAYMENT).count(),
            "point_records": PointRecord.objects.count(),
        }
        first_balance = PointAccount.objects.get(member__openid="test-openid").balance

        call_command("seed_mvp", stdout=StringIO())

        second_counts = {
            "members": Member.objects.count(),
            "merchants": Merchant.objects.count(),
            "contents": LearningContent.objects.count(),
            "records": LearningRecord.objects.count(),
            "activities": Activity.objects.count(),
            "signups": ActivitySignup.objects.count(),
            "checkins": ActivityCheckin.objects.count(),
            "tasks": ElderServiceTask.objects.count(),
            "relations": ElderCareRelation.objects.count(),
            "feedbacks": ElderServiceFeedback.objects.count(),
            "reports": Report.objects.count(),
            "civic_feedbacks": CivicFeedback.objects.count(),
            "problem_feedbacks": ProblemFeedback.objects.count(),
            "merchant_settlements": MerchantSettlement.objects.count(),
            "exchange_rules": PointExchangeRule.objects.count(),
            "merchant_payments": PointRecord.objects.filter(source_type=PointRecord.SourceType.MERCHANT_PAYMENT).count(),
            "point_records": PointRecord.objects.count(),
        }
        second_balance = PointAccount.objects.get(member__openid="test-openid").balance

        self.assertEqual(second_counts, first_counts)
        self.assertEqual(second_balance, first_balance)

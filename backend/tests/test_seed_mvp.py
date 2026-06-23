from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.activities.models import Activity, ActivityCheckin, ActivitySignup
from apps.elder_services.models import ElderServiceFeedback, ElderServiceTask
from apps.learning.models import LearningContent, LearningRecord
from apps.members.models import Member
from apps.merchants.models import Merchant, MerchantProduct, ProductRedemption
from apps.points.models import PointAccount, PointRecord
from apps.reports.models import Report


class SeedMvpCommandTests(TestCase):
    def test_seed_mvp_creates_frontend_dev_accounts_with_business_data(self):
        call_command("seed_mvp", stdout=StringIO())

        member = Member.objects.get(openid="test-openid")
        merchant = Merchant.objects.get(openid="merchant-openid")

        self.assertTrue(member.is_active)
        self.assertTrue(merchant.is_active)
        self.assertGreaterEqual(LearningContent.objects.filter(is_active=True).count(), 2)
        self.assertTrue(LearningRecord.objects.filter(member=member, is_completed=True).exists())
        self.assertTrue(Activity.objects.filter(status=Activity.Status.PUBLISHED).exists())
        self.assertTrue(ActivitySignup.objects.filter(member=member).exists())
        self.assertTrue(ActivityCheckin.objects.filter(member=member, status=ActivityCheckin.Status.PENDING).exists())
        self.assertTrue(ElderServiceTask.objects.filter(status=ElderServiceTask.Status.PUBLISHED).exists())
        self.assertTrue(ElderServiceFeedback.objects.filter(member=member, status=ElderServiceFeedback.Status.PENDING).exists())
        self.assertTrue(Report.objects.filter(member=member, status=Report.Status.PENDING).exists())
        self.assertGreaterEqual(MerchantProduct.objects.filter(merchant=merchant, is_active=True).count(), 2)
        self.assertTrue(ProductRedemption.objects.filter(merchant=merchant, member=member, status=ProductRedemption.Status.PENDING).exists())
        self.assertTrue(ProductRedemption.objects.filter(merchant=merchant, member=member, status=ProductRedemption.Status.COMPLETED).exists())
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
            "feedbacks": ElderServiceFeedback.objects.count(),
            "reports": Report.objects.count(),
            "products": MerchantProduct.objects.count(),
            "redemptions": ProductRedemption.objects.count(),
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
            "feedbacks": ElderServiceFeedback.objects.count(),
            "reports": Report.objects.count(),
            "products": MerchantProduct.objects.count(),
            "redemptions": ProductRedemption.objects.count(),
            "point_records": PointRecord.objects.count(),
        }
        second_balance = PointAccount.objects.get(member__openid="test-openid").balance

        self.assertEqual(second_counts, first_counts)
        self.assertEqual(second_balance, first_balance)

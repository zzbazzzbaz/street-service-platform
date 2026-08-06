from django.test import TestCase
from django.utils import timezone

from apps.activities.models import Activity
from apps.merchants.models import Merchant
from tests.helpers import admin_auth_header, create_admin_user, create_member, auth_header


class CoordinateModelTests(TestCase):
    def test_activity_has_nullable_latitude_longitude(self):
        activity = Activity.objects.create(
            title="测试活动",
            body="",
            location="社区中心",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            points=0,
            status="draft",
        )
        self.assertIsNone(activity.latitude)
        self.assertIsNone(activity.longitude)

    def test_merchant_has_nullable_latitude_longitude(self):
        merchant = Merchant.objects.create(
            openid="test-merchant-coords",
            name="测试商户",
        )
        self.assertIsNone(merchant.latitude)
        self.assertIsNone(merchant.longitude)

    def test_activity_can_store_coordinates(self):
        activity = Activity.objects.create(
            title="坐标活动",
            body="",
            location="天安门",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            points=0,
            status="draft",
            latitude=39.908823,
            longitude=116.397470,
        )
        activity.refresh_from_db()
        self.assertAlmostEqual(activity.latitude, 39.908823, places=6)
        self.assertAlmostEqual(activity.longitude, 116.397470, places=6)

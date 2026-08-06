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


class AdminActivityCoordinateTests(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.headers = admin_auth_header(self.admin)
        self.start = timezone.now() + timezone.timedelta(days=1)

    def _create_activity(self, extra=None):
        payload = {
            "title": "坐标活动",
            "body": "",
            "location": "天安门",
            "start_time": self.start.isoformat(),
            "end_time": (self.start + timezone.timedelta(hours=2)).isoformat(),
            "points": 0,
            "status": "draft",
        }
        if extra:
            payload.update(extra)
        return self.client.post("/api/admin/activities", payload, content_type="application/json", **self.headers)

    def test_admin_create_activity_with_coordinates(self):
        response = self._create_activity({"latitude": 39.908823, "longitude": 116.397470})
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertAlmostEqual(data["latitude"], 39.908823, places=6)
        self.assertAlmostEqual(data["longitude"], 116.397470, places=6)

    def test_admin_create_activity_without_coordinates_returns_null(self):
        response = self._create_activity()
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertIsNone(data["latitude"])
        self.assertIsNone(data["longitude"])

    def test_admin_create_activity_rejects_latitude_only(self):
        response = self._create_activity({"latitude": 39.908823})
        self.assertEqual(response.status_code, 400)
        self.assertIn("同时", response.json()["message"])

    def test_admin_create_activity_rejects_invalid_latitude_range(self):
        response = self._create_activity({"latitude": 91, "longitude": 116})
        self.assertEqual(response.status_code, 400)
        self.assertIn("纬度", response.json()["message"])

    def test_admin_create_activity_rejects_invalid_longitude_range(self):
        response = self._create_activity({"latitude": 39, "longitude": 181})
        self.assertEqual(response.status_code, 400)
        self.assertIn("经度", response.json()["message"])

    def test_admin_patch_activity_updates_coordinates(self):
        create_resp = self._create_activity()
        activity_id = create_resp.json()["data"]["id"]
        patch_resp = self.client.patch(
            f"/api/admin/activities/{activity_id}",
            {"latitude": 39.908823, "longitude": 116.397470},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(patch_resp.status_code, 200)
        data = patch_resp.json()["data"]
        self.assertAlmostEqual(data["latitude"], 39.908823, places=6)
        self.assertAlmostEqual(data["longitude"], 116.397470, places=6)

    def test_admin_patch_activity_rejects_single_coordinate(self):
        create_resp = self._create_activity()
        activity_id = create_resp.json()["data"]["id"]
        patch_resp = self.client.patch(
            f"/api/admin/activities/{activity_id}",
            {"latitude": 39.9},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(patch_resp.status_code, 400)

    def test_admin_activity_detail_returns_coordinates(self):
        create_resp = self._create_activity({"latitude": 39.908823, "longitude": 116.397470})
        activity_id = create_resp.json()["data"]["id"]
        detail_resp = self.client.get(f"/api/admin/activities/{activity_id}", **self.headers)
        self.assertEqual(detail_resp.status_code, 200)
        data = detail_resp.json()["data"]
        self.assertAlmostEqual(data["latitude"], 39.908823, places=6)
        self.assertAlmostEqual(data["longitude"], 116.397470, places=6)

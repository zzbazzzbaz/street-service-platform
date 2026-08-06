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


class AdminMerchantCoordinateTests(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.headers = admin_auth_header(self.admin)

    def test_admin_create_merchant_with_coordinates(self):
        response = self.client.post(
            "/api/admin/merchants",
            {"name": "带坐标商户", "address": "天安门", "latitude": 39.908823, "longitude": 116.397470, "is_active": True},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertAlmostEqual(data["latitude"], 39.908823, places=6)
        self.assertAlmostEqual(data["longitude"], 116.397470, places=6)

    def test_admin_create_merchant_without_coordinates_returns_null(self):
        response = self.client.post(
            "/api/admin/merchants",
            {"name": "无坐标商户", "is_active": True},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertIsNone(data["latitude"])
        self.assertIsNone(data["longitude"])

    def test_admin_create_merchant_rejects_latitude_only(self):
        response = self.client.post(
            "/api/admin/merchants",
            {"name": "半坐标商户", "latitude": 39.9},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("同时", response.json()["message"])

    def test_admin_create_merchant_rejects_invalid_range(self):
        response = self.client.post(
            "/api/admin/merchants",
            {"name": "超范围商户", "latitude": 91, "longitude": 116},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_patch_merchant_updates_coordinates(self):
        create_resp = self.client.post(
            "/api/admin/merchants",
            {"name": "PATCH商户", "is_active": True},
            content_type="application/json",
            **self.headers,
        )
        merchant_id = create_resp.json()["data"]["id"]
        patch_resp = self.client.patch(
            f"/api/admin/merchants/{merchant_id}",
            {"latitude": 39.908823, "longitude": 116.397470},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(patch_resp.status_code, 200)
        data = patch_resp.json()["data"]
        self.assertAlmostEqual(data["latitude"], 39.908823, places=6)

    def test_admin_patch_merchant_rejects_single_coordinate(self):
        create_resp = self.client.post(
            "/api/admin/merchants",
            {"name": "PATCH校验商户", "is_active": True},
            content_type="application/json",
            **self.headers,
        )
        merchant_id = create_resp.json()["data"]["id"]
        patch_resp = self.client.patch(
            f"/api/admin/merchants/{merchant_id}",
            {"longitude": 116.4},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(patch_resp.status_code, 400)

    def test_admin_merchant_detail_returns_coordinates(self):
        create_resp = self.client.post(
            "/api/admin/merchants",
            {"name": "详情商户", "address": "天安门", "latitude": 39.908823, "longitude": 116.397470, "is_active": True},
            content_type="application/json",
            **self.headers,
        )
        merchant_id = create_resp.json()["data"]["id"]
        detail_resp = self.client.get(f"/api/admin/merchants/{merchant_id}", **self.headers)
        self.assertEqual(detail_resp.status_code, 200)
        data = detail_resp.json()["data"]
        self.assertAlmostEqual(data["latitude"], 39.908823, places=6)


class UserActivityCoordinateTests(TestCase):
    def setUp(self):
        self.member = create_member()
        self.headers = auth_header("member", self.member.openid)
        self.activity = Activity.objects.create(
            title="坐标活动",
            body="",
            location="天安门",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            points=0,
            status=Activity.Status.PUBLISHED,
            latitude=39.908823,
            longitude=116.397470,
        )
        self.activity_no_coords = Activity.objects.create(
            title="无坐标活动",
            body="",
            location="某地",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            points=0,
            status=Activity.Status.PUBLISHED,
        )

    def test_activity_list_returns_coordinates(self):
        response = self.client.get("/api/activities", **self.headers)
        self.assertEqual(response.status_code, 200)
        items = response.json()["data"]["items"]
        coord_item = next(i for i in items if i["id"] == self.activity.id)
        self.assertAlmostEqual(coord_item["latitude"], 39.908823, places=6)
        self.assertAlmostEqual(coord_item["longitude"], 116.397470, places=6)
        no_coord_item = next(i for i in items if i["id"] == self.activity_no_coords.id)
        self.assertIsNone(no_coord_item["latitude"])
        self.assertIsNone(no_coord_item["longitude"])

    def test_activity_detail_returns_coordinates(self):
        response = self.client.get(f"/api/activities/{self.activity.id}", **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertAlmostEqual(data["latitude"], 39.908823, places=6)
        self.assertAlmostEqual(data["longitude"], 116.397470, places=6)

    def test_activity_detail_returns_null_when_no_coordinates(self):
        response = self.client.get(f"/api/activities/{self.activity_no_coords.id}", **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertIsNone(data["latitude"])
        self.assertIsNone(data["longitude"])

    def test_my_signups_returns_coordinates(self):
        from apps.activities.services import signup_activity
        signup_activity(self.member, self.activity)
        response = self.client.get("/api/activities/my-signups", **self.headers)
        self.assertEqual(response.status_code, 200)
        item = response.json()["data"]["items"][0]
        self.assertAlmostEqual(item["latitude"], 39.908823, places=6)
        self.assertAlmostEqual(item["longitude"], 116.397470, places=6)


class UserMerchantCoordinateTests(TestCase):
    def setUp(self):
        self.member = create_member()
        self.headers = auth_header("member", self.member.openid)
        self.merchant = Merchant.objects.create(
            openid="merchant-with-coords",
            name="坐标商户",
            address="天安门",
            latitude=39.908823,
            longitude=116.397470,
            is_active=True,
        )
        self.merchant_no_coords = Merchant.objects.create(
            openid="merchant-no-coords",
            name="无坐标商户",
            is_active=True,
        )

    def test_public_merchant_list_returns_coordinates(self):
        response = self.client.get("/api/merchants", **self.headers)
        self.assertEqual(response.status_code, 200)
        items = response.json()["data"]["items"]
        coord_item = next(i for i in items if i["id"] == self.merchant.id)
        self.assertAlmostEqual(coord_item["latitude"], 39.908823, places=6)
        self.assertAlmostEqual(coord_item["longitude"], 116.397470, places=6)
        no_coord_item = next(i for i in items if i["id"] == self.merchant_no_coords.id)
        self.assertIsNone(no_coord_item["latitude"])
        self.assertIsNone(no_coord_item["longitude"])

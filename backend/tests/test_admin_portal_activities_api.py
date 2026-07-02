from django.test import TestCase
from django.utils import timezone

from apps.activities.models import Activity, ActivityCheckin, ActivitySignup
from apps.points.models import PointAccount
from tests.helpers import admin_auth_header, create_admin_user, create_member


class AdminPortalActivitiesApiTests(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.headers = admin_auth_header(self.admin)
        self.member = create_member()

    def test_activity_management_signup_views_and_checkin_review(self):
        start = timezone.now() + timezone.timedelta(days=1)
        create_response = self.client.post(
            "/api/admin/activities",
            {
                "title": "志愿活动",
                "body": "<p>说明</p>",
                "location": "社区中心",
                "start_time": start.isoformat(),
                "end_time": (start + timezone.timedelta(hours=2)).isoformat(),
                "points": 9,
                "status": "draft",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(create_response.status_code, 200)
        activity_id = create_response.json()["data"]["id"]
        activity = Activity.objects.get(pk=activity_id)
        signup = ActivitySignup.objects.create(member=self.member, activity=activity)
        checkin = ActivityCheckin.objects.create(member=self.member, activity=activity)

        code_response = self.client.get(f"/api/admin/activities/{activity_id}/checkin-code", **self.headers)
        status_response = self.client.post(
            f"/api/admin/activities/{activity_id}/status",
            {"status": "published"},
            content_type="application/json",
            **self.headers,
        )
        signup_detail = self.client.get(f"/api/admin/activities/signups/{signup.id}", **self.headers)
        checkin_confirm = self.client.post(
            f"/api/admin/activities/checkins/{checkin.id}/review",
            {"action": "confirm", "comment": ""},
            content_type="application/json",
            **self.headers,
        )
        repeat = self.client.post(
            f"/api/admin/activities/checkins/{checkin.id}/review",
            {"action": "confirm", "comment": ""},
            content_type="application/json",
            **self.headers,
        )
        delete_response = self.client.delete(f"/api/admin/activities/{activity_id}", **self.headers)

        self.assertEqual(code_response.status_code, 200)
        self.assertTrue(code_response.json()["data"]["checkin_code"])
        self.assertIn("checkin_qr_image", code_response.json()["data"])
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(signup_detail.status_code, 200)
        self.assertEqual(signup_detail.json()["data"]["member_id"], self.member.id)
        self.assertEqual(checkin_confirm.status_code, 200)
        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 9)
        self.assertEqual(repeat.status_code, 400)
        self.assertEqual(delete_response.status_code, 400)

    def test_activity_create_rejects_invalid_time_range(self):
        now = timezone.now()
        response = self.client.post(
            "/api/admin/activities",
            {"title": "错误活动", "start_time": now.isoformat(), "end_time": now.isoformat(), "points": 1},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)

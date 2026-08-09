from django.test import TestCase
from django.utils import timezone

from apps.activities.models import Activity
from tests.helpers import admin_auth_header, auth_header, create_admin_user, create_member


class ActivityTypeFieldTests(TestCase):
    def test_activity_has_activity_type_default(self):
        activity = Activity.objects.create(
            title="社区志愿活动",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
        )
        self.assertEqual(activity.activity_type, Activity.ActivityType.VOLUNTEER)
        self.assertIn("offline", [v for v, _ in Activity.ActivityType.choices])


class ActivityTypeApiTests(TestCase):
    def setUp(self):
        self.member = create_member(openid="atype-member")
        self.member_headers = auth_header("member", self.member.openid)
        self.admin_headers = admin_auth_header(create_admin_user())
        now = timezone.now()
        Activity.objects.create(
            title="线下活动", activity_type="offline", status=Activity.Status.PUBLISHED,
            start_time=now, end_time=now + timezone.timedelta(hours=1),
        )
        Activity.objects.create(
            title="志愿任务", activity_type="volunteer", status=Activity.Status.PUBLISHED,
            start_time=now, end_time=now + timezone.timedelta(hours=2),
        )

    def test_activity_list_returns_and_filters_activity_type(self):
        all_resp = self.client.get("/api/activities", **self.member_headers)
        self.assertEqual(all_resp.status_code, 200)
        self.assertEqual(all_resp.json()["data"]["total"], 2)
        self.assertIn("activity_type", all_resp.json()["data"]["items"][0])

        offline_resp = self.client.get("/api/activities?activity_type=offline", **self.member_headers)
        self.assertEqual(offline_resp.json()["data"]["total"], 1)
        self.assertEqual(offline_resp.json()["data"]["items"][0]["activity_type"], "offline")

    def test_admin_create_activity_with_type(self):
        now = timezone.now()
        response = self.client.post(
            "/api/admin/activities",
            {
                "title": "新建线下活动",
                "activity_type": "offline",
                "start_time": now.isoformat(),
                "end_time": (now + timezone.timedelta(hours=1)).isoformat(),
            },
            content_type="application/json",
            **self.admin_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["activity_type"], "offline")


class ActivityEndedSignupTests(TestCase):
    def test_cannot_signup_ended_activity(self):
        member = create_member(openid="ended-member")
        headers = auth_header("member", member.openid)
        now = timezone.now()
        activity = Activity.objects.create(
            title="已结束活动", activity_type="volunteer", status=Activity.Status.PUBLISHED,
            start_time=now - timezone.timedelta(hours=2),
            end_time=now - timezone.timedelta(hours=1),
        )
        response = self.client.post(f"/api/activities/{activity.id}/signup", **headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("结束", response.json()["message"])
        self.assertFalse(activity.signups.exists())

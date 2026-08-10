from django.test import TestCase
from django.utils import timezone

from apps.activities.models import Activity, ActivityCheckin, ActivitySignup
from tests.helpers import admin_auth_header, auth_header, create_admin_user, create_member


def _make_activity(title, activity_type, **kwargs):
    now = timezone.now()
    defaults = {
        "activity_type": activity_type,
        "status": Activity.Status.PUBLISHED,
        "start_time": now,
        "end_time": now + timezone.timedelta(days=1),
    }
    defaults.update(kwargs)
    return Activity.objects.create(title=title, **defaults)


class MySignupsFilterTests(TestCase):
    def setUp(self):
        self.member = create_member(openid="ms-filter")
        self.headers = auth_header("member", self.member.openid)
        self.vol = _make_activity("志愿任务", "volunteer")
        self.off = _make_activity("线下活动", "offline")
        ActivitySignup.objects.create(member=self.member, activity=self.vol)
        ActivitySignup.objects.create(member=self.member, activity=self.off)

    def test_my_signups_filters_by_activity_type(self):
        off_resp = self.client.get("/api/activities/my-signups?activity_type=offline", **self.headers)
        self.assertEqual(off_resp.status_code, 200)
        data = off_resp.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["activity_type"], "offline")
        self.assertEqual(data["items"][0]["title"], "线下活动")

        vol_resp = self.client.get("/api/activities/my-signups?activity_type=volunteer", **self.headers)
        self.assertEqual(vol_resp.json()["data"]["total"], 1)
        self.assertEqual(vol_resp.json()["data"]["items"][0]["activity_type"], "volunteer")


class CheckinResponseTypeTests(TestCase):
    def test_checkin_response_returns_activity_type(self):
        member = create_member(openid="chk-type")
        headers = auth_header("member", member.openid)
        activity = _make_activity("线下活动", "offline")
        ActivitySignup.objects.create(member=member, activity=activity)
        response = self.client.post(
            f"/api/activities/{activity.id}/checkin",
            {"checkin_code": activity.checkin_code},
            content_type="application/json",
            **headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["activity_type"], "offline")


class AdminActivitiesFilterTests(TestCase):
    def setUp(self):
        self.headers = admin_auth_header(create_admin_user())
        _make_activity("志愿任务", "volunteer")
        _make_activity("线下活动", "offline")

    def test_admin_activities_filters_by_activity_type(self):
        resp = self.client.get("/api/admin/activities?activity_type=offline", **self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["activity_type"], "offline")


class AdminSignupsAndCheckinsFilterTests(TestCase):
    def setUp(self):
        self.headers = admin_auth_header(create_admin_user())
        self.member = create_member(openid="adm-sc", real_name="张三", phone="13800001234")
        self.vol = _make_activity("志愿任务", "volunteer")
        self.off = _make_activity("线下活动", "offline")
        ActivitySignup.objects.create(member=self.member, activity=self.vol)
        ActivitySignup.objects.create(member=self.member, activity=self.off)

    def test_admin_signups_filters_and_returns_type_and_member(self):
        resp = self.client.get("/api/admin/activities/signups?activity_type=offline", **self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual(data["total"], 1)
        item = data["items"][0]
        self.assertEqual(item["activity_type"], "offline")
        self.assertEqual(item["member_id"], self.member.id)
        self.assertEqual(item["member_name"], "张三")
        self.assertEqual(item["member_phone"], "138****1234")

    def test_admin_checkins_filters_and_returns_type_and_member(self):
        ActivityCheckin.objects.create(member=self.member, activity=self.off)
        resp = self.client.get("/api/admin/activities/checkins?activity_type=offline", **self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual(data["total"], 1)
        item = data["items"][0]
        self.assertEqual(item["activity_type"], "offline")
        self.assertEqual(item["activity_title"], "线下活动")
        self.assertEqual(item["member_id"], self.member.id)
        self.assertEqual(item["member_name"], "张三")


class BlockActivityTypeChangeTests(TestCase):
    def test_cannot_change_activity_type_when_signups_exist(self):
        admin_headers = admin_auth_header(create_admin_user())
        member = create_member(openid="blk-type")
        activity = _make_activity("志愿任务", "volunteer")
        ActivitySignup.objects.create(member=member, activity=activity)
        response = self.client.patch(
            f"/api/admin/activities/{activity.id}",
            {"activity_type": "offline"},
            content_type="application/json",
            **admin_headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("类型", response.json()["message"])

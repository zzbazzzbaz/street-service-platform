from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.activities.models import Activity, ActivityCheckin, ActivitySignup
from apps.activities.services import checkin_activity, review_checkin, signup_activity
from apps.points.models import PointAccount, PointRecord
from shared.exceptions import BusinessError
from tests.helpers import auth_header, create_member


class ActivitiesFlowTests(TestCase):
    def setUp(self):
        self.member = create_member()
        self.operator = get_user_model().objects.create_user(
            username="manager",
            password="password",
            is_backend_manager=True,
        )
        self.activity = Activity.objects.create(
            title="社区活动",
            body="活动正文",
            location="社区中心",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            points=6,
            status=Activity.Status.PUBLISHED,
        )

    def test_activity_generates_checkin_code_and_qr_image(self):
        self.activity.refresh_from_db()

        self.assertTrue(self.activity.checkin_code)
        self.assertTrue(self.activity.checkin_qr_image)

    def test_signup_rejects_duplicate(self):
        signup_activity(self.member, self.activity)

        with self.assertRaisesRegex(BusinessError, "重复报名"):
            signup_activity(self.member, self.activity)

        self.assertEqual(ActivitySignup.objects.count(), 1)

    def test_checkin_requires_signup_and_correct_code(self):
        with self.assertRaisesRegex(BusinessError, "未报名"):
            checkin_activity(self.member, self.activity, checkin_code=self.activity.checkin_code)

        signup_activity(self.member, self.activity)

        with self.assertRaisesRegex(BusinessError, "签到码"):
            checkin_activity(self.member, self.activity, checkin_code="bad-code")

    def test_checkin_review_awards_points_once(self):
        signup_activity(self.member, self.activity)
        checkin = checkin_activity(self.member, self.activity, checkin_code=self.activity.checkin_code)

        with self.assertRaisesRegex(BusinessError, "重复签到"):
            checkin_activity(self.member, self.activity, checkin_code=self.activity.checkin_code)

        review_checkin(checkin, action="confirm", comment="", operator=self.operator)

        self.assertEqual(ActivityCheckin.objects.get(pk=checkin.pk).status, ActivityCheckin.Status.CONFIRMED)
        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 6)
        self.assertEqual(PointRecord.objects.filter(source_type=PointRecord.SourceType.ACTIVITY).count(), 1)

        with self.assertRaisesRegex(BusinessError, "已审核"):
            review_checkin(checkin, action="confirm", comment="", operator=self.operator)

    def test_activity_api_signup_and_checkin(self):
        headers = auth_header("member", self.member.openid)

        list_response = self.client.get("/api/activities", **headers)
        detail_response = self.client.get(f"/api/activities/{self.activity.id}", **headers)
        signup_response = self.client.post(f"/api/activities/{self.activity.id}/signup", {}, content_type="application/json", **headers)
        checkin_response = self.client.post(
            f"/api/activities/{self.activity.id}/checkin",
            {"checkin_code": self.activity.checkin_code},
            content_type="application/json",
            **headers,
        )
        my_signups_response = self.client.get("/api/activities/my-signups", **headers)

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertNotIn("checkin_code", list_response.json()["data"]["items"][0])
        self.assertNotIn("checkin_qr_image", detail_response.json()["data"])
        self.assertEqual(signup_response.status_code, 200)
        self.assertEqual(checkin_response.status_code, 200)
        self.assertEqual(my_signups_response.status_code, 200)
        self.assertEqual(my_signups_response.json()["data"]["total"], 1)
        self.assertEqual(ActivityCheckin.objects.count(), 1)

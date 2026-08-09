from django.test import TestCase
from django.utils import timezone

from apps.activities.models import Activity, ActivitySignup
from apps.reports.models import Report
from tests.helpers import auth_header, create_member


class ServiceRecordsApiTests(TestCase):
    def setUp(self):
        self.member = create_member(openid="sr-member")
        self.headers = auth_header("member", self.member.openid)
        self.report = Report.objects.create(member=self.member, category_code="safety_hazard", location="地点A", image_urls=["/a.jpg"])
        now = timezone.now()
        self.activity = Activity.objects.create(
            title="志愿任务", activity_type="volunteer", status=Activity.Status.PUBLISHED,
            start_time=now, end_time=now + timezone.timedelta(hours=1),
        )
        self.signup = ActivitySignup.objects.create(member=self.member, activity=self.activity)

    def test_list_returns_merged_timeline(self):
        response = self.client.get("/api/service-records", **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 2)
        types = {item["record_type"] for item in data["items"]}
        self.assertEqual(types, {"report", "activity_signup"})
        item = next(i for i in data["items"] if i["record_type"] == "report")
        self.assertEqual(item["source_id"], self.report.id)
        self.assertEqual(item["status"], "pending")
        self.assertIn("status_label", item)
        self.assertIn("occurred_at", item)

    def test_list_only_returns_own_records(self):
        other = create_member(openid="sr-other")
        Report.objects.create(member=other, category_code="safety_hazard", location="别人", image_urls=["/o.jpg"])
        response = self.client.get("/api/service-records", **self.headers)
        self.assertEqual(response.json()["data"]["total"], 2)

    def test_detail_returns_full_content_and_ownership_check(self):
        resp = self.client.get(f"/api/service-records/report/{self.report.id}", **self.headers)
        self.assertEqual(resp.status_code, 200)
        detail = resp.json()["data"]
        self.assertEqual(detail["record_type"], "report")
        self.assertEqual(detail["source_id"], self.report.id)
        self.assertEqual(detail["image_urls"], ["/a.jpg"])

        other = create_member(openid="sr-owner-check")
        other_headers = auth_header("member", other.openid)
        forbidden = self.client.get(f"/api/service-records/report/{self.report.id}", **other_headers)
        self.assertEqual(forbidden.status_code, 404)

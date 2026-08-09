from django.test import TestCase

from apps.reports.models import Report
from tests.helpers import auth_header, create_member


class ReportCategoryEnumTests(TestCase):
    def test_enum_contains_good_deed(self):
        self.assertIn("good_deed", [v for v, _ in Report.CategoryCode.choices])
        self.assertIn("safety_hazard", [v for v, _ in Report.CategoryCode.choices])


class ReportTypeFilterApiTests(TestCase):
    def setUp(self):
        self.member = create_member(openid="rt-member")
        self.headers = auth_header("member", self.member.openid)
        Report.objects.create(member=self.member, category_code="safety_hazard", location="地点A", image_urls=["/a.jpg"])
        Report.objects.create(member=self.member, category_code="good_deed", location="地点B", image_urls=["/b.jpg"])

    def test_report_type_filter(self):
        all_resp = self.client.get("/api/reports", **self.headers)
        self.assertEqual(all_resp.json()["data"]["total"], 2)

        report_resp = self.client.get("/api/reports?report_type=report", **self.headers)
        self.assertEqual(report_resp.json()["data"]["total"], 1)
        self.assertEqual(report_resp.json()["data"]["items"][0]["category_code"], "safety_hazard")

        deed_resp = self.client.get("/api/reports?report_type=good_deed", **self.headers)
        self.assertEqual(deed_resp.json()["data"]["total"], 1)
        self.assertEqual(deed_resp.json()["data"]["items"][0]["category_code"], "good_deed")

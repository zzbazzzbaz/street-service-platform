from django.test import TestCase

from apps.members.models import Member
from apps.reports.models import Report
from tests.helpers import auth_header, create_member


class ReportsApiTests(TestCase):
    def test_approved_member_submits_report_with_category_and_images(self):
        member = create_member(audit_status=Member.AuditStatus.APPROVED)

        response = self.client.post(
            "/api/reports",
            {
                "category_code": "safety_hazard",
                "description": "路口路灯夜间不亮",
                "location": "椿树街道东口",
                "image_urls": ["https://example.com/media/uploads/report/a.png"],
            },
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["category_code"], "safety_hazard")
        self.assertEqual(data["title"], "安全隐患")
        self.assertEqual(data["image_urls"], ["https://example.com/media/uploads/report/a.png"])
        self.assertNotIn("image", data)
        report = Report.objects.get(pk=data["id"])
        self.assertEqual(report.title, "安全隐患")

    def test_unapproved_member_cannot_submit_report(self):
        member = create_member(audit_status=Member.AuditStatus.PENDING)

        response = self.client.post(
            "/api/reports",
            {
                "category_code": "safety_hazard",
                "location": "椿树街道东口",
                "image_urls": ["https://example.com/a.png"],
            },
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], 40301)

    def test_report_requires_backend_category_and_one_to_ten_images(self):
        member = create_member(audit_status=Member.AuditStatus.APPROVED)

        invalid_category = self.client.post(
            "/api/reports",
            {"category_code": "frontend_only", "location": "路口", "image_urls": ["https://example.com/a.png"]},
            content_type="application/json",
            **auth_header("member", member.openid),
        )
        too_many_images = self.client.post(
            "/api/reports",
            {
                "category_code": "other",
                "location": "路口",
                "image_urls": [f"https://example.com/{index}.png" for index in range(11)],
            },
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(invalid_category.status_code, 400)
        self.assertIn("分类", invalid_category.json()["message"])
        self.assertEqual(too_many_images.status_code, 400)
        self.assertIn("图片", too_many_images.json()["message"])

    def test_report_list_filters_status_and_only_returns_current_member(self):
        member = create_member(openid="member-openid", audit_status=Member.AuditStatus.APPROVED)
        other = create_member(openid="other-openid", audit_status=Member.AuditStatus.APPROVED)
        my_pending = Report.objects.create(
            member=member,
            category_code=Report.CategoryCode.SAFETY_HAZARD,
            title="安全隐患",
            location="路口",
            image_urls=["https://example.com/a.png"],
        )
        Report.objects.create(
            member=member,
            category_code=Report.CategoryCode.OTHER,
            title="其他",
            status=Report.Status.REJECTED,
            location="路口",
            image_urls=["https://example.com/b.png"],
        )
        Report.objects.create(
            member=other,
            category_code=Report.CategoryCode.SAFETY_HAZARD,
            title="安全隐患",
            location="路口",
            image_urls=["https://example.com/c.png"],
        )

        response = self.client.get(
            "/api/reports",
            {"status": "pending"},
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["id"], my_pending.id)
        self.assertEqual(data["items"][0]["category_code"], "safety_hazard")

from django.test import TestCase

from apps.members.models import Member
from apps.reports.models import Report
from tests.helpers import auth_header, create_member


class MemberAuditGateApiTests(TestCase):
    def test_pending_member_is_blocked_from_report_civic_and_problem_feedback(self):
        member = create_member(audit_status=Member.AuditStatus.PENDING)
        headers = auth_header("member", member.openid)

        report_response = self.client.post(
            "/api/reports",
            {"category_code": "safety_hazard", "location": "示例街道东口"},
            content_type="application/json",
            **headers,
        )
        civic_response = self.client.post(
            "/api/civic-feedbacks",
            {"title": "建议", "content": "内容"},
            content_type="application/json",
            **headers,
        )
        problem_response = self.client.post(
            "/api/problem-feedbacks",
            {"title": "问题", "content": "内容"},
            content_type="application/json",
            **headers,
        )

        for response in (report_response, civic_response, problem_response):
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["message"], "当前用户资料未审核通过")
        self.assertFalse(Report.objects.filter(member=member).exists())

    def test_pending_member_cannot_submit_elder_task_feedback(self):
        member = create_member(audit_status=Member.AuditStatus.PENDING)

        response = self.client.post(
            "/api/elder-services/tasks/1/feedback",
            {"content": "已完成"},
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["message"], "当前用户资料未审核通过")

    def test_pending_member_keeps_basic_features(self):
        member = create_member(audit_status=Member.AuditStatus.PENDING)
        headers = auth_header("member", member.openid)

        points_response = self.client.get("/api/points/balance", **headers)
        learning_response = self.client.get("/api/learning/contents", **headers)
        merchants_response = self.client.get("/api/merchants", **headers)

        self.assertEqual(points_response.status_code, 200)
        self.assertEqual(learning_response.status_code, 200)
        self.assertEqual(merchants_response.status_code, 200)

    def test_approved_member_can_submit_report(self):
        member = create_member(audit_status=Member.AuditStatus.APPROVED)

        response = self.client.post(
            "/api/reports",
            {
                "category_code": "safety_hazard",
                "description": "路口路灯夜间不亮",
                "location": "示例街道东口",
                "image_urls": ["https://example.com/a.png"],
            },
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 200)

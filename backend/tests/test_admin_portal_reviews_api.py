from django.test import TestCase

from apps.civic_feedbacks.models import CivicFeedback
from apps.points.models import PointAccount, PointRecord
from apps.problem_feedbacks.models import ProblemFeedback
from apps.reports.models import Report
from tests.helpers import admin_auth_header, create_admin_user, create_member


class AdminPortalReviewsApiTests(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.headers = admin_auth_header(self.admin)
        self.member = create_member(real_name="李明")

    def test_report_review_uses_service_and_records_operator(self):
        report = Report.objects.create(member=self.member, title="路灯坏了", points=6)

        list_response = self.client.get("/api/admin/reports?keyword=李明&status=pending", **self.headers)
        update_response = self.client.patch(
            f"/api/admin/reports/{report.id}",
            {"category_code": "safety_hazard", "description": "补充描述", "location": "小区门口", "points": 6, "image_urls": ["https://example.com/a.png"]},
            content_type="application/json",
            **self.headers,
        )
        approve_response = self.client.post(
            f"/api/admin/reports/{report.id}/review",
            {"action": "approve", "comment": ""},
            content_type="application/json",
            **self.headers,
        )
        repeat_response = self.client.post(
            f"/api/admin/reports/{report.id}/review",
            {"action": "approve", "comment": ""},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["data"]["total"], 1)
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(approve_response.status_code, 200)
        record = PointRecord.objects.get(source_type=PointRecord.SourceType.REPORT)
        self.assertEqual(record.operator_id, self.admin.id)
        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 6)
        self.assertEqual(repeat_response.status_code, 400)

    def test_civic_feedback_review_and_problem_feedback_reply_status(self):
        civic = CivicFeedback.objects.create(member=self.member, title="建议", content="内容")
        problem = ProblemFeedback.objects.create(member=self.member, title="问题", content="内容")

        civic_update = self.client.patch(
            f"/api/admin/civic-feedbacks/{civic.id}",
            {"title": "建议更新", "content": "内容更新", "points": 5, "material_urls": ["https://example.com/m.png"]},
            content_type="application/json",
            **self.headers,
        )
        civic_accept = self.client.post(
            f"/api/admin/civic-feedbacks/{civic.id}/review",
            {"action": "accept", "reply": "已采纳", "points": 5},
            content_type="application/json",
            **self.headers,
        )
        civic_repeat = self.client.post(
            f"/api/admin/civic-feedbacks/{civic.id}/review",
            {"action": "accept", "reply": "再次采纳", "points": 5},
            content_type="application/json",
            **self.headers,
        )
        status_without_reply = self.client.post(
            f"/api/admin/problem-feedbacks/{problem.id}/status",
            {"status": "replied"},
            content_type="application/json",
            **self.headers,
        )
        reply_response = self.client.post(
            f"/api/admin/problem-feedbacks/{problem.id}/reply",
            {"reply": "已收到"},
            content_type="application/json",
            **self.headers,
        )
        close_response = self.client.post(
            f"/api/admin/problem-feedbacks/{problem.id}/status",
            {"status": "closed"},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(civic_update.status_code, 200)
        self.assertEqual(civic_accept.status_code, 200)
        self.assertEqual(civic_repeat.status_code, 400)
        self.assertEqual(PointRecord.objects.filter(source_type=PointRecord.SourceType.CIVIC_FEEDBACK).count(), 1)
        self.assertEqual(status_without_reply.status_code, 400)
        self.assertEqual(reply_response.status_code, 200)
        self.assertIsNotNone(reply_response.json()["data"]["replied_at"])
        self.assertEqual(close_response.status_code, 200)
        self.assertEqual(close_response.json()["data"]["status"], "closed")

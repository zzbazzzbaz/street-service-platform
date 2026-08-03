from django.test import TestCase

from apps.members.models import Member
from apps.problem_feedbacks.models import ProblemFeedback
from tests.helpers import admin_auth_header, create_admin_user, create_member


class AdminVisibilityReviewApiTests(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.headers = admin_auth_header(self.admin)
        self.member = create_member(audit_status=Member.AuditStatus.APPROVED)
        self.feedback = ProblemFeedback.objects.create(
            member=self.member, title="测试", content="内容",
        )

    def test_approve_visibility(self):
        response = self.client.post(
            f"/api/admin/problem-feedbacks/{self.feedback.id}/visibility",
            {"visibility_status": "approved", "is_public": True},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.feedback.refresh_from_db()
        self.assertEqual(self.feedback.visibility_status, "approved")
        self.assertTrue(self.feedback.is_public)
        self.assertIsNotNone(self.feedback.visibility_reviewed_at)
        self.assertEqual(self.feedback.visibility_reviewer_id, self.admin.id)

    def test_reject_visibility(self):
        response = self.client.post(
            f"/api/admin/problem-feedbacks/{self.feedback.id}/visibility",
            {"visibility_status": "rejected", "is_public": False},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.feedback.refresh_from_db()
        self.assertEqual(self.feedback.visibility_status, "rejected")
        self.assertFalse(self.feedback.is_public)

    def test_approved_must_have_is_public_true(self):
        response = self.client.post(
            f"/api/admin/problem-feedbacks/{self.feedback.id}/visibility",
            {"visibility_status": "approved", "is_public": False},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_reset_to_pending(self):
        self.feedback.visibility_status = ProblemFeedback.VisibilityStatus.APPROVED
        self.feedback.is_public = True
        self.feedback.save()
        response = self.client.post(
            f"/api/admin/problem-feedbacks/{self.feedback.id}/visibility",
            {"visibility_status": "pending", "is_public": False},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.feedback.refresh_from_db()
        self.assertEqual(self.feedback.visibility_status, "pending")
        self.assertFalse(self.feedback.is_public)

    def test_visibility_does_not_change_business_status(self):
        self.feedback.status = ProblemFeedback.Status.REPLIED
        self.feedback.reply = "已回复"
        self.feedback.save()
        self.client.post(
            f"/api/admin/problem-feedbacks/{self.feedback.id}/visibility",
            {"visibility_status": "approved", "is_public": True},
            content_type="application/json",
            **self.headers,
        )
        self.feedback.refresh_from_db()
        self.assertEqual(self.feedback.status, "replied")

    def test_admin_list_returns_visibility_and_source_type(self):
        response = self.client.get(
            "/api/admin/problem-feedbacks",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        item = response.json()["data"]["items"][0]
        self.assertIn("visibility_status", item)
        self.assertIn("is_public", item)
        self.assertEqual(item["source_type"], "problem_feedback")

    def test_admin_list_filters_visibility_status(self):
        ProblemFeedback.objects.create(
            member=self.member, title="已公开", content="内容",
            visibility_status=ProblemFeedback.VisibilityStatus.APPROVED,
            is_public=True,
        )
        response = self.client.get(
            "/api/admin/problem-feedbacks",
            {"visibility_status": "approved"},
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["total"], 1)

    def test_admin_patch_does_not_allow_title_content(self):
        response = self.client.patch(
            f"/api/admin/problem-feedbacks/{self.feedback.id}",
            {"title": "篡改标题", "content": "篡改内容"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.feedback.refresh_from_db()
        self.assertEqual(self.feedback.title, "测试")
        self.assertEqual(self.feedback.content, "内容")

from django.test import TestCase

from apps.members.models import Member
from tests.helpers import auth_header, create_member


class ProblemFeedbacksApiTests(TestCase):
    def test_approved_member_creates_problem_feedback(self):
        member = create_member(audit_status=Member.AuditStatus.APPROVED)

        response = self.client.post(
            "/api/problem-feedbacks",
            {"title": "账号问题", "content": "无法查看某个页面"},
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["title"], "账号问题")
        self.assertEqual(data["status"], "submitted")
        self.assertEqual(data["reply"], "")

    def test_unapproved_member_cannot_create_problem_feedback(self):
        member = create_member(audit_status=Member.AuditStatus.NONE)

        response = self.client.post(
            "/api/problem-feedbacks",
            {"title": "账号问题", "content": "无法查看某个页面"},
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], 40301)

    def test_problem_feedback_list_only_returns_current_member_and_filters_status(self):
        member = create_member(openid="member-openid", audit_status=Member.AuditStatus.APPROVED)
        other = create_member(openid="other-openid", audit_status=Member.AuditStatus.APPROVED)
        from apps.problem_feedbacks.models import ProblemFeedback

        mine = ProblemFeedback.objects.create(member=member, title="我的问题", content="内容")
        ProblemFeedback.objects.create(member=member, title="已回复", content="内容", status=ProblemFeedback.Status.REPLIED)
        ProblemFeedback.objects.create(member=other, title="别人问题", content="内容")

        response = self.client.get(
            "/api/problem-feedbacks",
            {"status": "submitted"},
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["id"], mine.id)

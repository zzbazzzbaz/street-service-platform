from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.members.models import Member
from apps.points.models import PointAccount, PointRecord
from tests.helpers import auth_header, create_member


class CivicFeedbacksApiTests(TestCase):
    def test_approved_member_creates_civic_feedback(self):
        member = create_member(audit_status=Member.AuditStatus.APPROVED)

        response = self.client.post(
            "/api/civic-feedbacks",
            {
                "title": "建议增设临时停车引导牌",
                "content": "学校门口早高峰停车较乱",
                "material_urls": ["https://example.com/a.png"],
            },
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["title"], "建议增设临时停车引导牌")
        self.assertEqual(data["material_urls"], ["https://example.com/a.png"])
        self.assertEqual(data["status"], "submitted")
        self.assertEqual(data["points"], 0)

    def test_unapproved_member_cannot_create_civic_feedback(self):
        member = create_member(audit_status=Member.AuditStatus.PENDING)

        response = self.client.post(
            "/api/civic-feedbacks",
            {"title": "建议", "content": "内容"},
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], 40301)

    def test_civic_feedback_list_only_returns_current_member_and_filters_status(self):
        member = create_member(openid="member-openid", audit_status=Member.AuditStatus.APPROVED)
        other = create_member(openid="other-openid", audit_status=Member.AuditStatus.APPROVED)
        from apps.civic_feedbacks.models import CivicFeedback

        mine = CivicFeedback.objects.create(member=member, title="我的建议", content="内容")
        CivicFeedback.objects.create(member=member, title="已采纳", content="内容", status=CivicFeedback.Status.ACCEPTED)
        CivicFeedback.objects.create(member=other, title="别人建议", content="内容")

        response = self.client.get(
            "/api/civic-feedbacks",
            {"status": "submitted"},
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["id"], mine.id)

    def test_accepting_civic_feedback_grants_points_once(self):
        member = create_member(audit_status=Member.AuditStatus.APPROVED)
        operator = get_user_model().objects.create_user(username="manager", password="password", is_backend_manager=True)
        from apps.civic_feedbacks.models import CivicFeedback
        from apps.civic_feedbacks.services import accept_civic_feedback

        feedback = CivicFeedback.objects.create(member=member, title="建议", content="内容", points=7)

        accept_civic_feedback(feedback, reply="已采纳", operator=operator)
        accept_civic_feedback(feedback, reply="已采纳", operator=operator)

        self.assertEqual(PointAccount.objects.get(member=member).balance, 7)
        self.assertEqual(PointRecord.objects.filter(source_type=PointRecord.SourceType.CIVIC_FEEDBACK).count(), 1)

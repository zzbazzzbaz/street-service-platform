from django.test import TestCase

from apps.members.models import Member
from apps.problem_feedbacks.models import ProblemFeedback
from tests.helpers import create_member


class PublicProblemFeedbacksApiTests(TestCase):
    def setUp(self):
        self.member = create_member(
            openid="member-openid",
            audit_status=Member.AuditStatus.APPROVED,
            real_name="张三",
            phone="13800001234",
        )

    def test_public_endpoint_returns_only_approved_public_feedbacks(self):
        public = ProblemFeedback.objects.create(
            member=self.member, title="公开留言", content="内容1",
            visibility_status=ProblemFeedback.VisibilityStatus.APPROVED,
            is_public=True,
        )
        ProblemFeedback.objects.create(
            member=self.member, title="待审核", content="内容2",
            visibility_status=ProblemFeedback.VisibilityStatus.PENDING,
            is_public=False,
        )
        ProblemFeedback.objects.create(
            member=self.member, title="被拒绝", content="内容3",
            visibility_status=ProblemFeedback.VisibilityStatus.REJECTED,
            is_public=False,
        )

        response = self.client.get("/api/problem-feedbacks/public")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["id"], public.id)

    def test_public_endpoint_does_not_return_member_info(self):
        ProblemFeedback.objects.create(
            member=self.member, title="公开", content="内容",
            visibility_status=ProblemFeedback.VisibilityStatus.APPROVED,
            is_public=True,
        )
        response = self.client.get("/api/problem-feedbacks/public")
        item = response.json()["data"]["items"][0]
        self.assertNotIn("member_id", item)
        self.assertNotIn("member_name", item)
        self.assertNotIn("member_phone", item)

    def test_public_endpoint_no_auth_required(self):
        response = self.client.get("/api/problem-feedbacks/public")
        self.assertEqual(response.status_code, 200)

    def test_unpublish_removes_from_public(self):
        feedback = ProblemFeedback.objects.create(
            member=self.member, title="取消公开", content="内容",
            visibility_status=ProblemFeedback.VisibilityStatus.APPROVED,
            is_public=True,
        )
        feedback.visibility_status = ProblemFeedback.VisibilityStatus.REJECTED
        feedback.is_public = False
        feedback.save()
        response = self.client.get("/api/problem-feedbacks/public")
        self.assertEqual(response.json()["data"]["total"], 0)

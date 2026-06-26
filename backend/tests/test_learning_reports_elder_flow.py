from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.elder_services.models import ElderServiceFeedback, ElderServiceTask
from apps.elder_services.services import review_feedback, submit_feedback
from apps.learning.models import LearningContent, LearningRecord
from apps.learning.services import complete_learning
from apps.points.models import PointAccount, PointRecord
from apps.reports.models import Report
from apps.reports.services import review_report, submit_report
from shared.exceptions import BusinessError
from tests.helpers import auth_header, create_member


class LearningReportsElderFlowTests(TestCase):
    def setUp(self):
        self.member = create_member()
        self.operator = get_user_model().objects.create_user(
            username="manager",
            password="password",
            is_backend_manager=True,
        )

    def test_learning_completion_awards_points_once(self):
        content = LearningContent.objects.create(
            title="安全学习",
            body="正文",
            points=10,
            required_seconds=60,
            is_active=True,
        )

        first = complete_learning(self.member, content, learned_seconds=60)
        second = complete_learning(self.member, content, learned_seconds=80)

        self.assertTrue(first.is_completed)
        self.assertEqual(first.id, second.id)
        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 10)
        self.assertEqual(PointRecord.objects.filter(source_type=PointRecord.SourceType.LEARNING).count(), 1)

    def test_learning_rejects_inactive_content(self):
        content = LearningContent.objects.create(title="下架内容", body="正文", is_active=False)

        with self.assertRaisesRegex(BusinessError, "未上架"):
            complete_learning(self.member, content, learned_seconds=60)

    def test_learning_api_lists_and_completes_content(self):
        content = LearningContent.objects.create(
            title="安全学习",
            body="正文",
            points=3,
            required_seconds=10,
            is_active=True,
        )
        headers = auth_header("member", self.member.openid)

        list_response = self.client.get("/api/learning/contents", **headers)
        detail_response = self.client.get(f"/api/learning/contents/{content.id}", **headers)
        complete_response = self.client.post(
            f"/api/learning/contents/{content.id}/complete",
            {"learned_seconds": 10},
            content_type="application/json",
            **headers,
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["data"]["total"], 1)
        list_item = list_response.json()["data"]["items"][0]
        self.assertEqual(list_item["content_type"], "article")
        self.assertEqual(list_item["cover_url"], list_item["cover"])
        self.assertEqual(list_item["image_urls"], [])
        self.assertEqual(list_item["video_url"], "")
        self.assertEqual(detail_response.status_code, 200)
        detail_data = detail_response.json()["data"]
        self.assertEqual(detail_data["content_type"], "article")
        self.assertEqual(detail_data["cover_url"], detail_data["cover"])
        self.assertEqual(detail_data["image_urls"], [])
        self.assertEqual(detail_data["video_url"], "")
        self.assertEqual(complete_response.status_code, 200)
        self.assertTrue(LearningRecord.objects.get(member=self.member, content=content).is_completed)

    def test_missing_learning_content_uses_unified_404_response(self):
        headers = auth_header("member", self.member.openid)

        response = self.client.get("/api/learning/contents/9999", **headers)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], 40400)
        self.assertIn("message", response.json())

    def test_report_review_approve_awards_points_and_reject_does_not(self):
        approved = submit_report(self.member, title="井盖破损", description="描述", image="", location="路口")
        rejected = submit_report(self.member, title="重复问题", description="描述", image="", location="路口")

        review_report(approved, action="approve", comment="", operator=self.operator)
        review_report(rejected, action="reject", comment="不符合要求", operator=self.operator)

        self.assertEqual(Report.objects.get(pk=approved.pk).status, Report.Status.APPROVED)
        self.assertEqual(Report.objects.get(pk=rejected.pk).status, Report.Status.REJECTED)
        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 5)
        self.assertEqual(PointRecord.objects.filter(source_type=PointRecord.SourceType.REPORT).count(), 1)

        with self.assertRaisesRegex(BusinessError, "已审核"):
            review_report(approved, action="approve", comment="", operator=self.operator)

    def test_elder_feedback_review_approve_awards_points_once(self):
        task = ElderServiceTask.objects.create(
            title="探访老人",
            description="服务描述",
            location="社区",
            points=8,
            status=ElderServiceTask.Status.PUBLISHED,
        )
        feedback = submit_feedback(self.member, task, content="已完成探访", image="")

        with self.assertRaisesRegex(BusinessError, "重复"):
            submit_feedback(self.member, task, content="再次提交", image="")

        review_feedback(feedback, action="approve", comment="", operator=self.operator)

        self.assertEqual(ElderServiceFeedback.objects.get(pk=feedback.pk).status, ElderServiceFeedback.Status.APPROVED)
        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 8)
        self.assertEqual(PointRecord.objects.filter(source_type=PointRecord.SourceType.ELDER_SERVICE).count(), 1)

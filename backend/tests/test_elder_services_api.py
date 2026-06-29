from django.test import TestCase

from apps.elder_services.models import ElderCareRelation, ElderServiceFeedback, ElderServiceTask
from apps.members.models import Member
from tests.helpers import auth_header, create_member


class ElderServicesApiTests(TestCase):
    def setUp(self):
        self.member = create_member(openid="member-openid", audit_status=Member.AuditStatus.APPROVED)
        self.other = create_member(openid="other-openid", audit_status=Member.AuditStatus.APPROVED)
        self.relation = ElderCareRelation.objects.create(
            member=self.member,
            elder_name="刘阿姨",
            elder_address="东里 3 号楼",
            frequency="每周一次",
        )
        self.other_relation = ElderCareRelation.objects.create(
            member=self.other,
            elder_name="王叔叔",
            elder_address="西里 2 号楼",
            frequency="每周一次",
        )
        self.task = ElderServiceTask.objects.create(
            relation=self.relation,
            title="刘阿姨每周关爱探访",
            description="完成一次关怀后提交反馈",
            points=20,
            status=ElderServiceTask.Status.PUBLISHED,
        )
        ElderServiceTask.objects.create(
            relation=self.other_relation,
            title="王叔叔每周关爱探访",
            description="完成一次关怀后提交反馈",
            points=20,
            status=ElderServiceTask.Status.PUBLISHED,
        )

    def test_my_tasks_only_returns_current_member_relation_tasks(self):
        response = self.client.get(
            "/api/elder-services/my-tasks",
            **auth_header("member", self.member.openid),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        item = data["items"][0]
        self.assertEqual(item["task_id"], self.task.id)
        self.assertEqual(item["elder_name"], "刘阿姨")
        self.assertEqual(item["elder_address"], "东里 3 号楼")
        self.assertEqual(item["frequency"], "每周一次")
        self.assertEqual(item["feedback_status"], "none")
        self.assertIsNone(item["latest_feedback"])

    def test_unapproved_member_cannot_view_my_tasks(self):
        pending = create_member(openid="pending-openid", audit_status=Member.AuditStatus.PENDING)

        response = self.client.get(
            "/api/elder-services/my-tasks",
            **auth_header("member", pending.openid),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], 40301)

    def test_submit_feedback_requires_relation_owner_and_returns_task_context(self):
        response = self.client.post(
            f"/api/elder-services/tasks/{self.task.id}/feedback",
            {"content": "已完成电话关怀", "image_urls": ["https://example.com/a.png"]},
            content_type="application/json",
            **auth_header("member", self.member.openid),
        )
        other_response = self.client.post(
            f"/api/elder-services/tasks/{self.task.id}/feedback",
            {"content": "尝试提交", "image_urls": []},
            content_type="application/json",
            **auth_header("member", self.other.openid),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["task_id"], self.task.id)
        self.assertEqual(data["task_title"], "刘阿姨每周关爱探访")
        self.assertEqual(data["elder_name"], "刘阿姨")
        self.assertEqual(data["image_urls"], ["https://example.com/a.png"])
        self.assertEqual(other_response.status_code, 404)

    def test_rejected_feedback_can_be_resubmitted_pending_or_approved_cannot(self):
        rejected = ElderServiceFeedback.objects.create(
            member=self.member,
            relation=self.relation,
            task=self.task,
            content="旧反馈",
            status=ElderServiceFeedback.Status.REJECTED,
            review_comment="图片不清晰",
        )

        resubmit = self.client.post(
            f"/api/elder-services/tasks/{self.task.id}/feedback",
            {"content": "重新提交", "image_urls": []},
            content_type="application/json",
            **auth_header("member", self.member.openid),
        )
        duplicate = self.client.post(
            f"/api/elder-services/tasks/{self.task.id}/feedback",
            {"content": "第三次提交", "image_urls": []},
            content_type="application/json",
            **auth_header("member", self.member.openid),
        )

        self.assertEqual(resubmit.status_code, 200)
        self.assertEqual(duplicate.status_code, 400)
        self.assertNotEqual(resubmit.json()["data"]["id"], rejected.id)
        self.assertEqual(ElderServiceFeedback.objects.filter(member=self.member, task=self.task).count(), 2)

    def test_my_tasks_can_filter_by_latest_feedback_status(self):
        ElderServiceFeedback.objects.create(
            member=self.member,
            relation=self.relation,
            task=self.task,
            content="待审核反馈",
            status=ElderServiceFeedback.Status.PENDING,
        )

        pending = self.client.get(
            "/api/elder-services/my-tasks",
            {"feedback_status": "pending"},
            **auth_header("member", self.member.openid),
        )
        none = self.client.get(
            "/api/elder-services/my-tasks",
            {"feedback_status": "none"},
            **auth_header("member", self.member.openid),
        )

        self.assertEqual(pending.status_code, 200)
        self.assertEqual(pending.json()["data"]["total"], 1)
        self.assertEqual(pending.json()["data"]["items"][0]["feedback_status"], "pending")
        self.assertIsNotNone(pending.json()["data"]["items"][0]["latest_feedback"])
        self.assertEqual(none.status_code, 200)
        self.assertEqual(none.json()["data"]["total"], 0)

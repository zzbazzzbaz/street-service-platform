from django.test import TestCase

from apps.elder_services.models import ElderCareRelation, ElderServiceFeedback, ElderServiceTask
from apps.members.models import Member
from apps.points.models import PointAccount, PointRecord
from tests.helpers import admin_auth_header, create_admin_user, create_member


class AdminPortalElderServicesApiTests(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.headers = admin_auth_header(self.admin)
        self.courier = create_member(
            openid="courier-openid",
            identity_type=Member.IdentityType.COURIER,
            audit_status=Member.AuditStatus.APPROVED,
        )

    def test_relation_task_and_feedback_review_workflow(self):
        relation_response = self.client.post(
            "/api/admin/elder-services/relations",
            {"member_id": self.courier.id, "elder_name": "刘阿姨", "elder_address": "幸福小区", "frequency": "每周一次", "is_active": True},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(relation_response.status_code, 200)
        relation_id = relation_response.json()["data"]["id"]

        task_response = self.client.post(
            "/api/admin/elder-services/tasks",
            {"title": "探访任务", "relation_id": relation_id, "description": "探访", "location": "社区", "points": 7, "status": "published"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(task_response.status_code, 200)
        task_id = task_response.json()["data"]["id"]
        feedback = ElderServiceFeedback.objects.create(member=self.courier, relation_id=relation_id, task_id=task_id, content="已完成")

        feedback_review = self.client.post(
            f"/api/admin/elder-services/feedbacks/{feedback.id}/review",
            {"action": "approve", "comment": ""},
            content_type="application/json",
            **self.headers,
        )
        repeat = self.client.post(
            f"/api/admin/elder-services/feedbacks/{feedback.id}/review",
            {"action": "approve", "comment": ""},
            content_type="application/json",
            **self.headers,
        )
        task_delete = self.client.delete(f"/api/admin/elder-services/tasks/{task_id}", **self.headers)
        relation_status = self.client.post(
            f"/api/admin/elder-services/relations/{relation_id}/status",
            {"is_active": False},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(feedback_review.status_code, 200)
        self.assertEqual(PointAccount.objects.get(member=self.courier).balance, 7)
        self.assertEqual(PointRecord.objects.get(source_type=PointRecord.SourceType.ELDER_SERVICE).operator_id, self.admin.id)
        self.assertEqual(repeat.status_code, 409)
        self.assertEqual(task_delete.status_code, 400)
        self.assertEqual(relation_status.status_code, 200)
        self.assertFalse(relation_status.json()["data"]["is_active"])

    def test_relation_requires_approved_active_courier(self):
        normal = create_member(openid="normal-openid", identity_type=Member.IdentityType.NORMAL_USER)

        response = self.client.post(
            "/api/admin/elder-services/relations",
            {"member_id": normal.id, "elder_name": "刘阿姨", "elder_address": "幸福小区"},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("小哥", response.json()["message"])

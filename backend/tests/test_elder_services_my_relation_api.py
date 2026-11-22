from django.test import TestCase

from apps.elder_services.models import ElderCareRelation
from apps.members.models import Member
from tests.helpers import auth_header, create_member


class MyRelationApiTests(TestCase):
    def setUp(self):
        self.member = create_member(
            openid="courier-openid",
            audit_status=Member.AuditStatus.APPROVED,
        )
        self.relation = ElderCareRelation.objects.create(
            member=self.member,
            elder_name="张阿姨",
            elder_address="示例街道幸福里 2 号楼",
        )

    def test_returns_active_relation_for_current_member(self):
        response = self.client.get(
            "/api/elder-services/my-relation",
            **auth_header("member", self.member.openid),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["id"], self.relation.id)
        self.assertEqual(data["member_id"], self.member.id)
        self.assertEqual(data["elder_name"], "张阿姨")
        self.assertEqual(data["elder_address"], "示例街道幸福里 2 号楼")
        self.assertTrue(data["is_active"])

    def test_returns_null_when_no_relation(self):
        no_relation_member = create_member(
            openid="no-relation-openid",
            audit_status=Member.AuditStatus.APPROVED,
        )
        response = self.client.get(
            "/api/elder-services/my-relation",
            **auth_header("member", no_relation_member.openid),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["data"])

    def test_inactive_relation_returns_null(self):
        self.relation.is_active = False
        self.relation.save()
        response = self.client.get(
            "/api/elder-services/my-relation",
            **auth_header("member", self.member.openid),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["data"])

    def test_approved_user_without_courier_identity_can_access(self):
        normal = create_member(
            openid="normal-openid",
            audit_status=Member.AuditStatus.APPROVED,
        )
        response = self.client.get(
            "/api/elder-services/my-relation",
            **auth_header("member", normal.openid),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["data"])

    def test_pending_user_cannot_access(self):
        pending = create_member(
            openid="pending-elder-openid",
            audit_status=Member.AuditStatus.PENDING,
        )
        response = self.client.get(
            "/api/elder-services/my-relation",
            **auth_header("member", pending.openid),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["message"], "当前用户资料未审核通过")


class DirectFeedbackApiTests(TestCase):
    def setUp(self):
        self.member = create_member(
            openid="courier-openid",
            audit_status=Member.AuditStatus.APPROVED,
        )
        self.relation = ElderCareRelation.objects.create(
            member=self.member,
            elder_name="张阿姨",
            elder_address="示例街道幸福里 2 号楼",
        )

    def test_submit_feedback_without_task_id(self):
        response = self.client.post(
            "/api/elder-services/feedbacks",
            {"content": "今天上门看望老人", "image_urls": ["https://example.com/a.jpg"]},
            content_type="application/json",
            **auth_header("member", self.member.openid),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["relation_id"], self.relation.id)
        self.assertEqual(data["member_id"], self.member.id)
        self.assertEqual(data["elder_name"], "张阿姨")
        self.assertEqual(data["elder_address"], "示例街道幸福里 2 号楼")
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["content"], "今天上门看望老人")

    def test_submit_feedback_requires_at_least_one_image(self):
        response = self.client.post(
            "/api/elder-services/feedbacks",
            {"content": "没有图片", "image_urls": []},
            content_type="application/json",
            **auth_header("member", self.member.openid),
        )
        self.assertEqual(response.status_code, 400)

    def test_submit_feedback_without_relation_returns_403(self):
        no_relation = create_member(
            openid="no-relation-openid",
            audit_status=Member.AuditStatus.APPROVED,
        )
        response = self.client.post(
            "/api/elder-services/feedbacks",
            {"content": "测试", "image_urls": ["https://example.com/a.jpg"]},
            content_type="application/json",
            **auth_header("member", no_relation.openid),
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("帮扶关系", response.json()["message"])

    def test_can_submit_multiple_feedbacks(self):
        for i in range(3):
            response = self.client.post(
                "/api/elder-services/feedbacks",
                {"content": f"第{i+1}次", "image_urls": ["https://example.com/a.jpg"]},
                content_type="application/json",
                **auth_header("member", self.member.openid),
            )
            self.assertEqual(response.status_code, 200)

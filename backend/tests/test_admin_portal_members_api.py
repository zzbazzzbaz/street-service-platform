from django.test import TestCase

from apps.members.models import Member
from apps.points.services import add_points
from apps.points.models import PointAccount, PointRecord
from tests.helpers import admin_auth_header, create_admin_user, create_member


class AdminPortalMembersApiTests(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.headers = admin_auth_header(self.admin)

    def test_member_search_update_status_audit_and_points_overview(self):
        member = create_member(
            openid="courier-openid",
            nickname="王小哥",
            phone="13800000001",
            real_name="王强",
            identity_type=Member.IdentityType.COURIER,
            audit_status=Member.AuditStatus.PENDING,
        )
        create_member(openid="other-openid", nickname="其他用户")
        add_points(member, 15, source_type=PointRecord.SourceType.MANUAL, reason="测试加分", operator=self.admin)

        list_response = self.client.get("/api/admin/members?keyword=王小哥&audit_status=pending", **self.headers)
        detail_response = self.client.get(f"/api/admin/members/{member.id}", **self.headers)
        update_response = self.client.patch(
            f"/api/admin/members/{member.id}",
            {"nickname": "王师傅", "phone": "13900000001", "real_name": "王强", "identity_type": "courier"},
            content_type="application/json",
            **self.headers,
        )
        audit_response = self.client.post(
            f"/api/admin/members/{member.id}/audit",
            {"action": "approve", "remark": "资料完整"},
            content_type="application/json",
            **self.headers,
        )
        status_response = self.client.post(
            f"/api/admin/members/{member.id}/status",
            {"is_active": False},
            content_type="application/json",
            **self.headers,
        )
        points_response = self.client.get(f"/api/admin/members/{member.id}/points", **self.headers)

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["data"]["total"], 1)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["data"]["nickname"], "王师傅")
        self.assertEqual(audit_response.status_code, 200)
        self.assertEqual(audit_response.json()["data"]["audit_status"], "approved")
        self.assertEqual(status_response.status_code, 200)
        self.assertFalse(status_response.json()["data"]["is_active"])
        self.assertEqual(points_response.status_code, 200)
        self.assertEqual(points_response.json()["data"]["account"]["balance"], PointAccount.objects.get(member=member).balance)
        self.assertEqual(len(points_response.json()["data"]["records"]), 1)

    def test_member_audit_reject_requires_remark(self):
        member = create_member(audit_status=Member.AuditStatus.PENDING)

        response = self.client.post(
            f"/api/admin/members/{member.id}/audit",
            {"action": "reject", "remark": ""},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("驳回", response.json()["message"])

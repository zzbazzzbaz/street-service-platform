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
            openid="user-openid",
            nickname="王小哥",
            phone="13800000001",
            real_name="王强",
            wechat_id="wangqiang_wx",
            gender="男",
            occupation="顺丰快递",
            is_party_member=True,
            address="幸福街道 1 号楼",
            audit_status=Member.AuditStatus.PENDING,
        )
        create_member(openid="other-openid", nickname="其他用户")
        add_points(member, 15, source_type=PointRecord.SourceType.MANUAL, reason="测试加分", operator=self.admin)

        list_response = self.client.get("/api/admin/members?keyword=王强&audit_status=pending", **self.headers)
        detail_response = self.client.get(f"/api/admin/members/{member.id}", **self.headers)
        update_response = self.client.patch(
            f"/api/admin/members/{member.id}",
            {
                "nickname": "王师傅",
                "phone": "13900000001",
                "real_name": "王强",
                "wechat_id": "wangqiang_new",
                "gender": "男",
                "occupation": "京东快递",
                "is_party_member": False,
                "address": "幸福街道 2 号楼",
            },
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
        self.assertEqual(update_response.json()["data"]["occupation"], "京东快递")
        self.assertEqual(update_response.json()["data"]["address"], "幸福街道 2 号楼")
        self.assertFalse(update_response.json()["data"]["is_party_member"])
        self.assertEqual(update_response.json()["data"]["username"], "13900000001")
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

    def test_member_soft_delete_archives_identity_and_hides_from_list(self):
        member = create_member(
            openid="user-openid",
            username="13800000009",
            phone="13800000009",
            nickname="待删除用户",
        )

        response = self.client.delete(f"/api/admin/members/{member.id}?reason=重复账号", **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["deleted"])

        member.refresh_from_db()
        self.assertIsNotNone(member.deleted_at)
        self.assertFalse(member.is_active)
        self.assertEqual(member.deleted_username, "13800000009")
        self.assertEqual(member.deleted_phone, "13800000009")
        self.assertEqual(member.deleted_by_id, self.admin.id)
        self.assertEqual(member.delete_reason, "重复账号")
        self.assertEqual(member.username, f"deleted_{member.id}")
        self.assertEqual(member.phone, f"deleted_{member.id}")

        list_response = self.client.get("/api/admin/members?keyword=待删除用户", **self.headers)
        self.assertEqual(list_response.json()["data"]["total"], 0)

        # 原手机号可以重新注册
        new_member = create_member(openid="new-openid", username="13800000009", phone="13800000009")
        self.assertNotEqual(new_member.id, member.id)

        # 重复删除返回错误
        again = self.client.delete(f"/api/admin/members/{member.id}", **self.headers)
        self.assertEqual(again.status_code, 400)
        self.assertIn("已删除", again.json()["message"])

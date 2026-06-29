from django.test import TestCase

from apps.members.models import Member
from tests.helpers import auth_header, create_member


class MembersAuditApiTests(TestCase):
    def test_submit_audit_profile_moves_member_to_pending(self):
        member = create_member(audit_status=Member.AuditStatus.REJECTED, audit_remark="资料不清晰")

        response = self.client.post(
            "/api/members/audit-profile",
            {"real_name": "李建国", "identity_type": "courier"},
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["real_name"], "李建国")
        self.assertEqual(data["identity_type"], "courier")
        self.assertEqual(data["audit_status"], "pending")
        self.assertEqual(data["audit_remark"], "")
        member.refresh_from_db()
        self.assertIsNotNone(member.audit_submitted_at)

    def test_submit_audit_profile_rejects_invalid_identity_type(self):
        member = create_member()

        response = self.client.post(
            "/api/members/audit-profile",
            {"real_name": "李建国", "identity_type": "worker"},
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("身份类型", response.json()["message"])

    def test_approved_member_cannot_resubmit_audit_profile(self):
        member = create_member(audit_status=Member.AuditStatus.APPROVED)

        response = self.client.post(
            "/api/members/audit-profile",
            {"real_name": "李建国", "identity_type": "courier"},
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "审核通过后不能自行修改资料")

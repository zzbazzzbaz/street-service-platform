from unittest.mock import patch

from django.contrib.auth.hashers import check_password
from django.test import TestCase

from apps.members.models import Member
from tests.helpers import auth_header


class MemberRegisterApiTests(TestCase):
    def _payload(self, **overrides) -> dict:
        payload = {
            "real_name": "李建国",
            "wechat_id": "lijianguo_wx",
            "gender": "男",
            "occupation": "顺丰快递",
            "address": "幸福街道 1 号楼",
            "phone": "13610000001",
            "is_party_member": True,
        }
        payload.update(overrides)
        return payload

    def test_register_creates_pending_member_and_returns_login(self):
        response = self.client.post("/api/auth/register", self._payload(), content_type="application/json")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertTrue(data["need_audit"])
        self.assertEqual(data["token_type"], "Bearer")
        self.assertTrue(data["access_token"])
        self.assertEqual(data["member"]["audit_status"], "pending")
        self.assertNotIn("identity_type", data["member"])

        member = Member.objects.get(phone="13610000001")
        self.assertEqual(member.audit_status, Member.AuditStatus.PENDING)
        self.assertEqual(member.username, "13610000001")
        self.assertEqual(member.nickname, "李建国")
        self.assertEqual(member.real_name, "李建国")
        self.assertEqual(member.wechat_id, "lijianguo_wx")
        self.assertEqual(member.gender, "男")
        self.assertEqual(member.occupation, "顺丰快递")
        self.assertTrue(member.is_party_member)
        self.assertEqual(member.address, "幸福街道 1 号楼")
        self.assertTrue(check_password("000000", member.password))
        self.assertIsNotNone(member.audit_submitted_at)

    def test_register_token_can_access_me_without_openid(self):
        response = self.client.post("/api/auth/register", self._payload(), content_type="application/json")
        token = response.json()["data"]["access_token"]

        me_response = self.client.get("/api/members/me", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["data"]["audit_status"], "pending")
        self.assertEqual(me_response.json()["data"]["openid"], "")

    def test_register_missing_required_fields_returns_parameter_error(self):
        response = self.client.post("/api/auth/register", {"real_name": "李建国"}, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], 40000)

    def test_register_validates_fields(self):
        cases = [
            ({"real_name": "李"}, "姓名需为 2-10 个字"),
            ({"real_name": "李建国一二三四五六七八九十"}, "姓名需为 2-10 个字"),
            ({"wechat_id": ""}, "微信号不能为空"),
            ({"wechat_id": "x" * 65}, "微信号最多 64 字"),
            ({"gender": "未知"}, "性别不正确"),
            ({"occupation": "程序员"}, "职业不正确"),
            ({"address": ""}, "住址不能为空"),
            ({"address": "x" * 256}, "住址最多 255 字"),
            ({"phone": "12345"}, "手机号格式不正确"),
        ]
        for overrides, message in cases:
            payload = self._payload(**overrides)
            with self.subTest(overrides=overrides):
                response = self.client.post("/api/auth/register", payload, content_type="application/json")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["message"], message)

    def test_register_rejects_duplicate_phone(self):
        Member.objects.create(openid="existing-openid", phone="13610000001", username="13610000001")

        response = self.client.post("/api/auth/register", self._payload(), content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "该手机号已注册")

    def test_register_rejects_reused_wechat_login_code(self):
        Member.objects.create(openid="existing-openid", phone="13610000009")

        with patch("apps.members.services.wechat_code_to_openid", return_value="existing-openid"):
            response = self.client.post(
                "/api/auth/register",
                self._payload(login_code="wx-login-code"),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "该微信已注册")

    def test_register_uses_wechat_phone_code_phone(self):
        with patch("apps.members.services.wechat_phone_code_to_phone", return_value="13700000001"):
            response = self.client.post(
                "/api/auth/register",
                self._payload(phone="13610000009", phone_code="wx-phone-code"),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Member.objects.filter(phone="13700000001").exists())
        self.assertFalse(Member.objects.filter(phone="13610000009").exists())

    def test_dev_wechat_login_creates_none_status_member(self):
        response = self.client.post("/api/auth/wechat-login", {"openid": "dev-openid"}, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["member"]["audit_status"], "none")
        self.assertTrue(Member.objects.filter(openid="dev-openid").exists())


class MemberResubmitApiTests(TestCase):
    def _payload(self, **overrides) -> dict:
        payload = {
            "real_name": "赵待审",
            "wechat_id": "zhaodaishen_wx",
            "gender": "女",
            "occupation": "其他",
            "address": "幸福街道 3 号楼",
            "is_party_member": False,
        }
        payload.update(overrides)
        return payload

    def test_rejected_member_can_resubmit_to_pending(self):
        member = Member.objects.create(
            openid="rejected-openid",
            username="13610000002",
            phone="13610000002",
            audit_status=Member.AuditStatus.REJECTED,
            audit_remark="住址不完整",
        )

        response = self.client.post(
            "/api/members/register-info",
            self._payload(),
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 200)
        member.refresh_from_db()
        self.assertEqual(member.audit_status, Member.AuditStatus.PENDING)
        self.assertEqual(member.audit_remark, "")
        self.assertEqual(member.occupation, "其他")
        self.assertEqual(member.address, "幸福街道 3 号楼")
        self.assertIsNotNone(member.audit_submitted_at)

    def test_pending_member_cannot_resubmit(self):
        member = Member.objects.create(openid="pending-openid", phone="13610000003", audit_status=Member.AuditStatus.PENDING)

        response = self.client.post(
            "/api/members/register-info",
            self._payload(),
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "资料审核中，请等待审核结果")

    def test_approved_member_cannot_resubmit(self):
        member = Member.objects.create(openid="approved-openid", phone="13610000004", audit_status=Member.AuditStatus.APPROVED)

        response = self.client.post(
            "/api/members/register-info",
            self._payload(),
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "审核已通过，如需修改资料请联系街道工作人员")

    def test_member_without_phone_binds_phone_on_resubmit(self):
        member = Member.objects.create(openid="dev-openid", audit_status=Member.AuditStatus.NONE)

        response = self.client.post(
            "/api/members/register-info",
            self._payload(phone="13610000005"),
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 200)
        member.refresh_from_db()
        self.assertEqual(member.phone, "13610000005")
        self.assertEqual(member.username, "13610000005")

    def test_member_without_phone_must_provide_valid_phone(self):
        member = Member.objects.create(openid="dev-openid", audit_status=Member.AuditStatus.NONE)

        response = self.client.post(
            "/api/members/register-info",
            self._payload(phone=""),
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "手机号格式不正确")

    def test_member_with_phone_ignores_submitted_phone(self):
        member = Member.objects.create(openid="rejected-openid", phone="13610000006", audit_status=Member.AuditStatus.REJECTED)

        response = self.client.post(
            "/api/members/register-info",
            self._payload(phone="13610000007"),
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 200)
        member.refresh_from_db()
        self.assertEqual(member.phone, "13610000006")

    def test_member_with_phone_but_no_username_gets_login_name(self):
        member = Member.objects.create(
            openid="rejected-openid",
            phone="13610000008",
            audit_status=Member.AuditStatus.REJECTED,
        )

        response = self.client.post(
            "/api/members/register-info",
            self._payload(),
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 200)
        member.refresh_from_db()
        self.assertEqual(member.username, "13610000008")
        self.assertEqual(member.phone, "13610000008")

    def test_resubmit_requires_token(self):
        response = self.client.post("/api/members/register-info", self._payload(), content_type="application/json")

        self.assertEqual(response.status_code, 401)

    def test_audit_profile_endpoint_is_removed(self):
        member = Member.objects.create(openid="rejected-openid", audit_status=Member.AuditStatus.REJECTED)

        response = self.client.post(
            "/api/members/audit-profile",
            {"real_name": "赵待审", "identity_type": "courier"},
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 404)

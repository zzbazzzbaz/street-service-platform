from django.contrib.auth.hashers import make_password
from django.test import TestCase

from apps.members.models import Member
from apps.merchants.models import Merchant
from tests.helpers import auth_header, create_merchant


class MemberPasswordChangeApiTests(TestCase):
    def _member(self, **kwargs) -> Member:
        defaults = {
            "openid": "member-openid",
            "username": "13610000001",
            "phone": "13610000001",
            "password": make_password("000000"),
        }
        defaults.update(kwargs)
        return Member.objects.create(**defaults)

    def test_change_password_success_and_login_with_new_password(self):
        member = self._member()

        response = self.client.post(
            "/api/members/password",
            {"current_password": "000000", "new_password": "newPass123"},
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 200)
        login = self.client.post(
            "/api/auth/login",
            {"username": "13610000001", "password": "newPass123"},
            content_type="application/json",
        )
        self.assertEqual(login.status_code, 200)

    def test_change_password_rejects_wrong_current_password(self):
        member = self._member()

        response = self.client.post(
            "/api/members/password",
            {"current_password": "wrong", "new_password": "newPass123"},
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "当前密码错误")

    def test_change_password_validates_new_password(self):
        member = self._member()
        headers = auth_header("member", member.openid)

        too_short = self.client.post(
            "/api/members/password",
            {"current_password": "000000", "new_password": "123"},
            content_type="application/json",
            **headers,
        )
        same = self.client.post(
            "/api/members/password",
            {"current_password": "000000", "new_password": "000000"},
            content_type="application/json",
            **headers,
        )

        self.assertEqual(too_short.json()["message"], "新密码长度至少 6 位")
        self.assertEqual(same.json()["message"], "新密码不能与当前密码相同")

    def test_change_password_requires_existing_password(self):
        member = self._member(password="")

        response = self.client.post(
            "/api/members/password",
            {"current_password": "000000", "new_password": "newPass123"},
            content_type="application/json",
            **auth_header("member", member.openid),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "账号未设置密码，请联系街道工作人员")

    def test_change_password_requires_token(self):
        response = self.client.post(
            "/api/members/password",
            {"current_password": "000000", "new_password": "newPass123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)


class MerchantPasswordChangeApiTests(TestCase):
    def test_change_password_success_and_login_with_new_password(self):
        merchant = create_merchant(
            username="13900000001",
            password=make_password("000000"),
            audit_status=Merchant.AuditStatus.APPROVED,
        )

        response = self.client.post(
            "/api/merchant/password",
            {"current_password": "000000", "new_password": "newPass123"},
            content_type="application/json",
            **auth_header("merchant", merchant.openid),
        )

        self.assertEqual(response.status_code, 200)
        login = self.client.post(
            "/api/merchant/auth/login",
            {"username": "13900000001", "password": "newPass123"},
            content_type="application/json",
        )
        self.assertEqual(login.status_code, 200)

    def test_change_password_rejects_wrong_current_password(self):
        merchant = create_merchant(username="13900000002", password=make_password("000000"))

        response = self.client.post(
            "/api/merchant/password",
            {"current_password": "wrong", "new_password": "newPass123"},
            content_type="application/json",
            **auth_header("merchant", merchant.openid),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "当前密码错误")

    def test_change_password_requires_existing_password(self):
        merchant = create_merchant(username="13900000003", password="")

        response = self.client.post(
            "/api/merchant/password",
            {"current_password": "000000", "new_password": "newPass123"},
            content_type="application/json",
            **auth_header("merchant", merchant.openid),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "账号未设置密码，请联系街道工作人员")

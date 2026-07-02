from django.test import TestCase

from tests.helpers import admin_auth_header, create_admin_user


class AdminPortalAccountsApiTests(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.headers = admin_auth_header(self.admin)

    def test_admin_user_crud_equivalent_workflow(self):
        create_response = self.client.post(
            "/api/admin/admin-users",
            {
                "username": "operator",
                "password": "password123",
                "email": "op@example.com",
                "first_name": "运",
                "last_name": "营",
                "is_backend_manager": True,
                "is_active": True,
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(create_response.status_code, 200)
        user_id = create_response.json()["data"]["id"]
        self.assertTrue(create_response.json()["data"]["is_staff"])

        list_response = self.client.get("/api/admin/admin-users?keyword=operator", **self.headers)
        detail_response = self.client.get(f"/api/admin/admin-users/{user_id}", **self.headers)
        update_response = self.client.patch(
            f"/api/admin/admin-users/{user_id}",
            {"email": "updated@example.com", "first_name": "更新", "last_name": "账号", "is_backend_manager": True},
            content_type="application/json",
            **self.headers,
        )
        password_response = self.client.post(
            f"/api/admin/admin-users/{user_id}/password",
            {"password": "newpass123"},
            content_type="application/json",
            **self.headers,
        )
        login_response = self.client.post(
            "/api/admin/auth/login",
            {"username": "operator", "password": "newpass123"},
            content_type="application/json",
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["data"]["total"], 1)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["data"]["email"], "updated@example.com")
        self.assertEqual(password_response.status_code, 200)
        self.assertEqual(login_response.status_code, 200)

    def test_admin_user_status_prevents_self_disable_and_allows_disabling_other_admin(self):
        self_response = self.client.post(
            f"/api/admin/admin-users/{self.admin.id}/status",
            {"is_active": False},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(self_response.status_code, 400)
        self.assertIn("不能禁用自己", self_response.json()["message"])

        other = create_admin_user(username="other")
        status_response = self.client.post(
            f"/api/admin/admin-users/{other.id}/status",
            {"is_active": False},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(status_response.status_code, 200)
        self.assertFalse(status_response.json()["data"]["is_active"])

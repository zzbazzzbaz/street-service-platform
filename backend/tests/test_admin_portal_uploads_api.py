from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from tests.helpers import admin_auth_header, auth_header, create_admin_user, create_member


class AdminPortalUploadsApiTests(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.headers = admin_auth_header(self.admin)

    def test_admin_uploads_image_and_rejects_member_token(self):
        image = SimpleUploadedFile("cover.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")
        response = self.client.post(
            "/api/admin/uploads/images",
            {"files": [image], "business_type": "learning_content", "related_id": "1"},
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["files"][0]["mime_type"], "image/png")

        member = create_member()
        denied = self.client.post(
            "/api/admin/uploads/images",
            {"files": [SimpleUploadedFile("cover.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")]},
            **auth_header("member", member.openid),
        )
        self.assertEqual(denied.status_code, 403)

    def test_admin_uploads_support_admin_business_types(self):
        for business_type in ["merchant", "admin"]:
            with self.subTest(business_type=business_type):
                image = SimpleUploadedFile(f"{business_type}.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")
                response = self.client.post(
                    "/api/admin/uploads/images",
                    {"files": [image], "business_type": business_type},
                    **self.headers,
                )

                self.assertEqual(response.status_code, 200)
                self.assertIn(f"/uploads/{business_type}/", response.json()["data"]["files"][0]["url"])

    def test_admin_uploads_video_and_rejects_invalid_mime_type(self):
        video = SimpleUploadedFile("lesson.mp4", b"mp4-data", content_type="video/mp4")
        response = self.client.post("/api/admin/uploads/videos", {"files": [video]}, **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["mime_type"], "video/mp4")

        bad = SimpleUploadedFile("lesson.mov", b"mov-data", content_type="video/quicktime")
        bad_response = self.client.post("/api/admin/uploads/videos", {"files": [bad]}, **self.headers)
        self.assertEqual(bad_response.status_code, 400)

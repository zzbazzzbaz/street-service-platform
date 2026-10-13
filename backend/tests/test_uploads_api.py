from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from tests.helpers import auth_header, create_member, create_merchant


def image_file(name="photo.jpg", content_type="image/jpeg"):
    return SimpleUploadedFile(name, b"fake-image-content", content_type=content_type)


class UploadsApiTests(TestCase):
    def setUp(self):
        self.member = create_member()
        self.merchant = create_merchant()

    def test_member_uploads_image(self):
        response = self.client.post(
            "/api/uploads/images",
            {"business_type": "report", "files": [image_file()]},
            **auth_header("member", self.member.openid),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data["files"]), 1)
        self.assertTrue(data["files"][0]["url"].startswith("http://testserver/media/uploads/report/"))
        self.assertEqual(data["files"][0]["original_name"], "photo.jpg")
        self.assertEqual(data["files"][0]["mime_type"], "image/jpeg")

    def test_merchant_uploads_image(self):
        response = self.client.post(
            "/api/uploads/images",
            {"business_type": "merchant_product", "files": [image_file("product.png", "image/png")]},
            **auth_header("merchant", self.merchant.openid),
        )

        self.assertEqual(response.status_code, 200)
        file_data = response.json()["data"]["files"][0]
        self.assertTrue(file_data["url"].startswith("http://testserver/media/uploads/merchant_product/"))
        self.assertEqual(file_data["mime_type"], "image/png")

    def test_pending_merchant_can_upload_but_disabled_merchant_cannot(self):
        pending = create_merchant(
            openid="pending-upload-openid",
            audit_status="pending",
            is_active=False,
        )
        allowed = self.client.post(
            "/api/uploads/images",
            {"business_type": "merchant", "files": [image_file("shop.jpg")]},
            **auth_header("merchant", pending.openid),
        )
        disabled = create_merchant(
            openid="disabled-upload-openid",
            audit_status="approved",
            is_active=False,
        )
        denied = self.client.post(
            "/api/uploads/images",
            {"business_type": "merchant", "files": [image_file("shop.jpg")]},
            **auth_header("merchant", disabled.openid),
        )

        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["message"], "当前账号已停用")

    def test_upload_rejects_invalid_mime_type(self):
        response = self.client.post(
            "/api/uploads/images",
            {"business_type": "report", "files": [image_file("bad.txt", "text/plain")]},
            **auth_header("member", self.member.openid),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("不支持", response.json()["message"])

    def test_upload_rejects_too_many_files(self):
        files = [image_file(f"{index}.jpg") for index in range(11)]

        response = self.client.post(
            "/api/uploads/images",
            {"business_type": "report", "files": files},
            **auth_header("member", self.member.openid),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("最多", response.json()["message"])

    def test_upload_requires_files(self):
        response = self.client.post(
            "/api/uploads/images",
            {"business_type": "report"},
            **auth_header("member", self.member.openid),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("请上传图片", response.json()["message"])

    def test_upload_accepts_new_feedback_business_types(self):
        for business_type in ["civic_feedback", "problem_feedback", "elder_service_feedback"]:
            with self.subTest(business_type=business_type):
                response = self.client.post(
                    "/api/uploads/images",
                    {"business_type": business_type, "files": [image_file(f"{business_type}.jpg")]},
                    **auth_header("member", self.member.openid),
                )

                self.assertEqual(response.status_code, 200)
                url = response.json()["data"]["files"][0]["url"]
                self.assertIn(f"/media/uploads/{business_type}/", url)

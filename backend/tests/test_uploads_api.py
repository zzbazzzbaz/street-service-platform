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

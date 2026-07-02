from django.test import TestCase

from apps.learning.models import LearningContent, LearningRecord
from tests.helpers import admin_auth_header, create_admin_user, create_member


class AdminPortalLearningApiTests(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.headers = admin_auth_header(self.admin)

    def test_learning_content_management_and_restricted_delete(self):
        create_response = self.client.post(
            "/api/admin/learning/contents",
            {
                "title": "后台学习",
                "cover": "/media/uploads/learning_content/cover.png",
                "image": "/media/uploads/learning_content/image.png",
                "video": "/media/uploads/learning_content/video.mp4",
                "body": "<p>正文</p>",
                "content_type": "video",
                "points": 5,
                "required_seconds": 30,
                "is_active": True,
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(create_response.status_code, 200)
        content_id = create_response.json()["data"]["id"]

        list_response = self.client.get("/api/admin/learning/contents?keyword=后台", **self.headers)
        detail_response = self.client.get(f"/api/admin/learning/contents/{content_id}", **self.headers)
        update_response = self.client.patch(
            f"/api/admin/learning/contents/{content_id}",
            {"title": "后台学习更新", "points": 8, "required_seconds": 40, "content_type": "video"},
            content_type="application/json",
            **self.headers,
        )
        status_response = self.client.post(
            f"/api/admin/learning/contents/{content_id}/status",
            {"is_active": False},
            content_type="application/json",
            **self.headers,
        )
        member = create_member()
        LearningRecord.objects.create(member=member, content_id=content_id)
        delete_response = self.client.delete(f"/api/admin/learning/contents/{content_id}", **self.headers)

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["data"]["total"], 1)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["data"]["title"], "后台学习更新")
        self.assertEqual(status_response.status_code, 200)
        self.assertFalse(status_response.json()["data"]["is_active"])
        self.assertEqual(delete_response.status_code, 400)
        self.assertIn("关联数据", delete_response.json()["message"])

    def test_learning_records_are_read_only_views(self):
        member = create_member()
        content = LearningContent.objects.create(title="学习内容")
        record = LearningRecord.objects.create(member=member, content=content, learned_seconds=12)

        list_response = self.client.get("/api/admin/learning/records", **self.headers)
        detail_response = self.client.get(f"/api/admin/learning/records/{record.id}", **self.headers)
        create_response = self.client.post("/api/admin/learning/records", {}, content_type="application/json", **self.headers)

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["data"]["total"], 1)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["data"]["member_id"], member.id)
        self.assertEqual(create_response.status_code, 405)

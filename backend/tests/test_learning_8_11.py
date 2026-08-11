from datetime import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.learning.models import LearningContent
from apps.learning.services import content_data
from tests.helpers import auth_header, create_member


class LearningContentsFilterTests(TestCase):
    def setUp(self):
        self.headers = auth_header("member", create_member().openid)

    def test_learning_contents_filter_announcement(self):
        LearningContent.objects.create(title="公告A", is_announcement=True)
        LearningContent.objects.create(title="普通B")
        r = self.client.get("/api/learning/contents?is_announcement=true", **self.headers)
        body = r.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["total"], 1)
        self.assertEqual(body["data"]["items"][0]["title"], "公告A")
        self.assertTrue(body["data"]["items"][0]["is_announcement"])

    def test_learning_contents_filter_pinned(self):
        LearningContent.objects.create(title="置顶", is_announcement=True, is_pinned=True, pin_order=1)
        LearningContent.objects.create(title="未置顶", is_announcement=True)
        r = self.client.get("/api/learning/contents?is_pinned=true", **self.headers)
        self.assertEqual(r.json()["data"]["total"], 1)
        self.assertEqual(r.json()["data"]["items"][0]["title"], "置顶")


class LearningContentSerializationTests(TestCase):
    def test_content_data_returns_new_fields(self):
        c = LearningContent.objects.create(
            title="公告", is_announcement=True, is_pinned=True, pin_order=1
        )
        data = content_data(c, request=None)
        self.assertTrue(data["is_announcement"])
        self.assertTrue(data["is_pinned"])
        self.assertEqual(data["pin_order"], 1)
        self.assertIn("created_at", data)


class LearningContentAnnouncementModelTests(TestCase):
    def test_learning_content_announcement_defaults(self):
        c = LearningContent.objects.create(title="默认公告字段")
        self.assertFalse(c.is_announcement)
        self.assertFalse(c.is_pinned)
        self.assertIsNone(c.pin_order)
        self.assertIsInstance(c.created_at, datetime)

    def test_pin_order_unique_only_when_pinned(self):
        LearningContent.objects.create(title="a", is_pinned=True, pin_order=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            LearningContent.objects.create(title="b", is_pinned=True, pin_order=1)
        # 未置顶时允许相同 pin_order
        LearningContent.objects.create(title="c", is_pinned=False, pin_order=1)

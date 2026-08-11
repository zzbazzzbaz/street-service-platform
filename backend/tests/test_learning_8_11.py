from datetime import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.learning.models import LearningContent
from apps.learning.services import content_data
from tests.helpers import admin_auth_header, auth_header, create_admin_user, create_member


class AdminLearningAnnouncementTests(TestCase):
    def setUp(self):
        self.headers = admin_auth_header(create_admin_user())

    def test_admin_learning_contents_filter(self):
        LearningContent.objects.create(title="公告", is_announcement=True)
        LearningContent.objects.create(title="普通", is_announcement=False)
        r = self.client.get("/api/admin/learning/contents?is_announcement=true", **self.headers)
        self.assertEqual(r.json()["data"]["total"], 1)
        self.assertTrue(r.json()["data"]["items"][0]["is_announcement"])

    def test_admin_learning_create_announcement_requires_article(self):
        payload = {
            "title": "公告视频",
            "is_announcement": True,
            "content_type": "video",
            "body": "<p>x</p>",
        }
        r = self.client.post("/api/admin/learning/contents", payload, content_type="application/json", **self.headers)
        self.assertEqual(r.status_code, 400)

    def test_admin_learning_create_keeps_body_html(self):
        payload = {
            "title": "富文本公告",
            "is_announcement": True,
            "content_type": "article",
            "body": "<h2>标题</h2><p>正文</p><p><img src=\"https://commu.iloveminmeng.com/media/learning/a.jpg\"></p>",
        }
        r = self.client.post("/api/admin/learning/contents", payload, content_type="application/json", **self.headers)
        cid = r.json()["data"]["id"]
        detail = self.client.get(f"/api/admin/learning/contents/{cid}", **self.headers).json()["data"]
        self.assertIn("<h2>标题</h2>", detail["body"])
        self.assertIn("a.jpg", detail["body"])
        self.assertTrue(detail["is_announcement"])

    def test_admin_learning_status_off_clears_pin(self):
        c = LearningContent.objects.create(title="公告", is_announcement=True, is_pinned=True, pin_order=1, is_active=True)
        self.client.post(
            f"/api/admin/learning/contents/{c.id}/status",
            {"is_active": False},
            content_type="application/json",
            **self.headers,
        )
        c.refresh_from_db()
        self.assertFalse(c.is_pinned)
        self.assertIsNone(c.pin_order)


def _pin_content(title="公告", **kw):
    defaults = {"is_announcement": True, "is_active": True, "cover": "learning/covers/x.jpg"}
    defaults.update(kw)
    return LearningContent.objects.create(title=title, **defaults)


class SetPinnedAnnouncementsTests(TestCase):
    def setUp(self):
        self.headers = admin_auth_header(create_admin_user())

    def test_set_pinned_normal_overwrite(self):
        c1 = _pin_content("p1")
        c2 = _pin_content("p2")
        c1.is_pinned, c1.pin_order = True, 1
        c1.save()
        r = self.client.post(
            "/api/admin/learning/announcements/pinned",
            {"items": [{"content_id": c2.id, "pin_order": 1}]},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()["data"]
        self.assertEqual([i["id"] for i in body], [c2.id])
        self.assertEqual([i["pin_order"] for i in body], [1])
        c1.refresh_from_db()
        self.assertFalse(c1.is_pinned)
        self.assertIsNone(c1.pin_order)

    def test_set_pinned_empty_clears_all(self):
        c1 = _pin_content("p1")
        c1.is_pinned, c1.pin_order = True, 1
        c1.save()
        r = self.client.post(
            "/api/admin/learning/announcements/pinned",
            {"items": []},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(r.json()["data"], [])
        c1.refresh_from_db()
        self.assertFalse(c1.is_pinned)
        self.assertIsNone(c1.pin_order)

    def test_set_pinned_duplicate_id_rejected(self):
        c1 = _pin_content("p1")
        r = self.client.post(
            "/api/admin/learning/announcements/pinned",
            {"items": [{"content_id": c1.id, "pin_order": 1}, {"content_id": c1.id, "pin_order": 2}]},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(r.status_code, 400)

    def test_set_pinned_not_announcement_rejected(self):
        c = LearningContent.objects.create(title="普通")
        r = self.client.post(
            "/api/admin/learning/announcements/pinned",
            {"items": [{"content_id": c.id, "pin_order": 1}]},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(r.status_code, 400)

    def test_set_pinned_order_not_continuous_rejected(self):
        c1 = _pin_content("p1")
        c2 = _pin_content("p2")
        r = self.client.post(
            "/api/admin/learning/announcements/pinned",
            {"items": [{"content_id": c1.id, "pin_order": 1}, {"content_id": c2.id, "pin_order": 3}]},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(r.status_code, 400)


class PinnedAnnouncementsTests(TestCase):
    def test_pinned_announcements_public_and_ordered(self):
        LearningContent.objects.create(title="p1", is_announcement=True, is_pinned=True, pin_order=1)
        LearningContent.objects.create(title="p2", is_announcement=True, is_pinned=True, pin_order=2)
        # 非公告置顶项不应出现
        LearningContent.objects.create(title="普通", is_pinned=True, pin_order=3)
        r = self.client.get("/api/learning/announcements/pinned")
        body = r.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual([i["title"] for i in body["data"]], ["p1", "p2"])
        self.assertEqual([i["pin_order"] for i in body["data"]], [1, 2])

    def test_pinned_announcements_empty(self):
        r = self.client.get("/api/learning/announcements/pinned")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["data"], [])

    def test_pinned_announcements_max_three(self):
        for i in range(1, 5):
            LearningContent.objects.create(title=f"p{i}", is_announcement=True, is_pinned=True, pin_order=i)
        r = self.client.get("/api/learning/announcements/pinned")
        self.assertEqual(len(r.json()["data"]), 3)


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

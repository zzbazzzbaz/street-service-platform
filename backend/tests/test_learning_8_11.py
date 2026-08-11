from datetime import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.learning.models import LearningContent


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

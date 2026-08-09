from django.test import TestCase
from django.utils import timezone

from apps.activities.models import Activity


class ActivityTypeFieldTests(TestCase):
    def test_activity_has_activity_type_default(self):
        activity = Activity.objects.create(
            title="社区志愿活动",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
        )
        self.assertEqual(activity.activity_type, Activity.ActivityType.VOLUNTEER)
        self.assertIn("offline", [v for v, _ in Activity.ActivityType.choices])

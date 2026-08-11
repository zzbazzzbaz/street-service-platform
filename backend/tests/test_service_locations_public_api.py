from django.test import TestCase

from apps.service_locations.models import ServiceLocation


class ServiceLocationModelTests(TestCase):
    def test_defaults_and_str(self):
        loc = ServiceLocation.objects.create(
            name="便民站", address="东里社区一层", business_hours="09:00-17:00", service_content="政策咨询"
        )
        self.assertTrue(loc.is_active)
        self.assertIsNone(loc.latitude)
        self.assertIsNone(loc.longitude)
        self.assertIsNotNone(loc.created_at)
        self.assertIsNotNone(loc.updated_at)
        self.assertEqual(str(loc), "便民站")

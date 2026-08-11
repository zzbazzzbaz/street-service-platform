from django.test import TestCase

from apps.service_locations.models import ServiceLocation


class ServiceLocationModelTests(TestCase):
    def test_defaults_and_str(self):
        loc = ServiceLocation.objects.create(
            name="便民站", address="东里社区一层", business_hours="09:00-17:00", service_content="政策咨询"
        )
        self.assertTrue(loc.is_active)
        self.assertIsNone(loc.latitude)
        self.assertIsNotNone(loc.created_at)
        self.assertEqual(str(loc), "便民站")


class ServiceLocationsPublicApiTests(TestCase):
    def test_list_unauthenticated_only_active(self):
        ServiceLocation.objects.create(name="启用", address="a", business_hours="b", service_content="c", is_active=True)
        ServiceLocation.objects.create(name="停用", address="a", business_hours="b", service_content="c", is_active=False)
        r = self.client.get("/api/service-locations")
        body = r.json()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["total"], 1)
        self.assertEqual(body["data"]["items"][0]["name"], "启用")
        self.assertIn("latitude", body["data"]["items"][0])
        self.assertIn("updated_at", body["data"]["items"][0])

    def test_list_empty(self):
        r = self.client.get("/api/service-locations")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["data"]["items"], [])

    def test_list_pagination(self):
        for i in range(3):
            ServiceLocation.objects.create(name=f"n{i}", address="a", business_hours="b", service_content="c")
        r = self.client.get("/api/service-locations?page=1&page_size=2")
        self.assertEqual(r.json()["data"]["total"], 3)
        self.assertEqual(len(r.json()["data"]["items"]), 2)

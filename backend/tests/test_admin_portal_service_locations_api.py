from django.test import TestCase

from apps.service_locations.models import ServiceLocation
from tests.helpers import admin_auth_header, create_admin_user


class AdminServiceLocationsApiTests(TestCase):
    def setUp(self):
        self.headers = admin_auth_header(create_admin_user())

    def _payload(self, **kw):
        defaults = {
            "name": "便民站",
            "address": "东里社区一层",
            "business_hours": "周一至周五 09:00-17:00",
            "service_content": "政策咨询",
            "latitude": 39.908823,
            "longitude": 116.39747,
            "is_active": True,
        }
        defaults.update(kw)
        return defaults

    def test_create_and_detail(self):
        r = self.client.post("/api/admin/service-locations", self._payload(), content_type="application/json", **self.headers)
        self.assertEqual(r.status_code, 200)
        cid = r.json()["data"]["id"]
        d = self.client.get(f"/api/admin/service-locations/{cid}", **self.headers).json()["data"]
        self.assertEqual(d["name"], "便民站")
        self.assertEqual(d["latitude"], 39.908823)

    def test_list_keyword_and_filter(self):
        ServiceLocation.objects.create(name="东里站", address="x", business_hours="y", service_content="z")
        ServiceLocation.objects.create(name="西里站", address="x", business_hours="y", service_content="z", is_active=False)
        r = self.client.get("/api/admin/service-locations?keyword=东里", **self.headers)
        self.assertEqual(r.json()["data"]["total"], 1)
        r2 = self.client.get("/api/admin/service-locations?is_active=false", **self.headers)
        self.assertEqual(r2.json()["data"]["total"], 1)

    def test_update(self):
        loc = ServiceLocation.objects.create(name="a", address="b", business_hours="c", service_content="d")
        r = self.client.patch(
            f"/api/admin/service-locations/{loc.id}",
            {"name": "新名", "latitude": 40.0, "longitude": 116.0},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(r.status_code, 200)
        loc.refresh_from_db()
        self.assertEqual(loc.name, "新名")
        self.assertEqual(loc.latitude, 40.0)

    def test_status_toggle(self):
        loc = ServiceLocation.objects.create(name="a", address="b", business_hours="c", service_content="d", is_active=True)
        self.client.post(
            f"/api/admin/service-locations/{loc.id}/status",
            {"is_active": False},
            content_type="application/json",
            **self.headers,
        )
        loc.refresh_from_db()
        self.assertFalse(loc.is_active)

    def test_create_validation_empty_name(self):
        r = self.client.post("/api/admin/service-locations", self._payload(name=""), content_type="application/json", **self.headers)
        self.assertEqual(r.status_code, 400)

    def test_create_validation_single_coord(self):
        r = self.client.post("/api/admin/service-locations", self._payload(longitude=None), content_type="application/json", **self.headers)
        self.assertEqual(r.status_code, 400)

    def test_create_validation_coord_range(self):
        r = self.client.post("/api/admin/service-locations", self._payload(latitude=999.0), content_type="application/json", **self.headers)
        self.assertEqual(r.status_code, 400)

    def test_update_not_found(self):
        r = self.client.patch("/api/admin/service-locations/99999", {"name": "x"}, content_type="application/json", **self.headers)
        self.assertEqual(r.status_code, 404)

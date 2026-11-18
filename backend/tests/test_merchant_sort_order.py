from django.test import TestCase

from apps.merchants.models import Merchant
from tests.helpers import admin_auth_header, auth_header, create_admin_user, create_member, create_merchant


class MerchantSortOrderApiTests(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.headers = admin_auth_header(self.admin)
        self.member = create_member(openid="sort-member")
        self.member_headers = auth_header("member", self.member.openid)

    def test_admin_list_orders_by_sort_order_and_returns_field(self):
        first = create_merchant(openid="sort-merchant-1", name="排序一", sort_order=1)
        second = create_merchant(openid="sort-merchant-2", name="排序二", sort_order=2)
        unsorted = create_merchant(openid="sort-merchant-3", name="未排序")

        response = self.client.get("/api/admin/merchants", **self.headers)

        self.assertEqual(response.status_code, 200)
        items = response.json()["data"]["items"]
        self.assertEqual([item["id"] for item in items[:3]], [first.id, second.id, unsorted.id])
        self.assertEqual(items[0]["sort_order"], 1)
        self.assertIsNone(items[2]["sort_order"])

    def test_patch_updates_and_clears_sort_order(self):
        merchant = create_merchant(openid="sort-merchant-patch", name="可排序商户")

        response = self.client.patch(
            f"/api/admin/merchants/{merchant.id}",
            {"sort_order": 5},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["sort_order"], 5)
        merchant.refresh_from_db()
        self.assertEqual(merchant.sort_order, 5)

        clear_response = self.client.patch(
            f"/api/admin/merchants/{merchant.id}",
            {"sort_order": None},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(clear_response.status_code, 200)
        self.assertIsNone(clear_response.json()["data"]["sort_order"])
        merchant.refresh_from_db()
        self.assertIsNone(merchant.sort_order)

    def test_batch_sort_orders_reorders_merchants(self):
        merchant_a = create_merchant(openid="sort-batch-a", name="批量一")
        merchant_b = create_merchant(openid="sort-batch-b", name="批量二")
        merchant_c = create_merchant(openid="sort-batch-c", name="批量三")

        response = self.client.put(
            "/api/admin/merchants/sort-orders",
            {
                "items": [
                    {"merchant_id": merchant_c.id, "sort_order": 1},
                    {"merchant_id": merchant_a.id, "sort_order": 2},
                    {"merchant_id": merchant_b.id, "sort_order": 3},
                ]
            },
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["updated"], 3)
        self.assertEqual(Merchant.objects.get(pk=merchant_c.id).sort_order, 1)
        self.assertEqual(Merchant.objects.get(pk=merchant_a.id).sort_order, 2)
        self.assertEqual(Merchant.objects.get(pk=merchant_b.id).sort_order, 3)

        list_response = self.client.get("/api/admin/merchants", **self.headers)
        ids = [item["id"] for item in list_response.json()["data"]["items"]]
        self.assertEqual(ids[:3], [merchant_c.id, merchant_a.id, merchant_b.id])

    def test_batch_sort_orders_rejects_duplicate_ids(self):
        merchant = create_merchant(openid="sort-batch-duplicate", name="重复商户")

        response = self.client.put(
            "/api/admin/merchants/sort-orders",
            {
                "items": [
                    {"merchant_id": merchant.id, "sort_order": 1},
                    {"merchant_id": merchant.id, "sort_order": 2},
                ]
            },
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], 40000)

    def test_batch_sort_orders_rejects_negative_order(self):
        merchant = create_merchant(openid="sort-batch-negative", name="负数排序商户")

        response = self.client.put(
            "/api/admin/merchants/sort-orders",
            {"items": [{"merchant_id": merchant.id, "sort_order": -1}]},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], 40000)

    def test_public_merchant_list_uses_same_sort_order(self):
        first = create_merchant(openid="sort-public-1", name="公开排序一", sort_order=1)
        second = create_merchant(openid="sort-public-2", name="公开排序二", sort_order=2)
        unsorted = create_merchant(openid="sort-public-3", name="公开未排序")

        response = self.client.get("/api/merchants", **self.member_headers)

        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.json()["data"]["items"]]
        self.assertEqual(ids[:3], [first.id, second.id, unsorted.id])

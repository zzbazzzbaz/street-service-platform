from django.test import TestCase

from apps.merchants.models import Merchant
from tests.helpers import admin_auth_header, auth_header, create_admin_user, create_member


class MerchantCategoryFieldsTests(TestCase):
    def test_model_has_new_fields_and_enum(self):
        merchant = Merchant.objects.create(openid="cat-openid", name="测试商户")
        self.assertEqual(merchant.category_code, Merchant.CategoryCode.OTHER)
        self.assertEqual(merchant.business_hours, "")
        self.assertEqual(merchant.service_content, "")
        self.assertIn("repair", [v for v, _ in Merchant.CategoryCode.choices])


class AdminMerchantCategoryFieldsTests(TestCase):
    def setUp(self):
        self.headers = admin_auth_header(create_admin_user())

    def test_create_and_update_merchant_category_fields(self):
        create_response = self.client.post(
            "/api/admin/merchants",
            {
                "openid": "cat-admin-openid",
                "name": "便民家电维修店",
                "category_code": "repair",
                "business_hours": "周一至周日 08:00-19:00",
                "service_content": "提供小家电检测、维修及上门取送服务",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(create_response.status_code, 200)
        data = create_response.json()["data"]
        self.assertEqual(data["category_code"], "repair")
        self.assertEqual(data["business_hours"], "周一至周日 08:00-19:00")
        self.assertEqual(data["service_content"], "提供小家电检测、维修及上门取送服务")
        merchant_id = data["id"]

        update_response = self.client.patch(
            f"/api/admin/merchants/{merchant_id}",
            {"category_code": "retail", "business_hours": "周六休息"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["data"]["category_code"], "retail")
        self.assertEqual(update_response.json()["data"]["business_hours"], "周六休息")

    def test_create_merchant_rejects_invalid_category_code(self):
        response = self.client.post(
            "/api/admin/merchants",
            {"openid": "bad-cat-openid", "name": "非法分类商户", "category_code": "not_a_real_code"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("category_code", response.json()["errors"] or {})

    def test_merchant_business_hours_too_long_rejected(self):
        response = self.client.post(
            "/api/admin/merchants",
            {"openid": "long-hours-openid", "name": "超长营业时间", "business_hours": "x" * 200},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)


class PublicMerchantCategoryFieldsTests(TestCase):
    def test_public_merchant_list_returns_category_fields(self):
        member = create_member(openid="pub-cat-member")
        Merchant.objects.create(
            openid="pub-cat-openid",
            name="便民家电维修店",
            category_code="repair",
            business_hours="周一至周日 08:00-19:00",
            service_content="提供小家电检测、维修及上门取送服务",
        )
        response = self.client.get("/api/merchants", **auth_header("member", member.openid))
        self.assertEqual(response.status_code, 200)
        item = response.json()["data"]["items"][0]
        self.assertEqual(item["category_code"], "repair")
        self.assertEqual(item["business_hours"], "周一至周日 08:00-19:00")
        self.assertEqual(item["service_content"], "提供小家电检测、维修及上门取送服务")
        self.assertNotIn("openid", item)

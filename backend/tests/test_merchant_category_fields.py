from django.test import TestCase

from apps.merchants.models import Merchant


class MerchantCategoryFieldsTests(TestCase):
    def test_model_has_new_fields_and_enum(self):
        merchant = Merchant.objects.create(openid="cat-openid", name="测试商户")
        self.assertEqual(merchant.category_code, Merchant.CategoryCode.OTHER)
        self.assertEqual(merchant.business_hours, "")
        self.assertEqual(merchant.service_content, "")
        self.assertIn("repair", [v for v, _ in Merchant.CategoryCode.choices])

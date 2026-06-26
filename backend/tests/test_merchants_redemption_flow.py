from django.test import TestCase

from apps.merchants.models import MerchantProduct, ProductRedemption
from apps.merchants.services import merchant_redemption_summary, redeem_product
from apps.points.models import PointAccount, PointRecord
from apps.points.services import add_points
from shared.exceptions import BusinessError
from tests.helpers import auth_header, create_member, create_merchant


class MerchantsRedemptionFlowTests(TestCase):
    def setUp(self):
        self.member = create_member()
        self.merchant = create_merchant()
        self.other_merchant = create_merchant(openid="other-merchant", name="其他商户")
        self.product = MerchantProduct.objects.create(
            merchant=self.merchant,
            name="兑换商品",
            description="商品说明",
            points_required=20,
            is_active=True,
        )

    def test_redeem_product_deducts_points_and_creates_pending_record(self):
        add_points(self.member, 30, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        redemption = redeem_product(self.member, self.product)

        self.assertEqual(redemption.status, ProductRedemption.Status.PENDING)
        self.assertEqual(redemption.points_spent, 20)
        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 10)
        self.assertEqual(PointRecord.objects.filter(source_type=PointRecord.SourceType.PRODUCT_REDEMPTION).count(), 1)
        self.assertIsNotNone(redemption.point_record_id)
        self.assertEqual(redemption.point_record.balance_after, 10)

    def test_redeem_product_rejects_inactive_and_insufficient_balance(self):
        inactive = MerchantProduct.objects.create(
            merchant=self.merchant,
            name="下架商品",
            description="商品说明",
            points_required=1,
            is_active=False,
        )

        with self.assertRaisesRegex(BusinessError, "下架"):
            redeem_product(self.member, inactive)

        with self.assertRaisesRegex(BusinessError, "积分余额不足"):
            redeem_product(self.member, self.product)

    def test_merchant_summary_only_counts_own_records(self):
        add_points(self.member, 100, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        redeem_product(self.member, self.product)
        other_product = MerchantProduct.objects.create(
            merchant=self.other_merchant,
            name="其他商品",
            description="商品说明",
            points_required=10,
            is_active=True,
        )
        redeem_product(self.member, other_product)

        summary = merchant_redemption_summary(self.merchant, month=ProductRedemption.objects.first().created_at.strftime("%Y-%m"))

        self.assertEqual(summary["redemption_count"], 1)
        self.assertEqual(summary["product_count"], 1)
        self.assertEqual(summary["points_total"], 20)

    def test_member_product_api_and_merchant_redemption_api(self):
        add_points(self.member, 50, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        inactive_merchant = create_merchant(openid="inactive-merchant", name="停用商户", is_active=False)
        other_product = MerchantProduct.objects.create(
            merchant=self.other_merchant,
            name="其他商户商品",
            description="商品说明",
            points_required=10,
            is_active=True,
        )
        member_headers = auth_header("member", self.member.openid)
        merchant_headers = auth_header("merchant", self.merchant.openid)

        merchants_response = self.client.get("/api/merchants", **member_headers)
        list_response = self.client.get("/api/merchant-products", **member_headers)
        filtered_list_response = self.client.get("/api/merchant-products", {"merchant_id": self.merchant.id}, **member_headers)
        detail_response = self.client.get(f"/api/merchant-products/{self.product.id}", **member_headers)
        redeem_response = self.client.post(
            f"/api/merchant-products/{self.product.id}/redeem",
            {},
            content_type="application/json",
            **member_headers,
        )
        redemptions_response = self.client.get("/api/product-redemptions", **member_headers)
        merchant_records_response = self.client.get("/api/merchant/redemptions", **merchant_headers)
        summary_response = self.client.get(
            "/api/merchant/redemptions/summary",
            {"month": ProductRedemption.objects.first().created_at.strftime("%Y-%m")},
            **merchant_headers,
        )

        self.assertEqual(merchants_response.status_code, 200)
        merchant_items = merchants_response.json()["data"]["items"]
        self.assertEqual([item["id"] for item in merchant_items], [self.other_merchant.id, self.merchant.id])
        self.assertNotIn(inactive_merchant.id, [item["id"] for item in merchant_items])
        self.assertNotIn("openid", merchant_items[0])
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["data"]["total"], 2)
        self.assertEqual(filtered_list_response.status_code, 200)
        filtered_items = filtered_list_response.json()["data"]["items"]
        self.assertEqual([item["id"] for item in filtered_items], [self.product.id])
        self.assertEqual(filtered_items[0]["merchant_id"], self.merchant.id)
        self.assertNotEqual(filtered_items[0]["id"], other_product.id)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(redeem_response.status_code, 200)
        self.assertEqual(redemptions_response.status_code, 200)
        self.assertEqual(merchant_records_response.status_code, 200)
        member_redemption = redemptions_response.json()["data"]["items"][0]
        merchant_redemption = merchant_records_response.json()["data"]["items"][0]
        for item in (member_redemption, merchant_redemption):
            self.assertEqual(item["merchant_name"], self.merchant.name)
            self.assertEqual(item["member_name_masked"], "测*")
            self.assertEqual(item["member_phone_masked"], "138****0000")
            self.assertIsNotNone(item["point_record_id"])
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(summary_response.json()["data"]["redemption_count"], 1)

    def test_merchant_fixed_code_endpoint_is_removed_from_mvp(self):
        merchant_headers = auth_header("merchant", self.merchant.openid)

        response = self.client.get("/api/merchant/fixed-code", **merchant_headers)

        self.assertEqual(response.status_code, 404)

    def test_openapi_does_not_publish_merchant_fixed_code(self):
        response = self.client.get("/api/openapi.json")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("/api/merchant/fixed-code", response.json()["paths"])

    def test_merchant_completes_own_pending_redemption_after_delivery(self):
        add_points(self.member, 50, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        redemption = redeem_product(self.member, self.product)
        merchant_headers = auth_header("merchant", self.merchant.openid)

        response = self.client.post(
            f"/api/merchant/redemptions/{redemption.id}/complete",
            {},
            content_type="application/json",
            **merchant_headers,
        )

        redemption.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["status"], ProductRedemption.Status.COMPLETED)
        self.assertEqual(redemption.status, ProductRedemption.Status.COMPLETED)

    def test_merchant_cannot_complete_other_merchant_redemption(self):
        add_points(self.member, 50, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        redemption = redeem_product(self.member, self.product)
        other_merchant_headers = auth_header("merchant", self.other_merchant.openid)

        response = self.client.post(
            f"/api/merchant/redemptions/{redemption.id}/complete",
            {},
            content_type="application/json",
            **other_merchant_headers,
        )

        redemption.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(redemption.status, ProductRedemption.Status.PENDING)

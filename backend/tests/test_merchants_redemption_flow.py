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
        member_headers = auth_header("member", self.member.openid)
        merchant_headers = auth_header("merchant", self.merchant.openid)

        list_response = self.client.get("/api/merchant-products", **member_headers)
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

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(redeem_response.status_code, 200)
        self.assertEqual(redemptions_response.status_code, 200)
        self.assertEqual(merchant_records_response.status_code, 200)
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(summary_response.json()["data"]["redemption_count"], 1)

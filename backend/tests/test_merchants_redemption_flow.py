from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.merchants.models import MerchantSettlement
from apps.merchants.services import fixed_code_data, merchant_payment_info, merchant_point_record_data, pay_merchant_with_points
from apps.points.models import PointAccount, PointExchangeRule, PointRecord
from apps.points.services import add_points
from shared.exceptions import BusinessError
from tests.helpers import auth_header, create_member, create_merchant


class MerchantPointPaymentFlowTests(TestCase):
    def setUp(self):
        self.member = create_member()
        self.merchant = create_merchant()
        self.other_merchant = create_merchant(openid="other-merchant", name="其他商户")
        PointExchangeRule.objects.create(points_per_yuan=100, is_active=True)

    def test_pay_merchant_with_points_deducts_balance_and_records_metadata(self):
        add_points(self.member, 150, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        record = pay_merchant_with_points(self.member, self.merchant, 100, request_no="pay-001")

        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 50)
        self.assertEqual(record.source_type, PointRecord.SourceType.MERCHANT_PAYMENT)
        self.assertEqual(record.merchant, self.merchant)
        self.assertEqual(record.amount, -100)
        self.assertEqual(record.yuan_amount, Decimal("1.00"))
        self.assertEqual(record.request_no, "pay-001")
        self.assertEqual(record.balance_after, 50)

    def test_pay_merchant_rejects_inactive_insufficient_and_missing_rule(self):
        inactive = create_merchant(openid="inactive-merchant", name="停用商户", is_active=False)
        add_points(self.member, 50, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        with self.assertRaisesRegex(BusinessError, "商户已停用"):
            pay_merchant_with_points(self.member, inactive, 10)

        with self.assertRaisesRegex(BusinessError, "积分余额不足"):
            pay_merchant_with_points(self.member, self.merchant, 100)

        PointExchangeRule.objects.update(is_active=False)
        with self.assertRaisesRegex(BusinessError, "积分兑换比例未配置"):
            pay_merchant_with_points(self.member, self.merchant, 10)

    def test_pay_merchant_request_no_is_idempotent(self):
        add_points(self.member, 200, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        first = pay_merchant_with_points(self.member, self.merchant, 100, request_no="same-req")
        second = pay_merchant_with_points(self.member, self.merchant, 100, request_no="same-req")

        self.assertEqual(first.id, second.id)
        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 100)
        self.assertEqual(PointRecord.objects.filter(source_type=PointRecord.SourceType.MERCHANT_PAYMENT).count(), 1)

    def test_fixed_code_and_payment_info_services(self):
        add_points(self.member, 120, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        fixed_code = fixed_code_data(self.merchant)
        payment_info = merchant_payment_info(self.member, self.merchant)

        self.assertEqual(fixed_code["merchant_id"], self.merchant.id)
        self.assertIn(str(self.merchant.id), fixed_code["code_content"])
        self.assertEqual(payment_info["merchant_id"], self.merchant.id)
        self.assertEqual(payment_info["points_per_yuan"], 100)
        self.assertEqual(payment_info["balance"], 120)

    def test_merchant_payment_api_flow(self):
        add_points(self.member, 150, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        member_headers = auth_header("member", self.member.openid)
        merchant_headers = auth_header("merchant", self.merchant.openid)

        info_response = self.client.get(f"/api/merchants/{self.merchant.id}/payment-info", **member_headers)
        pay_response = self.client.post(
            f"/api/merchants/{self.merchant.id}/point-payments",
            {"points": 100, "request_no": "api-pay-001"},
            content_type="application/json",
            **member_headers,
        )
        fixed_code_response = self.client.get("/api/merchant/fixed-code", **merchant_headers)
        records_response = self.client.get("/api/merchant/point-records", **merchant_headers)

        self.assertEqual(info_response.status_code, 200)
        self.assertEqual(info_response.json()["data"]["points_per_yuan"], 100)
        self.assertEqual(pay_response.status_code, 200)
        self.assertEqual(pay_response.json()["data"]["points"], 100)
        self.assertEqual(pay_response.json()["data"]["yuan_amount"], "1.00")
        self.assertEqual(pay_response.json()["data"]["balance_after"], 50)
        self.assertEqual(fixed_code_response.status_code, 200)
        self.assertIn(str(self.merchant.id), fixed_code_response.json()["data"]["code_content"])
        self.assertEqual(records_response.status_code, 200)
        self.assertEqual(records_response.json()["data"]["total"], 1)
        self.assertEqual(records_response.json()["data"]["items"][0]["merchant_id"], self.merchant.id)

    def test_merchant_payment_api_rejects_third_payment_same_day(self):
        add_points(self.member, 500, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        member_headers = auth_header("member", self.member.openid)

        for i in range(2):
            response = self.client.post(
                f"/api/merchants/{self.merchant.id}/point-payments",
                {"points": 100, "request_no": f"api-{i}"},
                content_type="application/json",
                **member_headers,
            )
            self.assertEqual(response.status_code, 200)

        response = self.client.post(
            f"/api/merchants/{self.merchant.id}/point-payments",
            {"points": 100, "request_no": "api-over"},
            content_type="application/json",
            **member_headers,
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], 40003)
        self.assertIn("上限", response.json()["message"])

    def test_merchant_point_records_only_include_current_merchant(self):
        add_points(self.member, 300, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        own_record = pay_merchant_with_points(self.member, self.merchant, 100, request_no="own")
        pay_merchant_with_points(self.member, self.other_merchant, 100, request_no="other")

        headers = auth_header("merchant", self.merchant.openid)
        response = self.client.get("/api/merchant/point-records", **headers)

        self.assertEqual(response.status_code, 200)
        items = response.json()["data"]["items"]
        self.assertEqual([item["id"] for item in items], [own_record.id])

    def test_merchant_point_records_support_month_filter_and_filtered_summary(self):
        add_points(self.member, 500, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        june_first = pay_merchant_with_points(self.member, self.merchant, 100, request_no="june-first")
        june_second = pay_merchant_with_points(self.member, self.merchant, 200, request_no="june-second")
        may_record = pay_merchant_with_points(self.member, self.other_merchant, 100, request_no="may")
        other_record = pay_merchant_with_points(self.member, self.other_merchant, 100, request_no="other")
        PointRecord.objects.filter(pk__in=[june_first.pk, june_second.pk]).update(created_at=timezone.datetime(2026, 6, 10, tzinfo=timezone.get_current_timezone()))
        PointRecord.objects.filter(pk=may_record.pk).update(created_at=timezone.datetime(2026, 5, 10, tzinfo=timezone.get_current_timezone()))
        PointRecord.objects.filter(pk=other_record.pk).update(created_at=timezone.datetime(2026, 6, 10, tzinfo=timezone.get_current_timezone()))

        response = self.client.get(
            "/api/merchant/point-records",
            {"month": "2026-06", "page_size": 1},
            **auth_header("merchant", self.merchant.openid),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 2)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["summary"]["record_count"], 2)
        self.assertEqual(data["summary"]["total_points"], 300)
        self.assertEqual(data["summary"]["total_yuan_amount"], "3.00")

    def test_merchant_point_records_support_date_range_filter(self):
        add_points(self.member, 300, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        inside = pay_merchant_with_points(self.member, self.merchant, 100, request_no="inside")
        outside = pay_merchant_with_points(self.member, self.merchant, 100, request_no="outside")
        PointRecord.objects.filter(pk=inside.pk).update(created_at=timezone.datetime(2026, 6, 15, tzinfo=timezone.get_current_timezone()))
        PointRecord.objects.filter(pk=outside.pk).update(created_at=timezone.datetime(2026, 6, 20, tzinfo=timezone.get_current_timezone()))

        response = self.client.get(
            "/api/merchant/point-records",
            {"date_from": "2026-06-15", "date_to": "2026-06-15"},
            **auth_header("merchant", self.merchant.openid),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["id"], inside.id)
        self.assertEqual(data["summary"]["total_points"], 100)

    def test_openapi_does_not_publish_old_mall_routes(self):
        response = self.client.get("/api/openapi.json")

        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        self.assertNotIn("/api/merchant-products", paths)
        self.assertNotIn("/api/product-redemptions", paths)
        self.assertNotIn("/api/merchant/redemptions", paths)

    def test_merchant_point_record_data_masks_member(self):
        add_points(self.member, 150, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        record = pay_merchant_with_points(self.member, self.merchant, 100, request_no="mask")

        data = merchant_point_record_data(record)

        self.assertEqual(data["member_name_masked"], "测*")
        self.assertEqual(data["member_phone_masked"], "138****0000")

    def test_daily_payment_limit_allows_two_payments_per_merchant(self):
        add_points(self.member, 500, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")

        first = pay_merchant_with_points(self.member, self.merchant, 100, request_no="day-1")
        second = pay_merchant_with_points(self.member, self.merchant, 100, request_no="day-2")

        self.assertNotEqual(first.id, second.id)
        self.assertEqual(PointRecord.objects.filter(member=self.member, merchant=self.merchant).count(), 2)

    def test_daily_payment_limit_rejects_third_payment_same_day(self):
        add_points(self.member, 500, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        pay_merchant_with_points(self.member, self.merchant, 100, request_no="day-1")
        pay_merchant_with_points(self.member, self.merchant, 100, request_no="day-2")

        with self.assertRaises(BusinessError) as ctx:
            pay_merchant_with_points(self.member, self.merchant, 100, request_no="day-3")

        self.assertEqual(ctx.exception.status, 403)
        self.assertIn("上限", ctx.exception.message)

    def test_daily_payment_limit_isolated_per_merchant(self):
        add_points(self.member, 500, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        pay_merchant_with_points(self.member, self.merchant, 100, request_no="m-1")
        pay_merchant_with_points(self.member, self.merchant, 100, request_no="m-2")

        record = pay_merchant_with_points(self.member, self.other_merchant, 100, request_no="m-other")

        self.assertIsNotNone(record.id)
        self.assertEqual(record.merchant_id, self.other_merchant.id)

    def test_daily_payment_limit_does_not_block_idempotent_replay(self):
        add_points(self.member, 500, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        pay_merchant_with_points(self.member, self.merchant, 100, request_no="replay")
        pay_merchant_with_points(self.member, self.merchant, 100, request_no="day-2")

        replay = pay_merchant_with_points(self.member, self.merchant, 100, request_no="replay")

        self.assertEqual(replay.request_no, "replay")
        self.assertEqual(PointRecord.objects.filter(member=self.member, merchant=self.merchant).count(), 2)

    def test_daily_payment_limit_ignores_failed_payments(self):
        add_points(self.member, 250, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        with self.assertRaisesRegex(BusinessError, "积分余额不足"):
            pay_merchant_with_points(self.member, self.merchant, 300, request_no="fail")

        pay_merchant_with_points(self.member, self.merchant, 100, request_no="ok-1")
        pay_merchant_with_points(self.member, self.merchant, 100, request_no="ok-2")

        self.assertEqual(PointRecord.objects.filter(member=self.member, merchant=self.merchant).count(), 2)

    def test_daily_payment_limit_resets_next_day(self):
        add_points(self.member, 500, source_type=PointRecord.SourceType.MANUAL, reason="测试加分")
        first = pay_merchant_with_points(self.member, self.merchant, 100, request_no="yesterday-1")
        second = pay_merchant_with_points(self.member, self.merchant, 100, request_no="yesterday-2")
        PointRecord.objects.filter(pk__in=[first.pk, second.pk]).update(
            created_at=timezone.datetime(2026, 8, 17, 12, 0, tzinfo=timezone.get_current_timezone())
        )

        today_record = pay_merchant_with_points(self.member, self.merchant, 100, request_no="today-1")

        self.assertEqual(today_record.request_no, "today-1")
        self.assertEqual(PointRecord.objects.filter(member=self.member, merchant=self.merchant).count(), 3)


class MerchantSettlementsApiTests(TestCase):
    def setUp(self):
        self.merchant = create_merchant()
        self.other_merchant = create_merchant(openid="other-merchant", name="其他商户")

    def test_merchant_can_query_own_settlements_by_year_and_status(self):
        mine = MerchantSettlement.objects.create(
            merchant=self.merchant,
            period_type=MerchantSettlement.PeriodType.MONTH,
            period_label="2026-06",
            date_from=timezone.datetime(2026, 6, 1).date(),
            date_to=timezone.datetime(2026, 6, 30).date(),
            record_count=2,
            total_points=300,
            total_yuan_amount=Decimal("3.00"),
            status=MerchantSettlement.Status.PROCESSED,
            processor_name="管理员",
        )
        MerchantSettlement.objects.create(
            merchant=self.merchant,
            period_type=MerchantSettlement.PeriodType.MONTH,
            period_label="2025-12",
            date_from=timezone.datetime(2025, 12, 1).date(),
            date_to=timezone.datetime(2025, 12, 31).date(),
            record_count=1,
            total_points=100,
            total_yuan_amount=Decimal("1.00"),
        )
        MerchantSettlement.objects.create(
            merchant=self.other_merchant,
            period_type=MerchantSettlement.PeriodType.MONTH,
            period_label="2026-06",
            date_from=timezone.datetime(2026, 6, 1).date(),
            date_to=timezone.datetime(2026, 6, 30).date(),
            record_count=1,
            total_points=100,
            total_yuan_amount=Decimal("1.00"),
            status=MerchantSettlement.Status.PROCESSED,
        )

        response = self.client.get(
            "/api/merchant/settlements",
            {"year": 2026, "status": "processed"},
            **auth_header("merchant", self.merchant.openid),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["id"], mine.id)
        self.assertEqual(data["items"][0]["period_label"], "2026-06")
        self.assertEqual(data["items"][0]["total_yuan_amount"], "3.00")

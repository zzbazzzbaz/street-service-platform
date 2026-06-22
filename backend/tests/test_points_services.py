from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.points.models import ManualPointAdjustment, PointAccount, PointRecord
from apps.points.services import add_points, deduct_points, manual_add_points
from shared.exceptions import BusinessError
from tests.helpers import auth_header, create_member


class PointsServiceTests(TestCase):
    def setUp(self):
        self.member = create_member()
        self.operator = get_user_model().objects.create_user(
            username="manager",
            password="password",
            is_backend_manager=True,
        )

    def test_add_points_updates_balance_and_creates_record(self):
        record = add_points(
            self.member,
            10,
            source_type=PointRecord.SourceType.LEARNING,
            source_id="content-1",
            reason="完成学习",
        )

        self.assertEqual(record.amount, 10)
        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 10)
        self.assertEqual(PointRecord.objects.count(), 1)

    def test_deduct_points_updates_balance_and_creates_record(self):
        add_points(self.member, 30, source_type=PointRecord.SourceType.MANUAL, reason="初始积分")

        record = deduct_points(
            self.member,
            12,
            source_type=PointRecord.SourceType.PRODUCT_REDEMPTION,
            source_id="redemption-1",
            reason="兑换商品",
        )

        self.assertEqual(record.amount, -12)
        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 18)
        self.assertEqual(PointRecord.objects.count(), 2)

    def test_deduct_points_rejects_insufficient_balance_without_success_record(self):
        with self.assertRaisesRegex(BusinessError, "积分余额不足"):
            deduct_points(
                self.member,
                1,
                source_type=PointRecord.SourceType.PRODUCT_REDEMPTION,
                reason="兑换商品",
            )

        self.assertFalse(PointAccount.objects.filter(member=self.member).exists())
        self.assertEqual(PointRecord.objects.count(), 0)

    def test_manual_add_points_requires_reason_and_operator(self):
        with self.assertRaisesRegex(BusinessError, "原因"):
            manual_add_points(self.member, 5, reason="", operator=self.operator)

        with self.assertRaisesRegex(BusinessError, "操作人"):
            manual_add_points(self.member, 5, reason="志愿服务", operator=None)

        manual_add_points(self.member, 5, reason="志愿服务", operator=self.operator)

        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 5)

    def test_manual_adjustment_save_uses_points_service(self):
        adjustment = ManualPointAdjustment.objects.create(
            member=self.member,
            amount=9,
            reason="社区服务",
            operator=self.operator,
        )

        self.assertEqual(adjustment.point_record.amount, 9)
        self.assertEqual(PointAccount.objects.get(member=self.member).balance, 9)

    def test_points_balance_and_records_api(self):
        add_points(self.member, 7, source_type=PointRecord.SourceType.MANUAL, reason="测试")
        headers = auth_header("member", self.member.openid)

        balance_response = self.client.get("/api/points/balance", **headers)
        records_response = self.client.get("/api/points/records", **headers)

        self.assertEqual(balance_response.status_code, 200)
        self.assertEqual(balance_response.json()["data"]["balance"], 7)
        self.assertEqual(records_response.status_code, 200)
        self.assertEqual(records_response.json()["data"]["total"], 1)

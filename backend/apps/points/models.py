from django.conf import settings
from django.db import models


class PointAccount(models.Model):
    member = models.OneToOneField("members.Member", on_delete=models.CASCADE, related_name="point_account", verbose_name="用户")
    balance = models.IntegerField("余额", default=0)

    class Meta:
        db_table = "points_account"
        verbose_name = "积分账户"
        verbose_name_plural = "积分账户"

    def __str__(self) -> str:
        return f"{self.member}：{self.balance}"


class PointRecord(models.Model):
    class ChangeType(models.TextChoices):
        INCOME = "income", "收入"
        EXPENSE = "expense", "扣减"

    class SourceType(models.TextChoices):
        LEARNING = "learning", "学习"
        REPORT = "report", "随手拍"
        ACTIVITY = "activity", "活动"
        ELDER_SERVICE = "elder_service", "老人服务"
        MANUAL = "manual", "人工"
        PRODUCT_REDEMPTION = "product_redemption", "商品兑换"

    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="point_records", verbose_name="用户")
    amount = models.IntegerField("积分变动值")
    change_type = models.CharField("变动类型", max_length=20, choices=ChangeType.choices)
    source_type = models.CharField("来源类型", max_length=32, choices=SourceType.choices)
    source_id = models.CharField("来源ID", max_length=64, blank=True)
    reason = models.CharField("原因", max_length=255)
    balance_after = models.IntegerField("变动后余额", null=True, blank=True)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="operated_point_records",
        null=True,
        blank=True,
        verbose_name="操作人",
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "points_record"
        verbose_name = "积分流水"
        verbose_name_plural = "积分流水"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return f"{self.member} {self.amount}"


class ManualPointAdjustment(models.Model):
    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="manual_point_adjustments", verbose_name="用户")
    amount = models.PositiveIntegerField("积分值")
    reason = models.CharField("原因", max_length=255)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="manual_point_adjustments",
        verbose_name="操作人",
    )
    point_record = models.OneToOneField(
        PointRecord,
        on_delete=models.PROTECT,
        related_name="manual_adjustment",
        null=True,
        blank=True,
        verbose_name="积分流水",
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "points_manual_adjustment"
        verbose_name = "人工加分"
        verbose_name_plural = "人工加分"
        ordering = ("-created_at", "-id")

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.point_record_id is None:
            from apps.points.services import manual_add_points

            self.point_record = manual_add_points(self.member, self.amount, reason=self.reason, operator=self.operator)
            super().save(update_fields=["point_record"])

    def __str__(self) -> str:
        return f"{self.member} +{self.amount}"

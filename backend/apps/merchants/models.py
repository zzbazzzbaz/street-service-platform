from django.conf import settings
from django.db import models


class Merchant(models.Model):
    class CategoryCode(models.TextChoices):
        FOOD = "food", "餐饮商户"
        RETAIL = "retail", "零售商超"
        REPAIR = "repair", "维修服务"
        HEALTHCARE = "healthcare", "医药健康"
        LIFE_SERVICE = "life_service", "生活服务"
        OTHER = "other", "其他"

    class AuditStatus(models.TextChoices):
        NONE = "none", "未提交"
        PENDING = "pending", "待审核"
        APPROVED = "approved", "已通过"
        REJECTED = "rejected", "已驳回"

    openid = models.CharField("OpenID", max_length=128, unique=True, null=True, blank=True)
    username = models.CharField("用户名", max_length=64, unique=True, null=True, blank=True)
    password = models.CharField("密码", max_length=128, blank=True)
    name = models.CharField("商户名称", max_length=100)
    contact_name = models.CharField("联系人", max_length=50, blank=True)
    phone = models.CharField("手机号", max_length=20, blank=True)
    address = models.CharField("经营地址", max_length=255, blank=True)
    community = models.CharField("所属社区", max_length=100, blank=True)
    merchant_nature = models.CharField("商户性质", max_length=100, blank=True)
    latitude = models.FloatField("纬度", null=True, blank=True)
    longitude = models.FloatField("经度", null=True, blank=True)
    category_code = models.CharField(
        "商户分类",
        max_length=32,
        choices=CategoryCode.choices,
        default=CategoryCode.OTHER,
    )
    business_hours = models.CharField("营业时间", max_length=100, blank=True)
    service_content = models.TextField("服务内容", blank=True)
    audit_status = models.CharField(
        "审核状态",
        max_length=20,
        choices=AuditStatus.choices,
        default=AuditStatus.NONE,
    )
    audit_remark = models.CharField("审核意见", max_length=255, blank=True)
    sort_order = models.PositiveIntegerField("排序值", null=True, blank=True, default=None, db_index=True)
    is_active = models.BooleanField("是否启用", default=True)
    deleted_at = models.DateTimeField("删除时间", null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_merchants",
        verbose_name="删除人",
    )
    delete_reason = models.CharField("删除原因", max_length=255, blank=True)
    deleted_username = models.CharField("原用户名", max_length=64, blank=True)
    deleted_phone = models.CharField("原手机号", max_length=20, blank=True)
    deleted_openid = models.CharField("原OpenID", max_length=128, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "merchants_merchant"
        verbose_name = "商户"
        verbose_name_plural = "商户"
        ordering = ("-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=["phone"],
                condition=~models.Q(phone=""),
                name="uniq_merchant_phone_when_present",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class MerchantSettlement(models.Model):
    class PeriodType(models.TextChoices):
        MONTH = "month", "自然月"
        CUSTOM = "custom", "自定义"

    class Status(models.TextChoices):
        PENDING = "pending", "待处理"
        PROCESSED = "processed", "已处理"

    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="settlements", verbose_name="商户")
    period_type = models.CharField("周期类型", max_length=20, choices=PeriodType.choices)
    period_label = models.CharField("周期标签", max_length=32)
    date_from = models.DateField("开始日期")
    date_to = models.DateField("结束日期")
    record_count = models.PositiveIntegerField("流水数", default=0)
    total_points = models.PositiveIntegerField("总积分", default=0)
    total_yuan_amount = models.DecimalField("总金额", max_digits=12, decimal_places=2, default=0)
    status = models.CharField("状态", max_length=20, choices=Status.choices, default=Status.PENDING)
    processed_at = models.DateTimeField("处理时间", null=True, blank=True)
    processor_name = models.CharField("处理人", max_length=80, blank=True)
    remark = models.TextField("备注", blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "merchant_settlement"
        verbose_name = "商户结算记录"
        verbose_name_plural = "商户结算记录"
        ordering = ("-date_from", "-id")

    def __str__(self) -> str:
        return f"{self.merchant} {self.period_label}"


class MerchantPointCode(models.Model):
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="point_codes", verbose_name="商户")
    points = models.PositiveIntegerField("固定积分")
    code = models.CharField("二维码标识", max_length=64, unique=True)
    is_active = models.BooleanField("是否启用", default=True)
    remark = models.CharField("备注", max_length=255, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "merchant_point_code"
        verbose_name = "商户固定积分码"
        verbose_name_plural = "商户固定积分码"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return f"{self.merchant} {self.points}积分"

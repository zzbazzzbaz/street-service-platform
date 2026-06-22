from django.db import models


class Merchant(models.Model):
    openid = models.CharField("OpenID", max_length=128, unique=True)
    name = models.CharField("商户名称", max_length=100)
    contact_name = models.CharField("联系人", max_length=50, blank=True)
    phone = models.CharField("手机号", max_length=20, blank=True)
    address = models.CharField("经营地址", max_length=255, blank=True)
    is_active = models.BooleanField("是否启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "merchants_merchant"
        verbose_name = "商户"
        verbose_name_plural = "商户"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return self.name


class MerchantProduct(models.Model):
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="products", verbose_name="商户")
    name = models.CharField("商品名称", max_length=120)
    image = models.ImageField("商品图片", upload_to="merchant-products/", blank=True)
    description = models.TextField("商品说明", blank=True)
    points_required = models.PositiveIntegerField("兑换所需积分")
    is_active = models.BooleanField("是否上架", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "merchants_product"
        verbose_name = "商户商品"
        verbose_name_plural = "商户商品"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return self.name


class ProductRedemption(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待交付"
        COMPLETED = "completed", "已完成"

    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="redemptions", verbose_name="商户")
    product = models.ForeignKey(MerchantProduct, on_delete=models.PROTECT, related_name="redemptions", verbose_name="商品")
    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="product_redemptions", verbose_name="用户")
    points_spent = models.PositiveIntegerField("消耗积分")
    status = models.CharField("状态", max_length=20, choices=Status.choices, default=Status.PENDING)
    point_record = models.ForeignKey(
        "points.PointRecord",
        on_delete=models.SET_NULL,
        related_name="product_redemptions",
        null=True,
        blank=True,
        verbose_name="关联积分流水",
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "merchants_product_redemption"
        verbose_name = "商品兑换记录"
        verbose_name_plural = "商品兑换记录"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return f"{self.member} - {self.product}"

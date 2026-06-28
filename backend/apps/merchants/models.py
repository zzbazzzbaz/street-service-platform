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

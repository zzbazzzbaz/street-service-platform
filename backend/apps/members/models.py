from django.db import models


class Member(models.Model):
    class IdentityType(models.TextChoices):
        NORMAL_USER = "normal_user", "普通用户"
        COURIER = "courier", "小哥"

    class AuditStatus(models.TextChoices):
        NONE = "none", "未提交"
        PENDING = "pending", "待审核"
        APPROVED = "approved", "已通过"
        REJECTED = "rejected", "已驳回"

    openid = models.CharField("OpenID", max_length=128, unique=True)
    username = models.CharField("用户名", max_length=64, unique=True, null=True, blank=True)
    password = models.CharField("密码", max_length=128, blank=True)
    nickname = models.CharField("昵称", max_length=64, blank=True)
    phone = models.CharField("手机号", max_length=20, blank=True)
    real_name = models.CharField("真实姓名", max_length=50, blank=True)
    identity_type = models.CharField(
        "身份类型",
        max_length=32,
        choices=IdentityType.choices,
        default=IdentityType.NORMAL_USER,
    )
    audit_status = models.CharField(
        "审核状态",
        max_length=20,
        choices=AuditStatus.choices,
        default=AuditStatus.NONE,
    )
    audit_remark = models.CharField("审核说明", max_length=255, blank=True)
    audit_submitted_at = models.DateTimeField("最近提交审核时间", null=True, blank=True)
    is_active = models.BooleanField("是否启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "members_member"
        verbose_name = "用户"
        verbose_name_plural = "用户"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return self.nickname or self.openid

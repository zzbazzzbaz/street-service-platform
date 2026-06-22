from django.db import models


class Member(models.Model):
    class Role(models.TextChoices):
        COURIER = "courier", "小哥用户"
        COMMUNITY = "community", "社区参与用户"

    openid = models.CharField("OpenID", max_length=128, unique=True)
    nickname = models.CharField("昵称", max_length=64, blank=True)
    phone = models.CharField("手机号", max_length=20, blank=True)
    role = models.CharField("角色", max_length=20, choices=Role.choices, default=Role.COMMUNITY)
    is_active = models.BooleanField("是否启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "members_member"
        verbose_name = "用户"
        verbose_name_plural = "用户"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return self.nickname or self.openid

from django.db import models


class Member(models.Model):
    class AuditStatus(models.TextChoices):
        NONE = "none", "未提交"
        PENDING = "pending", "待审核"
        APPROVED = "approved", "已通过"
        REJECTED = "rejected", "已驳回"

    class Gender(models.TextChoices):
        MALE = "男", "男"
        FEMALE = "女", "女"

    class Occupation(models.TextChoices):
        SF = "顺丰快递", "顺丰快递"
        JD = "京东快递", "京东快递"
        MEITUAN = "美团快递", "美团快递"
        DADA = "达达快递", "达达快递"
        STO = "申通快递", "申通快递"
        TAOBAO_SHANGOU = "淘宝闪购", "淘宝闪购"
        ZTO = "中通快递", "中通快递"
        OTHER = "其他", "其他"

    openid = models.CharField("OpenID", max_length=128, unique=True, null=True, blank=True)
    username = models.CharField("用户名", max_length=64, unique=True, null=True, blank=True)
    password = models.CharField("密码", max_length=128, blank=True)
    nickname = models.CharField("昵称", max_length=64, blank=True)
    phone = models.CharField("手机号", max_length=20, blank=True)
    real_name = models.CharField("真实姓名", max_length=50, blank=True)
    wechat_id = models.CharField("微信号", max_length=64, blank=True)
    gender = models.CharField("性别", max_length=8, blank=True, choices=Gender.choices)
    occupation = models.CharField("职业", max_length=64, blank=True, choices=Occupation.choices)
    is_party_member = models.BooleanField("是否党员", default=False)
    address = models.CharField("住址", max_length=255, blank=True)
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
        constraints = [
            models.UniqueConstraint(
                fields=["phone"],
                condition=~models.Q(phone=""),
                name="uniq_member_phone_when_present",
            ),
        ]

    def __str__(self) -> str:
        return self.nickname or self.username or self.real_name or f"member-{self.pk}"

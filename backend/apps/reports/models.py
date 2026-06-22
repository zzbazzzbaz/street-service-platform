from django.db import models


class Report(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待审核"
        APPROVED = "approved", "已通过"
        REJECTED = "rejected", "已驳回"

    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="reports", verbose_name="用户")
    title = models.CharField("标题", max_length=120)
    description = models.TextField("描述", blank=True)
    image = models.ImageField("图片", upload_to="reports/", blank=True)
    location = models.CharField("位置", max_length=255, blank=True)
    points = models.PositiveIntegerField("积分值", default=5)
    status = models.CharField("状态", max_length=20, choices=Status.choices, default=Status.PENDING)
    review_comment = models.CharField("审核意见", max_length=255, blank=True)
    point_record = models.ForeignKey(
        "points.PointRecord",
        on_delete=models.SET_NULL,
        related_name="reports",
        null=True,
        blank=True,
        verbose_name="关联积分流水",
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "reports_report"
        verbose_name = "随手拍"
        verbose_name_plural = "随手拍"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return self.title

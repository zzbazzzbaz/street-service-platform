from django.db import models


class CivicFeedback(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "已提交"
        ACCEPTED = "accepted", "已采纳"
        REJECTED = "rejected", "已驳回"

    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="civic_feedbacks", verbose_name="用户")
    title = models.CharField("标题", max_length=120)
    content = models.TextField("内容")
    material_urls = models.JSONField("材料图片URL列表", default=list, blank=True)
    status = models.CharField("状态", max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    reply = models.TextField("处理回复", blank=True)
    points = models.PositiveIntegerField("积分值", default=0)
    point_record = models.ForeignKey(
        "points.PointRecord",
        on_delete=models.SET_NULL,
        related_name="civic_feedbacks",
        null=True,
        blank=True,
        verbose_name="关联积分流水",
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "civic_feedback"
        verbose_name = "社情民意"
        verbose_name_plural = "社情民意"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return self.title

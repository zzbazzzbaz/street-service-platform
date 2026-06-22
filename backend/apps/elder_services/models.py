from django.db import models


class ElderServiceTask(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        PUBLISHED = "published", "已发布"
        CLOSED = "closed", "已关闭"

    title = models.CharField("标题", max_length=120)
    description = models.TextField("描述", blank=True)
    location = models.CharField("地点", max_length=255, blank=True)
    points = models.PositiveIntegerField("积分值", default=0)
    status = models.CharField("状态", max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "elder_service_task"
        verbose_name = "老人服务任务"
        verbose_name_plural = "老人服务任务"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return self.title


class ElderServiceFeedback(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待审核"
        APPROVED = "approved", "已通过"
        REJECTED = "rejected", "已驳回"

    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="elder_feedbacks", verbose_name="用户")
    task = models.ForeignKey(ElderServiceTask, on_delete=models.CASCADE, related_name="feedbacks", verbose_name="任务")
    content = models.TextField("反馈内容")
    image = models.ImageField("图片", upload_to="elder-services/feedbacks/", blank=True)
    status = models.CharField("状态", max_length=20, choices=Status.choices, default=Status.PENDING)
    review_comment = models.CharField("审核意见", max_length=255, blank=True)
    point_record = models.ForeignKey(
        "points.PointRecord",
        on_delete=models.SET_NULL,
        related_name="elder_feedbacks",
        null=True,
        blank=True,
        verbose_name="关联积分流水",
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "elder_service_feedback"
        verbose_name = "老人服务反馈"
        verbose_name_plural = "老人服务反馈"
        unique_together = (("member", "task"),)
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return f"{self.member} - {self.task}"

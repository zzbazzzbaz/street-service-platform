from django.db import models
from django.db.models import Q


class ElderCareRelation(models.Model):
    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="elder_care_relations", verbose_name="帮扶人")
    elder_name = models.CharField("老人称呼", max_length=80)
    elder_address = models.CharField("老人地址", max_length=255)
    frequency = models.CharField("服务频次", max_length=80, blank=True)
    is_active = models.BooleanField("是否有效", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "elder_care_relation"
        verbose_name = "结对帮扶关系"
        verbose_name_plural = "结对帮扶关系"
        ordering = ("-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=["member"],
                condition=Q(is_active=True),
                name="uniq_active_relation_per_member",
            ),
            models.UniqueConstraint(
                fields=["elder_name", "elder_address"],
                condition=Q(is_active=True),
                name="uniq_active_elder",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.member} - {self.elder_name}"


class ElderServiceTask(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        PUBLISHED = "published", "已发布"
        CLOSED = "closed", "已关闭"

    title = models.CharField("标题", max_length=120)
    relation = models.ForeignKey(
        ElderCareRelation,
        on_delete=models.PROTECT,
        related_name="tasks",
        null=True,
        blank=True,
        verbose_name="对口关系",
    )
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
    relation = models.ForeignKey(
        ElderCareRelation,
        on_delete=models.PROTECT,
        related_name="feedbacks",
        null=True,
        blank=True,
        verbose_name="对口关系",
    )
    task = models.ForeignKey(
        ElderServiceTask,
        on_delete=models.CASCADE,
        related_name="feedbacks",
        null=True,
        blank=True,
        verbose_name="关联任务（旧）",
    )
    elder_name = models.CharField("老人姓名快照", max_length=80, blank=True)
    elder_address = models.CharField("老人地址快照", max_length=255, blank=True)
    content = models.TextField("反馈内容")
    image = models.ImageField("图片", upload_to="elder-services/feedbacks/", blank=True)
    image_urls = models.JSONField("图片URL列表", default=list, blank=True)
    points = models.PositiveIntegerField("积分值", default=0)
    status = models.CharField("状态", max_length=20, choices=Status.choices, default=Status.PENDING)
    review_comment = models.CharField("审核意见", max_length=255, blank=True)
    reviewed_at = models.DateTimeField("审核时间", null=True, blank=True)
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
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return f"{self.member} - {self.elder_name or (self.task.title if self.task_id else '')}"

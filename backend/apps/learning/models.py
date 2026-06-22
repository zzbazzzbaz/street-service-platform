from django.db import models


class LearningContent(models.Model):
    title = models.CharField("标题", max_length=120)
    cover = models.ImageField("封面", upload_to="learning/covers/", blank=True)
    body = models.TextField("正文", blank=True)
    points = models.PositiveIntegerField("积分值", default=0)
    required_seconds = models.PositiveIntegerField("要求学习秒数", default=60)
    is_active = models.BooleanField("是否上架", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "learning_content"
        verbose_name = "学习内容"
        verbose_name_plural = "学习内容"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return self.title


class LearningRecord(models.Model):
    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="learning_records", verbose_name="用户")
    content = models.ForeignKey(LearningContent, on_delete=models.CASCADE, related_name="records", verbose_name="学习内容")
    learned_seconds = models.PositiveIntegerField("学习秒数", default=0)
    is_completed = models.BooleanField("是否完成", default=False)
    completed_at = models.DateTimeField("完成时间", null=True, blank=True)
    point_record = models.ForeignKey(
        "points.PointRecord",
        on_delete=models.SET_NULL,
        related_name="learning_records",
        null=True,
        blank=True,
        verbose_name="关联积分流水",
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "learning_record"
        verbose_name = "学习记录"
        verbose_name_plural = "学习记录"
        unique_together = (("member", "content"),)
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return f"{self.member} - {self.content}"

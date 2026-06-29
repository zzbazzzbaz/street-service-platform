from django.db import models


class ProblemFeedback(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "已提交"
        PROCESSING = "processing", "处理中"
        REPLIED = "replied", "已回复"
        CLOSED = "closed", "已关闭"

    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="problem_feedbacks", verbose_name="用户")
    title = models.CharField("标题", max_length=120)
    content = models.TextField("内容")
    status = models.CharField("状态", max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    reply = models.TextField("回复", blank=True)
    replied_at = models.DateTimeField("回复时间", null=True, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "problem_feedback"
        verbose_name = "问题反馈"
        verbose_name_plural = "问题反馈"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return self.title

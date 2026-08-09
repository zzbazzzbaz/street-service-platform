from __future__ import annotations

from io import BytesIO
from uuid import uuid4

import qrcode
from django.core.files.base import ContentFile
from django.db import models


class Activity(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        PUBLISHED = "published", "已发布"
        CLOSED = "closed", "已关闭"

    class ActivityType(models.TextChoices):
        VOLUNTEER = "volunteer", "志愿任务"
        OFFLINE = "offline", "线下活动"

    title = models.CharField("标题", max_length=120)
    body = models.TextField("正文", blank=True)
    location = models.CharField("地点", max_length=255, blank=True)
    latitude = models.FloatField("纬度", null=True, blank=True)
    longitude = models.FloatField("经度", null=True, blank=True)
    start_time = models.DateTimeField("开始时间")
    end_time = models.DateTimeField("结束时间")
    points = models.PositiveIntegerField("积分值", default=0)
    status = models.CharField("状态", max_length=20, choices=Status.choices, default=Status.DRAFT)
    activity_type = models.CharField(
        "活动类型",
        max_length=20,
        choices=ActivityType.choices,
        default=ActivityType.VOLUNTEER,
    )
    checkin_code = models.CharField("签到码", max_length=64, unique=True, blank=True)
    checkin_qr_image = models.ImageField("签到二维码", upload_to="activities/qrcodes/", blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "activities_activity"
        verbose_name = "活动"
        verbose_name_plural = "活动"
        ordering = ("-start_time", "-id")

    def save(self, *args, **kwargs):
        if not self.checkin_code:
            self.checkin_code = uuid4().hex
        super().save(*args, **kwargs)
        if not self.checkin_qr_image:
            self._generate_qr_image()
            super().save(update_fields=["checkin_qr_image"])

    def _generate_qr_image(self):
        image = qrcode.make(self.checkin_code)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        self.checkin_qr_image.save(f"activity-{self.pk}-checkin.png", ContentFile(buffer.getvalue()), save=False)

    def __str__(self) -> str:
        return self.title


class ActivitySignup(models.Model):
    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="activity_signups", verbose_name="用户")
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="signups", verbose_name="活动")
    created_at = models.DateTimeField("报名时间", auto_now_add=True)

    class Meta:
        db_table = "activities_signup"
        verbose_name = "活动报名"
        verbose_name_plural = "活动报名"
        unique_together = (("member", "activity"),)
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return f"{self.member} - {self.activity}"


class ActivityCheckin(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待确认"
        CONFIRMED = "confirmed", "已确认"
        REJECTED = "rejected", "已驳回"

    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="activity_checkins", verbose_name="用户")
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="checkins", verbose_name="活动")
    status = models.CharField("状态", max_length=20, choices=Status.choices, default=Status.PENDING)
    review_comment = models.CharField("审核意见", max_length=255, blank=True)
    point_record = models.ForeignKey(
        "points.PointRecord",
        on_delete=models.SET_NULL,
        related_name="activity_checkins",
        null=True,
        blank=True,
        verbose_name="关联积分流水",
    )
    created_at = models.DateTimeField("签到时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "activities_checkin"
        verbose_name = "活动签到"
        verbose_name_plural = "活动签到"
        unique_together = (("member", "activity"),)
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return f"{self.member} - {self.activity}"

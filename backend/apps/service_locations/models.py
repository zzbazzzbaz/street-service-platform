from django.db import models


class ServiceLocation(models.Model):
    name = models.CharField("名称", max_length=100)
    address = models.CharField("地址", max_length=200)
    business_hours = models.CharField("开放时间", max_length=100)
    service_content = models.CharField("服务事项", max_length=500)
    latitude = models.FloatField("纬度", null=True, blank=True)
    longitude = models.FloatField("经度", null=True, blank=True)
    is_active = models.BooleanField("是否展示", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "service_location"
        verbose_name = "服务阵地"
        verbose_name_plural = "服务阵地"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return self.name

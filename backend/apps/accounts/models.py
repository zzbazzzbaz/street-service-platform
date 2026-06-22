from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    is_backend_manager = models.BooleanField("后台业务管理员", default=False)

    class Meta:
        db_table = "accounts_user"
        verbose_name = "后台账号"
        verbose_name_plural = "后台账号"

    def save(self, *args, **kwargs):
        if self.is_backend_manager:
            self.is_staff = True
        super().save(*args, **kwargs)

from django.contrib import admin

from apps.members.models import Member
from shared.admin import BackendManagerAdminMixin


@admin.register(Member)
class MemberAdmin(BackendManagerAdminMixin):
    list_display = ("id", "openid", "nickname", "phone", "role", "is_active", "created_at")
    list_filter = ("role", "is_active", "created_at")
    search_fields = ("openid", "nickname", "phone")
    readonly_fields = ("created_at",)

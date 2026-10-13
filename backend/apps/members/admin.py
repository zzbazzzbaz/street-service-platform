from django.contrib import admin

from apps.members.models import Member
from shared.admin import BackendManagerAdminMixin


@admin.register(Member)
class MemberAdmin(BackendManagerAdminMixin):
    list_display = ("id", "openid", "nickname", "phone", "real_name", "wechat_id", "occupation", "audit_status", "is_active", "created_at")
    list_filter = ("occupation", "audit_status", "is_active", "created_at")
    search_fields = ("openid", "username", "nickname", "phone", "real_name", "wechat_id")
    readonly_fields = ("created_at",)

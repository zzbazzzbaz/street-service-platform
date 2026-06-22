from django.contrib import admin

from apps.learning.models import LearningContent, LearningRecord
from shared.admin import BackendManagerAdminMixin


@admin.register(LearningContent)
class LearningContentAdmin(BackendManagerAdminMixin):
    list_display = ("id", "title", "points", "required_seconds", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("title",)
    readonly_fields = ("created_at",)


@admin.register(LearningRecord)
class LearningRecordAdmin(BackendManagerAdminMixin):
    list_display = ("id", "member", "content", "learned_seconds", "is_completed", "completed_at")
    list_filter = ("is_completed", "completed_at", "created_at")
    search_fields = ("member__openid", "member__nickname", "content__title")
    readonly_fields = ("member", "content", "learned_seconds", "is_completed", "completed_at", "point_record", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

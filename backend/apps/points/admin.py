from django.contrib import admin

from apps.points.models import ManualPointAdjustment, PointAccount, PointRecord
from shared.admin import BackendManagerAdminMixin


@admin.register(PointAccount)
class PointAccountAdmin(BackendManagerAdminMixin):
    list_display = ("id", "member", "balance")
    search_fields = ("member__openid", "member__nickname", "member__phone")
    readonly_fields = ("member", "balance")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PointRecord)
class PointRecordAdmin(BackendManagerAdminMixin):
    list_display = ("id", "member", "amount", "balance_after", "change_type", "source_type", "reason", "operator", "created_at")
    list_filter = ("change_type", "source_type", "created_at")
    search_fields = ("member__openid", "member__nickname", "reason")
    readonly_fields = (
        "member",
        "amount",
        "balance_after",
        "change_type",
        "source_type",
        "source_id",
        "reason",
        "operator",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return self._has_backend_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ManualPointAdjustment)
class ManualPointAdjustmentAdmin(BackendManagerAdminMixin):
    list_display = ("id", "member", "amount", "reason", "operator", "point_record", "created_at")
    list_filter = ("created_at",)
    search_fields = ("member__openid", "member__nickname", "reason")
    readonly_fields = ("operator", "point_record", "created_at")

    def save_model(self, request, obj, form, change):
        if obj.operator_id is None:
            obj.operator = request.user
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return False
        return super().has_change_permission(request, obj)

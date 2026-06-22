from django.contrib import admin

from apps.activities.models import Activity, ActivityCheckin, ActivitySignup
from apps.activities.services import review_checkin
from shared.admin import BackendManagerAdminMixin


@admin.register(Activity)
class ActivityAdmin(BackendManagerAdminMixin):
    list_display = ("id", "title", "location", "status", "points", "start_time", "end_time")
    list_filter = ("status", "start_time", "end_time")
    search_fields = ("title", "location")
    readonly_fields = ("checkin_code", "checkin_qr_image", "created_at")


@admin.register(ActivitySignup)
class ActivitySignupAdmin(BackendManagerAdminMixin):
    list_display = ("id", "member", "activity", "created_at")
    list_filter = ("created_at",)
    search_fields = ("member__openid", "member__nickname", "activity__title")
    readonly_fields = ("member", "activity", "created_at")

    def has_add_permission(self, request):
        return False


@admin.register(ActivityCheckin)
class ActivityCheckinAdmin(BackendManagerAdminMixin):
    list_display = ("id", "member", "activity", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("member__openid", "member__nickname", "activity__title")
    readonly_fields = ("point_record", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if change:
            old = ActivityCheckin.objects.get(pk=obj.pk)
            if old.status == ActivityCheckin.Status.PENDING and obj.status != ActivityCheckin.Status.PENDING:
                action = "confirm" if obj.status == ActivityCheckin.Status.CONFIRMED else "reject"
                review_checkin(old, action=action, comment=obj.review_comment, operator=request.user)
                return
        super().save_model(request, obj, form, change)

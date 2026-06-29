from django.contrib import admin

from apps.reports.models import Report
from apps.reports.services import review_report
from shared.admin import BackendManagerAdminMixin, admin_image_preview


@admin.register(Report)
class ReportAdmin(BackendManagerAdminMixin):
    list_display = ("id", "member", "category_code", "title", "location", "status", "points", "created_at")
    list_filter = ("category_code", "status", "created_at")
    search_fields = ("member__openid", "member__nickname", "title", "location")
    readonly_fields = ("image_preview", "point_record", "created_at", "updated_at")

    @admin.display(description="图片预览")
    def image_preview(self, obj):
        return admin_image_preview(obj.image)

    def save_model(self, request, obj, form, change):
        if change:
            old = Report.objects.get(pk=obj.pk)
            if old.status == Report.Status.PENDING and obj.status != Report.Status.PENDING:
                action = "approve" if obj.status == Report.Status.APPROVED else "reject"
                review_report(old, action=action, comment=obj.review_comment, operator=request.user)
                return
        super().save_model(request, obj, form, change)

from django.contrib import admin

from apps.elder_services.models import ElderServiceFeedback, ElderServiceTask
from apps.elder_services.services import review_feedback
from shared.admin import BackendManagerAdminMixin


@admin.register(ElderServiceTask)
class ElderServiceTaskAdmin(BackendManagerAdminMixin):
    list_display = ("id", "title", "location", "points", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "location")
    readonly_fields = ("created_at",)


@admin.register(ElderServiceFeedback)
class ElderServiceFeedbackAdmin(BackendManagerAdminMixin):
    list_display = ("id", "member", "task", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("member__openid", "member__nickname", "task__title", "content")
    readonly_fields = ("point_record", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if change:
            old = ElderServiceFeedback.objects.get(pk=obj.pk)
            if old.status == ElderServiceFeedback.Status.PENDING and obj.status != ElderServiceFeedback.Status.PENDING:
                action = "approve" if obj.status == ElderServiceFeedback.Status.APPROVED else "reject"
                review_feedback(old, action=action, comment=obj.review_comment, operator=request.user)
                return
        super().save_model(request, obj, form, change)

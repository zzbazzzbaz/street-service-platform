from django.contrib import admin

from apps.civic_feedbacks.models import CivicFeedback
from apps.civic_feedbacks.services import accept_civic_feedback, reject_civic_feedback
from shared.admin import BackendManagerAdminMixin


@admin.register(CivicFeedback)
class CivicFeedbackAdmin(BackendManagerAdminMixin):
    list_display = ("id", "member", "title", "status", "points", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("member__openid", "member__nickname", "member__real_name", "title", "content")
    readonly_fields = ("point_record", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if change:
            old = CivicFeedback.objects.get(pk=obj.pk)
            if old.status == CivicFeedback.Status.SUBMITTED and obj.status == CivicFeedback.Status.ACCEPTED:
                old.points = obj.points
                old.save(update_fields=["points", "updated_at"])
                accept_civic_feedback(old, reply=obj.reply, operator=request.user)
                return
            if old.status == CivicFeedback.Status.SUBMITTED and obj.status == CivicFeedback.Status.REJECTED:
                reject_civic_feedback(old, reply=obj.reply)
                return
        super().save_model(request, obj, form, change)

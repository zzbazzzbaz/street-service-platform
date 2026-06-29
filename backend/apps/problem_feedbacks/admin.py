from django.contrib import admin

from apps.problem_feedbacks.models import ProblemFeedback
from apps.problem_feedbacks.services import reply_problem_feedback
from shared.admin import BackendManagerAdminMixin


@admin.register(ProblemFeedback)
class ProblemFeedbackAdmin(BackendManagerAdminMixin):
    list_display = ("id", "member", "title", "status", "created_at", "replied_at")
    list_filter = ("status", "created_at", "replied_at")
    search_fields = ("member__openid", "member__nickname", "member__real_name", "title", "content")
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if change:
            old = ProblemFeedback.objects.get(pk=obj.pk)
            if obj.reply and old.reply != obj.reply:
                reply_problem_feedback(old, reply=obj.reply)
                return
        super().save_model(request, obj, form, change)

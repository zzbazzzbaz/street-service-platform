from django.contrib import admin

from apps.elder_services.models import ElderCareRelation, ElderServiceFeedback, ElderServiceTask
from apps.elder_services.services import review_feedback
from shared.admin import BackendManagerAdminMixin, admin_image_preview


@admin.register(ElderCareRelation)
class ElderCareRelationAdmin(BackendManagerAdminMixin):
    list_display = ("id", "member", "elder_name", "elder_address", "frequency", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("member__openid", "member__nickname", "member__real_name", "elder_name", "elder_address")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ElderServiceTask)
class ElderServiceTaskAdmin(BackendManagerAdminMixin):
    list_display = ("id", "title", "relation", "location", "points", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "location", "relation__elder_name", "relation__member__real_name")
    readonly_fields = ("created_at",)


@admin.register(ElderServiceFeedback)
class ElderServiceFeedbackAdmin(BackendManagerAdminMixin):
    list_display = ("id", "member", "relation", "task", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("member__openid", "member__nickname", "task__title", "content")
    readonly_fields = ("image_preview", "point_record", "created_at", "updated_at")

    @admin.display(description="图片预览")
    def image_preview(self, obj):
        return admin_image_preview(obj.image)

    def save_model(self, request, obj, form, change):
        if change:
            old = ElderServiceFeedback.objects.get(pk=obj.pk)
            if old.status == ElderServiceFeedback.Status.PENDING and obj.status != ElderServiceFeedback.Status.PENDING:
                action = "approve" if obj.status == ElderServiceFeedback.Status.APPROVED else "reject"
                review_feedback(old, action=action, comment=obj.review_comment, operator=request.user)
                return
        super().save_model(request, obj, form, change)

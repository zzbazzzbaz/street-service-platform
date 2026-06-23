from django.contrib import admin
from django.utils.html import format_html


def admin_image_preview(file_field, *, empty_text: str = "暂无图片", size: int = 160):
    if not file_field:
        return empty_text
    try:
        url = file_field.url
    except ValueError:
        return empty_text
    return format_html(
        '<a href="{}" target="_blank" rel="noopener">'
        '<img src="{}" style="max-width:{}px;max-height:{}px;border:1px solid #ddd;border-radius:4px;" />'
        '</a><br><a href="{}" target="_blank" rel="noopener">打开原图</a>',
        url,
        url,
        size,
        size,
        url,
    )


class BackendManagerAdminMixin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return self._has_backend_permission(request)

    def has_view_permission(self, request, obj=None):
        return self._has_backend_permission(request)

    def has_add_permission(self, request):
        return self._has_backend_permission(request)

    def has_change_permission(self, request, obj=None):
        return self._has_backend_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self._has_backend_permission(request)

    def _has_backend_permission(self, request) -> bool:
        user = request.user
        return bool(
            user
            and user.is_active
            and user.is_staff
            and getattr(user, "is_backend_manager", False)
        )

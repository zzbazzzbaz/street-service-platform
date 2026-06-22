from django.contrib import admin


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

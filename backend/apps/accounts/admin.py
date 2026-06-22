from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("id", "username", "is_backend_manager", "is_active", "is_staff", "is_superuser", "last_login")
    list_filter = ("is_backend_manager", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("业务权限", {"fields": ("is_backend_manager",)}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("业务权限", {"fields": ("is_backend_manager",)}),
    )

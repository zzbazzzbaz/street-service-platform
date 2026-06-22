from django.contrib import admin

from apps.merchants.models import Merchant
from shared.admin import BackendManagerAdminMixin


@admin.register(Merchant)
class MerchantAdmin(BackendManagerAdminMixin):
    list_display = ("id", "openid", "name", "contact_name", "phone", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("openid", "name", "contact_name", "phone")
    readonly_fields = ("created_at",)

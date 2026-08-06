from django.contrib import admin

from apps.merchants.models import Merchant, MerchantPointCode, MerchantSettlement
from shared.admin import BackendManagerAdminMixin


@admin.register(Merchant)
class MerchantAdmin(BackendManagerAdminMixin):
    list_display = ("id", "openid", "name", "contact_name", "phone", "address", "latitude", "longitude", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("openid", "name", "contact_name", "phone")
    readonly_fields = ("created_at",)


@admin.register(MerchantPointCode)
class MerchantPointCodeAdmin(BackendManagerAdminMixin):
    list_display = ("id", "merchant", "points", "code", "is_active", "remark", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("merchant__name", "code", "remark")
    readonly_fields = ("code", "created_at", "updated_at")


@admin.register(MerchantSettlement)
class MerchantSettlementAdmin(BackendManagerAdminMixin):
    list_display = ("id", "merchant", "period_label", "date_from", "date_to", "record_count", "total_points", "total_yuan_amount", "status")
    list_filter = ("period_type", "status", "date_from")
    search_fields = ("merchant__name", "merchant__openid", "period_label", "processor_name")
    readonly_fields = ("created_at", "updated_at")

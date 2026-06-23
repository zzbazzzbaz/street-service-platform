from django.contrib import admin

from apps.merchants.models import Merchant, MerchantProduct, ProductRedemption
from shared.admin import BackendManagerAdminMixin, admin_image_preview


@admin.register(Merchant)
class MerchantAdmin(BackendManagerAdminMixin):
    list_display = ("id", "openid", "name", "contact_name", "phone", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("openid", "name", "contact_name", "phone")
    readonly_fields = ("created_at",)


@admin.register(MerchantProduct)
class MerchantProductAdmin(BackendManagerAdminMixin):
    list_display = ("id", "merchant", "name", "points_required", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("merchant__name", "name")
    readonly_fields = ("image_preview", "created_at")

    @admin.display(description="商品图片预览")
    def image_preview(self, obj):
        return admin_image_preview(obj.image)


@admin.register(ProductRedemption)
class ProductRedemptionAdmin(BackendManagerAdminMixin):
    list_display = ("id", "merchant", "product", "member", "points_spent", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("merchant__name", "product__name", "member__openid", "member__nickname")
    readonly_fields = ("merchant", "product", "member", "points_spent", "point_record", "created_at")

    def has_add_permission(self, request):
        return False

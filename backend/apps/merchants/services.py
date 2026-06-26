from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from apps.members.models import Member
from apps.merchants.models import Merchant, MerchantProduct, ProductRedemption
from apps.points.models import PointRecord
from apps.points.services import deduct_points
from shared.auth import issue_token
from shared.exceptions import BusinessError


def merchant_data(merchant: Merchant) -> dict:
    return {
        "id": merchant.id,
        "openid": merchant.openid,
        "name": merchant.name,
        "contact_name": merchant.contact_name,
        "phone": merchant.phone,
        "address": merchant.address,
        "is_active": merchant.is_active,
    }


def test_login(openid: str) -> dict:
    openid = openid.strip()
    if not openid:
        raise BusinessError("openid 不能为空")
    merchant, _ = Merchant.objects.get_or_create(openid=openid, defaults={"name": f"测试商户-{openid}"})
    token, expires_in = issue_token(subject_type="merchant", openid=openid)
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "merchant": merchant_data(merchant),
    }


def wechat_login_placeholder(code: str) -> dict:
    code = code.strip()
    if not code:
        raise BusinessError("openid 或 code 不能为空", code=40000)
    if not settings.WECHAT_MINIAPP_APPID or not settings.WECHAT_MINIAPP_SECRET:
        raise BusinessError("商户微信登录未配置，开发期请使用测试登录", code=40000)
    raise BusinessError("商户微信登录暂未接入", code=40000)


def product_data(product: MerchantProduct, request=None) -> dict:
    from shared.media import file_url

    return {
        "id": product.id,
        "merchant_id": product.merchant_id,
        "merchant_name": product.merchant.name,
        "name": product.name,
        "image": file_url(request, product.image) if request is not None else (product.image.url if product.image else ""),
        "description": product.description,
        "points_required": product.points_required,
        "is_active": product.is_active,
        "created_at": product.created_at,
    }


def merchant_fixed_code_data(merchant: Merchant) -> dict:
    mode = "product_redemption"
    return {
        "merchant_id": merchant.id,
        "merchant_name": merchant.name,
        "qr_payload": f"street://merchant-products?merchant_id={merchant.id}&mode={mode}",
        "qrcode_url": "",
        "mode": mode,
    }


def redemption_data(redemption: ProductRedemption) -> dict:
    return {
        "id": redemption.id,
        "merchant_id": redemption.merchant_id,
        "product_id": redemption.product_id,
        "product_name": redemption.product.name,
        "member_id": redemption.member_id,
        "points_spent": redemption.points_spent,
        "status": redemption.status,
        "created_at": redemption.created_at,
    }


@transaction.atomic
def complete_redemption(redemption: ProductRedemption) -> ProductRedemption:
    redemption = ProductRedemption.objects.select_for_update().select_related("merchant", "product").get(pk=redemption.pk)
    if redemption.status == ProductRedemption.Status.COMPLETED:
        raise BusinessError("兑换记录已完成")
    redemption.status = ProductRedemption.Status.COMPLETED
    redemption.save(update_fields=["status"])
    return redemption


@transaction.atomic
def redeem_product(member: Member, product: MerchantProduct) -> ProductRedemption:
    product = MerchantProduct.objects.select_for_update().select_related("merchant").get(pk=product.pk)
    if not product.is_active:
        raise BusinessError("商品已下架")
    if product.points_required <= 0:
        raise BusinessError("商品兑换积分必须大于 0")
    point_record = deduct_points(
        member,
        product.points_required,
        source_type=PointRecord.SourceType.PRODUCT_REDEMPTION,
        source_id=f"product-{product.id}",
        reason=f"兑换商品：{product.name}",
    )
    redemption = ProductRedemption.objects.create(
        merchant=product.merchant,
        product=product,
        member=member,
        points_spent=product.points_required,
        status=ProductRedemption.Status.PENDING,
        point_record=point_record,
    )
    point_record.source_id = str(redemption.id)
    point_record.save(update_fields=["source_id"])
    return redemption


def merchant_redemption_summary(merchant: Merchant, *, month: str) -> dict:
    try:
        start = timezone.datetime.strptime(month, "%Y-%m").replace(tzinfo=timezone.get_current_timezone())
    except ValueError as exc:
        raise BusinessError("月份格式必须为 YYYY-MM") from exc
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    queryset = ProductRedemption.objects.filter(merchant=merchant, created_at__gte=start, created_at__lt=end)
    aggregate = queryset.aggregate(
        redemption_count=Count("id"),
        product_count=Count("product", distinct=True),
        points_total=Sum("points_spent"),
    )
    return {
        "month": month,
        "redemption_count": aggregate["redemption_count"] or 0,
        "product_count": aggregate["product_count"] or 0,
        "points_total": aggregate["points_total"] or 0,
    }

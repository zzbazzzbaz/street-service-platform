from ninja import Router
from django.shortcuts import get_object_or_404

from apps.merchants.models import Merchant, MerchantProduct, ProductRedemption
from apps.merchants.schemas import (
    MerchantLoginOut,
    MerchantOut,
    MerchantProductOut,
    MerchantProductsData,
    MerchantRedemptionSummaryOut,
    MerchantWechatLoginIn,
    ProductRedemptionOut,
    ProductRedemptionsData,
    PublicMerchantsData,
)
from apps.merchants.services import complete_redemption, merchant_data, merchant_redemption_summary, product_data, public_merchant_data, redeem_product, redemption_data, test_login, wechat_login_placeholder
from shared.api import ErrorResponse, SuccessResponse, error_response, success_response
from shared.auth import TokenError
from shared.exceptions import BusinessError
from shared.pagination import paginate_queryset
from shared.services import authenticate_member
from shared.services import authenticate_merchant


merchant_auth_router = Router(tags=["商户认证"])
public_merchant_router = Router(tags=["商户"])
merchant_router = Router(tags=["商户"])
product_router = Router(tags=["商品兑换"])
redemption_router = Router(tags=["商品兑换记录"])


@merchant_auth_router.post("/wechat-login", response={200: SuccessResponse[MerchantLoginOut], 400: ErrorResponse})
def merchant_wechat_login(request, payload: MerchantWechatLoginIn):
    try:
        if payload.openid.strip():
            return success_response(test_login(payload.openid))
        return success_response(wechat_login_placeholder(payload.code))
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@merchant_router.get("/me", response={200: SuccessResponse[MerchantOut], 401: ErrorResponse, 403: ErrorResponse})
def merchant_me(request):
    try:
        merchant = authenticate_merchant(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(merchant_data(merchant))


@public_merchant_router.get("", response={200: SuccessResponse[PublicMerchantsData], 401: ErrorResponse, 403: ErrorResponse})
def public_merchants(request, page: int = 1, page_size: int = 20):
    try:
        authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    items, page_data = paginate_queryset(Merchant.objects.filter(is_active=True), page=page, page_size=page_size)
    return success_response({"items": [public_merchant_data(item) for item in items], **page_data})


@product_router.get("", response={200: SuccessResponse[MerchantProductsData], 401: ErrorResponse, 403: ErrorResponse})
def merchant_products(request, page: int = 1, page_size: int = 20, merchant_id: int | None = None):
    try:
        authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    queryset = MerchantProduct.objects.filter(is_active=True, merchant__is_active=True).select_related("merchant")
    if merchant_id is not None:
        queryset = queryset.filter(merchant_id=merchant_id)
    items, page_data = paginate_queryset(queryset, page=page, page_size=page_size)
    return success_response({"items": [product_data(item, request=request) for item in items], **page_data})


@product_router.get("/{product_id}", response={200: SuccessResponse[MerchantProductOut], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def merchant_product_detail(request, product_id: int):
    try:
        authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    product = get_object_or_404(MerchantProduct.objects.select_related("merchant"), pk=product_id, is_active=True)
    return success_response(product_data(product, request=request))


@product_router.post("/{product_id}/redeem", response={200: SuccessResponse[ProductRedemptionOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def redeem_merchant_product(request, product_id: int):
    try:
        member = authenticate_member(request)
        product = get_object_or_404(MerchantProduct.objects.select_related("merchant"), pk=product_id)
        redemption = redeem_product(member, product)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(redemption_data(redemption))


@redemption_router.get("", response={200: SuccessResponse[ProductRedemptionsData], 401: ErrorResponse, 403: ErrorResponse})
def my_product_redemptions(request, page: int = 1, page_size: int = 20):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    items, page_data = paginate_queryset(member.product_redemptions.select_related("merchant", "product", "member", "point_record"), page=page, page_size=page_size)
    return success_response({"items": [redemption_data(item) for item in items], **page_data})


@merchant_router.get("/redemptions", response={200: SuccessResponse[ProductRedemptionsData], 401: ErrorResponse, 403: ErrorResponse})
def merchant_redemptions(request, page: int = 1, page_size: int = 20):
    try:
        merchant = authenticate_merchant(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    items, page_data = paginate_queryset(merchant.redemptions.select_related("merchant", "member", "product", "point_record"), page=page, page_size=page_size)
    return success_response({"items": [redemption_data(item) for item in items], **page_data})


@merchant_router.post("/redemptions/{redemption_id}/complete", response={200: SuccessResponse[ProductRedemptionOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def merchant_complete_redemption(request, redemption_id: int):
    try:
        merchant = authenticate_merchant(request)
        redemption = get_object_or_404(ProductRedemption.objects.select_related("merchant", "member", "product", "point_record"), pk=redemption_id, merchant=merchant)
        return success_response(redemption_data(complete_redemption(redemption)))
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@merchant_router.get("/redemptions/summary", response={200: SuccessResponse[MerchantRedemptionSummaryOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def merchant_redemptions_summary(request, month: str):
    try:
        merchant = authenticate_merchant(request)
        data = merchant_redemption_summary(merchant, month=month)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(data)

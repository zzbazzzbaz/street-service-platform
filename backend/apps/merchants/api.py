from django.shortcuts import get_object_or_404
from ninja import Router

from apps.merchants.models import Merchant
from apps.merchants.schemas import (
    MerchantFixedCodeOut,
    MerchantLoginOut,
    MerchantOut,
    MerchantPaymentInfoOut,
    MerchantPointPaymentIn,
    MerchantPointPaymentOut,
    MerchantPointRecordsData,
    MerchantWechatLoginIn,
    PublicMerchantsData,
)
from apps.merchants.services import (
    fixed_code_data,
    merchant_data,
    merchant_payment_info,
    merchant_point_record_data,
    payment_record_data,
    pay_merchant_with_points,
    public_merchant_data,
    test_login,
    wechat_login_placeholder,
)
from apps.points.models import PointRecord
from shared.api import ErrorResponse, SuccessResponse, error_response, success_response
from shared.auth import TokenError
from shared.exceptions import BusinessError
from shared.pagination import paginate_queryset
from shared.services import authenticate_member, authenticate_merchant


merchant_auth_router = Router(tags=["商户认证"])
public_merchant_router = Router(tags=["商户"])
merchant_router = Router(tags=["商户"])


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


@merchant_router.get("/fixed-code", response={200: SuccessResponse[MerchantFixedCodeOut], 401: ErrorResponse, 403: ErrorResponse})
def merchant_fixed_code(request):
    try:
        merchant = authenticate_merchant(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(fixed_code_data(merchant))


@merchant_router.get("/point-records", response={200: SuccessResponse[MerchantPointRecordsData], 401: ErrorResponse, 403: ErrorResponse})
def merchant_point_records(request, page: int = 1, page_size: int = 20):
    try:
        merchant = authenticate_merchant(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    queryset = PointRecord.objects.filter(
        merchant=merchant,
        source_type=PointRecord.SourceType.MERCHANT_PAYMENT,
    ).select_related("merchant", "member")
    items, page_data = paginate_queryset(queryset, page=page, page_size=page_size)
    return success_response({"items": [merchant_point_record_data(item) for item in items], **page_data})


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


@public_merchant_router.get("/{merchant_id}/payment-info", response={200: SuccessResponse[MerchantPaymentInfoOut], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def public_merchant_payment_info(request, merchant_id: int):
    try:
        member = authenticate_member(request)
        merchant = get_object_or_404(Merchant, pk=merchant_id)
        return success_response(merchant_payment_info(member, merchant))
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@public_merchant_router.post("/{merchant_id}/point-payments", response={200: SuccessResponse[MerchantPointPaymentOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def public_merchant_point_payment(request, merchant_id: int, payload: MerchantPointPaymentIn):
    try:
        member = authenticate_member(request)
        merchant = get_object_or_404(Merchant, pk=merchant_id)
        record = pay_merchant_with_points(member, merchant, payload.points, request_no=payload.request_no)
        return success_response(payment_record_data(record))
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)

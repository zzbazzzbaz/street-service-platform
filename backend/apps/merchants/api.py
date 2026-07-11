from django.shortcuts import get_object_or_404
from ninja import Router

from apps.merchants.models import Merchant
from apps.merchants.schemas import (
    MerchantFixedCodeOut,
    MerchantLoginOut,
    MerchantOut,
    MerchantPaymentInfoOut,
    MerchantPointCodePreviewOut,
    MerchantPointCodeScanIn,
    MerchantPointCodeScanOut,
    MerchantPointPaymentIn,
    MerchantPointPaymentOut,
    MerchantPointRecordsData,
    MerchantSettlementsData,
    MerchantWechatLoginIn,
    MerchantWechatPhoneLoginIn,
    PublicMerchantsData,
)
from apps.merchants.services import (
    fixed_code_data,
    merchant_data,
    merchant_payment_info,
    merchant_point_record_data,
    merchant_point_records_queryset,
    merchant_point_records_summary,
    payment_record_data,
    pay_merchant_with_points,
    point_code_payment_preview,
    public_merchant_data,
    scan_point_code,
    settlement_data,
    test_login,
    wechat_login_placeholder,
    wechat_phone_login as merchant_wechat_phone_login_service,
)
from apps.merchants.models import MerchantSettlement
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


@merchant_auth_router.post("/wechat-phone-login", response={200: SuccessResponse[MerchantLoginOut], 400: ErrorResponse})
def merchant_wechat_phone_login(request, payload: MerchantWechatPhoneLoginIn):
    try:
        return success_response(merchant_wechat_phone_login_service(payload.login_code, payload.phone_code))
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


@merchant_router.get("/point-records", response={200: SuccessResponse[MerchantPointRecordsData], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def merchant_point_records(request, page: int = 1, page_size: int = 20, date_from: str = "", date_to: str = "", month: str = ""):
    try:
        merchant = authenticate_merchant(request)
        queryset = merchant_point_records_queryset(merchant, date_from=date_from, date_to=date_to, month=month)
        summary = merchant_point_records_summary(queryset)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    items, page_data = paginate_queryset(queryset, page=page, page_size=page_size)
    return success_response({"items": [merchant_point_record_data(item) for item in items], "summary": summary, **page_data})


@merchant_router.get("/settlements", response={200: SuccessResponse[MerchantSettlementsData], 401: ErrorResponse, 403: ErrorResponse})
def merchant_settlements(request, page: int = 1, page_size: int = 20, year: int | None = None, status: str = ""):
    try:
        merchant = authenticate_merchant(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    queryset = MerchantSettlement.objects.filter(merchant=merchant)
    if year:
        queryset = queryset.filter(date_from__year=year)
    if status:
        queryset = queryset.filter(status=status)
    items, page_data = paginate_queryset(queryset, page=page, page_size=page_size)
    return success_response({"items": [settlement_data(item) for item in items], **page_data})


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


@public_merchant_router.get("/point-codes/{code}", response={200: SuccessResponse[MerchantPointCodePreviewOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def public_point_code_preview(request, code: str):
    try:
        member = authenticate_member(request)
        return success_response(point_code_payment_preview(member, code))
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@public_merchant_router.post("/point-codes/{code}/scan", response={200: SuccessResponse[MerchantPointCodeScanOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def public_point_code_scan(request, code: str, payload: MerchantPointCodeScanIn):
    try:
        member = authenticate_member(request)
        record = scan_point_code(member, code, request_no=payload.request_no)
        return success_response(payment_record_data(record))
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)

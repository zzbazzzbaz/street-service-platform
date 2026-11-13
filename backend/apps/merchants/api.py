from django.shortcuts import get_object_or_404
from ninja import Router
from django_ratelimit.decorators import ratelimit

from apps.merchants.models import Merchant
from apps.merchants.schemas import (
    MerchantFixedCodeOut,
    MerchantLoginOut,
    MerchantOut,
    MerchantPasswordChangeIn,
    MerchantPaymentInfoOut,
    MerchantPointCodePreviewOut,
    MerchantPointCodeScanIn,
    MerchantPointCodeScanOut,
    MerchantPasswordLoginIn,
    MerchantPointCodesData,
    MerchantPointPaymentIn,
    MerchantPointPaymentOut,
    MerchantPointRecordsData,
    MerchantRegisterIn,
    MerchantRegisterInfoIn,
    MerchantRegisterOut,
    MerchantSettlementsData,
    MerchantWechatLoginIn,
    MerchantWechatPhoneLoginIn,
    PublicMerchantsData,
)
from apps.merchants.services import (
    change_password as merchant_change_password,
    fixed_code_data,
    merchant_data,
    merchant_payment_info,
    merchant_point_codes,
    merchant_point_record_data,
    merchant_point_records_queryset,
    merchant_point_records_summary,
    password_login,
    payment_record_data,
    pay_merchant_with_points,
    point_code_payment_preview,
    public_merchant_data,
    register_merchant,
    resubmit_register_info,
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
from shared.ratelimit import user_key
from shared.services import authenticate_member, authenticate_merchant_for_audit, require_approved_merchant


merchant_auth_router = Router(tags=["商户认证"])
public_merchant_router = Router(tags=["商户"])
merchant_router = Router(tags=["商户"])


@merchant_auth_router.post("/wechat-login", response={200: SuccessResponse[MerchantLoginOut], 400: ErrorResponse})
@ratelimit(key="ip", rate="5/m", block=True)
def merchant_wechat_login(request, payload: MerchantWechatLoginIn):
    try:
        if payload.openid.strip():
            return success_response(test_login(payload.openid))
        return success_response(wechat_login_placeholder(payload.code))
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@merchant_auth_router.post("/wechat-phone-login", response={200: SuccessResponse[MerchantLoginOut], 400: ErrorResponse})
@ratelimit(key="ip", rate="5/m", block=True)
def merchant_wechat_phone_login(request, payload: MerchantWechatPhoneLoginIn):
    try:
        return success_response(merchant_wechat_phone_login_service(payload.login_code, payload.phone_code))
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@merchant_auth_router.post("/login", response={200: SuccessResponse[MerchantLoginOut], 400: ErrorResponse, 403: ErrorResponse})
@ratelimit(key="ip", rate="5/m", block=True)
def merchant_password_login_view(request, payload: MerchantPasswordLoginIn):
    try:
        return success_response(password_login(payload.username, payload.password))
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@merchant_auth_router.post("/register", response={200: SuccessResponse[MerchantRegisterOut], 400: ErrorResponse})
@ratelimit(key="ip", rate="5/m", block=True)
def merchant_register(request, payload: MerchantRegisterIn):
    try:
        return success_response(
            register_merchant(
                shop_name=payload.shop_name,
                shop_address=payload.shop_address,
                service_content=payload.service_content,
                community=payload.community,
                merchant_nature=payload.merchant_nature,
                contact_name=payload.contact_name,
                contact_phone=payload.contact_phone,
                business_hours=payload.business_hours,
            )
        )
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@merchant_router.get("/me", response={200: SuccessResponse[MerchantOut], 401: ErrorResponse, 403: ErrorResponse})
def merchant_me(request):
    try:
        merchant = authenticate_merchant_for_audit(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(merchant_data(merchant))


@merchant_router.post("/register-info", response={200: SuccessResponse[MerchantOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
@ratelimit(key=user_key, rate="5/m", block=True)
def merchant_register_info(request, payload: MerchantRegisterInfoIn):
    try:
        merchant = authenticate_merchant_for_audit(request)
        return success_response(
            resubmit_register_info(
                merchant,
                shop_name=payload.shop_name,
                shop_address=payload.shop_address,
                service_content=payload.service_content,
                community=payload.community,
                merchant_nature=payload.merchant_nature,
                contact_name=payload.contact_name,
                business_hours=payload.business_hours,
                contact_phone=payload.contact_phone,
            )
        )
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@merchant_router.post("/password", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
@ratelimit(key=user_key, rate="5/m", block=True)
def merchant_password(request, payload: MerchantPasswordChangeIn):
    try:
        merchant = authenticate_merchant_for_audit(request)
        return success_response(
            merchant_change_password(
                merchant,
                current_password=payload.current_password,
                new_password=payload.new_password,
            )
        )
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@merchant_router.get("/fixed-code", response={200: SuccessResponse[MerchantFixedCodeOut], 401: ErrorResponse, 403: ErrorResponse})
def merchant_fixed_code(request):
    try:
        merchant = require_approved_merchant(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(fixed_code_data(merchant))


@merchant_router.get("/point-codes", response={200: SuccessResponse[MerchantPointCodesData], 401: ErrorResponse, 403: ErrorResponse})
def merchant_point_codes_view(request, include_inactive: bool = False):
    """返回当前登录商户的固定积分码列表，供商户端按积分面额选择并展示二维码。

    允许一个商户启用多个固定积分码（不同面额），商户端可按面额切换展示。
    默认仅返回启用中的码；传 include_inactive=true 可同时返回停用的码。
    """
    try:
        merchant = require_approved_merchant(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    items = merchant_point_codes(merchant, include_inactive=include_inactive)
    return success_response({"items": items})


@merchant_router.get("/point-records", response={200: SuccessResponse[MerchantPointRecordsData], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def merchant_point_records(request, page: int = 1, page_size: int = 20, date_from: str = "", date_to: str = "", month: str = ""):
    try:
        merchant = require_approved_merchant(request)
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
        merchant = require_approved_merchant(request)
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
    items, page_data = paginate_queryset(Merchant.objects.filter(is_active=True, deleted_at__isnull=True), page=page, page_size=page_size)
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
@ratelimit(key=user_key, rate="20/m", block=True)
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
@ratelimit(key=user_key, rate="20/m", block=True)
def public_point_code_scan(request, code: str, payload: MerchantPointCodeScanIn):
    try:
        member = authenticate_member(request)
        record = scan_point_code(member, code, request_no=payload.request_no)
        return success_response(payment_record_data(record))
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)

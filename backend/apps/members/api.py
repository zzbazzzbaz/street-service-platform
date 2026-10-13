from ninja import Router
from django_ratelimit.decorators import ratelimit

from apps.members.schemas import (
    LoginOut,
    MemberOut,
    MemberRegisterIn,
    MemberRegisterInfoIn,
    MemberRegisterOut,
    PasswordChangeIn,
    PasswordLoginIn,
    ProfileIn,
    WechatLoginIn,
    WechatPhoneLoginIn,
)
from apps.members.services import (
    change_password as member_change_password,
    member_data,
    password_login,
    register_member,
    resubmit_register_info,
    test_login,
    update_profile,
    wechat_login_placeholder,
    wechat_phone_login as member_wechat_phone_login,
)
from shared.api import ErrorResponse, SuccessResponse, error_response, success_response
from shared.auth import TokenError
from shared.exceptions import BusinessError
from shared.ratelimit import user_key
from shared.services import authenticate_member


auth_router = Router(tags=["认证"])
router = Router(tags=["用户"])


@auth_router.post("/wechat-login", response={200: SuccessResponse[LoginOut], 400: ErrorResponse})
@ratelimit(key="ip", rate="5/m", block=True)
def wechat_login(request, payload: WechatLoginIn):
    try:
        if payload.openid.strip():
            return success_response(test_login(payload.openid))
        return success_response(wechat_login_placeholder(payload.code))
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@auth_router.post("/wechat-phone-login", response={200: SuccessResponse[LoginOut], 400: ErrorResponse})
@ratelimit(key="ip", rate="5/m", block=True)
def wechat_phone_login(request, payload: WechatPhoneLoginIn):
    try:
        return success_response(member_wechat_phone_login(payload.login_code, payload.phone_code))
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@auth_router.post("/login", response={200: SuccessResponse[LoginOut], 400: ErrorResponse, 403: ErrorResponse})
@ratelimit(key="ip", rate="5/m", block=True)
def password_login_view(request, payload: PasswordLoginIn):
    try:
        return success_response(password_login(payload.username, payload.password))
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@auth_router.post("/register", response={200: SuccessResponse[MemberRegisterOut], 400: ErrorResponse})
@ratelimit(key="ip", rate="5/m", block=True)
def member_register(request, payload: MemberRegisterIn):
    try:
        return success_response(
            register_member(
                real_name=payload.real_name,
                wechat_id=payload.wechat_id,
                gender=payload.gender,
                occupation=payload.occupation,
                address=payload.address,
                phone=payload.phone,
                is_party_member=payload.is_party_member,
                phone_code=payload.phone_code,
                login_code=payload.login_code,
            )
        )
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@router.post("/register-info", response={200: SuccessResponse[MemberOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
@ratelimit(key=user_key, rate="5/m", block=True)
def member_register_info(request, payload: MemberRegisterInfoIn):
    try:
        member = authenticate_member(request)
        return success_response(
            resubmit_register_info(
                member,
                real_name=payload.real_name,
                wechat_id=payload.wechat_id,
                gender=payload.gender,
                occupation=payload.occupation,
                address=payload.address,
                is_party_member=payload.is_party_member,
                phone=payload.phone,
            )
        )
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@router.post("/password", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
@ratelimit(key=user_key, rate="5/m", block=True)
def member_password(request, payload: PasswordChangeIn):
    try:
        member = authenticate_member(request)
        return success_response(
            member_change_password(
                member,
                current_password=payload.current_password,
                new_password=payload.new_password,
            )
        )
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@router.get("/me", response={200: SuccessResponse[MemberOut], 401: ErrorResponse, 403: ErrorResponse})
def member_me(request):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(member_data(member))


@router.post("/profile", response={200: SuccessResponse[MemberOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def member_profile(request, payload: ProfileIn):
    try:
        member = authenticate_member(request)
        return success_response(
            update_profile(
                member,
                nickname=payload.nickname,
                phone=payload.phone,
            )
        )
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)

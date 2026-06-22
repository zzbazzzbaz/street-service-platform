from ninja import Router

from apps.members.schemas import LoginOut, MemberOut, ProfileIn, TestLoginIn, WechatLoginIn
from apps.members.services import member_data, test_login, update_profile, wechat_login_placeholder
from shared.api import ErrorResponse, SuccessResponse, error_response, success_response
from shared.auth import TokenError
from shared.exceptions import BusinessError
from shared.services import authenticate_member


auth_router = Router(tags=["认证"])
router = Router(tags=["用户"])


@auth_router.post("/test-login", response={200: SuccessResponse[LoginOut], 400: ErrorResponse})
def member_test_login(request, payload: TestLoginIn):
    try:
        return success_response(test_login(payload.openid))
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@auth_router.post("/wechat-login", response={200: SuccessResponse[LoginOut], 400: ErrorResponse})
def wechat_login(request, payload: WechatLoginIn):
    try:
        return success_response(wechat_login_placeholder(payload.code))
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
                role=payload.role,
            )
        )
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)

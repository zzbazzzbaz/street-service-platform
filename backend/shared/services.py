from __future__ import annotations

from apps.members.models import Member
from apps.merchants.models import Merchant
from shared.auth import TokenError, get_token_identity
from shared.exceptions import BusinessError


def authenticate_member(request) -> Member:
    try:
        identity = get_token_identity(request)
    except TokenError as exc:
        raise _auth_business_error(exc) from exc
    if identity.subject_type != "member":
        raise BusinessError("当前账号无权限访问", code=40301, status=403)
    member = Member.objects.filter(openid=identity.openid).first()
    if member is None or not member.is_active:
        raise BusinessError("当前账号无权限访问", code=40301, status=403)
    return member


def authenticate_merchant(request) -> Merchant:
    try:
        identity = get_token_identity(request)
    except TokenError as exc:
        raise _auth_business_error(exc) from exc
    if identity.subject_type != "merchant":
        raise BusinessError("当前账号无权限访问", code=40301, status=403)
    merchant = Merchant.objects.filter(openid=identity.openid).first()
    if merchant is None or not merchant.is_active:
        raise BusinessError("当前账号无权限访问", code=40301, status=403)
    return merchant


def require_approved_member(request) -> Member:
    member = authenticate_member(request)
    if member.audit_status != Member.AuditStatus.APPROVED:
        raise BusinessError("当前用户资料未审核通过", code=40301, status=403)
    return member


def _auth_business_error(exc: TokenError) -> BusinessError:
    message = str(exc)
    if "缺少 Bearer token" in message:
        return BusinessError("缺少登录凭证", code=40102, status=401)
    return BusinessError("登录已过期，请重新登录", code=40101, status=401)

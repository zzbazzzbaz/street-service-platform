from __future__ import annotations

from apps.members.models import Member
from apps.merchants.models import Merchant
from shared.auth import TokenError, TokenIdentity, get_token_identity
from shared.exceptions import BusinessError


def authenticate_member(request) -> Member:
    identity = _member_identity(request)
    member = _member_from_identity(identity)
    if member is None or not member.is_active:
        raise BusinessError("当前账号无权限访问", code=40301, status=403)
    return member


def authenticate_merchant(request, *, allow_inactive: bool = False) -> Merchant:
    identity = _merchant_identity(request)
    merchant = _merchant_from_identity(identity)
    if merchant is None:
        raise BusinessError("当前账号无权限访问", code=40301, status=403)
    if not allow_inactive and not merchant.is_active:
        raise BusinessError("当前账号无权限访问", code=40301, status=403)
    return merchant


def require_approved_member(request) -> Member:
    member = authenticate_member(request)
    if member.audit_status != Member.AuditStatus.APPROVED:
        raise BusinessError("当前用户资料未审核通过", code=40301, status=403)
    return member


def require_approved_merchant(request) -> Merchant:
    merchant = authenticate_merchant_for_audit(request)
    if merchant.audit_status in {Merchant.AuditStatus.NONE, Merchant.AuditStatus.PENDING}:
        raise BusinessError("商户资料审核中，请等待审核", code=40301, status=403)
    if merchant.audit_status == Merchant.AuditStatus.REJECTED:
        raise BusinessError("商户资料未通过审核，请联系街道工作人员", code=40301, status=403)
    return merchant


def authenticate_merchant_for_audit(request) -> Merchant:
    """审核期身份解析：待审核/已驳回商户可访问状态页与重提接口，其余停用账号仍拒绝。"""
    merchant = authenticate_merchant(request, allow_inactive=True)
    if not merchant.is_active and merchant.audit_status not in {Merchant.AuditStatus.PENDING, Merchant.AuditStatus.REJECTED}:
        raise BusinessError("当前账号已停用", code=40301, status=403)
    return merchant


def _member_identity(request) -> TokenIdentity:
    identity = _token_identity(request)
    if identity.subject_type != "member":
        raise BusinessError("当前账号无权限访问", code=40301, status=403)
    return identity


def _merchant_identity(request) -> TokenIdentity:
    identity = _token_identity(request)
    if identity.subject_type != "merchant":
        raise BusinessError("当前账号无权限访问", code=40301, status=403)
    return identity


def _token_identity(request) -> TokenIdentity:
    try:
        return get_token_identity(request)
    except TokenError as exc:
        raise _auth_business_error(exc) from exc


def _member_from_identity(identity: TokenIdentity) -> Member | None:
    if identity.subject_id:
        return Member.objects.filter(pk=identity.subject_id, deleted_at__isnull=True).first()
    if identity.openid:
        return Member.objects.filter(openid=identity.openid, deleted_at__isnull=True).first()
    return None


def _merchant_from_identity(identity: TokenIdentity) -> Merchant | None:
    if identity.subject_id:
        return Merchant.objects.filter(pk=identity.subject_id, deleted_at__isnull=True).first()
    if identity.openid:
        return Merchant.objects.filter(openid=identity.openid, deleted_at__isnull=True).first()
    return None


def _auth_business_error(exc: TokenError) -> BusinessError:
    message = str(exc)
    if "缺少 Bearer token" in message:
        return BusinessError("缺少登录凭证", code=40102, status=401)
    return BusinessError("登录已过期，请重新登录", code=40101, status=401)

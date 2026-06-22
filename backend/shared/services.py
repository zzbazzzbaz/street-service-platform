from __future__ import annotations

from apps.members.models import Member
from apps.merchants.models import Merchant
from shared.auth import TokenError, get_token_identity


def authenticate_member(request) -> Member:
    identity = get_token_identity(request)
    if identity.subject_type != "member":
        raise TokenError("token 主体类型错误")
    member = Member.objects.filter(openid=identity.openid).first()
    if member is None or not member.is_active:
        from shared.exceptions import BusinessError

        raise BusinessError("用户已禁用或不存在", code=40002, status=403)
    return member


def authenticate_merchant(request) -> Merchant:
    identity = get_token_identity(request)
    if identity.subject_type != "merchant":
        raise TokenError("token 主体类型错误")
    merchant = Merchant.objects.filter(openid=identity.openid).first()
    if merchant is None or not merchant.is_active:
        from shared.exceptions import BusinessError

        raise BusinessError("商户已禁用或不存在", code=40002, status=403)
    return merchant

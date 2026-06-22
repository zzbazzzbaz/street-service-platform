from __future__ import annotations

from django.conf import settings

from apps.members.models import Member
from shared.auth import issue_token
from shared.exceptions import BusinessError


def member_data(member: Member) -> dict:
    return {
        "id": member.id,
        "openid": member.openid,
        "nickname": member.nickname,
        "phone": member.phone,
        "is_active": member.is_active,
    }


def test_login(openid: str) -> dict:
    openid = openid.strip()
    if not openid:
        raise BusinessError("openid 不能为空")
    member, _ = Member.objects.get_or_create(openid=openid)
    token, expires_in = issue_token(subject_type="member", openid=openid)
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "member": member_data(member),
    }


def wechat_login_placeholder(code: str) -> dict:
    if not settings.WECHAT_MINIAPP_APPID or not settings.WECHAT_MINIAPP_SECRET:
        raise BusinessError("微信登录未配置，开发期请使用测试登录", code=40000)
    raise BusinessError("正式微信登录暂未接入", code=40000)


def update_profile(member: Member, *, nickname: str, phone: str) -> dict:
    member.nickname = nickname.strip()
    member.phone = phone.strip()
    member.save(update_fields=["nickname", "phone"])
    return member_data(member)

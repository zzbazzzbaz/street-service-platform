from __future__ import annotations

from django.conf import settings
from django.utils import timezone

from apps.members.models import Member
from shared.auth import issue_token
from shared.exceptions import BusinessError
from shared.wechat import code_to_openid as wechat_code_to_openid
from shared.wechat import phone_code_to_phone as wechat_phone_code_to_phone


def member_data(member: Member) -> dict:
    return {
        "id": member.id,
        "openid": member.openid,
        "nickname": member.nickname,
        "phone": member.phone,
        "real_name": member.real_name,
        "identity_type": member.identity_type,
        "audit_status": member.audit_status,
        "audit_remark": member.audit_remark,
        "audit_submitted_at": member.audit_submitted_at,
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
    code = code.strip()
    if not code:
        raise BusinessError("openid 或 code 不能为空", code=40000)
    if not settings.WECHAT_MINIAPP_APPID or not settings.WECHAT_MINIAPP_SECRET:
        raise BusinessError("微信登录未配置，开发期请使用测试登录", code=40000)
    raise BusinessError("正式微信登录暂未接入", code=40000)


def wechat_phone_login(login_code: str, phone_code: str) -> dict:
    login_code = login_code.strip()
    phone_code = phone_code.strip()
    if not phone_code:
        raise BusinessError("缺少手机号授权 code", code=40000)
    if not settings.WECHAT_MINIAPP_APPID or not settings.WECHAT_MINIAPP_SECRET:
        raise BusinessError("微信手机号登录未配置", code=40000)
    openid = wechat_code_to_openid(login_code)
    phone = wechat_phone_code_to_phone(phone_code)
    member, _ = Member.objects.get_or_create(openid=openid)
    member.phone = phone
    member.save(update_fields=["phone"])
    token, expires_in = issue_token(subject_type="member", openid=openid)
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "member": member_data(member),
    }


def update_profile(member: Member, *, nickname: str, phone: str) -> dict:
    member.nickname = nickname.strip()
    member.phone = phone.strip()
    member.save(update_fields=["nickname", "phone"])
    return member_data(member)


def submit_audit_profile(member: Member, *, real_name: str, identity_type: str) -> dict:
    real_name = real_name.strip()
    identity_type = identity_type.strip()
    if not real_name:
        raise BusinessError("真实姓名不能为空")
    if identity_type not in Member.IdentityType.values:
        raise BusinessError("身份类型不支持")
    if member.audit_status == Member.AuditStatus.APPROVED:
        raise BusinessError("审核通过后不能自行修改资料")

    member.real_name = real_name
    member.identity_type = identity_type
    member.audit_status = Member.AuditStatus.PENDING
    member.audit_remark = ""
    member.audit_submitted_at = timezone.now()
    member.save(
        update_fields=[
            "real_name",
            "identity_type",
            "audit_status",
            "audit_remark",
            "audit_submitted_at",
        ]
    )
    return member_data(member)

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone

from apps.members.models import Member
from shared.auth import issue_token
from shared.exceptions import BusinessError
from shared.passwords import INITIAL_PASSWORD, is_initial_password
from shared.validators import clean_phone
from shared.wechat import code_to_openid as wechat_code_to_openid
from shared.wechat import phone_code_to_phone as wechat_phone_code_to_phone


def member_data(member: Member) -> dict:
    return {
        "id": member.id,
        "openid": member.openid or "",
        "username": member.username or "",
        "nickname": member.nickname,
        "phone": member.phone,
        "real_name": member.real_name,
        "wechat_id": member.wechat_id,
        "gender": member.gender,
        "occupation": member.occupation,
        "is_party_member": member.is_party_member,
        "address": member.address,
        "audit_status": member.audit_status,
        "audit_remark": member.audit_remark,
        "audit_submitted_at": member.audit_submitted_at,
        "is_active": member.is_active,
    }


def _login_payload(member: Member, *, must_change_password: bool = False) -> dict:
    token, expires_in = issue_token(
        subject_type="member",
        openid=member.openid or "",
        subject_id=member.pk,
    )
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "must_change_password": must_change_password,
        "member": member_data(member),
    }


def test_login(openid: str) -> dict:
    openid = openid.strip()
    if not openid:
        raise BusinessError("openid 不能为空")
    member, _ = Member.objects.get_or_create(openid=openid)
    return _login_payload(member)


def wechat_login_placeholder(code: str) -> dict:
    code = code.strip()
    if not code:
        raise BusinessError("openid 或 code 不能为空", code=40000)
    if not settings.WECHAT_MINIAPP_APPID or not settings.WECHAT_MINIAPP_SECRET:
        raise BusinessError("微信登录未配置，开发期请使用测试登录", code=40000)
    raise BusinessError("正式微信登录暂未接入", code=40000)


def password_login(username: str, password: str) -> dict:
    username = username.strip()
    if not username or not password:
        raise BusinessError("用户名或密码错误", code=40000, status=400)
    member = Member.objects.filter(username=username).first()
    if member is None or not member.password:
        raise BusinessError("用户名或密码错误", code=40000, status=400)
    if not check_password(password, member.password):
        raise BusinessError("用户名或密码错误", code=40000, status=400)
    if not member.is_active:
        raise BusinessError("当前账号已停用", code=40301, status=403)
    # 用「提交的密码是否就是初始密码」代替 must_change_password 标志位：零额外开销，改密后自然消失
    return _login_payload(member, must_change_password=is_initial_password(password))


def _clean_real_name(value: str) -> str:
    real_name = (value or "").strip()
    if not 2 <= len(real_name) <= 10:
        raise BusinessError("姓名需为 2-10 个字", errors={"real_name": ["姓名需为 2-10 个字"]})
    return real_name


def _clean_wechat_id(value: str) -> str:
    wechat_id = (value or "").strip()
    if not wechat_id:
        raise BusinessError("微信号不能为空", errors={"wechat_id": ["微信号不能为空"]})
    if len(wechat_id) > 64:
        raise BusinessError("微信号最多 64 字", errors={"wechat_id": ["微信号最多 64 字"]})
    return wechat_id


def _clean_gender(value: str) -> str:
    gender = (value or "").strip()
    if gender not in Member.Gender.values:
        raise BusinessError("性别不正确", errors={"gender": ["性别不正确"]})
    return gender


def _clean_occupation(value: str) -> str:
    occupation = (value or "").strip()
    if occupation not in Member.Occupation.values:
        raise BusinessError("职业不正确", errors={"occupation": ["职业不正确"]})
    return occupation


def _clean_address(value: str) -> str:
    address = (value or "").strip()
    if not address:
        raise BusinessError("住址不能为空", errors={"address": ["住址不能为空"]})
    if len(address) > 255:
        raise BusinessError("住址最多 255 字", errors={"address": ["住址最多 255 字"]})
    return address


def _ensure_phone_available(
    phone: str,
    *,
    message: str = "该手机号已注册",
    exclude_member_id: int | None = None,
) -> None:
    queryset = Member.objects.filter(Q(phone=phone) | Q(username=phone))
    if exclude_member_id:
        queryset = queryset.exclude(pk=exclude_member_id)
    if queryset.exists():
        raise BusinessError(message, errors={"phone": [message]})


def register_member(
    *,
    real_name: str,
    wechat_id: str,
    gender: str,
    occupation: str,
    address: str,
    phone: str = "",
    is_party_member: bool = False,
    phone_code: str = "",
    login_code: str = "",
) -> dict:
    real_name = _clean_real_name(real_name)
    wechat_id = _clean_wechat_id(wechat_id)
    gender = _clean_gender(gender)
    occupation = _clean_occupation(occupation)
    address = _clean_address(address)

    phone_code = (phone_code or "").strip()
    if phone_code:
        phone = clean_phone(wechat_phone_code_to_phone(phone_code))
    else:
        phone = clean_phone(phone)

    openid = ""
    login_code = (login_code or "").strip()
    if login_code:
        openid = wechat_code_to_openid(login_code)

    _ensure_phone_available(phone)
    if openid and Member.objects.filter(openid=openid).exists():
        raise BusinessError("该微信已注册", errors={"login_code": ["该微信已注册"]})

    try:
        member = Member.objects.create(
            openid=openid or None,
            username=phone,
            password=make_password(INITIAL_PASSWORD),
            nickname=real_name,
            phone=phone,
            real_name=real_name,
            wechat_id=wechat_id,
            gender=gender,
            occupation=occupation,
            is_party_member=bool(is_party_member),
            address=address,
            audit_status=Member.AuditStatus.PENDING,
            audit_submitted_at=timezone.now(),
        )
    except IntegrityError as exc:
        raise BusinessError("该手机号已注册", errors={"phone": ["该手机号已注册"]}) from exc

    payload = _login_payload(member)
    payload["need_audit"] = True
    return payload


def resubmit_register_info(
    member: Member,
    *,
    real_name: str,
    wechat_id: str,
    gender: str,
    occupation: str,
    address: str,
    is_party_member: bool = False,
    phone: str = "",
) -> dict:
    if member.audit_status == Member.AuditStatus.PENDING:
        raise BusinessError("资料审核中，请等待审核结果")
    if member.audit_status == Member.AuditStatus.APPROVED:
        raise BusinessError("审核已通过，如需修改资料请联系街道工作人员")

    real_name = _clean_real_name(real_name)
    wechat_id = _clean_wechat_id(wechat_id)
    gender = _clean_gender(gender)
    occupation = _clean_occupation(occupation)
    address = _clean_address(address)

    update_fields = [
        "real_name",
        "wechat_id",
        "gender",
        "occupation",
        "is_party_member",
        "address",
        "audit_status",
        "audit_remark",
        "audit_submitted_at",
    ]
    member.real_name = real_name
    member.wechat_id = wechat_id
    member.gender = gender
    member.occupation = occupation
    member.is_party_member = bool(is_party_member)
    member.address = address
    member.audit_status = Member.AuditStatus.PENDING
    member.audit_remark = ""
    member.audit_submitted_at = timezone.now()

    if not member.phone:
        phone = clean_phone(phone)
        _ensure_phone_available(phone, message="该手机号已被其他账号使用", exclude_member_id=member.pk)
        member.phone = phone
        update_fields.append("phone")
    if member.phone and not member.username:
        _ensure_phone_available(member.phone, message="该手机号已被其他账号使用", exclude_member_id=member.pk)
        member.username = member.phone
        update_fields.append("username")

    member.save(update_fields=update_fields)
    return member_data(member)


def change_password(member: Member, *, current_password: str, new_password: str) -> dict:
    current_password = current_password or ""
    new_password = new_password or ""
    if not member.password:
        raise BusinessError("账号未设置密码，请联系街道工作人员")
    if not check_password(current_password, member.password):
        raise BusinessError("当前密码错误", errors={"current_password": ["当前密码错误"]})
    if len(new_password) < 6:
        raise BusinessError("新密码长度至少 6 位", errors={"new_password": ["新密码长度至少 6 位"]})
    if check_password(new_password, member.password):
        raise BusinessError("新密码不能与当前密码相同", errors={"new_password": ["新密码不能与当前密码相同"]})
    member.password = make_password(new_password)
    member.save(update_fields=["password"])
    return {}


def wechat_phone_login(login_code: str, phone_code: str) -> dict:
    login_code = login_code.strip()
    phone_code = phone_code.strip()
    if not phone_code:
        raise BusinessError("缺少手机号授权 code", code=40000)
    if not settings.WECHAT_MINIAPP_APPID or not settings.WECHAT_MINIAPP_SECRET:
        raise BusinessError("微信手机号登录未配置", code=40000)
    openid = wechat_code_to_openid(login_code)
    phone = wechat_phone_code_to_phone(phone_code)
    member = Member.objects.filter(phone=phone).order_by("id").first()
    if member is None:
        member = Member.objects.create(openid=openid, phone=phone)
    else:
        if member.openid and member.openid != openid:
            raise BusinessError("该手机号已绑定其他微信账号，请联系街道工作人员", code=40301, status=403)
        if Member.objects.filter(openid=openid).exclude(pk=member.pk).exists():
            raise BusinessError("该微信已绑定其他账号，请联系街道工作人员", code=40301, status=403)
        member.openid = openid
        member.save(update_fields=["openid"])
    if not member.is_active:
        raise BusinessError("当前账号已停用", code=40301, status=403)
    return _login_payload(member)


def update_profile(member: Member, *, nickname: str, phone: str) -> dict:
    member.nickname = nickname.strip()
    phone = (phone or "").strip()
    update_fields = ["nickname", "phone"]
    if phone:
        phone = clean_phone(phone)
        _ensure_phone_available(phone, message="该手机号已被其他账号使用", exclude_member_id=member.pk)
        if not member.username or member.username == member.phone:
            member.username = phone
            update_fields.append("username")
    member.phone = phone
    member.save(update_fields=update_fields)
    return member_data(member)

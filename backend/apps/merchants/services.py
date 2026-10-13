from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import re

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Q, Sum
from django.db import IntegrityError, transaction
from django.utils import timezone
from uuid import uuid4
import logging

from apps.members.models import Member
from apps.merchants.models import Merchant, MerchantPointCode, MerchantSettlement
from apps.points.models import PointExchangeRule, PointRecord
from apps.points.services import deduct_points, get_or_create_account
from shared.auth import issue_token
from shared.exceptions import BusinessError
from shared.privacy import mask_name, mask_phone
from shared.validators import clean_phone
from shared.wechat import code_to_openid as wechat_code_to_openid
from shared.wechat import phone_code_to_phone as wechat_phone_code_to_phone

logger = logging.getLogger("street.merchants")

INITIAL_PASSWORD = "000000"
BUSINESS_HOURS_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)$")


def merchant_data(merchant: Merchant) -> dict:
    return {
        "id": merchant.id,
        "openid": merchant.openid or "",
        "username": merchant.username or "",
        "name": merchant.name,
        "contact_name": merchant.contact_name,
        "phone": merchant.phone,
        "address": merchant.address,
        "community": merchant.community,
        "merchant_nature": merchant.merchant_nature,
        "latitude": merchant.latitude,
        "longitude": merchant.longitude,
        "category_code": merchant.category_code,
        "business_hours": merchant.business_hours,
        "service_content": merchant.service_content,
        "audit_status": merchant.audit_status,
        "audit_remark": merchant.audit_remark,
        "is_active": merchant.is_active,
    }


def public_merchant_data(merchant: Merchant) -> dict:
    return {
        "id": merchant.id,
        "name": merchant.name,
        "contact_name": merchant.contact_name,
        "phone": merchant.phone,
        "address": merchant.address,
        "latitude": merchant.latitude,
        "longitude": merchant.longitude,
        "category_code": merchant.category_code,
        "business_hours": merchant.business_hours,
        "service_content": merchant.service_content,
        "is_active": merchant.is_active,
    }


def _login_payload(merchant: Merchant) -> dict:
    token, expires_in = issue_token(
        subject_type="merchant",
        openid=merchant.openid or "",
        subject_id=merchant.pk,
    )
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "merchant": merchant_data(merchant),
    }


def test_login(openid: str) -> dict:
    openid = openid.strip()
    if not openid:
        raise BusinessError("openid 不能为空")
    merchant, _ = Merchant.objects.get_or_create(
        openid=openid,
        defaults={
            "name": f"测试商户-{openid}",
            "audit_status": Merchant.AuditStatus.APPROVED,
        },
    )
    return _login_payload(merchant)


def _ensure_login_allowed(merchant: Merchant) -> None:
    """登录放行规则：待审核/已驳回允许登录（仅可查看状态、重提资料、改密），其余停用账号拒绝。"""
    if not merchant.is_active and merchant.audit_status not in {Merchant.AuditStatus.PENDING, Merchant.AuditStatus.REJECTED}:
        raise BusinessError("当前账号已停用", code=40301, status=403)


def password_login(username: str, password: str) -> dict:
    username = (username or "").strip()
    if not username or not password:
        raise BusinessError("用户名或密码错误", code=40000, status=400)
    merchant = Merchant.objects.filter(username=username).first()
    if merchant is None or not merchant.password:
        raise BusinessError("用户名或密码错误", code=40000, status=400)
    if not check_password(password, merchant.password):
        raise BusinessError("用户名或密码错误", code=40000, status=400)
    _ensure_login_allowed(merchant)
    return _login_payload(merchant)


def _clean_registration_business_hours(value: str) -> str:
    value = (value or "").strip()
    match = BUSINESS_HOURS_PATTERN.match(value)
    if match is None:
        raise BusinessError(
            "营业时间格式必须为 HH:MM-HH:MM",
            errors={"business_hours": ["营业时间格式必须为 HH:MM-HH:MM"]},
        )
    start_hour, start_minute, end_hour, end_minute = (int(part) for part in match.groups())
    if end_hour * 60 + end_minute <= start_hour * 60 + start_minute:
        raise BusinessError(
            "营业时间结束时间必须晚于开始时间",
            errors={"business_hours": ["营业时间结束时间必须晚于开始时间"]},
        )
    return value


def _clean_shop_name(value: str) -> str:
    shop_name = (value or "").strip()
    if not shop_name:
        raise BusinessError("店铺名称不能为空", errors={"shop_name": ["店铺名称不能为空"]})
    if len(shop_name) > 100:
        raise BusinessError("店铺名称最多 100 字", errors={"shop_name": ["店铺名称最多 100 字"]})
    return shop_name


def _clean_shop_address(value: str) -> str:
    shop_address = (value or "").strip()
    if not shop_address:
        raise BusinessError("店铺地址不能为空", errors={"shop_address": ["店铺地址不能为空"]})
    if len(shop_address) > 255:
        raise BusinessError("店铺地址最多 255 字", errors={"shop_address": ["店铺地址最多 255 字"]})
    return shop_address


def _clean_service_content(value: str) -> str:
    service_content = (value or "").strip()
    if not service_content:
        raise BusinessError("服务内容不能为空", errors={"service_content": ["服务内容不能为空"]})
    if len(service_content) > 500:
        raise BusinessError("服务内容最多 500 字", errors={"service_content": ["服务内容最多 500 字"]})
    return service_content


def _clean_community(value: str) -> str:
    community = (value or "").strip()
    if not community:
        raise BusinessError("所属社区不能为空", errors={"community": ["所属社区不能为空"]})
    if len(community) > 100:
        raise BusinessError("所属社区最多 100 字", errors={"community": ["所属社区最多 100 字"]})
    return community


def _clean_merchant_nature(value: str) -> str:
    merchant_nature = (value or "").strip()
    if not merchant_nature:
        raise BusinessError("商户性质不能为空", errors={"merchant_nature": ["商户性质不能为空"]})
    if len(merchant_nature) > 100:
        raise BusinessError("商户性质最多 100 字", errors={"merchant_nature": ["商户性质最多 100 字"]})
    return merchant_nature


def _clean_contact_name(value: str) -> str:
    contact_name = (value or "").strip()
    if not contact_name:
        raise BusinessError("联系人不能为空", errors={"contact_name": ["联系人不能为空"]})
    if len(contact_name) > 50:
        raise BusinessError("联系人最多 50 字", errors={"contact_name": ["联系人最多 50 字"]})
    return contact_name


def _ensure_phone_available(
    phone: str,
    *,
    message: str = "该手机号已注册",
    exclude_merchant_id: int | None = None,
) -> None:
    queryset = Merchant.objects.filter(Q(phone=phone) | Q(username=phone))
    if exclude_merchant_id:
        queryset = queryset.exclude(pk=exclude_merchant_id)
    if queryset.exists():
        raise BusinessError(message, errors={"contact_phone": [message]})


def register_merchant(
    *,
    shop_name: str,
    shop_address: str,
    service_content: str,
    community: str,
    merchant_nature: str,
    contact_name: str,
    contact_phone: str,
    business_hours: str,
) -> dict:
    shop_name = _clean_shop_name(shop_name)
    shop_address = _clean_shop_address(shop_address)
    service_content = _clean_service_content(service_content)
    community = _clean_community(community)
    merchant_nature = _clean_merchant_nature(merchant_nature)
    contact_name = _clean_contact_name(contact_name)
    contact_phone = clean_phone(contact_phone, field="contact_phone")
    business_hours = _clean_registration_business_hours(business_hours)

    _ensure_phone_available(contact_phone)

    try:
        merchant = Merchant.objects.create(
            openid=None,
            username=contact_phone,
            password=make_password(INITIAL_PASSWORD),
            name=shop_name,
            contact_name=contact_name,
            phone=contact_phone,
            address=shop_address,
            community=community,
            merchant_nature=merchant_nature,
            business_hours=business_hours,
            service_content=service_content,
            audit_status=Merchant.AuditStatus.PENDING,
            is_active=False,
        )
    except IntegrityError as exc:
        raise BusinessError("该手机号已注册", errors={"contact_phone": ["该手机号已注册"]}) from exc

    payload = _login_payload(merchant)
    payload["need_audit"] = True
    return payload


def resubmit_register_info(
    merchant: Merchant,
    *,
    shop_name: str,
    shop_address: str,
    service_content: str,
    community: str,
    merchant_nature: str,
    contact_name: str,
    business_hours: str,
    contact_phone: str = "",
) -> dict:
    if merchant.audit_status == Merchant.AuditStatus.PENDING:
        raise BusinessError("资料审核中，请等待审核结果")
    if merchant.audit_status == Merchant.AuditStatus.APPROVED:
        raise BusinessError("审核已通过，如需修改资料请联系街道工作人员")

    shop_name = _clean_shop_name(shop_name)
    shop_address = _clean_shop_address(shop_address)
    service_content = _clean_service_content(service_content)
    community = _clean_community(community)
    merchant_nature = _clean_merchant_nature(merchant_nature)
    contact_name = _clean_contact_name(contact_name)
    business_hours = _clean_registration_business_hours(business_hours)

    update_fields = [
        "name",
        "address",
        "service_content",
        "community",
        "merchant_nature",
        "contact_name",
        "business_hours",
        "audit_status",
        "audit_remark",
    ]
    merchant.name = shop_name
    merchant.address = shop_address
    merchant.service_content = service_content
    merchant.community = community
    merchant.merchant_nature = merchant_nature
    merchant.contact_name = contact_name
    merchant.business_hours = business_hours
    merchant.audit_status = Merchant.AuditStatus.PENDING
    merchant.audit_remark = ""

    if not merchant.phone:
        contact_phone = clean_phone(contact_phone, field="contact_phone")
        _ensure_phone_available(contact_phone, message="该手机号已被其他商户使用", exclude_merchant_id=merchant.pk)
        merchant.phone = contact_phone
        update_fields.append("phone")
    if merchant.phone and not merchant.username:
        _ensure_phone_available(merchant.phone, message="该手机号已被其他商户使用", exclude_merchant_id=merchant.pk)
        merchant.username = merchant.phone
        update_fields.append("username")

    merchant.save(update_fields=update_fields)
    return merchant_data(merchant)


def change_password(merchant: Merchant, *, current_password: str, new_password: str) -> dict:
    current_password = current_password or ""
    new_password = new_password or ""
    if not merchant.password:
        raise BusinessError("账号未设置密码，请联系街道工作人员")
    if not check_password(current_password, merchant.password):
        raise BusinessError("当前密码错误", errors={"current_password": ["当前密码错误"]})
    if len(new_password) < 6:
        raise BusinessError("新密码长度至少 6 位", errors={"new_password": ["新密码长度至少 6 位"]})
    if check_password(new_password, merchant.password):
        raise BusinessError("新密码不能与当前密码相同", errors={"new_password": ["新密码不能与当前密码相同"]})
    merchant.password = make_password(new_password)
    merchant.save(update_fields=["password"])
    return {}


def wechat_login_placeholder(code: str) -> dict:
    code = code.strip()
    if not code:
        raise BusinessError("openid 或 code 不能为空", code=40000)
    if not settings.WECHAT_MINIAPP_APPID or not settings.WECHAT_MINIAPP_SECRET:
        raise BusinessError("商户微信登录未配置，开发期请使用测试登录", code=40000)
    raise BusinessError("商户微信登录暂未接入", code=40000)


def wechat_phone_login(login_code: str, phone_code: str) -> dict:
    login_code = login_code.strip()
    phone_code = phone_code.strip()
    if not phone_code:
        raise BusinessError("缺少手机号授权 code", code=40000)
    if not settings.WECHAT_MINIAPP_APPID or not settings.WECHAT_MINIAPP_SECRET:
        raise BusinessError("商户微信手机号登录未配置", code=40000)
    openid = wechat_code_to_openid(login_code)
    phone = wechat_phone_code_to_phone(phone_code)
    merchant = Merchant.objects.filter(phone=phone).order_by("id").first()
    if merchant is None:
        raise BusinessError("商户账号不存在或未启用", code=40301, status=403)
    _ensure_login_allowed(merchant)
    if Merchant.objects.filter(openid=openid).exclude(pk=merchant.pk).exists():
        raise BusinessError("该微信已绑定其他商户账号", code=40301, status=403)
    merchant.openid = openid
    merchant.save(update_fields=["openid"])
    return _login_payload(merchant)


def active_exchange_rule() -> PointExchangeRule:
    rule = PointExchangeRule.objects.filter(is_active=True).order_by("-updated_at", "-id").first()
    if rule is None:
        raise BusinessError("积分兑换比例未配置")
    if rule.points_per_yuan <= 0:
        raise BusinessError("积分兑换比例必须大于 0")
    return rule


def fixed_code_data(merchant: Merchant) -> dict:
    return {
        "merchant_id": merchant.id,
        "merchant_name": merchant.name,
        "code_content": f"street-service://merchant-pay?merchant_id={merchant.id}",
    }


def merchant_payment_info(member: Member, merchant: Merchant) -> dict:
    if not merchant.is_active:
        raise BusinessError("商户已停用", status=403, code=40003)
    rule = active_exchange_rule()
    account = get_or_create_account(member)
    return {
        "merchant_id": merchant.id,
        "merchant_name": merchant.name,
        "phone": merchant.phone,
        "address": merchant.address,
        "points_per_yuan": rule.points_per_yuan,
        "balance": account.balance,
    }


def payment_record_data(record: PointRecord) -> dict:
    return {
        "id": record.id,
        "merchant_id": record.merchant_id,
        "merchant_name": record.merchant.name if record.merchant_id else "",
        "points": abs(record.amount),
        "yuan_amount": f"{record.yuan_amount:.2f}" if record.yuan_amount is not None else "0.00",
        "balance_after": record.balance_after,
        "request_no": record.request_no,
        "created_at": record.created_at,
    }


def merchant_point_record_data(record: PointRecord) -> dict:
    data = payment_record_data(record)
    data.update(
        {
            "member_id": record.member_id,
            "member_name_masked": mask_name(record.member.nickname),
            "member_phone_masked": mask_phone(record.member.phone),
        }
    )
    return data


def merchant_point_records_queryset(merchant: Merchant, *, date_from: str = "", date_to: str = "", month: str = ""):
    queryset = PointRecord.objects.filter(
        merchant=merchant,
        source_type=PointRecord.SourceType.MERCHANT_PAYMENT,
    ).select_related("merchant", "member")
    start, end = _parse_record_filter_range(date_from=date_from, date_to=date_to, month=month)
    if start is not None:
        queryset = queryset.filter(created_at__gte=start)
    if end is not None:
        queryset = queryset.filter(created_at__lte=end)
    return queryset


def merchant_point_records_summary(queryset) -> dict:
    aggregate = queryset.aggregate(total_points=Sum("amount"), total_yuan_amount=Sum("yuan_amount"))
    total_points = abs(int(aggregate["total_points"] or 0))
    total_yuan_amount = aggregate["total_yuan_amount"] or Decimal("0.00")
    return {
        "record_count": queryset.count(),
        "total_points": total_points,
        "total_yuan_amount": f"{total_yuan_amount:.2f}",
    }


def settlement_data(settlement: MerchantSettlement) -> dict:
    return {
        "id": settlement.id,
        "period_type": settlement.period_type,
        "period_label": settlement.period_label,
        "date_from": settlement.date_from.isoformat(),
        "date_to": settlement.date_to.isoformat(),
        "record_count": settlement.record_count,
        "total_points": settlement.total_points,
        "total_yuan_amount": f"{settlement.total_yuan_amount:.2f}",
        "status": settlement.status,
        "processed_at": settlement.processed_at,
        "processor_name": settlement.processor_name,
        "remark": settlement.remark,
        "created_at": settlement.created_at,
    }


def _parse_record_filter_range(*, date_from: str, date_to: str, month: str):
    tz = timezone.get_current_timezone()
    if month:
        try:
            year, month_value = [int(part) for part in month.split("-", 1)]
            start_date = timezone.datetime(year, month_value, 1).date()
        except (TypeError, ValueError):
            raise BusinessError("月份格式必须为 YYYY-MM")
        if month_value == 12:
            next_month = timezone.datetime(year + 1, 1, 1).date()
        else:
            next_month = timezone.datetime(year, month_value + 1, 1).date()
        return timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time()), tz), timezone.make_aware(
            timezone.datetime.combine(next_month, timezone.datetime.min.time()), tz
        ) - timezone.timedelta(microseconds=1)

    start = _parse_local_date_start(date_from, tz) if date_from else None
    end = _parse_local_date_end(date_to, tz) if date_to else None
    return start, end


def _parse_local_date_start(value: str, tz):
    try:
        date_value = timezone.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise BusinessError("开始日期格式必须为 YYYY-MM-DD")
    return timezone.make_aware(timezone.datetime.combine(date_value, timezone.datetime.min.time()), tz)


def _parse_local_date_end(value: str, tz):
    try:
        date_value = timezone.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise BusinessError("结束日期格式必须为 YYYY-MM-DD")
    return timezone.make_aware(timezone.datetime.combine(date_value, timezone.datetime.max.time()), tz)


DAILY_MERCHANT_PAYMENT_LIMIT = 2


def _check_daily_payment_limit(member: Member, merchant: Merchant) -> None:
    tz = timezone.get_current_timezone()
    today = timezone.localdate()
    day_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()), tz)
    day_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()), tz)
    today_count = PointRecord.objects.filter(
        member=member,
        merchant=merchant,
        source_type=PointRecord.SourceType.MERCHANT_PAYMENT,
        created_at__range=(day_start, day_end),
    ).count()
    if today_count >= DAILY_MERCHANT_PAYMENT_LIMIT:
        logger.info(
            "商户支付每日限额拦截 member=%s merchant=%s today_count=%d",
            member.id,
            merchant.id,
            today_count,
        )
        raise BusinessError(f"今日在该商户支付已达 {DAILY_MERCHANT_PAYMENT_LIMIT} 次上限，请明日再试", status=403, code=40003)


@transaction.atomic
def pay_merchant_with_points(member: Member, merchant: Merchant, points: int, *, request_no: str = "") -> PointRecord:
    points = int(points)
    request_no = request_no.strip()
    merchant = Merchant.objects.select_for_update().get(pk=merchant.pk)
    if not merchant.is_active:
        raise BusinessError("商户已停用", status=403, code=40003)
    if points <= 0:
        raise BusinessError("积分值必须大于 0")
    if request_no:
        existing = (
            PointRecord.objects.select_related("merchant", "member")
            .filter(merchant=merchant, request_no=request_no, source_type=PointRecord.SourceType.MERCHANT_PAYMENT)
            .first()
        )
        if existing is not None:
            logger.info(
                "商户支付幂等重放 member=%s merchant=%s request_no=%s record_id=%s",
                member.id,
                merchant.id,
                request_no,
                existing.id,
            )
            return existing
    _check_daily_payment_limit(member, merchant)
    rule = active_exchange_rule()
    yuan_amount = (Decimal(points) / Decimal(rule.points_per_yuan)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    logger.info(
        "商户积分支付 member=%s merchant=%s points=%d yuan_amount=%s",
        member.id,
        merchant.id,
        points,
        yuan_amount,
    )
    return deduct_points(
        member,
        points,
        source_type=PointRecord.SourceType.MERCHANT_PAYMENT,
        source_id=str(merchant.id),
        reason=f"商户积分支付：{merchant.name}",
        merchant=merchant,
        yuan_amount=yuan_amount,
        request_no=request_no,
    )


# ---------------------------------------------------------------------------
# 商户固定积分码
# ---------------------------------------------------------------------------


def generate_point_code_token() -> str:
    return uuid4().hex


def point_code_content(code: str) -> str:
    return f"street-service://merchant-point-pay?code={code}"


def point_code_data(code: MerchantPointCode) -> dict:
    return {
        "id": code.id,
        "merchant_id": code.merchant_id,
        "merchant_name": code.merchant.name,
        "points": code.points,
        "code": code.code,
        "code_content": point_code_content(code.code),
        "is_active": code.is_active,
        "remark": code.remark,
        "created_at": code.created_at,
        "updated_at": code.updated_at,
    }


def get_active_point_code_or_404(code: str) -> MerchantPointCode:
    code = (code or "").strip()
    if not code:
        raise BusinessError("二维码标识不能为空")
    point_code = (
        MerchantPointCode.objects.select_related("merchant")
        .filter(code=code)
        .first()
    )
    if point_code is None:
        raise BusinessError("固定积分码不存在", status=404, code=40400)
    if not point_code.is_active:
        raise BusinessError("固定积分码已停用", status=403, code=40003)
    return point_code


def point_code_payment_preview(member: Member, code: str) -> dict:
    point_code = get_active_point_code_or_404(code)
    merchant = point_code.merchant
    if not merchant.is_active:
        raise BusinessError("商户已停用", status=403, code=40003)
    rule = active_exchange_rule()
    account = get_or_create_account(member)
    yuan_amount = (Decimal(point_code.points) / Decimal(rule.points_per_yuan)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return {
        "code": point_code.code,
        "merchant_id": merchant.id,
        "merchant_name": merchant.name,
        "points": point_code.points,
        "points_per_yuan": rule.points_per_yuan,
        "yuan_amount": f"{yuan_amount:.2f}",
        "balance": account.balance,
    }


def merchant_point_codes(merchant: Merchant, *, include_inactive: bool = False) -> list[dict]:
    queryset = MerchantPointCode.objects.filter(merchant=merchant)
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    queryset = queryset.order_by("points", "-id")
    return [point_code_data(code) for code in queryset.select_related("merchant")]


@transaction.atomic
def scan_point_code(member: Member, code: str, *, request_no: str = "") -> PointRecord:
    request_no = request_no.strip()
    point_code = get_active_point_code_or_404(code)
    merchant = Merchant.objects.select_for_update().get(pk=point_code.merchant_id)
    if not merchant.is_active:
        raise BusinessError("商户已停用", status=403, code=40003)
    points = point_code.points
    if points <= 0:
        raise BusinessError("固定积分值必须大于 0")
    if request_no:
        existing = (
            PointRecord.objects.select_related("merchant", "member")
            .filter(merchant=merchant, request_no=request_no, source_type=PointRecord.SourceType.MERCHANT_PAYMENT)
            .first()
        )
        if existing is not None:
            logger.info(
                "固定码扫码幂等重放 member=%s merchant=%s code=%s request_no=%s record_id=%s",
                member.id,
                merchant.id,
                point_code.code,
                request_no,
                existing.id,
            )
            return existing
    _check_daily_payment_limit(member, merchant)
    rule = active_exchange_rule()
    yuan_amount = (Decimal(points) / Decimal(rule.points_per_yuan)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    logger.info(
        "固定码扫码支付 member=%s merchant=%s code=%s points=%d yuan_amount=%s",
        member.id,
        merchant.id,
        point_code.code,
        points,
        yuan_amount,
    )
    return deduct_points(
        member,
        points,
        source_type=PointRecord.SourceType.MERCHANT_PAYMENT,
        source_id=str(merchant.id),
        reason=f"商户固定码支付：{merchant.name}",
        merchant=merchant,
        yuan_amount=yuan_amount,
        request_no=request_no,
    )

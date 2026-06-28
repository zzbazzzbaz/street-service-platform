from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction

from apps.members.models import Member
from apps.merchants.models import Merchant
from apps.points.models import PointExchangeRule, PointRecord
from apps.points.services import deduct_points, get_or_create_account
from shared.auth import issue_token
from shared.exceptions import BusinessError


def merchant_data(merchant: Merchant) -> dict:
    return {
        "id": merchant.id,
        "openid": merchant.openid,
        "name": merchant.name,
        "contact_name": merchant.contact_name,
        "phone": merchant.phone,
        "address": merchant.address,
        "is_active": merchant.is_active,
    }


def public_merchant_data(merchant: Merchant) -> dict:
    return {
        "id": merchant.id,
        "name": merchant.name,
        "contact_name": merchant.contact_name,
        "phone": merchant.phone,
        "address": merchant.address,
        "is_active": merchant.is_active,
    }


def test_login(openid: str) -> dict:
    openid = openid.strip()
    if not openid:
        raise BusinessError("openid 不能为空")
    merchant, _ = Merchant.objects.get_or_create(openid=openid, defaults={"name": f"测试商户-{openid}"})
    token, expires_in = issue_token(subject_type="merchant", openid=openid)
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "merchant": merchant_data(merchant),
    }


def wechat_login_placeholder(code: str) -> dict:
    code = code.strip()
    if not code:
        raise BusinessError("openid 或 code 不能为空", code=40000)
    if not settings.WECHAT_MINIAPP_APPID or not settings.WECHAT_MINIAPP_SECRET:
        raise BusinessError("商户微信登录未配置，开发期请使用测试登录", code=40000)
    raise BusinessError("商户微信登录暂未接入", code=40000)


def mask_name(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if len(value) == 1:
        return "*"
    return f"{value[0]}*"


def mask_phone(value: str) -> str:
    value = (value or "").strip()
    if len(value) < 7:
        return ""
    return f"{value[:3]}****{value[-4:]}"


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
            return existing
    rule = active_exchange_rule()
    yuan_amount = (Decimal(points) / Decimal(rule.points_per_yuan)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
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

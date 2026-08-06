from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction

from apps.members.models import Member
from apps.points.models import PointAccount, PointRecord
from shared.exceptions import BusinessError

logger = logging.getLogger("street.points")


def get_or_create_account(member: Member) -> PointAccount:
    account, _ = PointAccount.objects.get_or_create(member=member)
    return account


@transaction.atomic
def add_points(
    member: Member,
    amount: int,
    *,
    source_type: str,
    source_id: str = "",
    reason: str,
    operator=None,
) -> PointRecord:
    amount = int(amount)
    if amount <= 0:
        raise BusinessError("积分值必须大于 0")
    if not reason.strip():
        raise BusinessError("积分变动原因不能为空")

    get_or_create_account(member)
    account = PointAccount.objects.select_for_update().get(member=member)
    account.balance += amount
    account.save(update_fields=["balance"])
    record = PointRecord.objects.create(
        member=member,
        amount=amount,
        change_type=PointRecord.ChangeType.INCOME,
        source_type=source_type,
        source_id=str(source_id or ""),
        reason=reason.strip(),
        balance_after=account.balance,
        operator=operator,
    )
    logger.info(
        "积分增加 member=%s amount=%d source=%s balance_after=%d",
        member.id,
        amount,
        source_type,
        account.balance,
    )
    return record


@transaction.atomic
def deduct_points(
    member: Member,
    amount: int,
    *,
    source_type: str,
    source_id: str = "",
    reason: str,
    operator=None,
    merchant=None,
    yuan_amount: Decimal | None = None,
    request_no: str = "",
) -> PointRecord:
    amount = int(amount)
    if amount <= 0:
        raise BusinessError("积分值必须大于 0")
    get_or_create_account(member)
    account = PointAccount.objects.select_for_update().get(member=member)
    if not reason.strip():
        raise BusinessError("积分变动原因不能为空")
    if account.balance < amount:
        logger.warning(
            "积分扣减失败余额不足 member=%s need=%d balance=%d source=%s",
            member.id,
            amount,
            account.balance,
            source_type,
        )
        raise BusinessError("积分余额不足")

    account.balance -= amount
    account.save(update_fields=["balance"])
    record = PointRecord.objects.create(
        member=member,
        amount=-amount,
        change_type=PointRecord.ChangeType.EXPENSE,
        source_type=source_type,
        source_id=str(source_id or ""),
        reason=reason.strip(),
        balance_after=account.balance,
        operator=operator,
        merchant=merchant,
        yuan_amount=yuan_amount,
        request_no=request_no.strip(),
    )
    logger.info(
        "积分扣减 member=%s amount=%d source=%s balance_after=%d",
        member.id,
        amount,
        source_type,
        account.balance,
    )
    return record


def manual_add_points(member: Member, amount: int, *, reason: str, operator) -> PointRecord:
    if operator is None:
        raise BusinessError("人工加分必须记录操作人")
    if not reason.strip():
        raise BusinessError("人工加分原因不能为空")
    return add_points(
        member,
        amount,
        source_type=PointRecord.SourceType.MANUAL,
        reason=reason,
        operator=operator,
    )


def manual_deduct_points(member: Member, amount: int, *, reason: str, operator) -> PointRecord:
    if operator is None:
        raise BusinessError("人工扣分必须记录操作人")
    if not reason.strip():
        raise BusinessError("人工扣分原因不能为空")
    return deduct_points(
        member,
        amount,
        source_type=PointRecord.SourceType.MANUAL,
        reason=reason,
        operator=operator,
    )


def point_record_data(record: PointRecord) -> dict:
    return {
        "id": record.id,
        "amount": record.amount,
        "change_type": record.change_type,
        "source_type": record.source_type,
        "source_id": record.source_id,
        "reason": record.reason,
        "balance_after": record.balance_after,
        "merchant_id": record.merchant_id,
        "merchant_name": record.merchant.name if record.merchant_id else "",
        "yuan_amount": f"{record.yuan_amount:.2f}" if record.yuan_amount is not None else None,
        "request_no": record.request_no,
        "created_at": record.created_at,
    }

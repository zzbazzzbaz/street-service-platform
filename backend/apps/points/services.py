from __future__ import annotations

from django.db import transaction

from apps.members.models import Member
from apps.points.models import PointAccount, PointRecord
from shared.exceptions import BusinessError


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

    account = get_or_create_account(member)
    account.balance += amount
    account.save(update_fields=["balance"])
    return PointRecord.objects.create(
        member=member,
        amount=amount,
        change_type=PointRecord.ChangeType.INCOME,
        source_type=source_type,
        source_id=str(source_id or ""),
        reason=reason.strip(),
        balance_after=account.balance,
        operator=operator,
    )


@transaction.atomic
def deduct_points(
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
    account = get_or_create_account(member)
    if not reason.strip():
        raise BusinessError("积分变动原因不能为空")
    if account.balance < amount:
        raise BusinessError("积分余额不足")

    account.balance -= amount
    account.save(update_fields=["balance"])
    return PointRecord.objects.create(
        member=member,
        amount=-amount,
        change_type=PointRecord.ChangeType.EXPENSE,
        source_type=source_type,
        source_id=str(source_id or ""),
        reason=reason.strip(),
        balance_after=account.balance,
        operator=operator,
    )


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


def point_record_data(record: PointRecord) -> dict:
    return {
        "id": record.id,
        "amount": record.amount,
        "change_type": record.change_type,
        "source_type": record.source_type,
        "source_id": record.source_id,
        "reason": record.reason,
        "balance_after": record.balance_after,
        "created_at": record.created_at,
    }

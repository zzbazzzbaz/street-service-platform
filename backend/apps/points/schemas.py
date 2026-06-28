from datetime import datetime

from ninja import Schema


class PointBalanceOut(Schema):
    balance: int


class PointRecordOut(Schema):
    id: int
    amount: int
    change_type: str
    source_type: str
    source_id: str
    reason: str
    balance_after: int | None = None
    merchant_id: int | None = None
    merchant_name: str = ""
    yuan_amount: str | None = None
    request_no: str = ""
    created_at: datetime


class PointRecordsData(Schema):
    items: list[PointRecordOut]
    total: int
    page: int
    page_size: int

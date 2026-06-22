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
    created_at: datetime


class PointRecordsData(Schema):
    items: list[PointRecordOut]
    total: int
    page: int
    page_size: int

from datetime import datetime

from ninja import Schema


class ServiceRecordOut(Schema):
    record_type: str
    source_id: int
    title: str
    status: str
    status_label: str
    points: int
    occurred_at: datetime


class ServiceRecordsData(Schema):
    items: list[ServiceRecordOut]
    total: int
    page: int
    page_size: int

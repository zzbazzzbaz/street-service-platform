from datetime import datetime

from ninja import Schema


class ReportIn(Schema):
    title: str
    description: str = ""
    image: str = ""
    location: str = ""


class ReportOut(Schema):
    id: int
    title: str
    description: str
    image: str
    location: str
    points: int
    status: str
    review_comment: str
    point_record_id: int | None = None
    created_at: datetime


class ReportsData(Schema):
    items: list[ReportOut]
    total: int
    page: int
    page_size: int

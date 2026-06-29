from datetime import datetime

from ninja import Schema


class ReportIn(Schema):
    category_code: str = ""
    description: str = ""
    location: str
    image_urls: list[str] = []


class ReportOut(Schema):
    id: int
    category_code: str
    title: str
    description: str
    location: str
    image_urls: list[str]
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

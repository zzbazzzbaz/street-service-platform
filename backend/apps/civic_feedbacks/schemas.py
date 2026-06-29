from datetime import datetime

from ninja import Schema


class CivicFeedbackIn(Schema):
    title: str
    content: str
    material_urls: list[str] = []


class CivicFeedbackOut(Schema):
    id: int
    title: str
    content: str
    material_urls: list[str]
    status: str
    reply: str
    points: int
    point_record_id: int | None = None
    created_at: datetime


class CivicFeedbacksData(Schema):
    items: list[CivicFeedbackOut]
    total: int
    page: int
    page_size: int

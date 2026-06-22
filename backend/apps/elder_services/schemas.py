from datetime import datetime

from ninja import Schema


class ElderServiceTaskOut(Schema):
    id: int
    title: str
    description: str
    location: str
    points: int
    status: str


class ElderServiceTasksData(Schema):
    items: list[ElderServiceTaskOut]
    total: int
    page: int
    page_size: int


class FeedbackIn(Schema):
    content: str
    image: str = ""


class ElderServiceFeedbackOut(Schema):
    id: int
    task_id: int
    content: str
    image: str
    status: str
    review_comment: str
    point_record_id: int | None = None
    created_at: datetime


class ElderServiceFeedbacksData(Schema):
    items: list[ElderServiceFeedbackOut]
    total: int
    page: int
    page_size: int

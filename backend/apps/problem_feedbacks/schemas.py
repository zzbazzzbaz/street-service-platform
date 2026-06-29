from datetime import datetime

from ninja import Schema


class ProblemFeedbackIn(Schema):
    title: str
    content: str


class ProblemFeedbackOut(Schema):
    id: int
    title: str
    content: str
    status: str
    reply: str
    replied_at: datetime | None = None
    created_at: datetime


class ProblemFeedbacksData(Schema):
    items: list[ProblemFeedbackOut]
    total: int
    page: int
    page_size: int

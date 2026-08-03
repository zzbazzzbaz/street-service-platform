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
    visibility_status: str = "pending"
    is_public: bool = False
    reply: str
    replied_at: datetime | None = None
    created_at: datetime


class ProblemFeedbacksData(Schema):
    items: list[ProblemFeedbackOut]
    total: int
    page: int
    page_size: int


class PublicProblemFeedbackOut(Schema):
    id: int
    title: str
    content: str
    status: str
    visibility_status: str
    is_public: bool
    reply: str
    replied_at: datetime | None = None
    created_at: datetime


class PublicProblemFeedbacksData(Schema):
    items: list[PublicProblemFeedbackOut]
    total: int
    page: int
    page_size: int

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
    image_urls: list[str] = []


class DirectFeedbackIn(Schema):
    content: str
    image_urls: list[str] = []


class ElderRelationOut(Schema):
    id: int
    member_id: int
    elder_name: str
    elder_address: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ElderServiceFeedbackOut(Schema):
    id: int
    relation_id: int | None = None
    member_id: int | None = None
    task_id: int | None = None
    task_title: str = ""
    elder_name: str = ""
    elder_address: str = ""
    content: str
    image_urls: list[str]
    points: int = 0
    status: str
    review_comment: str
    reviewed_at: datetime | None = None
    point_record_id: int | None = None
    created_at: datetime


class ElderServiceFeedbacksData(Schema):
    items: list[ElderServiceFeedbackOut]
    total: int
    page: int
    page_size: int


class ElderServiceLatestFeedbackOut(Schema):
    id: int
    status: str
    review_comment: str
    point_record_id: int | None = None
    created_at: datetime


class ElderServiceMyTaskOut(Schema):
    task_id: int
    title: str
    description: str
    elder_name: str
    elder_address: str
    frequency: str
    points: int
    feedback_status: str
    latest_feedback: ElderServiceLatestFeedbackOut | None = None


class ElderServiceMyTasksData(Schema):
    items: list[ElderServiceMyTaskOut]
    total: int
    page: int
    page_size: int

from datetime import datetime

from ninja import Schema


class LearningContentOut(Schema):
    id: int
    title: str
    cover: str
    cover_url: str
    body: str
    content_type: str
    image_urls: list[str]
    video_url: str
    points: int
    required_seconds: int
    is_active: bool


class LearningContentsData(Schema):
    items: list[LearningContentOut]
    total: int
    page: int
    page_size: int


class CompleteLearningIn(Schema):
    learned_seconds: int


class LearningRecordOut(Schema):
    id: int
    content_id: int
    learned_seconds: int
    is_completed: bool
    completed_at: datetime | None = None
    point_record_id: int | None = None


class LearningRecordsData(Schema):
    items: list[LearningRecordOut]
    total: int
    page: int
    page_size: int

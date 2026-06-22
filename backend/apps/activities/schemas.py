from datetime import datetime

from ninja import Schema


class ActivityOut(Schema):
    id: int
    title: str
    body: str
    location: str
    start_time: datetime
    end_time: datetime
    points: int
    status: str


class ActivitiesData(Schema):
    items: list[ActivityOut]
    total: int
    page: int
    page_size: int


class ActivitySignupOut(Schema):
    id: int
    activity_id: int
    created_at: datetime


class ActivitySignupsData(Schema):
    items: list[ActivitySignupOut]
    total: int
    page: int
    page_size: int


class ActivityCheckinIn(Schema):
    checkin_code: str


class ActivityCheckinOut(Schema):
    id: int
    activity_id: int
    status: str
    review_comment: str
    point_record_id: int | None = None
    created_at: datetime

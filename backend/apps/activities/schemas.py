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
    user_signup_id: int | None = None
    signup_status: str = "not_joined"
    checkin_status: str = "not_checked"
    point_status: str = "not_granted"


class ActivitiesData(Schema):
    items: list[ActivityOut]
    total: int
    page: int
    page_size: int


class ActivitySignupOut(Schema):
    id: int
    activity_id: int
    title: str
    body: str
    location: str
    start_time: datetime
    end_time: datetime
    points: int
    signup_status: str
    created_at: datetime
    cancelled_at: datetime | None = None
    checkin_status: str
    checkin_at: datetime | None = None
    point_status: str
    point_record_id: int | None = None


class ActivitySignupCancelOut(Schema):
    activity_id: int
    signup_status: str
    cancelled_at: datetime


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

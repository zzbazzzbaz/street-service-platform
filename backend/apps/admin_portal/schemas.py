from datetime import date, datetime

from ninja import Schema


class AdminLoginIn(Schema):
    username: str
    password: str


class AdminUserOut(Schema):
    id: int
    username: str
    email: str
    first_name: str = ""
    last_name: str = ""
    is_active: bool
    is_staff: bool
    is_backend_manager: bool
    is_superuser: bool
    last_login: datetime | None = None


class AdminLoginOut(Schema):
    access_token: str
    token_type: str
    expires_in: int
    admin: AdminUserOut


class ChoiceItemOut(Schema):
    value: str
    label: str


class AdminEnumsOut(Schema):
    member_identity_types: list[ChoiceItemOut]
    member_audit_statuses: list[ChoiceItemOut]
    learning_content_types: list[ChoiceItemOut]
    report_category_codes: list[ChoiceItemOut]
    report_statuses: list[ChoiceItemOut]
    civic_feedback_statuses: list[ChoiceItemOut]
    problem_feedback_statuses: list[ChoiceItemOut]
    activity_statuses: list[ChoiceItemOut]
    activity_checkin_statuses: list[ChoiceItemOut]
    elder_task_statuses: list[ChoiceItemOut]
    elder_feedback_statuses: list[ChoiceItemOut]
    point_change_types: list[ChoiceItemOut]
    point_source_types: list[ChoiceItemOut]
    merchant_settlement_period_types: list[ChoiceItemOut]
    merchant_settlement_statuses: list[ChoiceItemOut]


class AdminDashboardSummaryOut(Schema):
    pending_member_audits: int
    pending_reports: int
    pending_civic_feedbacks: int
    pending_problem_feedbacks: int
    pending_activity_checkins: int
    pending_elder_service_feedbacks: int
    today_merchant_payment_count: int
    today_merchant_payment_points: int
    pending_merchant_settlements: int


class AdminUserCreateIn(Schema):
    username: str
    password: str
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    is_backend_manager: bool = True
    is_active: bool = True


class AdminUserUpdateIn(Schema):
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    is_backend_manager: bool = True


class StatusIn(Schema):
    is_active: bool


class PasswordResetIn(Schema):
    password: str


class MemberUpdateIn(Schema):
    nickname: str = ""
    phone: str = ""
    real_name: str = ""
    identity_type: str = ""


class MemberAuditIn(Schema):
    action: str
    remark: str = ""


class LearningContentIn(Schema):
    title: str
    cover: str = ""
    image: str = ""
    video: str = ""
    body: str = ""
    content_type: str = "article"
    points: int = 0
    required_seconds: int = 60
    is_active: bool = True


class LearningContentUpdateIn(Schema):
    title: str | None = None
    cover: str | None = None
    image: str | None = None
    video: str | None = None
    body: str | None = None
    content_type: str | None = None
    points: int | None = None
    required_seconds: int | None = None
    is_active: bool | None = None


class LearningContentStatusIn(Schema):
    is_active: bool


class ReportUpdateIn(Schema):
    category_code: str | None = None
    title: str | None = None
    description: str | None = None
    location: str | None = None
    points: int | None = None
    image_urls: list[str] | None = None


class ReviewIn(Schema):
    action: str
    comment: str = ""


class CivicFeedbackUpdateIn(Schema):
    title: str | None = None
    content: str | None = None
    material_urls: list[str] | None = None
    points: int | None = None


class CivicFeedbackReviewIn(Schema):
    action: str
    reply: str
    points: int = 0


class ProblemFeedbackUpdateIn(Schema):
    title: str | None = None
    content: str | None = None
    status: str | None = None


class ProblemFeedbackReplyIn(Schema):
    reply: str


class ProblemFeedbackStatusIn(Schema):
    status: str


class ActivityIn(Schema):
    title: str
    body: str = ""
    location: str = ""
    start_time: datetime
    end_time: datetime
    points: int = 0
    status: str = "draft"


class ActivityUpdateIn(Schema):
    title: str | None = None
    body: str | None = None
    location: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    points: int | None = None
    status: str | None = None


class ActivityStatusIn(Schema):
    status: str


class ElderRelationIn(Schema):
    member_id: int
    elder_name: str
    elder_address: str
    frequency: str = ""
    is_active: bool = True


class ElderRelationUpdateIn(Schema):
    member_id: int | None = None
    elder_name: str | None = None
    elder_address: str | None = None
    frequency: str | None = None
    is_active: bool | None = None


class ElderTaskIn(Schema):
    title: str
    relation_id: int | None = None
    description: str = ""
    location: str = ""
    points: int = 0
    status: str = "draft"


class ElderTaskUpdateIn(Schema):
    title: str | None = None
    relation_id: int | None = None
    description: str | None = None
    location: str | None = None
    points: int | None = None
    status: str | None = None


class GenericStatusIn(Schema):
    status: str


class ElderFeedbackUpdateIn(Schema):
    content: str | None = None
    image: str | None = None
    image_urls: list[str] | None = None


class ManualAdjustmentCreateIn(Schema):
    member_id: int
    amount: int
    reason: str


class ExchangeRuleIn(Schema):
    points_per_yuan: int
    is_active: bool = True


class ExchangeRuleStatusIn(Schema):
    is_active: bool


class MerchantIn(Schema):
    openid: str = ""
    name: str
    contact_name: str = ""
    phone: str = ""
    address: str = ""
    is_active: bool = True


class MerchantUpdateIn(Schema):
    openid: str | None = None
    name: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    address: str | None = None
    is_active: bool | None = None


class SettlementIn(Schema):
    merchant_id: int
    period_type: str
    period_label: str
    date_from: date
    date_to: date
    record_count: int = 0
    total_points: int = 0
    total_yuan_amount: str = "0.00"
    status: str = "pending"
    processor_name: str = ""
    remark: str = ""


class SettlementUpdateIn(Schema):
    period_type: str | None = None
    period_label: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    record_count: int | None = None
    total_points: int | None = None
    total_yuan_amount: str | None = None
    status: str | None = None
    processor_name: str | None = None
    remark: str | None = None


class SettlementGenerateIn(Schema):
    merchant_id: int
    period_type: str
    period_label: str
    date_from: date
    date_to: date


class SettlementProcessIn(Schema):
    processor_name: str
    remark: str = ""


class MerchantPointCodeCreateIn(Schema):
    merchant_id: int
    points: int
    remark: str = ""


class MerchantPointCodeUpdateIn(Schema):
    points: int | None = None
    remark: str | None = None
    is_active: bool | None = None

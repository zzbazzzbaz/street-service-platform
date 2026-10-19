from urllib.parse import quote

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Form, Router

from apps.activities.models import Activity, ActivityCheckin, ActivitySignup
from apps.activities.services import activity_data
from apps.admin_portal.auth import authenticate_admin
from apps.admin_portal.schemas import (
    ActivityIn,
    ActivityStatusIn,
    ActivityUpdateIn,
    AdminDashboardSummaryOut,
    AdminEnumsOut,
    AdminLoginIn,
    AdminLoginOut,
    AdminUserCreateIn,
    AdminUserOut,
    AdminUserUpdateIn,
    CivicFeedbackReviewIn,
    CivicFeedbackUpdateIn,
    ElderFeedbackUpdateIn,
    ElderRelationIn,
    ElderRelationUpdateIn,
    ElderTaskIn,
    ElderTaskUpdateIn,
    ExchangeRuleIn,
    ExchangeRuleStatusIn,
    GenericStatusIn,
    ImportResultOut,
    LearningContentIn,
    LearningContentStatusIn,
    LearningContentUpdateIn,
    PinnedItemIn,
    PinnedItemsIn,
    ServiceLocationIn,
    ServiceLocationStatusIn,
    ServiceLocationUpdateIn,
    ManualAdjustmentCreateIn,
    MemberAuditIn,
    MemberUpdateIn,
    MerchantAuditIn,
    MerchantIn,
    MerchantPointCodeCreateIn,
    MerchantPointCodeUpdateIn,
    MerchantUpdateIn,
    PasswordResetIn,
    ProblemFeedbackReplyIn,
    ProblemFeedbackStatusIn,
    ProblemFeedbackUpdateIn,
    ReportUpdateIn,
    ReviewIn,
    SettlementGenerateIn,
    SettlementIn,
    SettlementProcessIn,
    SettlementUpdateIn,
    StatusIn,
    VisibilityReviewIn,
)
from apps.admin_portal import importers
from apps.admin_portal import services as svc
from django_ratelimit.decorators import ratelimit
from apps.civic_feedbacks.models import CivicFeedback
from apps.elder_services.models import ElderCareRelation, ElderServiceFeedback, ElderServiceTask
from apps.learning.models import LearningContent, LearningRecord
from apps.learning.services import set_pinned_items
from apps.service_locations.models import ServiceLocation
from apps.service_locations.services import service_location_data
from apps.members.models import Member
from apps.members.services import member_data
from apps.merchants.models import Merchant, MerchantPointCode, MerchantSettlement
from apps.merchants.services import fixed_code_data, merchant_data, point_code_data, settlement_data
from apps.points.models import ManualPointAdjustment, PointAccount, PointExchangeRule, PointRecord
from apps.problem_feedbacks.models import ProblemFeedback
from apps.problem_feedbacks.services import reply_problem_feedback
from apps.reports.models import Report
from apps.reports.services import review_report
from shared.api import ErrorResponse, SuccessResponse, error_response, success_response
from shared.exceptions import BusinessError
from shared.ratelimit import user_key


router = Router(tags=["后台管理"])
auth_router = Router(tags=["后台认证"])


def _admin_or_error(request):
    return authenticate_admin(request)


def _business_error(exc: BusinessError):
    return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@auth_router.post("/login", response={200: SuccessResponse[AdminLoginOut], 400: ErrorResponse, 403: ErrorResponse})
@ratelimit(key="ip", rate="5/m", block=True)
def admin_login(request, payload: AdminLoginIn):
    try:
        return success_response(svc.login_admin(payload.username, payload.password))
    except BusinessError as exc:
        return _business_error(exc)


@auth_router.get("/me", response={200: SuccessResponse[AdminUserOut], 401: ErrorResponse, 403: ErrorResponse})
def admin_me(request):
    try:
        return success_response(svc.admin_user_data(_admin_or_error(request)))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/enums", response={200: SuccessResponse[AdminEnumsOut], 401: ErrorResponse, 403: ErrorResponse})
def admin_enums(request):
    try:
        _admin_or_error(request)
        return success_response(svc.enum_data())
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/dashboard/summary", response={200: SuccessResponse[AdminDashboardSummaryOut], 401: ErrorResponse, 403: ErrorResponse})
def admin_dashboard_summary(request):
    try:
        _admin_or_error(request)
        return success_response(svc.dashboard_summary_data())
    except BusinessError as exc:
        return _business_error(exc)


# Admin accounts


@router.get("/admin-users", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_users(request, keyword: str = "", page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        return success_response(svc.admin_users_data(keyword=keyword, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/admin-users", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def admin_user_create(request, payload: AdminUserCreateIn):
    try:
        _admin_or_error(request)
        return success_response(svc.create_admin_user(payload))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/admin-users/{user_id}/status", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_user_status(request, user_id: int, payload: StatusIn):
    try:
        admin = _admin_or_error(request)
        return success_response(svc.set_admin_user_status(user_id, is_active=payload.is_active, current_admin=admin))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/admin-users/{user_id}/password", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_user_password(request, user_id: int, payload: PasswordResetIn):
    try:
        _admin_or_error(request)
        return success_response(svc.reset_admin_user_password(user_id, password=payload.password))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/admin-users/{user_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_user_detail(request, user_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.admin_user_data(svc.get_or_404(svc.User, user_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.patch("/admin-users/{user_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_user_update(request, user_id: int, payload: AdminUserUpdateIn):
    try:
        _admin_or_error(request)
        return success_response(svc.update_admin_user(user_id, payload))
    except BusinessError as exc:
        return _business_error(exc)


# Members


@router.get("/members", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_members(request, keyword: str = "", audit_status: str = "", is_active: str = "", page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        return success_response(svc.members_data(keyword=keyword, audit_status=audit_status, is_active=is_active, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/members/{member_id}/points", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_member_points(request, member_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.member_points_data(member_id))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/members/{member_id}/status", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_member_status(request, member_id: int, payload: StatusIn):
    try:
        _admin_or_error(request)
        return success_response(svc.set_member_status(member_id, is_active=payload.is_active))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/members/{member_id}/audit", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_member_audit(request, member_id: int, payload: MemberAuditIn):
    try:
        _admin_or_error(request)
        return success_response(svc.audit_member(member_id, action=payload.action, remark=payload.remark))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/members/{member_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_member_detail(request, member_id: int):
    try:
        _admin_or_error(request)
        return success_response(member_data(svc.get_or_404(Member, member_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.patch("/members/{member_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_member_update(request, member_id: int, payload: MemberUpdateIn):
    try:
        _admin_or_error(request)
        return success_response(svc.update_member(member_id, payload))
    except BusinessError as exc:
        return _business_error(exc)


# Uploads and learning


@router.post("/uploads/images", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def admin_upload_images(request, business_type: str = Form("general"), related_id: str = Form("")):
    try:
        _admin_or_error(request)
        return success_response(svc.save_admin_images(request, request.FILES.getlist("files"), business_type=business_type, related_id=related_id))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/uploads/videos", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def admin_upload_videos(request):
    try:
        _admin_or_error(request)
        return success_response(svc.save_uploaded_video(request, request.FILES.getlist("files")))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/learning/records", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_learning_records(request, page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        return success_response(svc.paginated_data(LearningRecord.objects.select_related("member", "content"), svc.admin_record_data, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/learning/records/{record_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_learning_record_detail(request, record_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.admin_record_data(svc.get_or_404(LearningRecord, record_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/learning/contents", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_learning_contents(request, keyword: str = "", status: str = "", page: int = 1, page_size: int = 20, is_announcement: bool | None = None, is_active: bool | None = None):
    try:
        _admin_or_error(request)
        queryset = LearningContent.objects.all()
        if keyword:
            queryset = queryset.filter(title__icontains=keyword)
        if status in {"active", "inactive"}:
            queryset = queryset.filter(is_active=status == "active")
        if is_announcement is not None:
            queryset = queryset.filter(is_announcement=is_announcement)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        return success_response(svc.paginated_data(queryset, lambda item: svc.learning_content_admin_data(item, request=request), page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/learning/contents", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def admin_learning_content_create(request, payload: LearningContentIn):
    try:
        _admin_or_error(request)
        return success_response(svc.learning_content_admin_data(svc.create_learning_content(payload), request=request))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/learning/contents/{content_id}/status", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_learning_content_status(request, content_id: int, payload: LearningContentStatusIn):
    try:
        _admin_or_error(request)
        content = svc.get_or_404(LearningContent, content_id)
        content.is_active = payload.is_active
        if not content.is_active:
            content.is_pinned = False
            content.pin_order = None
        content.save(update_fields=["is_active", "is_pinned", "pin_order"])
        return success_response(svc.learning_content_admin_data(content, request=request))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/learning/contents/{content_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_learning_content_detail(request, content_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.learning_content_admin_data(svc.get_or_404(LearningContent, content_id), request=request))
    except BusinessError as exc:
        return _business_error(exc)


@router.patch("/learning/contents/{content_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_learning_content_update(request, content_id: int, payload: LearningContentUpdateIn):
    try:
        _admin_or_error(request)
        return success_response(svc.learning_content_admin_data(svc.update_learning_content(content_id, payload), request=request))
    except BusinessError as exc:
        return _business_error(exc)


@router.delete("/learning/contents/{content_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_learning_content_delete(request, content_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.delete_learning_content(content_id))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/learning/announcements/pinned", response={200: SuccessResponse[list[dict]], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def admin_learning_pinned_save(request, payload: PinnedItemsIn):
    try:
        _admin_or_error(request)
        pins = set_pinned_items([{"content_id": it.content_id, "pin_order": it.pin_order} for it in payload.items])
        return success_response([svc.learning_content_admin_data(c, request=request) for c in pins])
    except BusinessError as exc:
        return _business_error(exc)


# Service locations


@router.get("/service-locations", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_service_locations(request, keyword: str = "", is_active: str = "", page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        return success_response(svc.service_locations_data(keyword=keyword, is_active=is_active, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/service-locations", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def admin_service_location_create(request, payload: ServiceLocationIn):
    try:
        _admin_or_error(request)
        return success_response(service_location_data(svc.create_service_location(payload)))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/service-locations/{location_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_service_location_detail(request, location_id: int):
    try:
        _admin_or_error(request)
        return success_response(service_location_data(svc.get_or_404(ServiceLocation, location_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.patch("/service-locations/{location_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_service_location_update(request, location_id: int, payload: ServiceLocationUpdateIn):
    try:
        _admin_or_error(request)
        return success_response(service_location_data(svc.update_service_location(location_id, payload)))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/service-locations/{location_id}/status", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_service_location_status(request, location_id: int, payload: ServiceLocationStatusIn):
    try:
        _admin_or_error(request)
        location = svc.get_or_404(ServiceLocation, location_id)
        location.is_active = payload.is_active
        location.save(update_fields=["is_active"])
        return success_response(service_location_data(location))
    except BusinessError as exc:
        return _business_error(exc)


# Reports and feedbacks


@router.get("/reports", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_reports(request, keyword: str = "", category_code: str = "", status: str = "", page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        return success_response(svc.reports_data(keyword=keyword, category_code=category_code, status=status, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/reports/{report_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_report_detail(request, report_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.report_admin_data(svc.get_or_404(Report, report_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.patch("/reports/{report_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_report_update(request, report_id: int, payload: ReportUpdateIn):
    try:
        _admin_or_error(request)
        return success_response(svc.update_report(report_id, payload))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/reports/{report_id}/review", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_report_review(request, report_id: int, payload: ReviewIn):
    try:
        admin = _admin_or_error(request)
        return success_response(svc.report_admin_data(review_report(svc.get_or_404(Report, report_id), action=payload.action, comment=payload.comment, operator=admin)))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/civic-feedbacks", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_civic_feedbacks(request, keyword: str = "", status: str = "", page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        return success_response(svc.civic_feedbacks_data(keyword=keyword, status=status, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/civic-feedbacks/{feedback_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_civic_feedback_detail(request, feedback_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.civic_feedback_admin_data(svc.get_or_404(CivicFeedback, feedback_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.patch("/civic-feedbacks/{feedback_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_civic_feedback_update(request, feedback_id: int, payload: CivicFeedbackUpdateIn):
    try:
        _admin_or_error(request)
        return success_response(svc.update_civic_feedback(feedback_id, payload))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/civic-feedbacks/{feedback_id}/review", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_civic_feedback_review(request, feedback_id: int, payload: CivicFeedbackReviewIn):
    try:
        admin = _admin_or_error(request)
        return success_response(svc.review_civic_feedback(feedback_id, payload, admin))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/problem-feedbacks", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_problem_feedbacks(request, keyword: str = "", status: str = "", visibility_status: str = "", member_id: int = 0, page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        return success_response(svc.problem_feedbacks_data(
            keyword=keyword, status=status, visibility_status=visibility_status,
            member_id=member_id, page=page, page_size=page_size,
        ))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/problem-feedbacks/{feedback_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_problem_feedback_detail(request, feedback_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.problem_feedback_admin_data(svc.get_or_404(ProblemFeedback, feedback_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.patch("/problem-feedbacks/{feedback_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_problem_feedback_update(request, feedback_id: int, payload: ProblemFeedbackUpdateIn):
    try:
        _admin_or_error(request)
        return success_response(svc.update_problem_feedback(feedback_id, payload))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/problem-feedbacks/{feedback_id}/reply", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_problem_feedback_reply(request, feedback_id: int, payload: ProblemFeedbackReplyIn):
    try:
        _admin_or_error(request)
        return success_response(svc.problem_feedback_admin_data(reply_problem_feedback(svc.get_or_404(ProblemFeedback, feedback_id), reply=payload.reply)))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/problem-feedbacks/{feedback_id}/status", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_problem_feedback_status(request, feedback_id: int, payload: ProblemFeedbackStatusIn):
    try:
        _admin_or_error(request)
        return success_response(svc.set_problem_feedback_status(feedback_id, status=payload.status))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/problem-feedbacks/{feedback_id}/visibility", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_problem_feedback_visibility(request, feedback_id: int, payload: VisibilityReviewIn):
    try:
        admin = _admin_or_error(request)
        return success_response(svc.review_problem_feedback_visibility(
            feedback_id,
            visibility_status=payload.visibility_status,
            is_public=payload.is_public,
            operator=admin,
        ))
    except BusinessError as exc:
        return _business_error(exc)


# Activities


@router.get("/activities/signups", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_activity_signups(request, activity_type: str = "", page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        queryset = ActivitySignup.objects.select_related("member", "activity")
        if activity_type:
            if activity_type not in Activity.ActivityType.values:
                raise BusinessError("活动类型不支持")
            queryset = queryset.filter(activity__activity_type=activity_type)
        return success_response(svc.paginated_data(queryset, svc.signup_admin_data, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/activities/signups/{signup_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_activity_signup_detail(request, signup_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.signup_admin_data(svc.get_or_404(ActivitySignup, signup_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/activities/checkins", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_activity_checkins(request, activity_type: str = "", page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        queryset = ActivityCheckin.objects.select_related("member", "activity")
        if activity_type:
            if activity_type not in Activity.ActivityType.values:
                raise BusinessError("活动类型不支持")
            queryset = queryset.filter(activity__activity_type=activity_type)
        return success_response(svc.paginated_data(queryset, svc.checkin_admin_data, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/activities/checkins/{checkin_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_activity_checkin_detail(request, checkin_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.checkin_admin_data(svc.get_or_404(ActivityCheckin, checkin_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/activities/checkins/{checkin_id}/review", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_activity_checkin_review(request, checkin_id: int, payload: ReviewIn):
    try:
        admin = _admin_or_error(request)
        return success_response(svc.checkin_admin_data(svc.review_checkin(svc.get_or_404(ActivityCheckin, checkin_id), action=payload.action, comment=payload.comment, operator=admin)))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/activities", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_activities(request, status: str = "", activity_type: str = "", page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        queryset = Activity.objects.all()
        if status:
            queryset = queryset.filter(status=status)
        if activity_type:
            if activity_type not in Activity.ActivityType.values:
                raise BusinessError("活动类型不支持")
            queryset = queryset.filter(activity_type=activity_type)
        return success_response(svc.paginated_data(queryset, lambda item: activity_data(item, include_checkin_secret=True), page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/activities", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def admin_activity_create(request, payload: ActivityIn):
    try:
        _admin_or_error(request)
        return success_response(activity_data(svc.create_activity(payload), include_checkin_secret=True))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/activities/{activity_id}/checkin-code", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_activity_checkin_code(request, activity_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.checkin_code_data(svc.get_or_404(Activity, activity_id), request=request))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/activities/{activity_id}/status", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_activity_status(request, activity_id: int, payload: ActivityStatusIn):
    try:
        _admin_or_error(request)
        activity = svc.get_or_404(Activity, activity_id)
        if payload.status not in Activity.Status.values:
            raise BusinessError("活动状态不支持")
        activity.status = payload.status
        activity.save(update_fields=["status"])
        return success_response(activity_data(activity, include_checkin_secret=True))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/activities/{activity_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_activity_detail(request, activity_id: int):
    try:
        _admin_or_error(request)
        return success_response(activity_data(svc.get_or_404(Activity, activity_id), include_checkin_secret=True))
    except BusinessError as exc:
        return _business_error(exc)


@router.patch("/activities/{activity_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_activity_update(request, activity_id: int, payload: ActivityUpdateIn):
    try:
        _admin_or_error(request)
        return success_response(activity_data(svc.update_activity(activity_id, payload), include_checkin_secret=True))
    except BusinessError as exc:
        return _business_error(exc)


@router.delete("/activities/{activity_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_activity_delete(request, activity_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.delete_activity(activity_id))
    except BusinessError as exc:
        return _business_error(exc)


# Elder services


@router.get("/elder-services/relations", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_elder_relations(request, page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        return success_response(svc.paginated_data(ElderCareRelation.objects.select_related("member"), svc.relation_data, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/elder-services/relations", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def admin_elder_relation_create(request, payload: ElderRelationIn):
    try:
        _admin_or_error(request)
        return success_response(svc.relation_data(svc.create_relation(payload)))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/elder-services/relations/{relation_id}/status", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_elder_relation_status(request, relation_id: int, payload: StatusIn):
    try:
        _admin_or_error(request)
        relation = svc.get_or_404(ElderCareRelation, relation_id)
        relation.is_active = payload.is_active
        relation.save(update_fields=["is_active"])
        return success_response(svc.relation_data(relation))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/elder-services/relations/{relation_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_elder_relation_detail(request, relation_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.relation_data(svc.get_or_404(ElderCareRelation, relation_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.patch("/elder-services/relations/{relation_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_elder_relation_update(request, relation_id: int, payload: ElderRelationUpdateIn):
    try:
        _admin_or_error(request)
        return success_response(svc.relation_data(svc.update_relation(relation_id, payload)))
    except BusinessError as exc:
        return _business_error(exc)


@router.delete("/elder-services/relations/{relation_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_elder_relation_delete(request, relation_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.delete_relation(relation_id))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/elder-services/tasks", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_elder_tasks(request, page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        return success_response(svc.paginated_data(ElderServiceTask.objects.select_related("relation__member"), svc.elder_task_admin_data, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/elder-services/tasks", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def admin_elder_task_create(request, payload: ElderTaskIn):
    try:
        _admin_or_error(request)
        return success_response(svc.elder_task_admin_data(svc.create_elder_task(payload)))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/elder-services/tasks/{task_id}/status", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_elder_task_status(request, task_id: int, payload: GenericStatusIn):
    try:
        _admin_or_error(request)
        task = svc.get_or_404(ElderServiceTask, task_id)
        if payload.status not in ElderServiceTask.Status.values:
            raise BusinessError("任务状态不支持")
        task.status = payload.status
        task.save(update_fields=["status"])
        return success_response(svc.elder_task_admin_data(task))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/elder-services/tasks/{task_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_elder_task_detail(request, task_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.elder_task_admin_data(svc.get_or_404(ElderServiceTask, task_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.patch("/elder-services/tasks/{task_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_elder_task_update(request, task_id: int, payload: ElderTaskUpdateIn):
    try:
        _admin_or_error(request)
        return success_response(svc.elder_task_admin_data(svc.update_elder_task(task_id, payload)))
    except BusinessError as exc:
        return _business_error(exc)


@router.delete("/elder-services/tasks/{task_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_elder_task_delete(request, task_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.delete_elder_task(task_id))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/elder-services/feedbacks", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_elder_feedbacks(request, status: str = "", member_id: int = 0, relation_id: int = 0, keyword: str = "", page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        queryset = ElderServiceFeedback.objects.select_related("member", "task", "relation")
        if status:
            queryset = queryset.filter(status=status)
        if member_id:
            queryset = queryset.filter(member_id=member_id)
        if relation_id:
            queryset = queryset.filter(relation_id=relation_id)
        if keyword:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(member__nickname__icontains=keyword)
                | Q(member__real_name__icontains=keyword)
                | Q(member__phone__icontains=keyword)
                | Q(elder_name__icontains=keyword)
            )
        return success_response(svc.paginated_data(queryset, svc.elder_feedback_admin_data, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/elder-services/feedbacks/{feedback_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_elder_feedback_detail(request, feedback_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.elder_feedback_admin_data(svc.get_or_404(ElderServiceFeedback, feedback_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.patch("/elder-services/feedbacks/{feedback_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_elder_feedback_update(request, feedback_id: int, payload: ElderFeedbackUpdateIn):
    try:
        _admin_or_error(request)
        return success_response(svc.update_elder_feedback(feedback_id, payload))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/elder-services/feedbacks/{feedback_id}/review", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_elder_feedback_review(request, feedback_id: int, payload: ReviewIn):
    try:
        admin = _admin_or_error(request)
        return success_response(svc.elder_feedback_admin_data(svc.review_feedback(svc.get_or_404(ElderServiceFeedback, feedback_id), action=payload.action, comment=payload.comment, operator=admin)))
    except BusinessError as exc:
        return _business_error(exc)


# Points


@router.get("/points/accounts", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_point_accounts(request, page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        return success_response(svc.paginated_data(PointAccount.objects.select_related("member"), svc.point_account_data, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/points/accounts/{account_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_point_account_detail(request, account_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.point_account_data(svc.get_or_404(PointAccount, account_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/points/records", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_point_records(request, page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        return success_response(svc.paginated_data(PointRecord.objects.select_related("merchant", "member"), svc.point_record_admin_data, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/points/records/{record_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_point_record_detail(request, record_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.point_record_admin_data(svc.get_or_404(PointRecord, record_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/points/manual-adjustments", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_manual_adjustments(request, page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        return success_response(svc.paginated_data(ManualPointAdjustment.objects.select_related("member", "operator"), svc.manual_adjustment_data, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/points/manual-adjustments", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
@ratelimit(key=user_key, rate="20/m", block=True)
def admin_manual_adjustment_create(request, payload: ManualAdjustmentCreateIn):
    try:
        admin = _admin_or_error(request)
        return success_response(svc.create_manual_adjustment(payload, admin))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/points/manual-adjustments/{adjustment_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_manual_adjustment_detail(request, adjustment_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.manual_adjustment_data(svc.get_or_404(ManualPointAdjustment, adjustment_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/points/exchange-rules", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_exchange_rules(request, page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        return success_response(svc.paginated_data(PointExchangeRule.objects.all(), svc.exchange_rule_data, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/points/exchange-rules", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def admin_exchange_rule_create(request, payload: ExchangeRuleIn):
    try:
        _admin_or_error(request)
        rule = PointExchangeRule(points_per_yuan=payload.points_per_yuan, is_active=payload.is_active)
        return success_response(svc.exchange_rule_data(svc.save_exchange_rule(rule)))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/points/exchange-rules/{rule_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_exchange_rule_detail(request, rule_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.exchange_rule_data(svc.get_or_404(PointExchangeRule, rule_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.patch("/points/exchange-rules/{rule_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_exchange_rule_update(request, rule_id: int, payload: ExchangeRuleIn):
    try:
        _admin_or_error(request)
        return success_response(svc.exchange_rule_data(svc.save_exchange_rule(svc.get_or_404(PointExchangeRule, rule_id), points_per_yuan=payload.points_per_yuan, is_active=payload.is_active)))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/points/exchange-rules/{rule_id}/status", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_exchange_rule_status(request, rule_id: int, payload: ExchangeRuleStatusIn):
    try:
        _admin_or_error(request)
        return success_response(svc.exchange_rule_data(svc.save_exchange_rule(svc.get_or_404(PointExchangeRule, rule_id), is_active=payload.is_active)))
    except BusinessError as exc:
        return _business_error(exc)


# Merchants


@router.get("/merchants/point-records", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_merchant_point_records(request, keyword: str = "", merchant_id: int | None = None, month: str = "", date_from: str | None = None, date_to: str | None = None, page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        queryset = svc.merchant_payment_records_queryset(merchant_id=merchant_id, keyword=keyword, month=month, date_from=date_from, date_to=date_to)
        return success_response(svc.merchant_payment_records_data(queryset, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/merchants/settlements", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_settlements(request, merchant_id: int | None = None, status: str = "", page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        return success_response(svc.settlements_data(merchant_id=merchant_id, status=status, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/merchants/settlements", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def admin_settlement_create(request, payload: SettlementIn):
    try:
        _admin_or_error(request)
        return success_response(settlement_data(svc.create_settlement(payload)))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/merchants/settlements/generate", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def admin_settlement_generate(request, payload: SettlementGenerateIn):
    try:
        _admin_or_error(request)
        return success_response(settlement_data(svc.generate_settlement(payload)))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/merchants/settlements/{settlement_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_settlement_detail(request, settlement_id: int):
    try:
        _admin_or_error(request)
        return success_response(settlement_data(svc.get_or_404(MerchantSettlement, settlement_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.patch("/merchants/settlements/{settlement_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_settlement_update(request, settlement_id: int, payload: SettlementUpdateIn):
    try:
        _admin_or_error(request)
        return success_response(settlement_data(svc.update_settlement(settlement_id, payload)))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/merchants/settlements/{settlement_id}/process", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_settlement_process(request, settlement_id: int, payload: SettlementProcessIn):
    try:
        _admin_or_error(request)
        return success_response(settlement_data(svc.process_settlement(settlement_id, payload)))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/merchants", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_merchants(request, keyword: str = "", is_active: str = "", audit_status: str = "", page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        return success_response(svc.merchants_data(keyword=keyword, is_active=is_active, audit_status=audit_status, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/merchants/{merchant_id}/audit", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_merchant_audit(request, merchant_id: int, payload: MerchantAuditIn):
    try:
        _admin_or_error(request)
        return success_response(svc.audit_merchant(merchant_id, action=payload.action, remark=payload.remark))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/merchants", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def admin_merchant_create(request, payload: MerchantIn):
    try:
        _admin_or_error(request)
        return success_response(merchant_data(svc.create_merchant(payload)))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/merchants/{merchant_id}/fixed-code", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_merchant_fixed_code(request, merchant_id: int):
    try:
        _admin_or_error(request)
        return success_response(fixed_code_data(svc.get_or_404(Merchant, merchant_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/merchants/{merchant_id}/point-records", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_merchant_point_records_by_merchant(request, merchant_id: int, keyword: str = "", month: str = "", date_from: str | None = None, date_to: str | None = None, page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        svc.get_or_404(Merchant, merchant_id)
        queryset = svc.merchant_payment_records_queryset(merchant_id=merchant_id, keyword=keyword, month=month, date_from=date_from, date_to=date_to)
        return success_response(svc.merchant_payment_records_data(queryset, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/merchants/{merchant_id}/status", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_merchant_status(request, merchant_id: int, payload: StatusIn):
    try:
        _admin_or_error(request)
        merchant = svc.get_or_404(Merchant, merchant_id)
        merchant.is_active = payload.is_active
        merchant.save(update_fields=["is_active"])
        return success_response(merchant_data(merchant))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/merchants/{merchant_id}/password", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_merchant_password(request, merchant_id: int, payload: PasswordResetIn):
    try:
        _admin_or_error(request)
        return success_response(svc.reset_merchant_password(merchant_id, password=payload.password))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/merchants/point-codes", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse})
def admin_point_codes(request, merchant_id: int | None = None, is_active: str = "", page: int = 1, page_size: int = 20):
    try:
        _admin_or_error(request)
        return success_response(svc.point_codes_data(merchant_id=merchant_id, is_active=is_active, page=page, page_size=page_size))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/merchants/point-codes", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_point_code_create(request, payload: MerchantPointCodeCreateIn):
    try:
        _admin_or_error(request)
        return success_response(point_code_data(svc.create_point_code(payload)))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/merchants/point-codes/{code_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_point_code_detail(request, code_id: int):
    try:
        _admin_or_error(request)
        return success_response(point_code_data(svc.get_or_404(MerchantPointCode, code_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.patch("/merchants/point-codes/{code_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_point_code_update(request, code_id: int, payload: MerchantPointCodeUpdateIn):
    try:
        _admin_or_error(request)
        return success_response(point_code_data(svc.update_point_code(code_id, payload)))
    except BusinessError as exc:
        return _business_error(exc)


@router.post("/merchants/point-codes/{code_id}/status", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_point_code_status(request, code_id: int, payload: StatusIn):
    try:
        _admin_or_error(request)
        return success_response(point_code_data(svc.set_point_code_status(code_id, is_active=payload.is_active)))
    except BusinessError as exc:
        return _business_error(exc)


@router.delete("/merchants/point-codes/{code_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_point_code_delete(request, code_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.delete_point_code(code_id))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/merchants/{merchant_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_merchant_detail(request, merchant_id: int):
    try:
        _admin_or_error(request)
        return success_response(merchant_data(svc.get_or_404(Merchant, merchant_id)))
    except BusinessError as exc:
        return _business_error(exc)


@router.patch("/merchants/{merchant_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_merchant_update(request, merchant_id: int, payload: MerchantUpdateIn):
    try:
        _admin_or_error(request)
        return success_response(merchant_data(svc.update_merchant(merchant_id, payload)))
    except BusinessError as exc:
        return _business_error(exc)


@router.delete("/merchants/{merchant_id}", response={200: SuccessResponse[dict], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def admin_merchant_delete(request, merchant_id: int):
    try:
        _admin_or_error(request)
        return success_response(svc.delete_merchant(merchant_id))
    except BusinessError as exc:
        return _business_error(exc)


# 账号 Excel 导入（Vue 管理端使用；模板下载 + 一步式上传校验落库）


XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx_download(content: bytes, filename: str) -> HttpResponse:
    response = HttpResponse(content, content_type=XLSX_CONTENT_TYPE)
    response["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"
    response["Cache-Control"] = "no-store"
    return response


def _uploaded_import_file(request):
    for field in ("file", "files", "files[]"):
        uploaded = request.FILES.get(field)
        if uploaded is not None:
            return uploaded
    raise BusinessError(
        "请选择要上传的 .xlsx 文件",
        errors=[{"row": 1, "column": "文件", "value": "", "message": "请求里没有找到上传文件（表单字段名用 file）"}],
    )


@router.get("/imports/members/template", tags=["后台管理-账号导入"])
def admin_member_import_template(request):
    """下载会员导入模板（.xlsx）。"""
    try:
        _admin_or_error(request)
    except BusinessError as exc:
        return _business_error(exc)
    return _xlsx_download(importers.member_import_template(), "会员导入模板.xlsx")


@router.post("/imports/members", response={200: SuccessResponse[ImportResultOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def admin_import_members(request):
    """上传会员 Excel，整批校验通过才落库；有任何问题整批驳回。"""
    try:
        _admin_or_error(request)
        return success_response(importers.import_members(_uploaded_import_file(request)))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/imports/merchants/template", tags=["后台管理-账号导入"])
def admin_merchant_import_template(request):
    """下载商户导入模板（.xlsx）。"""
    try:
        _admin_or_error(request)
    except BusinessError as exc:
        return _business_error(exc)
    return _xlsx_download(importers.merchant_import_template(), "商户导入模板.xlsx")


@router.post("/imports/merchants", response={200: SuccessResponse[ImportResultOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def admin_import_merchants(request):
    """上传商户 Excel，整批校验通过才落库；有任何问题整批驳回。"""
    try:
        _admin_or_error(request)
        return success_response(importers.import_merchants(_uploaded_import_file(request)))
    except BusinessError as exc:
        return _business_error(exc)


@router.get("/imports/admin-users/template", tags=["后台管理-账号导入"])
def admin_user_import_template(request):
    """下载后台账号导入模板（.xlsx）。"""
    try:
        _admin_or_error(request)
    except BusinessError as exc:
        return _business_error(exc)
    return _xlsx_download(importers.admin_user_import_template(), "后台账号导入模板.xlsx")


@router.post("/imports/admin-users", response={200: SuccessResponse[ImportResultOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def admin_import_admin_users(request):
    """上传后台账号 Excel，整批校验通过才落库；有任何问题整批驳回。"""
    try:
        _admin_or_error(request)
        return success_response(importers.import_admin_users(_uploaded_import_file(request)))
    except BusinessError as exc:
        return _business_error(exc)

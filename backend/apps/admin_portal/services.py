from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import logging

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from apps.activities.models import Activity, ActivityCheckin, ActivitySignup
from apps.activities.services import activity_data, checkin_data, review_checkin, signup_data
from apps.civic_feedbacks.models import CivicFeedback
from apps.civic_feedbacks.services import accept_civic_feedback, civic_feedback_data, reject_civic_feedback
from apps.core.services import MAX_IMAGE_SIZE, save_uploaded_images
from apps.elder_services.models import ElderCareRelation, ElderServiceFeedback, ElderServiceTask
from apps.elder_services.services import feedback_data as elder_feedback_data
from apps.elder_services.services import review_feedback
from apps.learning.models import LearningContent, LearningRecord
from apps.learning.services import content_data, record_data
from apps.members.models import Member
from apps.members.services import member_data
from apps.merchants.models import Merchant, MerchantPointCode, MerchantSettlement
from apps.merchants.services import fixed_code_data, generate_point_code_token, merchant_data, merchant_point_record_data, merchant_point_records_summary, point_code_data, settlement_data
from apps.points.models import ManualPointAdjustment, PointAccount, PointExchangeRule, PointRecord
from apps.points.services import get_or_create_account, manual_add_points, point_record_data
from apps.problem_feedbacks.models import ProblemFeedback
from apps.problem_feedbacks.services import problem_feedback_data, reply_problem_feedback
from apps.reports.models import Report
from apps.reports.services import report_data, review_report
from shared.auth import issue_admin_token
from shared.exceptions import BusinessError
from shared.media import media_url
from shared.pagination import paginate_queryset
from shared.privacy import mask_phone, member_brief

logger = logging.getLogger("street.admin")


User = get_user_model()


def admin_user_data(user) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
        "is_backend_manager": user.is_backend_manager,
        "is_superuser": user.is_superuser,
        "last_login": user.last_login,
    }


def login_admin(username: str, password: str) -> dict:
    username = username.strip()
    if not username or not password:
        raise BusinessError("用户名或密码错误", code=40000, status=400)
    user = authenticate(username=username, password=password)
    if user is None:
        raise BusinessError("用户名或密码错误", code=40000, status=400)
    if not user.is_active or not user.is_staff or not user.is_backend_manager:
        raise BusinessError("当前账号无权限访问", code=40301, status=403)
    update_last_login(None, user)
    token, expires_in = issue_admin_token(user_id=user.id)
    user.refresh_from_db()
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "admin": admin_user_data(user),
    }


def enum_data() -> dict:
    return {
        "member_identity_types": _choices(Member.IdentityType.choices),
        "member_audit_statuses": _choices(Member.AuditStatus.choices),
        "learning_content_types": _choices(LearningContent.ContentType.choices),
        "report_category_codes": _choices(Report.CategoryCode.choices),
        "report_statuses": _choices(Report.Status.choices),
        "civic_feedback_statuses": _choices(CivicFeedback.Status.choices),
        "problem_feedback_statuses": _choices(ProblemFeedback.Status.choices),
        "activity_statuses": _choices(Activity.Status.choices),
        "activity_checkin_statuses": _choices(ActivityCheckin.Status.choices),
        "elder_task_statuses": _choices(ElderServiceTask.Status.choices),
        "elder_feedback_statuses": _choices(ElderServiceFeedback.Status.choices),
        "point_change_types": _choices(PointRecord.ChangeType.choices),
        "point_source_types": _choices(PointRecord.SourceType.choices),
        "merchant_settlement_period_types": _choices(MerchantSettlement.PeriodType.choices),
        "merchant_settlement_statuses": _choices(MerchantSettlement.Status.choices),
    }


def dashboard_summary_data() -> dict:
    today = timezone.localdate()
    merchant_payments = PointRecord.objects.filter(
        source_type=PointRecord.SourceType.MERCHANT_PAYMENT,
        created_at__date=today,
    )
    total_points = merchant_payments.aggregate(total=Sum("amount"))["total"] or 0
    return {
        "pending_member_audits": Member.objects.filter(audit_status=Member.AuditStatus.PENDING).count(),
        "pending_reports": Report.objects.filter(status=Report.Status.PENDING).count(),
        "pending_civic_feedbacks": CivicFeedback.objects.filter(status=CivicFeedback.Status.SUBMITTED).count(),
        "pending_problem_feedbacks": ProblemFeedback.objects.filter(status=ProblemFeedback.Status.SUBMITTED).count(),
        "pending_activity_checkins": ActivityCheckin.objects.filter(status=ActivityCheckin.Status.PENDING).count(),
        "pending_elder_service_feedbacks": ElderServiceFeedback.objects.filter(status=ElderServiceFeedback.Status.PENDING).count(),
        "today_merchant_payment_count": merchant_payments.count(),
        "today_merchant_payment_points": abs(int(total_points)),
        "pending_merchant_settlements": MerchantSettlement.objects.filter(status=MerchantSettlement.Status.PENDING).count(),
    }


def _choices(choices) -> list[dict]:
    return [{"value": value, "label": label} for value, label in choices]


def paginated_data(queryset, data_func, *, page: int = 1, page_size: int = 20) -> dict:
    items, page_data = paginate_queryset(queryset, page=page, page_size=page_size)
    return {"items": [data_func(item) for item in items], **page_data}


def get_or_404(model, pk):
    item = model.objects.filter(pk=pk).first()
    if item is None:
        raise BusinessError("资源不存在", code=40400, status=404)
    return item


# ---------------------------------------------------------------------------
# Admin account and member management
# ---------------------------------------------------------------------------


def admin_users_data(*, keyword: str = "", page: int = 1, page_size: int = 20) -> dict:
    queryset = User.objects.filter(is_backend_manager=True).order_by("-id")
    keyword = keyword.strip()
    if keyword:
        queryset = queryset.filter(Q(username__icontains=keyword) | Q(email__icontains=keyword) | Q(first_name__icontains=keyword) | Q(last_name__icontains=keyword))
    return paginated_data(queryset, admin_user_data, page=page, page_size=page_size)


def create_admin_user(payload) -> dict:
    username = payload.username.strip()
    if not username:
        raise BusinessError("username 不能为空")
    if User.objects.filter(username=username).exists():
        raise BusinessError("username 已存在")
    if len(payload.password) < 8:
        raise BusinessError("密码长度至少 8 位")
    user = User.objects.create_user(
        username=username,
        password=payload.password,
        email=payload.email.strip(),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        is_backend_manager=payload.is_backend_manager,
        is_active=payload.is_active,
    )
    user.save()
    return admin_user_data(user)


def update_admin_user(user_id: int, payload) -> dict:
    user = get_or_404(User, user_id)
    user.email = payload.email.strip()
    user.first_name = payload.first_name.strip()
    user.last_name = payload.last_name.strip()
    user.is_backend_manager = payload.is_backend_manager
    user.save(update_fields=["email", "first_name", "last_name", "is_backend_manager", "is_staff"])
    return admin_user_data(user)


def set_admin_user_status(user_id: int, *, is_active: bool, current_admin) -> dict:
    user = get_or_404(User, user_id)
    if not is_active:
        if user.id == current_admin.id:
            raise BusinessError("不能禁用自己")
        active_count = User.objects.filter(is_active=True, is_staff=True, is_backend_manager=True).count()
        if user.is_active and active_count <= 1:
            raise BusinessError("至少保留一个启用的后台管理员")
    user.is_active = is_active
    user.save(update_fields=["is_active"])
    return admin_user_data(user)


def reset_admin_user_password(user_id: int, *, password: str) -> dict:
    user = get_or_404(User, user_id)
    if len(password) < 8:
        raise BusinessError("密码长度至少 8 位")
    user.set_password(password)
    user.save(update_fields=["password"])
    return {"id": user.id, "password_reset": True}


def members_data(*, keyword: str = "", identity_type: str = "", audit_status: str = "", is_active: str = "", page: int = 1, page_size: int = 20) -> dict:
    queryset = Member.objects.all()
    keyword = keyword.strip()
    if keyword:
        queryset = queryset.filter(Q(openid__icontains=keyword) | Q(nickname__icontains=keyword) | Q(phone__icontains=keyword) | Q(real_name__icontains=keyword))
    if identity_type:
        queryset = queryset.filter(identity_type=identity_type)
    if audit_status:
        queryset = queryset.filter(audit_status=audit_status)
    if is_active in {"true", "false"}:
        queryset = queryset.filter(is_active=is_active == "true")
    return paginated_data(queryset, member_data, page=page, page_size=page_size)


def update_member(member_id: int, payload) -> dict:
    member = get_or_404(Member, member_id)
    if payload.identity_type and payload.identity_type not in Member.IdentityType.values:
        raise BusinessError("身份类型不支持")
    member.nickname = payload.nickname.strip()
    member.phone = payload.phone.strip()
    member.real_name = payload.real_name.strip()
    if payload.identity_type:
        member.identity_type = payload.identity_type
    member.save(update_fields=["nickname", "phone", "real_name", "identity_type"])
    return member_data(member)


def set_member_status(member_id: int, *, is_active: bool) -> dict:
    member = get_or_404(Member, member_id)
    member.is_active = is_active
    member.save(update_fields=["is_active"])
    return member_data(member)


def audit_member(member_id: int, *, action: str, remark: str) -> dict:
    member = get_or_404(Member, member_id)
    action = action.strip()
    remark = remark.strip()
    if action == "approve":
        member.audit_status = Member.AuditStatus.APPROVED
        member.audit_remark = remark
    elif action == "reject":
        if not remark:
            raise BusinessError("驳回必须填写审核意见")
        member.audit_status = Member.AuditStatus.REJECTED
        member.audit_remark = remark
    else:
        raise BusinessError("审核动作不支持")
    member.save(update_fields=["audit_status", "audit_remark"])
    return member_data(member)


def member_points_data(member_id: int) -> dict:
    member = get_or_404(Member, member_id)
    account = get_or_create_account(member)
    records = PointRecord.objects.filter(member=member).select_related("merchant", "member")[:10]
    return {
        "member": member_data(member),
        "account": {"id": account.id, "balance": account.balance},
        "records": [point_record_admin_data(record) for record in records],
    }


# ---------------------------------------------------------------------------
# Uploads and learning management
# ---------------------------------------------------------------------------


ALLOWED_VIDEO_TYPES = {"video/mp4"}
MAX_VIDEO_SIZE = 100 * 1024 * 1024


def save_uploaded_video(request, files) -> dict:
    files = list(files)
    if len(files) != 1:
        raise BusinessError("一次只能上传 1 个视频")
    uploaded_file = files[0]
    if uploaded_file.content_type not in ALLOWED_VIDEO_TYPES:
        raise BusinessError("不支持的视频格式")
    if uploaded_file.size > MAX_VIDEO_SIZE:
        raise BusinessError("单个视频不能超过 100MB")
    ext = Path(uploaded_file.name).suffix.lower()
    relative_path = f"uploads/videos/{uuid4().hex}{ext}"
    file_path = Path(settings.MEDIA_ROOT) / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("wb+") as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    return {
        "file_id": relative_path,
        "url": media_url(request, relative_path),
        "original_name": uploaded_file.name,
        "size": uploaded_file.size,
        "mime_type": uploaded_file.content_type,
        "created_at": timezone.now(),
    }


def save_admin_images(request, files, *, business_type: str, related_id: str) -> dict:
    return save_uploaded_images(request, files, business_type=business_type, related_id=related_id)


def learning_content_admin_data(content: LearningContent, request=None) -> dict:
    return content_data(content, request=request)


def _media_field_value(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    marker = "/media/"
    if marker in value:
        return value.split(marker, 1)[1]
    return value.removeprefix("media/").lstrip("/")


def validate_learning_content_payload(payload) -> None:
    if not payload.title.strip():
        raise BusinessError("标题不能为空")
    if payload.content_type not in LearningContent.ContentType.values:
        raise BusinessError("内容类型不支持")
    if int(payload.points) < 0 or int(payload.required_seconds) < 0:
        raise BusinessError("积分值和学习秒数必须为非负整数")


def create_learning_content(payload) -> LearningContent:
    validate_learning_content_payload(payload)
    return LearningContent.objects.create(
        title=payload.title.strip(),
        cover=_media_field_value(payload.cover),
        image=_media_field_value(payload.image),
        video=_media_field_value(payload.video),
        body=payload.body,
        content_type=payload.content_type,
        points=payload.points,
        required_seconds=payload.required_seconds,
        is_active=payload.is_active,
    )


def update_learning_content(content_id: int, payload) -> LearningContent:
    content = get_or_404(LearningContent, content_id)
    for field in ["title", "body", "content_type", "points", "required_seconds", "is_active"]:
        value = getattr(payload, field)
        if value is not None:
            setattr(content, field, value.strip() if isinstance(value, str) else value)
    for field in ["cover", "image", "video"]:
        value = getattr(payload, field)
        if value is not None:
            setattr(content, field, _media_field_value(value))
    validate_learning_content_payload(content)
    content.save()
    return content


def delete_learning_content(content_id: int) -> dict:
    content = get_or_404(LearningContent, content_id)
    if content.records.exists():
        raise BusinessError("存在关联数据，不能删除")
    content.delete()
    return {"deleted": True}


def admin_record_data(record: LearningRecord) -> dict:
    data = record_data(record)
    data.update(member_brief(record.member))
    data["content_title"] = record.content.title
    return data


# ---------------------------------------------------------------------------
# Review and feedback workflows
# ---------------------------------------------------------------------------


def report_admin_data(report: Report, request=None) -> dict:
    data = report_data(report, request=request)
    data.update(member_brief(report.member))
    return data


def civic_feedback_admin_data(feedback: CivicFeedback) -> dict:
    data = civic_feedback_data(feedback)
    data.update(member_brief(feedback.member))
    return data


def problem_feedback_admin_data(feedback: ProblemFeedback) -> dict:
    data = problem_feedback_data(feedback)
    data.update(member_brief(feedback.member))
    return data


def point_record_admin_data(record: PointRecord) -> dict:
    data = point_record_data(record)
    data.update(member_brief(record.member))
    return data


def elder_feedback_admin_data(feedback: ElderServiceFeedback, request=None) -> dict:
    data = elder_feedback_data(feedback, request=request)
    data.update(member_brief(feedback.member))
    return data


def reports_data(*, keyword: str = "", category_code: str = "", status: str = "", page: int = 1, page_size: int = 20) -> dict:
    queryset = Report.objects.select_related("member")
    if keyword:
        queryset = queryset.filter(
            Q(member__openid__icontains=keyword)
            | Q(member__nickname__icontains=keyword)
            | Q(member__real_name__icontains=keyword)
            | Q(title__icontains=keyword)
            | Q(location__icontains=keyword)
        )
    if category_code:
        queryset = queryset.filter(category_code=category_code)
    if status:
        queryset = queryset.filter(status=status)
    return paginated_data(queryset, report_admin_data, page=page, page_size=page_size)


def update_report(report_id: int, payload) -> dict:
    report = get_or_404(Report, report_id)
    if payload.category_code is not None:
        if payload.category_code not in Report.CategoryCode.values:
            raise BusinessError("分类编码不支持")
        report.category_code = payload.category_code
    for field in ["title", "description", "location"]:
        value = getattr(payload, field)
        if value is not None:
            setattr(report, field, value.strip())
    if payload.points is not None:
        if payload.points < 0:
            raise BusinessError("积分值必须为非负整数")
        report.points = payload.points
    if payload.image_urls is not None:
        report.image_urls = [str(url).strip() for url in payload.image_urls if str(url).strip()]
    report.save()
    return report_admin_data(report)


def civic_feedbacks_data(*, keyword: str = "", status: str = "", page: int = 1, page_size: int = 20) -> dict:
    queryset = CivicFeedback.objects.select_related("member")
    if keyword:
        queryset = queryset.filter(Q(member__openid__icontains=keyword) | Q(member__nickname__icontains=keyword) | Q(member__real_name__icontains=keyword) | Q(title__icontains=keyword))
    if status:
        queryset = queryset.filter(status=status)
    return paginated_data(queryset, civic_feedback_admin_data, page=page, page_size=page_size)


def update_civic_feedback(feedback_id: int, payload) -> dict:
    feedback = get_or_404(CivicFeedback, feedback_id)
    for field in ["title", "content"]:
        value = getattr(payload, field)
        if value is not None:
            setattr(feedback, field, value.strip())
    if payload.material_urls is not None:
        feedback.material_urls = [str(url).strip() for url in payload.material_urls if str(url).strip()]
    if payload.points is not None:
        if payload.points < 0:
            raise BusinessError("积分值必须为非负整数")
        feedback.points = payload.points
    feedback.save()
    return civic_feedback_admin_data(feedback)


def review_civic_feedback(feedback_id: int, payload, operator) -> dict:
    feedback = get_or_404(CivicFeedback, feedback_id)
    if feedback.status != CivicFeedback.Status.SUBMITTED:
        raise BusinessError("记录已审核")
    if not payload.reply.strip():
        raise BusinessError("回复不能为空")
    if payload.action == "accept":
        if payload.points < 0:
            raise BusinessError("积分值必须为非负整数")
        feedback.points = payload.points
        feedback.save(update_fields=["points"])
        feedback = accept_civic_feedback(feedback, reply=payload.reply, operator=operator)
    elif payload.action == "reject":
        feedback = reject_civic_feedback(feedback, reply=payload.reply)
    else:
        raise BusinessError("审核动作不支持")
    return civic_feedback_admin_data(feedback)


def problem_feedbacks_data(*, keyword: str = "", status: str = "", page: int = 1, page_size: int = 20) -> dict:
    queryset = ProblemFeedback.objects.select_related("member")
    if keyword:
        queryset = queryset.filter(Q(member__openid__icontains=keyword) | Q(member__nickname__icontains=keyword) | Q(title__icontains=keyword))
    if status:
        queryset = queryset.filter(status=status)
    return paginated_data(queryset, problem_feedback_admin_data, page=page, page_size=page_size)


def update_problem_feedback(feedback_id: int, payload) -> dict:
    feedback = get_or_404(ProblemFeedback, feedback_id)
    for field in ["title", "content"]:
        value = getattr(payload, field)
        if value is not None:
            setattr(feedback, field, value.strip())
    if payload.status is not None:
        set_problem_feedback_status(feedback.id, status=payload.status)
        feedback.refresh_from_db()
    else:
        feedback.save()
    return problem_feedback_admin_data(feedback)


def set_problem_feedback_status(feedback_id: int, *, status: str) -> dict:
    feedback = get_or_404(ProblemFeedback, feedback_id)
    if status not in ProblemFeedback.Status.values:
        raise BusinessError("处理状态不支持")
    if status == ProblemFeedback.Status.REPLIED and not feedback.reply.strip():
        raise BusinessError("请先回复问题反馈")
    feedback.status = status
    feedback.save(update_fields=["status", "updated_at"])
    return problem_feedback_admin_data(feedback)


# ---------------------------------------------------------------------------
# Activity management
# ---------------------------------------------------------------------------


def validate_activity_payload(obj) -> None:
    if not obj.title.strip():
        raise BusinessError("标题不能为空")
    if obj.status not in Activity.Status.values:
        raise BusinessError("活动状态不支持")
    if obj.points < 0:
        raise BusinessError("积分值必须为非负整数")
    if obj.end_time <= obj.start_time:
        raise BusinessError("结束时间必须晚于开始时间")


def create_activity(payload) -> Activity:
    validate_activity_payload(payload)
    return Activity.objects.create(
        title=payload.title.strip(),
        body=payload.body,
        location=payload.location.strip(),
        start_time=payload.start_time,
        end_time=payload.end_time,
        points=payload.points,
        status=payload.status,
    )


def update_activity(activity_id: int, payload) -> Activity:
    activity = get_or_404(Activity, activity_id)
    for field in ["title", "body", "location", "start_time", "end_time", "points", "status"]:
        value = getattr(payload, field)
        if value is not None:
            setattr(activity, field, value.strip() if isinstance(value, str) else value)
    validate_activity_payload(activity)
    activity.save()
    return activity


def delete_activity(activity_id: int) -> dict:
    activity = get_or_404(Activity, activity_id)
    if activity.signups.exists() or activity.checkins.exists():
        raise BusinessError("存在关联数据，不能删除")
    activity.delete()
    return {"deleted": True}


def signup_admin_data(signup: ActivitySignup) -> dict:
    data = signup_data(signup)
    data.update(member_brief(signup.member))
    return data


def checkin_admin_data(checkin: ActivityCheckin) -> dict:
    data = checkin_data(checkin)
    data.update(member_brief(checkin.member))
    data["activity_title"] = checkin.activity.title
    return data


def checkin_code_data(activity: Activity, request=None) -> dict:
    return {
        "activity_id": activity.id,
        "checkin_code": activity.checkin_code,
        "checkin_qr_image": activity.checkin_qr_image.url if activity.checkin_qr_image else "",
    }


# ---------------------------------------------------------------------------
# Elder service management
# ---------------------------------------------------------------------------


def relation_data(relation: ElderCareRelation) -> dict:
    return {
        "id": relation.id,
        **member_brief(relation.member),
        "elder_name": relation.elder_name,
        "elder_address": relation.elder_address,
        "frequency": relation.frequency,
        "is_active": relation.is_active,
        "created_at": relation.created_at,
        "updated_at": relation.updated_at,
    }


def validate_relation_member(member: Member) -> None:
    if not member.is_active or member.identity_type != Member.IdentityType.COURIER or member.audit_status != Member.AuditStatus.APPROVED:
        raise BusinessError("必须选择启用且审核通过的小哥")


def create_relation(payload) -> ElderCareRelation:
    member = get_or_404(Member, payload.member_id)
    validate_relation_member(member)
    if not payload.elder_name.strip() or not payload.elder_address.strip():
        raise BusinessError("老人称呼和地址不能为空")
    return ElderCareRelation.objects.create(
        member=member,
        elder_name=payload.elder_name.strip(),
        elder_address=payload.elder_address.strip(),
        frequency=payload.frequency.strip(),
        is_active=payload.is_active,
    )


def update_relation(relation_id: int, payload) -> ElderCareRelation:
    relation = get_or_404(ElderCareRelation, relation_id)
    if payload.member_id is not None:
        member = get_or_404(Member, payload.member_id)
        validate_relation_member(member)
        relation.member = member
    for field in ["elder_name", "elder_address", "frequency", "is_active"]:
        value = getattr(payload, field)
        if value is not None:
            setattr(relation, field, value.strip() if isinstance(value, str) else value)
    relation.save()
    return relation


def delete_relation(relation_id: int) -> dict:
    relation = get_or_404(ElderCareRelation, relation_id)
    if relation.tasks.exists() or relation.feedbacks.exists():
        raise BusinessError("存在关联数据，不能删除")
    relation.delete()
    return {"deleted": True}


def elder_task_admin_data(task: ElderServiceTask) -> dict:
    relation = task.relation
    member = relation.member if relation else None
    return {
        "id": task.id,
        "title": task.title,
        "relation_id": task.relation_id,
        **member_brief(member),
        "elder_name": relation.elder_name if relation else "",
        "description": task.description,
        "location": task.location,
        "points": task.points,
        "status": task.status,
        "created_at": task.created_at,
    }


def validate_elder_task_payload(obj) -> None:
    if not obj.title.strip():
        raise BusinessError("标题不能为空")
    if obj.status not in ElderServiceTask.Status.values:
        raise BusinessError("任务状态不支持")
    if obj.points < 0:
        raise BusinessError("积分值必须为非负整数")


def create_elder_task(payload) -> ElderServiceTask:
    validate_elder_task_payload(payload)
    relation = get_or_404(ElderCareRelation, payload.relation_id) if payload.relation_id else None
    return ElderServiceTask.objects.create(
        title=payload.title.strip(),
        relation=relation,
        description=payload.description,
        location=payload.location.strip(),
        points=payload.points,
        status=payload.status,
    )


def update_elder_task(task_id: int, payload) -> ElderServiceTask:
    task = get_or_404(ElderServiceTask, task_id)
    for field in ["title", "description", "location", "points", "status"]:
        value = getattr(payload, field)
        if value is not None:
            setattr(task, field, value.strip() if isinstance(value, str) else value)
    if payload.relation_id is not None:
        task.relation = get_or_404(ElderCareRelation, payload.relation_id) if payload.relation_id else None
    validate_elder_task_payload(task)
    task.save()
    return task


def delete_elder_task(task_id: int) -> dict:
    task = get_or_404(ElderServiceTask, task_id)
    if task.feedbacks.exists():
        raise BusinessError("存在关联数据，不能删除")
    task.delete()
    return {"deleted": True}


def update_elder_feedback(feedback_id: int, payload) -> dict:
    feedback = get_or_404(ElderServiceFeedback, feedback_id)
    if payload.content is not None:
        feedback.content = payload.content.strip()
    if payload.image is not None:
        feedback.image = _media_field_value(payload.image)
    if payload.image_urls is not None:
        feedback.image_urls = [str(url).strip() for url in payload.image_urls if str(url).strip()]
    feedback.save()
    return elder_feedback_admin_data(feedback)


# ---------------------------------------------------------------------------
# Points management
# ---------------------------------------------------------------------------


def point_account_data(account: PointAccount) -> dict:
    return {
        "id": account.id,
        **member_brief(account.member),
        "balance": account.balance,
    }


def manual_adjustment_data(adjustment: ManualPointAdjustment) -> dict:
    return {
        "id": adjustment.id,
        **member_brief(adjustment.member),
        "amount": adjustment.amount,
        "reason": adjustment.reason,
        "operator_id": adjustment.operator_id,
        "point_record_id": adjustment.point_record_id,
        "created_at": adjustment.created_at,
    }


def create_manual_adjustment(payload, operator) -> dict:
    member = get_or_404(Member, payload.member_id)
    if not member.is_active:
        raise BusinessError("用户已停用")
    if payload.amount <= 0:
        raise BusinessError("积分值必须大于 0")
    if not payload.reason.strip():
        raise BusinessError("人工加分原因不能为空")
    adjustment = ManualPointAdjustment.objects.create(member=member, amount=payload.amount, reason=payload.reason.strip(), operator=operator)
    return manual_adjustment_data(adjustment)


def exchange_rule_data(rule: PointExchangeRule) -> dict:
    return {"id": rule.id, "points_per_yuan": rule.points_per_yuan, "is_active": rule.is_active, "updated_at": rule.updated_at}


@transaction.atomic
def save_exchange_rule(rule: PointExchangeRule, *, points_per_yuan: int | None = None, is_active: bool | None = None) -> PointExchangeRule:
    if points_per_yuan is not None:
        if points_per_yuan <= 0:
            raise BusinessError("积分兑换比例必须大于 0")
        rule.points_per_yuan = points_per_yuan
    if is_active is not None:
        rule.is_active = is_active
    if rule.is_active:
        PointExchangeRule.objects.exclude(pk=rule.pk).update(is_active=False)
    rule.save()
    return rule


# ---------------------------------------------------------------------------
# Merchant and settlement management
# ---------------------------------------------------------------------------


def merchants_data(*, keyword: str = "", is_active: str = "", page: int = 1, page_size: int = 20) -> dict:
    queryset = Merchant.objects.all()
    if keyword:
        queryset = queryset.filter(Q(openid__icontains=keyword) | Q(name__icontains=keyword) | Q(contact_name__icontains=keyword) | Q(phone__icontains=keyword))
    if is_active in {"true", "false"}:
        queryset = queryset.filter(is_active=is_active == "true")
    return paginated_data(queryset, merchant_data, page=page, page_size=page_size)


def validate_merchant_unique(openid: str, *, exclude_id: int | None = None) -> None:
    openid = openid.strip()
    if openid:
        queryset = Merchant.objects.filter(openid=openid)
        if exclude_id is not None:
            queryset = queryset.exclude(pk=exclude_id)
        if queryset.exists():
            raise BusinessError("商户 openid 已存在")


def create_merchant(payload) -> Merchant:
    if not payload.name.strip():
        raise BusinessError("商户名称不能为空")
    validate_merchant_unique(payload.openid)
    return Merchant.objects.create(
        openid=payload.openid.strip(),
        name=payload.name.strip(),
        contact_name=payload.contact_name.strip(),
        phone=payload.phone.strip(),
        address=payload.address.strip(),
        is_active=payload.is_active,
    )


def update_merchant(merchant_id: int, payload) -> Merchant:
    merchant = get_or_404(Merchant, merchant_id)
    if payload.openid is not None:
        validate_merchant_unique(payload.openid, exclude_id=merchant.id)
        merchant.openid = payload.openid.strip()
    for field in ["name", "contact_name", "phone", "address", "is_active"]:
        value = getattr(payload, field)
        if value is not None:
            setattr(merchant, field, value.strip() if isinstance(value, str) else value)
    if not merchant.name.strip():
        raise BusinessError("商户名称不能为空")
    merchant.save()
    return merchant


def delete_merchant(merchant_id: int) -> dict:
    merchant = get_or_404(Merchant, merchant_id)
    if merchant.point_records.exists() or merchant.settlements.exists():
        raise BusinessError("存在关联数据，不能删除")
    merchant.delete()
    return {"deleted": True}


def merchant_payment_records_queryset(*, merchant_id: int | None = None, keyword: str = "", date_from=None, date_to=None, month: str = ""):
    queryset = PointRecord.objects.filter(source_type=PointRecord.SourceType.MERCHANT_PAYMENT).select_related("member", "merchant")
    if merchant_id is not None:
        queryset = queryset.filter(merchant_id=merchant_id)
    if keyword:
        queryset = queryset.filter(
            Q(merchant__name__icontains=keyword)
            | Q(merchant__openid__icontains=keyword)
            | Q(member__nickname__icontains=keyword)
            | Q(member__phone__icontains=keyword)
            | Q(request_no__icontains=keyword)
        )
    if month:
        year, month_value = [int(part) for part in month.split("-", 1)]
        queryset = queryset.filter(created_at__year=year, created_at__month=month_value)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    return queryset


def merchant_payment_records_data(queryset, *, page: int = 1, page_size: int = 20) -> dict:
    items, page_data = paginate_queryset(queryset, page=page, page_size=page_size)
    return {"items": [merchant_point_record_data(item) for item in items], "summary": merchant_point_records_summary(queryset), **page_data}


def settlements_data(*, merchant_id: int | None = None, status: str = "", page: int = 1, page_size: int = 20) -> dict:
    queryset = MerchantSettlement.objects.select_related("merchant")
    if merchant_id is not None:
        queryset = queryset.filter(merchant_id=merchant_id)
    if status:
        queryset = queryset.filter(status=status)
    return paginated_data(queryset, settlement_data, page=page, page_size=page_size)


def create_settlement(payload) -> MerchantSettlement:
    merchant = get_or_404(Merchant, payload.merchant_id)
    return MerchantSettlement.objects.create(
        merchant=merchant,
        period_type=payload.period_type,
        period_label=payload.period_label.strip(),
        date_from=payload.date_from,
        date_to=payload.date_to,
        record_count=payload.record_count,
        total_points=payload.total_points,
        total_yuan_amount=Decimal(str(payload.total_yuan_amount)),
        status=payload.status,
        processor_name=payload.processor_name.strip(),
        remark=payload.remark.strip(),
    )


def update_settlement(settlement_id: int, payload) -> MerchantSettlement:
    settlement = get_or_404(MerchantSettlement, settlement_id)
    for field in ["period_type", "period_label", "date_from", "date_to", "record_count", "total_points", "total_yuan_amount", "status", "processor_name", "remark"]:
        value = getattr(payload, field)
        if value is not None:
            if field == "total_yuan_amount":
                value = Decimal(str(value))
            elif isinstance(value, str):
                value = value.strip()
            setattr(settlement, field, value)
    settlement.save()
    return settlement


def generate_settlement(payload) -> MerchantSettlement:
    merchant = get_or_404(Merchant, payload.merchant_id)
    existing = MerchantSettlement.objects.filter(merchant=merchant, period_label=payload.period_label.strip()).first()
    if existing is not None and existing.status == MerchantSettlement.Status.PROCESSED:
        raise BusinessError("已处理结算不能重新生成")
    queryset = merchant_payment_records_queryset(merchant_id=merchant.id, date_from=payload.date_from, date_to=payload.date_to)
    summary = merchant_point_records_summary(queryset)
    defaults = {
        "period_type": payload.period_type,
        "date_from": payload.date_from,
        "date_to": payload.date_to,
        "record_count": summary["record_count"],
        "total_points": summary["total_points"],
        "total_yuan_amount": Decimal(str(summary["total_yuan_amount"])),
        "status": MerchantSettlement.Status.PENDING,
    }
    if existing is None:
        return MerchantSettlement.objects.create(merchant=merchant, period_label=payload.period_label.strip(), **defaults)
    for key, value in defaults.items():
        setattr(existing, key, value)
    existing.save()
    return existing


def process_settlement(settlement_id: int, payload) -> MerchantSettlement:
    settlement = get_or_404(MerchantSettlement, settlement_id)
    if not payload.processor_name.strip():
        raise BusinessError("处理人不能为空")
    settlement.status = MerchantSettlement.Status.PROCESSED
    settlement.processed_at = timezone.now()
    settlement.processor_name = payload.processor_name.strip()
    settlement.remark = payload.remark.strip()
    settlement.save(update_fields=["status", "processed_at", "processor_name", "remark", "updated_at"])
    logger.info(
        "商户结算处理 settlement=%s merchant=%s processor=%s total_points=%s",
        settlement.id,
        settlement.merchant_id,
        settlement.processor_name,
        settlement.total_points,
    )
    return settlement


# ---------------------------------------------------------------------------
# 商户固定积分码管理
# ---------------------------------------------------------------------------


def point_codes_data(*, merchant_id: int | None = None, is_active: str = "", page: int = 1, page_size: int = 20) -> dict:
    queryset = MerchantPointCode.objects.select_related("merchant")
    if merchant_id is not None:
        queryset = queryset.filter(merchant_id=merchant_id)
    if is_active in {"true", "false"}:
        queryset = queryset.filter(is_active=is_active == "true")
    return paginated_data(queryset, point_code_data, page=page, page_size=page_size)


def create_point_code(payload) -> MerchantPointCode:
    merchant = get_or_404(Merchant, payload.merchant_id)
    if not merchant.is_active:
        raise BusinessError("商户已停用")
    if payload.points <= 0:
        raise BusinessError("固定积分值必须大于 0")
    return MerchantPointCode.objects.create(
        merchant=merchant,
        points=payload.points,
        code=generate_point_code_token(),
        is_active=True,
        remark=payload.remark.strip(),
    )


def update_point_code(code_id: int, payload) -> MerchantPointCode:
    point_code = get_or_404(MerchantPointCode, code_id)
    if payload.points is not None:
        if payload.points <= 0:
            raise BusinessError("固定积分值必须大于 0")
        point_code.points = payload.points
    if payload.remark is not None:
        point_code.remark = payload.remark.strip()
    if payload.is_active is not None:
        point_code.is_active = payload.is_active
    point_code.save()
    return point_code


def set_point_code_status(code_id: int, *, is_active: bool) -> MerchantPointCode:
    point_code = get_or_404(MerchantPointCode, code_id)
    point_code.is_active = is_active
    point_code.save(update_fields=["is_active"])
    return point_code


def delete_point_code(code_id: int) -> dict:
    point_code = get_or_404(MerchantPointCode, code_id)
    point_code.delete()
    return {"deleted": True}

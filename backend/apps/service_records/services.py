from __future__ import annotations

from apps.activities.models import ActivityCheckin, ActivitySignup
from apps.civic_feedbacks.models import CivicFeedback
from apps.elder_services.models import ElderServiceFeedback
from apps.learning.models import LearningRecord
from apps.members.models import Member
from apps.problem_feedbacks.models import ProblemFeedback
from apps.reports.models import Report
from shared.exceptions import BusinessError

STATUS_LABELS = {
    "report": {v: label for v, label in Report.Status.choices},
    "activity_checkin": {v: label for v, label in ActivityCheckin.Status.choices},
    "civic_feedback": {v: label for v, label in CivicFeedback.Status.choices},
    "problem_feedback": {v: label for v, label in ProblemFeedback.Status.choices},
    "elder_service": {v: label for v, label in ElderServiceFeedback.Status.choices},
}


def _collect_reports(member: Member) -> list[dict]:
    items = []
    for r in member.reports.select_related("point_record"):
        items.append(
            {
                "record_type": "report",
                "source_id": r.id,
                "title": r.title,
                "status": r.status,
                "status_label": STATUS_LABELS["report"].get(r.status, r.status),
                "points": r.point_record.amount if r.point_record_id else 0,
                "occurred_at": r.created_at,
            }
        )
    return items


def _collect_signups(member: Member) -> list[dict]:
    items = []
    for s in member.activity_signups.select_related("activity"):
        items.append(
            {
                "record_type": "activity_signup",
                "source_id": s.id,
                "title": s.activity.title,
                "status": "joined",
                "status_label": "已报名",
                "points": 0,
                "occurred_at": s.created_at,
            }
        )
    return items


def _collect_checkins(member: Member) -> list[dict]:
    items = []
    for c in member.activity_checkins.select_related("activity", "point_record"):
        items.append(
            {
                "record_type": "activity_checkin",
                "source_id": c.id,
                "title": c.activity.title,
                "status": c.status,
                "status_label": STATUS_LABELS["activity_checkin"].get(c.status, c.status),
                "points": c.point_record.amount if c.point_record_id else 0,
                "occurred_at": c.created_at,
            }
        )
    return items


def _collect_civic_feedbacks(member: Member) -> list[dict]:
    items = []
    for f in member.civic_feedbacks.select_related("point_record"):
        items.append(
            {
                "record_type": "civic_feedback",
                "source_id": f.id,
                "title": f.title,
                "status": f.status,
                "status_label": STATUS_LABELS["civic_feedback"].get(f.status, f.status),
                "points": f.point_record.amount if f.point_record_id else 0,
                "occurred_at": f.created_at,
            }
        )
    return items


def _collect_problem_feedbacks(member: Member) -> list[dict]:
    items = []
    for f in member.problem_feedbacks.all():
        items.append(
            {
                "record_type": "problem_feedback",
                "source_id": f.id,
                "title": f.title,
                "status": f.status,
                "status_label": STATUS_LABELS["problem_feedback"].get(f.status, f.status),
                "points": 0,
                "occurred_at": f.created_at,
            }
        )
    return items


def _collect_elder_feedbacks(member: Member) -> list[dict]:
    items = []
    for f in member.elder_feedbacks.select_related("point_record"):
        items.append(
            {
                "record_type": "elder_service",
                "source_id": f.id,
                "title": f.elder_name or f.content[:30],
                "status": f.status,
                "status_label": STATUS_LABELS["elder_service"].get(f.status, f.status),
                "points": f.point_record.amount if f.point_record_id else 0,
                "occurred_at": f.created_at,
            }
        )
    return items


def _collect_learning(member: Member) -> list[dict]:
    items = []
    for r in member.learning_records.select_related("content", "point_record"):
        items.append(
            {
                "record_type": "learning",
                "source_id": r.id,
                "title": r.content.title,
                "status": "completed" if r.is_completed else "incomplete",
                "status_label": "已完成" if r.is_completed else "未完成",
                "points": r.point_record.amount if r.point_record_id else 0,
                "occurred_at": r.created_at,
            }
        )
    return items


def _all_items(member: Member) -> list[dict]:
    items = []
    items.extend(_collect_reports(member))
    items.extend(_collect_signups(member))
    items.extend(_collect_checkins(member))
    items.extend(_collect_civic_feedbacks(member))
    items.extend(_collect_problem_feedbacks(member))
    items.extend(_collect_elder_feedbacks(member))
    items.extend(_collect_learning(member))
    items.sort(key=lambda item: item["occurred_at"], reverse=True)
    return items


def list_service_records(member: Member, *, page: int = 1, page_size: int = 20) -> tuple[list[dict], dict]:
    items = _all_items(member)
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], {"total": total, "page": page, "page_size": page_size}


# ---------------------------------------------------------------------------
# Detail serialization
# ---------------------------------------------------------------------------


def _report_detail(r) -> dict:
    return {
        "title": r.title,
        "description": r.description,
        "location": r.location,
        "image_urls": r.image_urls,
        "review_comment": r.review_comment,
        "created_at": r.created_at,
    }


def _signup_detail(s) -> dict:
    return {
        "title": s.activity.title,
        "location": s.activity.location,
        "start_time": s.activity.start_time,
        "end_time": s.activity.end_time,
        "created_at": s.created_at,
    }


def _checkin_detail(c) -> dict:
    return {
        "title": c.activity.title,
        "review_comment": c.review_comment,
        "created_at": c.created_at,
    }


def _civic_detail(f) -> dict:
    return {"title": f.title, "content": f.content, "material_urls": f.material_urls, "reply": f.reply, "created_at": f.created_at}


def _problem_detail(f) -> dict:
    return {"title": f.title, "content": f.content, "reply": f.reply, "created_at": f.created_at}


def _elder_detail(f) -> dict:
    return {
        "elder_name": f.elder_name,
        "content": f.content,
        "image_urls": f.image_urls,
        "review_comment": f.review_comment,
        "created_at": f.created_at,
    }


def _learning_detail(r) -> dict:
    return {"title": r.content.title, "is_completed": r.is_completed, "created_at": r.created_at}


_DETAIL_GETTERS = {
    "report": (Report, _report_detail),
    "activity_signup": (ActivitySignup, _signup_detail),
    "activity_checkin": (ActivityCheckin, _checkin_detail),
    "civic_feedback": (CivicFeedback, _civic_detail),
    "problem_feedback": (ProblemFeedback, _problem_detail),
    "elder_service": (ElderServiceFeedback, _elder_detail),
    "learning": (LearningRecord, _learning_detail),
}


def _list_status(obj) -> str:
    if isinstance(obj, (Report, ActivityCheckin, CivicFeedback, ProblemFeedback, ElderServiceFeedback)):
        return obj.status
    if isinstance(obj, ActivitySignup):
        return "joined"
    if isinstance(obj, LearningRecord):
        return "completed" if obj.is_completed else "incomplete"
    return ""


def _list_status_label(obj) -> str:
    if isinstance(obj, Report):
        return STATUS_LABELS["report"].get(obj.status, obj.status)
    if isinstance(obj, ActivitySignup):
        return "已报名"
    if isinstance(obj, ActivityCheckin):
        return STATUS_LABELS["activity_checkin"].get(obj.status, obj.status)
    if isinstance(obj, CivicFeedback):
        return STATUS_LABELS["civic_feedback"].get(obj.status, obj.status)
    if isinstance(obj, ProblemFeedback):
        return STATUS_LABELS["problem_feedback"].get(obj.status, obj.status)
    if isinstance(obj, ElderServiceFeedback):
        return STATUS_LABELS["elder_service"].get(obj.status, obj.status)
    if isinstance(obj, LearningRecord):
        return "已完成" if obj.is_completed else "未完成"
    return ""


def _points(obj) -> int:
    point_record_id = getattr(obj, "point_record_id", None)
    if point_record_id:
        return obj.point_record.amount
    return 0


def service_record_detail(member: Member, record_type: str, source_id: int) -> dict:
    if record_type not in _DETAIL_GETTERS:
        raise BusinessError("记录类型不支持", status=404, code=40400)
    model, detail_func = _DETAIL_GETTERS[record_type]
    obj = model.objects.filter(pk=source_id, member=member).first()
    if obj is None:
        raise BusinessError("记录不存在", status=404, code=40400)
    common = {
        "record_type": record_type,
        "source_id": obj.id,
        "status": _list_status(obj),
        "status_label": _list_status_label(obj),
        "points": _points(obj),
        "occurred_at": obj.created_at,
    }
    common.update(detail_func(obj))
    return common

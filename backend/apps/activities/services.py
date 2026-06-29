from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.activities.models import Activity, ActivityCheckin, ActivitySignup
from apps.members.models import Member
from apps.points.models import PointRecord
from apps.points.services import add_points
from shared.exceptions import BusinessError


def activity_data(activity: Activity, *, member: Member | None = None, include_checkin_secret: bool = False) -> dict:
    data = {
        "id": activity.id,
        "title": activity.title,
        "body": activity.body,
        "location": activity.location,
        "start_time": activity.start_time,
        "end_time": activity.end_time,
        "points": activity.points,
        "status": activity.status,
        "user_signup_id": None,
        "signup_status": "not_joined",
        "checkin_status": "not_checked",
        "point_status": "not_granted",
    }
    if member is not None:
        signup = getattr(activity, "_member_signup", None)
        if signup is None:
            signup = ActivitySignup.objects.filter(member=member, activity=activity).first()
        checkin = getattr(activity, "_member_checkin", None)
        if checkin is None:
            checkin = ActivityCheckin.objects.filter(member=member, activity=activity).first()
        if signup is not None:
            data["user_signup_id"] = signup.id
            data["signup_status"] = "joined"
        if checkin is not None:
            data["checkin_status"] = checkin.status
            data["point_status"] = "granted" if checkin.point_record_id else "not_granted"
    if include_checkin_secret:
        data["checkin_code"] = activity.checkin_code
        data["checkin_qr_image"] = activity.checkin_qr_image.url if activity.checkin_qr_image else ""
    return data


def signup_data(signup: ActivitySignup) -> dict:
    activity = signup.activity
    checkin = getattr(signup, "_member_checkin", None)
    if checkin is None:
        checkin = ActivityCheckin.objects.filter(member=signup.member, activity=activity).first()
    checkin_status = checkin.status if checkin is not None else "not_checked"
    point_record_id = checkin.point_record_id if checkin is not None else None
    return {
        "id": signup.id,
        "activity_id": signup.activity_id,
        "title": activity.title,
        "body": activity.body,
        "location": activity.location,
        "start_time": activity.start_time,
        "end_time": activity.end_time,
        "points": activity.points,
        "signup_status": "joined",
        "created_at": signup.created_at,
        "cancelled_at": None,
        "checkin_status": checkin_status,
        "checkin_at": checkin.created_at if checkin is not None else None,
        "point_status": "granted" if point_record_id else "not_granted",
        "point_record_id": point_record_id,
    }


def checkin_data(checkin: ActivityCheckin) -> dict:
    return {
        "id": checkin.id,
        "activity_id": checkin.activity_id,
        "status": checkin.status,
        "review_comment": checkin.review_comment,
        "point_record_id": checkin.point_record_id,
        "created_at": checkin.created_at,
    }


def signup_activity(member: Member, activity: Activity) -> ActivitySignup:
    if activity.status != Activity.Status.PUBLISHED:
        raise BusinessError("活动未发布")
    if ActivitySignup.objects.filter(member=member, activity=activity).exists():
        raise BusinessError("重复报名")
    return ActivitySignup.objects.create(member=member, activity=activity)


def cancel_signup(member: Member, activity: Activity) -> dict:
    signup = ActivitySignup.objects.filter(member=member, activity=activity).first()
    if signup is None:
        raise BusinessError("报名记录不存在", status=404, code=40400)
    if ActivityCheckin.objects.filter(member=member, activity=activity).exists():
        raise BusinessError("已签到的报名不能取消")
    signup.delete()
    return {
        "activity_id": activity.id,
        "signup_status": "cancelled",
        "cancelled_at": timezone.now(),
    }


def checkin_activity(member: Member, activity: Activity, *, checkin_code: str) -> ActivityCheckin:
    if activity.status != Activity.Status.PUBLISHED:
        raise BusinessError("活动未发布")
    if not ActivitySignup.objects.filter(member=member, activity=activity).exists():
        raise BusinessError("未报名活动")
    if checkin_code.strip() != activity.checkin_code:
        raise BusinessError("签到码错误")
    if ActivityCheckin.objects.filter(member=member, activity=activity).exists():
        raise BusinessError("重复签到")
    return ActivityCheckin.objects.create(member=member, activity=activity)


@transaction.atomic
def review_checkin(checkin: ActivityCheckin, *, action: str, comment: str, operator) -> ActivityCheckin:
    checkin = ActivityCheckin.objects.select_for_update().select_related("activity", "member").get(pk=checkin.pk)
    if checkin.status != ActivityCheckin.Status.PENDING:
        raise BusinessError("签到已审核")

    if action == "confirm":
        point_record = None
        if checkin.activity.points > 0:
            point_record = add_points(
                checkin.member,
                checkin.activity.points,
                source_type=PointRecord.SourceType.ACTIVITY,
                source_id=str(checkin.id),
                reason=f"活动签到确认：{checkin.activity.title}",
                operator=operator,
            )
        checkin.status = ActivityCheckin.Status.CONFIRMED
        checkin.point_record = point_record
    elif action == "reject":
        if not comment.strip():
            raise BusinessError("驳回必须填写审核意见")
        checkin.status = ActivityCheckin.Status.REJECTED
    else:
        raise BusinessError("审核动作不支持")

    checkin.review_comment = comment.strip()
    checkin.save(update_fields=["status", "review_comment", "point_record", "updated_at"])
    return checkin

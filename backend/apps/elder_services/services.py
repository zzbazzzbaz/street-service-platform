from __future__ import annotations

from django.db import transaction

from apps.elder_services.models import ElderCareRelation, ElderServiceFeedback, ElderServiceTask
from apps.members.models import Member
from apps.points.models import PointRecord
from apps.points.services import add_points
from shared.exceptions import BusinessError


def task_data(task: ElderServiceTask) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "location": task.location,
        "points": task.points,
        "status": task.status,
    }


def my_relation_data(member: Member) -> dict | None:
    relation = (
        ElderCareRelation.objects.filter(member=member, is_active=True)
        .order_by("-created_at")
        .first()
    )
    if relation is None:
        return None
    return {
        "id": relation.id,
        "member_id": relation.member_id,
        "elder_name": relation.elder_name,
        "elder_address": relation.elder_address,
        "is_active": relation.is_active,
        "created_at": relation.created_at,
        "updated_at": relation.updated_at,
    }


def feedback_data(feedback: ElderServiceFeedback, request=None) -> dict:
    relation = feedback.relation or (feedback.task.relation if feedback.task_id and feedback.task else None)
    elder_name = feedback.elder_name or (relation.elder_name if relation else "")
    elder_address = feedback.elder_address or (relation.elder_address if relation else "")
    points = feedback.points
    if points == 0 and feedback.task_id and feedback.task:
        points = feedback.task.points
    return {
        "id": feedback.id,
        "relation_id": feedback.relation_id,
        "member_id": feedback.member_id,
        "task_id": feedback.task_id,
        "task_title": feedback.task.title if feedback.task_id and feedback.task else "",
        "elder_name": elder_name,
        "elder_address": elder_address,
        "content": feedback.content,
        "image_urls": feedback.image_urls,
        "points": points,
        "status": feedback.status,
        "review_comment": feedback.review_comment,
        "reviewed_at": feedback.reviewed_at,
        "point_record_id": feedback.point_record_id,
        "created_at": feedback.created_at,
    }


def latest_feedback_for(member: Member, task: ElderServiceTask) -> ElderServiceFeedback | None:
    return ElderServiceFeedback.objects.filter(member=member, task=task).order_by("-created_at", "-id").first()


def latest_feedback_data(feedback: ElderServiceFeedback | None) -> dict | None:
    if feedback is None:
        return None
    return {
        "id": feedback.id,
        "status": feedback.status,
        "review_comment": feedback.review_comment,
        "point_record_id": feedback.point_record_id,
        "created_at": feedback.created_at,
    }


def my_task_data(task: ElderServiceTask, member: Member) -> dict:
    latest = getattr(task, "_latest_feedback", None)
    if latest is None:
        latest = latest_feedback_for(member, task)
    relation = task.relation
    feedback_status = latest.status if latest is not None else "none"
    return {
        "task_id": task.id,
        "title": task.title,
        "description": task.description,
        "elder_name": relation.elder_name if relation else "",
        "elder_address": relation.elder_address if relation else "",
        "frequency": relation.frequency if relation else "",
        "points": task.points,
        "feedback_status": feedback_status,
        "latest_feedback": latest_feedback_data(latest),
    }


def submit_feedback(member: Member, task: ElderServiceTask, *, content: str, image_urls: list[str] | None = None, image: str = "") -> ElderServiceFeedback:
    if task.status != ElderServiceTask.Status.PUBLISHED:
        raise BusinessError("老人服务任务未发布")
    if task.relation_id and (task.relation.member_id != member.id or not task.relation.is_active):
        raise BusinessError("老人服务任务不存在", code=40400, status=404)
    latest = latest_feedback_for(member, task)
    if latest is not None and latest.status in {ElderServiceFeedback.Status.PENDING, ElderServiceFeedback.Status.APPROVED}:
        raise BusinessError("同一任务不能重复提交反馈")
    content = content.strip()
    if not content:
        raise BusinessError("反馈内容不能为空")
    image_urls = [str(url).strip() for url in (image_urls or []) if str(url).strip()]
    if len(image_urls) > 10:
        raise BusinessError("反馈图片最多 10 张")
    return ElderServiceFeedback.objects.create(
        member=member,
        relation=task.relation,
        task=task,
        content=content,
        image=image.strip(),
        image_urls=image_urls,
    )


def create_feedback_direct(member: Member, *, content: str, image_urls: list[str] | None = None) -> ElderServiceFeedback:
    relation = (
        ElderCareRelation.objects.filter(member=member, is_active=True)
        .order_by("-created_at")
        .first()
    )
    if relation is None:
        raise BusinessError("暂未配置有效的结对帮扶关系", code=40301, status=403)
    content = content.strip()
    if not content:
        raise BusinessError("帮扶记录内容不能为空")
    image_urls = [str(url).strip() for url in (image_urls or []) if str(url).strip()]
    if not image_urls:
        raise BusinessError("至少上传 1 张帮扶现场照片")
    if len(image_urls) > 10:
        raise BusinessError("帮扶图片最多 10 张")
    return ElderServiceFeedback.objects.create(
        member=member,
        relation=relation,
        task=None,
        elder_name=relation.elder_name,
        elder_address=relation.elder_address,
        content=content,
        image_urls=image_urls,
        points=0,
    )


@transaction.atomic
def review_feedback(feedback: ElderServiceFeedback, *, action: str, comment: str, operator) -> ElderServiceFeedback:
    feedback = ElderServiceFeedback.objects.select_for_update().select_related("member").get(pk=feedback.pk)
    if feedback.status != ElderServiceFeedback.Status.PENDING:
        raise BusinessError("反馈已审核", code=40900, status=409)

    if action == "approve":
        point_record = None
        if feedback.task_id:
            feedback.task = ElderServiceTask.objects.get(pk=feedback.task_id)
        points = feedback.points
        if points == 0 and feedback.task_id and feedback.task:
            points = feedback.task.points
        if points > 0:
            point_record = add_points(
                feedback.member,
                points,
                source_type=PointRecord.SourceType.ELDER_SERVICE,
                source_id=str(feedback.id),
                reason=f"结对帮扶审核通过：{feedback.elder_name or (feedback.task.title if feedback.task_id and feedback.task else '')}",
                operator=operator,
            )
        feedback.status = ElderServiceFeedback.Status.APPROVED
        feedback.point_record = point_record
    elif action == "reject":
        if not comment.strip():
            raise BusinessError("驳回必须填写审核意见")
        feedback.status = ElderServiceFeedback.Status.REJECTED
    else:
        raise BusinessError("审核动作不支持")

    from django.utils import timezone
    feedback.review_comment = comment.strip()
    feedback.reviewed_at = timezone.now()
    feedback.save(update_fields=["status", "review_comment", "reviewed_at", "point_record", "updated_at"])
    return feedback

from __future__ import annotations

from django.db import transaction

from apps.elder_services.models import ElderServiceFeedback, ElderServiceTask
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


def feedback_data(feedback: ElderServiceFeedback, request=None) -> dict:
    task = feedback.task
    relation = feedback.relation or task.relation
    return {
        "id": feedback.id,
        "task_id": feedback.task_id,
        "task_title": task.title,
        "elder_name": relation.elder_name if relation else "",
        "content": feedback.content,
        "image_urls": feedback.image_urls,
        "points": task.points,
        "status": feedback.status,
        "review_comment": feedback.review_comment,
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


@transaction.atomic
def review_feedback(feedback: ElderServiceFeedback, *, action: str, comment: str, operator) -> ElderServiceFeedback:
    feedback = ElderServiceFeedback.objects.select_for_update().select_related("task", "member").get(pk=feedback.pk)
    if feedback.status != ElderServiceFeedback.Status.PENDING:
        raise BusinessError("反馈已审核")

    if action == "approve":
        point_record = None
        if feedback.task.points > 0:
            point_record = add_points(
                feedback.member,
                feedback.task.points,
                source_type=PointRecord.SourceType.ELDER_SERVICE,
                source_id=str(feedback.id),
                reason=f"老人服务审核通过：{feedback.task.title}",
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

    feedback.review_comment = comment.strip()
    feedback.save(update_fields=["status", "review_comment", "point_record", "updated_at"])
    return feedback

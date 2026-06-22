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
    from shared.media import file_url

    return {
        "id": feedback.id,
        "task_id": feedback.task_id,
        "content": feedback.content,
        "image": file_url(request, feedback.image) if request is not None else (feedback.image.url if feedback.image else ""),
        "status": feedback.status,
        "review_comment": feedback.review_comment,
        "point_record_id": feedback.point_record_id,
        "created_at": feedback.created_at,
    }


def submit_feedback(member: Member, task: ElderServiceTask, *, content: str, image: str = "") -> ElderServiceFeedback:
    if task.status != ElderServiceTask.Status.PUBLISHED:
        raise BusinessError("老人服务任务未发布")
    if ElderServiceFeedback.objects.filter(member=member, task=task).exists():
        raise BusinessError("同一任务不能重复提交反馈")
    content = content.strip()
    if not content:
        raise BusinessError("反馈内容不能为空")
    return ElderServiceFeedback.objects.create(member=member, task=task, content=content, image=image.strip())


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

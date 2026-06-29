from __future__ import annotations

from django.db import transaction

from apps.civic_feedbacks.models import CivicFeedback
from apps.members.models import Member
from apps.points.models import PointRecord
from apps.points.services import add_points
from shared.exceptions import BusinessError


def civic_feedback_data(feedback: CivicFeedback) -> dict:
    return {
        "id": feedback.id,
        "title": feedback.title,
        "content": feedback.content,
        "material_urls": feedback.material_urls,
        "status": feedback.status,
        "reply": feedback.reply,
        "points": feedback.points,
        "point_record_id": feedback.point_record_id,
        "created_at": feedback.created_at,
    }


def create_civic_feedback(member: Member, *, title: str, content: str, material_urls: list[str] | None = None) -> CivicFeedback:
    title = title.strip()
    content = content.strip()
    if not title:
        raise BusinessError("标题不能为空")
    if not content:
        raise BusinessError("内容不能为空")
    material_urls = [str(url).strip() for url in (material_urls or []) if str(url).strip()]
    if len(material_urls) > 6:
        raise BusinessError("材料图片最多 6 张")
    return CivicFeedback.objects.create(member=member, title=title, content=content, material_urls=material_urls)


@transaction.atomic
def accept_civic_feedback(feedback: CivicFeedback, *, reply: str, operator) -> CivicFeedback:
    feedback = CivicFeedback.objects.select_for_update().select_related("member").get(pk=feedback.pk)
    if feedback.point_record_id is None and feedback.points > 0:
        feedback.point_record = add_points(
            feedback.member,
            feedback.points,
            source_type=PointRecord.SourceType.CIVIC_FEEDBACK,
            source_id=str(feedback.id),
            reason=f"社情民意采纳：{feedback.title}",
            operator=operator,
        )
    feedback.status = CivicFeedback.Status.ACCEPTED
    feedback.reply = reply.strip()
    feedback.save(update_fields=["status", "reply", "point_record", "updated_at"])
    return feedback


def reject_civic_feedback(feedback: CivicFeedback, *, reply: str) -> CivicFeedback:
    reply = reply.strip()
    if not reply:
        raise BusinessError("驳回必须填写回复")
    feedback.status = CivicFeedback.Status.REJECTED
    feedback.reply = reply
    feedback.save(update_fields=["status", "reply", "updated_at"])
    return feedback

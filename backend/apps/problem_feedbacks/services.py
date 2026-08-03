from __future__ import annotations

from django.utils import timezone

from apps.members.models import Member
from apps.problem_feedbacks.models import ProblemFeedback
from shared.exceptions import BusinessError


def problem_feedback_data(feedback: ProblemFeedback) -> dict:
    return {
        "id": feedback.id,
        "title": feedback.title,
        "content": feedback.content,
        "status": feedback.status,
        "visibility_status": feedback.visibility_status,
        "is_public": feedback.is_public,
        "reply": feedback.reply,
        "replied_at": feedback.replied_at,
        "created_at": feedback.created_at,
    }


def public_problem_feedback_data(feedback: ProblemFeedback) -> dict:
    return {
        "id": feedback.id,
        "title": feedback.title,
        "content": feedback.content,
        "status": feedback.status,
        "visibility_status": feedback.visibility_status,
        "is_public": feedback.is_public,
        "reply": feedback.reply,
        "replied_at": feedback.replied_at,
        "created_at": feedback.created_at,
    }


def create_problem_feedback(member: Member, *, title: str, content: str) -> ProblemFeedback:
    title = title.strip()
    content = content.strip()
    if not title:
        raise BusinessError("标题不能为空")
    if not content:
        raise BusinessError("内容不能为空")
    return ProblemFeedback.objects.create(member=member, title=title, content=content)


def reply_problem_feedback(feedback: ProblemFeedback, *, reply: str) -> ProblemFeedback:
    reply = reply.strip()
    if not reply:
        raise BusinessError("回复不能为空")
    feedback.status = ProblemFeedback.Status.REPLIED
    feedback.reply = reply
    feedback.replied_at = timezone.now()
    feedback.save(update_fields=["status", "reply", "replied_at", "updated_at"])
    return feedback

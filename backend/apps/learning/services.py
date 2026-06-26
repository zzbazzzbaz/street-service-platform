from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.learning.models import LearningContent, LearningRecord
from apps.members.models import Member
from apps.points.models import PointRecord
from apps.points.services import add_points
from shared.exceptions import BusinessError


def content_data(content: LearningContent, request=None) -> dict:
    from shared.media import file_url

    cover_url = file_url(request, content.cover) if request is not None else (content.cover.url if content.cover else "")
    return {
        "id": content.id,
        "title": content.title,
        "cover": cover_url,
        "cover_url": cover_url,
        "body": content.body,
        "content_type": content.content_type,
        "image_urls": [],
        "video_url": "",
        "points": content.points,
        "required_seconds": content.required_seconds,
        "is_active": content.is_active,
    }


def record_data(record: LearningRecord) -> dict:
    return {
        "id": record.id,
        "content_id": record.content_id,
        "learned_seconds": record.learned_seconds,
        "is_completed": record.is_completed,
        "completed_at": record.completed_at,
        "point_record_id": record.point_record_id,
    }


@transaction.atomic
def complete_learning(member: Member, content: LearningContent, *, learned_seconds: int) -> LearningRecord:
    if not content.is_active:
        raise BusinessError("学习内容未上架")
    learned_seconds = max(int(learned_seconds), 0)
    record, _ = LearningRecord.objects.get_or_create(member=member, content=content)
    record.learned_seconds = max(record.learned_seconds, learned_seconds)

    if not record.is_completed and learned_seconds >= content.required_seconds:
        point_record = None
        if content.points > 0:
            point_record = add_points(
                member,
                content.points,
                source_type=PointRecord.SourceType.LEARNING,
                source_id=str(content.id),
                reason=f"完成学习：{content.title}",
            )
        record.is_completed = True
        record.completed_at = timezone.now()
        record.point_record = point_record

    record.save(update_fields=["learned_seconds", "is_completed", "completed_at", "point_record", "updated_at"])
    return record

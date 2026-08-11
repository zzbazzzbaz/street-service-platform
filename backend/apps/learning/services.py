from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.learning.models import LearningContent, LearningRecord
from apps.members.models import Member
from apps.points.models import PointRecord
from apps.points.services import add_points
from shared.exceptions import BusinessError


def content_data(content: LearningContent, request=None, member: Member | None = None) -> dict:
    from shared.media import file_url

    cover_url = file_url(request, content.cover) if request is not None else (content.cover.url if content.cover else "")
    image_url = file_url(request, content.image) if request is not None else (content.image.url if content.image else "")
    video_url = file_url(request, content.video) if request is not None else (content.video.url if content.video else "")
    record = getattr(content, "_member_record", None)
    if member is not None and record is None:
        record = LearningRecord.objects.filter(member=member, content=content).first()
    return {
        "id": content.id,
        "title": content.title,
        "cover": cover_url,
        "cover_url": cover_url,
        "body": content.body,
        "content_type": content.content_type,
        "image_urls": [image_url] if image_url else [],
        "video_url": video_url,
        "points": content.points,
        "required_seconds": content.required_seconds,
        "is_active": content.is_active,
        "is_announcement": content.is_announcement,
        "is_pinned": content.is_pinned,
        "pin_order": content.pin_order,
        "created_at": content.created_at,
        "is_completed": record.is_completed if record is not None else False,
        "completed_at": record.completed_at if record is not None and record.is_completed else None,
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


def pinned_announcements():
    return LearningContent.objects.filter(
        is_active=True, is_announcement=True, is_pinned=True
    ).order_by("pin_order")


def set_pinned_items(items):
    items = list(items)
    if len(items) > 3:
        raise BusinessError("最多置顶 3 条公告")
    ids = [it["content_id"] for it in items]
    orders = [it["pin_order"] for it in items]
    if len(set(ids)) != len(ids):
        raise BusinessError("置顶公告不能重复")
    if len(set(orders)) != len(orders):
        raise BusinessError("置顶顺序不能重复")
    if orders and sorted(orders) != list(range(1, len(orders) + 1)):
        raise BusinessError("置顶顺序必须从 1 开始连续")
    with transaction.atomic():
        contents = {c.id: c for c in LearningContent.objects.filter(id__in=ids)}
        for it in items:
            c = contents.get(it["content_id"])
            if c is None:
                raise BusinessError("内容不存在")
            if not c.is_active:
                raise BusinessError("内容未上架")
            if not c.is_announcement:
                raise BusinessError("仅公告类型内容可置顶")
            if not c.cover:
                raise BusinessError("公告未配置封面")
        LearningContent.objects.filter(is_pinned=True).update(is_pinned=False, pin_order=None)
        for it in items:
            c = contents[it["content_id"]]
            c.is_pinned = True
            c.pin_order = it["pin_order"]
            c.save(update_fields=["is_pinned", "pin_order"])
    return list(pinned_announcements())


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

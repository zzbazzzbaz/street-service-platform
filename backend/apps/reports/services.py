from __future__ import annotations

from django.db import transaction

from apps.members.models import Member
from apps.points.models import PointRecord
from apps.points.services import add_points
from apps.reports.models import Report
from shared.exceptions import BusinessError


def report_data(report: Report, request=None) -> dict:
    from shared.media import file_url

    return {
        "id": report.id,
        "title": report.title,
        "description": report.description,
        "image": file_url(request, report.image) if request is not None else (report.image.url if report.image else ""),
        "location": report.location,
        "points": report.points,
        "status": report.status,
        "review_comment": report.review_comment,
        "point_record_id": report.point_record_id,
        "created_at": report.created_at,
    }


def submit_report(member: Member, *, title: str, description: str = "", image: str = "", location: str = "") -> Report:
    title = title.strip()
    if not title:
        raise BusinessError("标题不能为空")
    return Report.objects.create(
        member=member,
        title=title,
        description=description.strip(),
        image=image.strip(),
        location=location.strip(),
    )


@transaction.atomic
def review_report(report: Report, *, action: str, comment: str, operator) -> Report:
    report = Report.objects.select_for_update().get(pk=report.pk)
    if report.status != Report.Status.PENDING:
        raise BusinessError("记录已审核")

    if action == "approve":
        point_record = None
        if report.points > 0:
            point_record = add_points(
                report.member,
                report.points,
                source_type=PointRecord.SourceType.REPORT,
                source_id=str(report.id),
                reason=f"随手拍审核通过：{report.title}",
                operator=operator,
            )
        report.status = Report.Status.APPROVED
        report.point_record = point_record
    elif action == "reject":
        if not comment.strip():
            raise BusinessError("驳回必须填写审核意见")
        report.status = Report.Status.REJECTED
    else:
        raise BusinessError("审核动作不支持")

    report.review_comment = comment.strip()
    report.save(update_fields=["status", "review_comment", "point_record", "updated_at"])
    return report

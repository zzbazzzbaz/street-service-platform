from __future__ import annotations

from django.db import transaction

from apps.members.models import Member
from apps.points.models import PointRecord
from apps.points.services import add_points
from apps.reports.models import Report
from shared.exceptions import BusinessError


def report_data(report: Report, request=None) -> dict:
    return {
        "id": report.id,
        "category_code": report.category_code,
        "title": report.title,
        "description": report.description,
        "location": report.location,
        "image_urls": report.image_urls,
        "points": report.points,
        "status": report.status,
        "review_comment": report.review_comment,
        "point_record_id": report.point_record_id,
        "created_at": report.created_at,
    }


def submit_report(
    member: Member,
    *,
    category_code: str,
    description: str = "",
    location: str,
    image_urls: list[str],
) -> Report:
    category_code = category_code.strip()
    if category_code not in Report.CategoryCode.values:
        raise BusinessError("分类编码不支持")
    location = location.strip()
    if not location:
        raise BusinessError("位置不能为空")
    image_urls = [str(url).strip() for url in image_urls if str(url).strip()]
    if not image_urls or len(image_urls) > 10:
        raise BusinessError("图片数量必须为 1-10 张")
    title = Report.CategoryCode(category_code).label
    return Report.objects.create(
        member=member,
        category_code=category_code,
        title=title,
        description=description.strip(),
        location=location,
        image_urls=image_urls,
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

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.reports.models import Report
from apps.reports.schemas import ReportIn, ReportOut, ReportsData
from apps.reports.services import report_data, submit_report
from shared.api import ErrorResponse, SuccessResponse, error_response, success_response
from shared.auth import TokenError
from shared.exceptions import BusinessError
from shared.pagination import paginate_queryset
from shared.services import authenticate_member, require_approved_member


router = Router(tags=["随手拍"])


@router.post("", response={200: SuccessResponse[ReportOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def create_report(request, payload: ReportIn):
    try:
        member = require_approved_member(request)
        report = submit_report(
            member,
            category_code=payload.category_code,
            description=payload.description,
            location=payload.location,
            image_urls=payload.image_urls,
        )
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(report_data(report, request=request))


@router.get("", response={200: SuccessResponse[ReportsData], 401: ErrorResponse, 403: ErrorResponse})
def my_reports(request, page: int = 1, page_size: int = 20, status: str = "", report_type: str = ""):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    queryset = member.reports.all()
    if status:
        queryset = queryset.filter(status=status)
    if report_type:
        if report_type == "report":
            queryset = queryset.exclude(category_code=Report.CategoryCode.GOOD_DEED)
        elif report_type == "good_deed":
            queryset = queryset.filter(category_code=Report.CategoryCode.GOOD_DEED)
        else:
            return error_response(40000, "report_type 取值必须为 report 或 good_deed", status=400)
    items, page_data = paginate_queryset(queryset, page=page, page_size=page_size)
    return success_response({"items": [report_data(item, request=request) for item in items], **page_data})


@router.get("/{report_id}", response={200: SuccessResponse[ReportOut], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def report_detail(request, report_id: int):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    report = get_object_or_404(Report, pk=report_id, member=member)
    return success_response(report_data(report, request=request))

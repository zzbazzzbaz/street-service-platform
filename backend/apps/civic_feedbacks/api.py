from django.shortcuts import get_object_or_404
from ninja import Router

from apps.civic_feedbacks.models import CivicFeedback
from apps.civic_feedbacks.schemas import CivicFeedbackIn, CivicFeedbackOut, CivicFeedbacksData
from apps.civic_feedbacks.services import civic_feedback_data, create_civic_feedback
from shared.api import ErrorResponse, SuccessResponse, error_response, success_response
from shared.auth import TokenError
from shared.exceptions import BusinessError
from shared.pagination import paginate_queryset
from shared.services import authenticate_member, require_approved_member


router = Router(tags=["社情民意"])


@router.post("", response={200: SuccessResponse[CivicFeedbackOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def create_feedback(request, payload: CivicFeedbackIn):
    try:
        member = require_approved_member(request)
        feedback = create_civic_feedback(
            member,
            title=payload.title,
            content=payload.content,
            material_urls=payload.material_urls,
        )
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(civic_feedback_data(feedback))


@router.get("", response={200: SuccessResponse[CivicFeedbacksData], 401: ErrorResponse, 403: ErrorResponse})
def my_feedbacks(request, page: int = 1, page_size: int = 20, status: str = ""):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    queryset = member.civic_feedbacks.all()
    if status:
        queryset = queryset.filter(status=status)
    items, page_data = paginate_queryset(queryset, page=page, page_size=page_size)
    return success_response({"items": [civic_feedback_data(item) for item in items], **page_data})


@router.get("/{feedback_id}", response={200: SuccessResponse[CivicFeedbackOut], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def feedback_detail(request, feedback_id: int):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    feedback = get_object_or_404(CivicFeedback, pk=feedback_id, member=member)
    return success_response(civic_feedback_data(feedback))

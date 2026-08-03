from django.shortcuts import get_object_or_404
from ninja import Router

from apps.problem_feedbacks.models import ProblemFeedback
from apps.problem_feedbacks.schemas import (
    ProblemFeedbackIn,
    ProblemFeedbackOut,
    ProblemFeedbacksData,
    PublicProblemFeedbacksData,
)
from apps.problem_feedbacks.services import create_problem_feedback, problem_feedback_data, public_problem_feedback_data
from shared.api import ErrorResponse, SuccessResponse, error_response, success_response
from shared.auth import TokenError
from shared.exceptions import BusinessError
from shared.pagination import paginate_queryset
from shared.services import authenticate_member, require_approved_member


router = Router(tags=["问题反馈"])


@router.post("", response={200: SuccessResponse[ProblemFeedbackOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def create_feedback(request, payload: ProblemFeedbackIn):
    try:
        member = require_approved_member(request)
        feedback = create_problem_feedback(member, title=payload.title, content=payload.content)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(problem_feedback_data(feedback))


@router.get("/public", response={200: SuccessResponse[PublicProblemFeedbacksData]})
def public_feedbacks(request, page: int = 1, page_size: int = 20):
    queryset = (
        ProblemFeedback.objects.filter(
            visibility_status=ProblemFeedback.VisibilityStatus.APPROVED,
            is_public=True,
        )
        .select_related("member")
        .order_by("-created_at", "-id")
    )
    items, page_data = paginate_queryset(queryset, page=page, page_size=page_size)
    return success_response({"items": [public_problem_feedback_data(item) for item in items], **page_data})


@router.get("", response={200: SuccessResponse[ProblemFeedbacksData], 401: ErrorResponse, 403: ErrorResponse})
def my_feedbacks(request, page: int = 1, page_size: int = 20, status: str = ""):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    queryset = member.problem_feedbacks.all()
    if status:
        queryset = queryset.filter(status=status)
    items, page_data = paginate_queryset(queryset, page=page, page_size=page_size)
    return success_response({"items": [problem_feedback_data(item) for item in items], **page_data})


@router.get("/{feedback_id}", response={200: SuccessResponse[ProblemFeedbackOut], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def feedback_detail(request, feedback_id: int):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    feedback = get_object_or_404(ProblemFeedback, pk=feedback_id, member=member)
    return success_response(problem_feedback_data(feedback))

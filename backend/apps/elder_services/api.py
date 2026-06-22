from django.shortcuts import get_object_or_404
from ninja import Router

from apps.elder_services.models import ElderServiceTask
from apps.elder_services.schemas import ElderServiceFeedbackOut, ElderServiceFeedbacksData, ElderServiceTaskOut, ElderServiceTasksData, FeedbackIn
from apps.elder_services.services import feedback_data, submit_feedback, task_data
from shared.api import ErrorResponse, SuccessResponse, error_response, success_response
from shared.auth import TokenError
from shared.exceptions import BusinessError
from shared.pagination import paginate_queryset
from shared.services import authenticate_member


router = Router(tags=["老人服务"])


@router.get("/tasks", response={200: SuccessResponse[ElderServiceTasksData], 401: ErrorResponse, 403: ErrorResponse})
def task_list(request, page: int = 1, page_size: int = 20):
    try:
        authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    items, page_data = paginate_queryset(ElderServiceTask.objects.filter(status=ElderServiceTask.Status.PUBLISHED), page=page, page_size=page_size)
    return success_response({"items": [task_data(item) for item in items], **page_data})


@router.get("/tasks/{task_id}", response={200: SuccessResponse[ElderServiceTaskOut], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def task_detail(request, task_id: int):
    try:
        authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    task = get_object_or_404(ElderServiceTask, pk=task_id, status=ElderServiceTask.Status.PUBLISHED)
    return success_response(task_data(task))


@router.post("/tasks/{task_id}/feedback", response={200: SuccessResponse[ElderServiceFeedbackOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def submit_task_feedback(request, task_id: int, payload: FeedbackIn):
    try:
        member = authenticate_member(request)
        task = get_object_or_404(ElderServiceTask, pk=task_id)
        feedback = submit_feedback(member, task, content=payload.content, image=payload.image)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(feedback_data(feedback, request=request))


@router.get("/feedbacks", response={200: SuccessResponse[ElderServiceFeedbacksData], 401: ErrorResponse, 403: ErrorResponse})
def my_feedbacks(request, page: int = 1, page_size: int = 20):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    items, page_data = paginate_queryset(member.elder_feedbacks.select_related("task"), page=page, page_size=page_size)
    return success_response({"items": [feedback_data(item, request=request) for item in items], **page_data})

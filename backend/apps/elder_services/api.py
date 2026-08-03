from django.shortcuts import get_object_or_404
from ninja import Router

from apps.elder_services.models import ElderServiceFeedback, ElderServiceTask
from apps.elder_services.schemas import (
    DirectFeedbackIn,
    ElderRelationOut,
    ElderServiceFeedbackOut,
    ElderServiceFeedbacksData,
    ElderServiceMyTasksData,
    ElderServiceTaskOut,
    ElderServiceTasksData,
    FeedbackIn,
)
from apps.elder_services.services import create_feedback_direct, feedback_data, latest_feedback_for, my_relation_data, my_task_data, submit_feedback, task_data
from shared.api import ErrorResponse, SuccessResponse, error_response, success_response
from shared.auth import TokenError
from shared.exceptions import BusinessError
from shared.pagination import normalise_page, normalise_page_size, paginate_queryset
from shared.services import authenticate_member, require_approved_member


router = Router(tags=["老人服务"])


@router.get("/my-relation", response={200: SuccessResponse[ElderRelationOut | None], 401: ErrorResponse, 403: ErrorResponse})
def my_relation(request):
    try:
        member = require_approved_member(request)
        if member.identity_type != "courier":
            raise BusinessError("当前用户无权限访问", code=40301, status=403)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(my_relation_data(member))


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


@router.get("/my-tasks", response={200: SuccessResponse[ElderServiceMyTasksData], 401: ErrorResponse, 403: ErrorResponse})
def my_tasks(request, page: int = 1, page_size: int = 20, feedback_status: str = ""):
    try:
        member = require_approved_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)

    queryset = ElderServiceTask.objects.filter(
        status=ElderServiceTask.Status.PUBLISHED,
        relation__member=member,
        relation__is_active=True,
    ).select_related("relation")
    tasks = list(queryset)
    latest_by_task = {
        feedback.task_id: feedback
        for feedback in ElderServiceFeedback.objects.filter(member=member, task_id__in=[task.id for task in tasks]).order_by("task_id", "-created_at", "-id")
    }
    filtered = []
    for task in tasks:
        task._latest_feedback = latest_by_task.get(task.id)
        computed_status = task._latest_feedback.status if task._latest_feedback is not None else "none"
        if feedback_status and feedback_status != computed_status:
            continue
        filtered.append(task)

    page = normalise_page(page)
    page_size = normalise_page_size(page_size)
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]
    page_data = {"total": total, "page": page, "page_size": page_size}
    return success_response({"items": [my_task_data(item, member) for item in items], **page_data})


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
        feedback = submit_feedback(member, task, content=payload.content, image_urls=payload.image_urls)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(feedback_data(feedback, request=request))


@router.post("/feedbacks", response={200: SuccessResponse[ElderServiceFeedbackOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse})
def submit_direct_feedback(request, payload: DirectFeedbackIn):
    try:
        member = require_approved_member(request)
        feedback = create_feedback_direct(member, content=payload.content, image_urls=payload.image_urls)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(feedback_data(feedback, request=request))


@router.get("/feedbacks", response={200: SuccessResponse[ElderServiceFeedbacksData], 401: ErrorResponse, 403: ErrorResponse})
def my_feedbacks(request, page: int = 1, page_size: int = 20, status: str = ""):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    queryset = member.elder_feedbacks.select_related("task", "relation")
    if status:
        queryset = queryset.filter(status=status)
    items, page_data = paginate_queryset(queryset, page=page, page_size=page_size)
    return success_response({"items": [feedback_data(item, request=request) for item in items], **page_data})

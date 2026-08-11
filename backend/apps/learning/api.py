from django.shortcuts import get_object_or_404
from ninja import Router

from apps.learning.models import LearningContent, LearningRecord
from apps.learning.schemas import CompleteLearningIn, LearningContentOut, LearningContentsData, LearningRecordOut, LearningRecordsData
from apps.learning.services import complete_learning, content_data, record_data
from shared.api import ErrorResponse, SuccessResponse, error_response, success_response
from shared.auth import TokenError
from shared.exceptions import BusinessError
from shared.pagination import paginate_queryset
from shared.services import authenticate_member


router = Router(tags=["学习"])


@router.get("/contents", response={200: SuccessResponse[LearningContentsData], 401: ErrorResponse, 403: ErrorResponse})
def learning_contents(request, page: int = 1, page_size: int = 20, is_announcement: bool | None = None, is_pinned: bool | None = None):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    queryset = LearningContent.objects.filter(is_active=True)
    if is_announcement is not None:
        queryset = queryset.filter(is_announcement=is_announcement)
    if is_pinned is not None:
        queryset = queryset.filter(is_pinned=is_pinned)
    items, page_data = paginate_queryset(queryset, page=page, page_size=page_size)
    records = {
        record.content_id: record
        for record in LearningRecord.objects.filter(member=member, content_id__in=[item.id for item in items])
    }
    for item in items:
        item._member_record = records.get(item.id)
    return success_response({"items": [content_data(item, request=request, member=member) for item in items], **page_data})


@router.get("/contents/{content_id}", response={200: SuccessResponse[LearningContentOut], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def learning_content_detail(request, content_id: int):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    content = get_object_or_404(LearningContent, pk=content_id, is_active=True)
    return success_response(content_data(content, request=request, member=member))


@router.post("/contents/{content_id}/complete", response={200: SuccessResponse[LearningRecordOut], 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def learning_complete(request, content_id: int, payload: CompleteLearningIn):
    try:
        member = authenticate_member(request)
        content = get_object_or_404(LearningContent, pk=content_id)
        record = complete_learning(member, content, learned_seconds=payload.learned_seconds)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(record_data(record))


@router.get("/records", response={200: SuccessResponse[LearningRecordsData], 401: ErrorResponse, 403: ErrorResponse})
def learning_records(request, page: int = 1, page_size: int = 20):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    items, page_data = paginate_queryset(member.learning_records.select_related("content"), page=page, page_size=page_size)
    return success_response({"items": [record_data(item) for item in items], **page_data})

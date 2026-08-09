from ninja import Router

from apps.service_records.schemas import ServiceRecordsData
from apps.service_records.services import list_service_records, service_record_detail
from shared.api import ErrorResponse, SuccessResponse, error_response, success_response
from shared.auth import TokenError
from shared.exceptions import BusinessError
from shared.services import authenticate_member


router = Router(tags=["统一服务记录"])


@router.get("", response={200: SuccessResponse[ServiceRecordsData], 401: ErrorResponse, 403: ErrorResponse})
def service_records_list(request, page: int = 1, page_size: int = 20):
    try:
        member = authenticate_member(request)
        items, page_data = list_service_records(member, page=page, page_size=page_size)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response({"items": items, **page_data})


@router.get("/{record_type}/{source_id}", response={200: SuccessResponse[dict], 401: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse})
def service_record_detail_view(request, record_type: str, source_id: int):
    try:
        member = authenticate_member(request)
        detail = service_record_detail(member, record_type, source_id)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(detail)

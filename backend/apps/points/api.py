from ninja import Router

from apps.points.schemas import PointBalanceOut, PointRecordsData
from apps.points.services import get_or_create_account, point_record_data
from shared.api import ErrorResponse, SuccessResponse, error_response, success_response
from shared.auth import TokenError
from shared.exceptions import BusinessError
from shared.pagination import paginate_queryset
from shared.services import authenticate_member


router = Router(tags=["积分"])


@router.get("/balance", response={200: SuccessResponse[PointBalanceOut], 401: ErrorResponse, 403: ErrorResponse})
def point_balance(request):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)

    account = get_or_create_account(member)
    return success_response({"balance": account.balance})


@router.get("/records", response={200: SuccessResponse[PointRecordsData], 401: ErrorResponse, 403: ErrorResponse})
def point_records(request, page: int = 1, page_size: int = 20):
    try:
        member = authenticate_member(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)

    records, page_data = paginate_queryset(member.point_records.all(), page=page, page_size=page_size)
    return success_response({"items": [point_record_data(record) for record in records], **page_data})

from ninja import Router

from apps.merchants.schemas import MerchantLoginOut, MerchantOut, MerchantTestLoginIn
from apps.merchants.services import merchant_data, test_login
from shared.api import ErrorResponse, SuccessResponse, error_response, success_response
from shared.auth import TokenError
from shared.exceptions import BusinessError
from shared.services import authenticate_merchant


merchant_auth_router = Router(tags=["商户认证"])
merchant_router = Router(tags=["商户"])


@merchant_auth_router.post("/test-login", response={200: SuccessResponse[MerchantLoginOut], 400: ErrorResponse})
def merchant_test_login(request, payload: MerchantTestLoginIn):
    try:
        return success_response(test_login(payload.openid))
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)


@merchant_router.get("/me", response={200: SuccessResponse[MerchantOut], 401: ErrorResponse, 403: ErrorResponse})
def merchant_me(request):
    try:
        merchant = authenticate_merchant(request)
    except TokenError as exc:
        return error_response(40001, str(exc), status=401)
    except BusinessError as exc:
        return error_response(exc.code, exc.message, status=exc.status, errors=exc.errors)
    return success_response(merchant_data(merchant))

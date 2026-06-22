from ninja import NinjaAPI, Schema
from ninja.errors import ValidationError

from apps.members.api import auth_router, router as members_router
from apps.merchants.api import merchant_auth_router, merchant_router
from shared.api import ErrorResponse, error_response
from shared.api import SuccessResponse, success_response


class HealthOut(Schema):
    status: str


api = NinjaAPI(title="街道服务数字化操作系统 API", version="0.1.0")


@api.exception_handler(ValidationError)
def validation_errors(request, exc):
    return error_response(40000, "请求参数错误", status=400, errors=exc.errors)


@api.get("/health", response=SuccessResponse[HealthOut], tags=["系统"])
def health(request):
    return success_response({"status": "ok"})


api.add_router("/auth", auth_router)
api.add_router("/members", members_router)
api.add_router("/merchant/auth", merchant_auth_router)
api.add_router("/merchant", merchant_router)

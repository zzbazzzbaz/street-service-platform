from ninja import NinjaAPI, Schema
from ninja.errors import ValidationError
from django.http import Http404

from apps.activities.api import router as activities_router
from apps.core.api import router as uploads_router
from apps.civic_feedbacks.api import router as civic_feedbacks_router
from apps.elder_services.api import router as elder_services_router
from apps.learning.api import router as learning_router
from apps.members.api import auth_router, router as members_router
from apps.merchants.api import merchant_auth_router, merchant_router, public_merchant_router
from apps.points.api import router as points_router
from apps.problem_feedbacks.api import router as problem_feedbacks_router
from apps.reports.api import router as reports_router
from shared.api import ErrorResponse, error_response
from shared.api import SuccessResponse, success_response


class HealthOut(Schema):
    status: str


api = NinjaAPI(title="街道服务数字化操作系统 API", version="0.1.0")


@api.exception_handler(ValidationError)
def validation_errors(request, exc):
    return error_response(40000, "请求参数错误", status=400, errors=exc.errors)


@api.exception_handler(Http404)
def not_found_errors(request, exc):
    return error_response(40400, "资源不存在", status=404)


@api.get("/health", response=SuccessResponse[HealthOut], tags=["系统"])
def health(request):
    return success_response({"status": "ok"})


api.add_router("/auth", auth_router)
api.add_router("/uploads", uploads_router)
api.add_router("/members", members_router)
api.add_router("/learning", learning_router)
api.add_router("/reports", reports_router)
api.add_router("/civic-feedbacks", civic_feedbacks_router)
api.add_router("/problem-feedbacks", problem_feedbacks_router)
api.add_router("/activities", activities_router)
api.add_router("/elder-services", elder_services_router)
api.add_router("/points", points_router)
api.add_router("/merchants", public_merchant_router)
api.add_router("/merchant/auth", merchant_auth_router)
api.add_router("/merchant", merchant_router)

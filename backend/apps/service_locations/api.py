from ninja import Router

from apps.service_locations.models import ServiceLocation
from apps.service_locations.services import service_location_data
from shared.api import SuccessResponse, success_response
from shared.pagination import paginate_queryset


router = Router(tags=["服务阵地"])


@router.get("", response={200: SuccessResponse[dict]})
def service_locations(request, page: int = 1, page_size: int = 50):
    queryset = ServiceLocation.objects.filter(is_active=True).order_by("-created_at", "-id")
    items, page_data = paginate_queryset(queryset, page=page, page_size=page_size)
    return success_response({"items": [service_location_data(item) for item in items], **page_data})

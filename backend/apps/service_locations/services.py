from __future__ import annotations

from apps.service_locations.models import ServiceLocation


def service_location_data(loc: ServiceLocation) -> dict:
    return {
        "id": loc.id,
        "name": loc.name,
        "address": loc.address,
        "business_hours": loc.business_hours,
        "service_content": loc.service_content,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "is_active": loc.is_active,
        "created_at": loc.created_at,
        "updated_at": loc.updated_at,
    }

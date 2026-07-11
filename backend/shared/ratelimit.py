from __future__ import annotations

from shared.auth import TokenError, get_token_identity


def get_client_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def user_key(group, request) -> str:
    try:
        identity = get_token_identity(request)
        identifier = identity.openid or str(identity.user_id or "")
        return f"{identity.subject_type}:{identifier}"
    except TokenError:
        return f"ip:{get_client_ip(request)}"

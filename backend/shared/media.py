from __future__ import annotations

from django.conf import settings


def absolute_url(request, url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    return request.build_absolute_uri(url)


def file_url(request, file_field) -> str:
    if not file_field:
        return ""
    try:
        return absolute_url(request, file_field.url)
    except ValueError:
        return ""


def media_url(request, path: str) -> str:
    path = (path or "").strip()
    if not path:
        return ""
    if path.startswith(settings.MEDIA_URL):
        return absolute_url(request, path)
    return absolute_url(request, f"{settings.MEDIA_URL}{path.lstrip('/')}")

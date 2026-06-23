from __future__ import annotations

import os
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from shared.media import media_url


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/ogg", "video/quicktime"}


def _save_upload(request, upload_type: str, allowed_types: set[str]):
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return JsonResponse({"error": "没有上传文件"}, status=400)

    if uploaded_file.content_type not in allowed_types:
        return JsonResponse({"error": "不支持的文件格式"}, status=400)

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    relative_path = f"tinymce/{upload_type}/{filename}"
    file_path = Path(settings.MEDIA_ROOT) / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("wb+") as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    return JsonResponse({"location": media_url(request, relative_path)})


@csrf_exempt
@staff_member_required
@require_POST
def upload_image(request):
    return _save_upload(request, "images", ALLOWED_IMAGE_TYPES)


@csrf_exempt
@staff_member_required
@require_POST
def upload_video(request):
    return _save_upload(request, "videos", ALLOWED_VIDEO_TYPES)

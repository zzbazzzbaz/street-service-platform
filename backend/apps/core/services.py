from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.utils import timezone

from shared.exceptions import BusinessError
from shared.media import media_url


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_BUSINESS_TYPES = {
    "report",
    "civic_feedback",
    "problem_feedback",
    "elder_service_feedback",
    "merchant_product",
    "learning_content",
    "general",
}
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_IMAGE_COUNT = 10


def save_uploaded_images(request, files, *, business_type: str = "general", related_id: str = "") -> dict:
    files = list(files)
    business_type = (business_type or "general").strip() or "general"
    if business_type not in ALLOWED_BUSINESS_TYPES:
        raise BusinessError("上传业务类型不支持")
    if not files:
        raise BusinessError("请上传图片")
    if len(files) > MAX_IMAGE_COUNT:
        raise BusinessError(f"一次最多上传 {MAX_IMAGE_COUNT} 张图片")

    saved_files = []
    for uploaded_file in files:
        saved_files.append(_save_one_image(request, uploaded_file, business_type=business_type, related_id=related_id))
    return {"files": saved_files}


def _save_one_image(request, uploaded_file, *, business_type: str, related_id: str) -> dict:
    if uploaded_file.content_type not in ALLOWED_IMAGE_TYPES:
        raise BusinessError("不支持的图片格式")
    if uploaded_file.size > MAX_IMAGE_SIZE:
        raise BusinessError("单张图片不能超过 10MB")

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    filename = f"{uuid4().hex}{ext}"
    parts = ["uploads", business_type]
    related_id = str(related_id or "").strip()
    if related_id:
        parts.append(related_id)
    relative_path = "/".join([*parts, filename])
    file_path = Path(settings.MEDIA_ROOT) / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("wb+") as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    return {
        "file_id": relative_path,
        "url": media_url(request, relative_path),
        "original_name": uploaded_file.name,
        "size": uploaded_file.size,
        "mime_type": uploaded_file.content_type,
        "created_at": timezone.now(),
    }

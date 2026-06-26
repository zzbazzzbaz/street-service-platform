from datetime import datetime

from ninja import Schema


class UploadedImageOut(Schema):
    file_id: str
    url: str
    original_name: str
    size: int
    mime_type: str
    created_at: datetime


class UploadedImagesData(Schema):
    files: list[UploadedImageOut]

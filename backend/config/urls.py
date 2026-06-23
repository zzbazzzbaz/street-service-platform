from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from config.api import api
from config import tinymce_upload


urlpatterns = [
    path("admin/tinymce/upload/image/", tinymce_upload.upload_image, name="tinymce-upload-image"),
    path("admin/tinymce/upload/video/", tinymce_upload.upload_video, name="tinymce-upload-video"),
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

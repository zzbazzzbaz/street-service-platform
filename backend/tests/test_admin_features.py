from django.contrib.admin.sites import AdminSite
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from tinymce.widgets import TinyMCE

from apps.accounts.models import User
from apps.activities.admin import ActivityAdmin
from apps.activities.models import Activity
from apps.elder_services.admin import ElderServiceFeedbackAdmin
from apps.elder_services.models import ElderServiceFeedback
from apps.learning.admin import LearningContentAdmin
from apps.learning.models import LearningContent
from apps.reports.admin import ReportAdmin
from apps.reports.models import Report


class AdminFeaturesTests(SimpleTestCase):
    def setUp(self):
        self.site = AdminSite()

    def test_learning_content_body_uses_tinymce_widget(self):
        model_admin = LearningContentAdmin(LearningContent, self.site)
        field = LearningContent._meta.get_field("body")

        form_field = model_admin.formfield_for_dbfield(field, request=None)

        self.assertIsInstance(form_field.widget, TinyMCE)

    def test_activity_body_uses_tinymce_widget(self):
        model_admin = ActivityAdmin(Activity, self.site)
        field = Activity._meta.get_field("body")

        form_field = model_admin.formfield_for_dbfield(field, request=None)

        self.assertIsInstance(form_field.widget, TinyMCE)

    def test_learning_content_other_text_fields_keep_default_widget(self):
        model_admin = LearningContentAdmin(LearningContent, self.site)
        field = LearningContent._meta.get_field("title")

        form_field = model_admin.formfield_for_dbfield(field, request=None)

        self.assertNotIsInstance(form_field.widget, TinyMCE)

    def test_learning_content_media_fields_use_file_upload_widgets(self):
        model_admin = LearningContentAdmin(LearningContent, self.site)

        image_field = model_admin.formfield_for_dbfield(LearningContent._meta.get_field("image"), request=None)
        video_field = model_admin.formfield_for_dbfield(LearningContent._meta.get_field("video"), request=None)

        self.assertEqual(image_field.widget.input_type, "file")
        self.assertEqual(video_field.widget.input_type, "file")

    def test_admin_image_preview_outputs_thumbnail_and_original_link(self):
        cases = [
            (ReportAdmin(Report, self.site), Report(image="reports/example.jpg"), "image_preview"),
            (
                ElderServiceFeedbackAdmin(ElderServiceFeedback, self.site),
                ElderServiceFeedback(image="elder-services/feedbacks/example.jpg"),
                "image_preview",
            ),
            (LearningContentAdmin(LearningContent, self.site), LearningContent(cover="learning/covers/example.jpg"), "cover_preview"),
            (LearningContentAdmin(LearningContent, self.site), LearningContent(image="learning/images/example.jpg"), "image_preview"),
            (
                ActivityAdmin(Activity, self.site),
                Activity(checkin_qr_image="activities/qrcodes/example.png"),
                "checkin_qr_preview",
            ),
        ]

        for model_admin, obj, method_name in cases:
            with self.subTest(model_admin=model_admin.__class__.__name__):
                html = str(getattr(model_admin, method_name)(obj))
                self.assertIn("<img", html)
                self.assertIn("target=\"_blank\"", html)
                self.assertIn("打开原图", html)

    def test_admin_image_preview_handles_empty_file(self):
        model_admin = ReportAdmin(Report, self.site)

        html = str(model_admin.image_preview(Report()))

        self.assertEqual(html, "暂无图片")

    def test_learning_content_video_preview_outputs_file_link(self):
        model_admin = LearningContentAdmin(LearningContent, self.site)

        html = str(model_admin.video_preview(LearningContent(video="learning/videos/example.mp4")))

        self.assertIn("target=\"_blank\"", html)
        self.assertIn("打开视频", html)


@override_settings(MEDIA_ROOT="/tmp/street-service-test-media")
class TinymceUploadTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(username="admin", password="password")
        self.client.force_login(self.admin_user)

    def test_image_upload_returns_tinymce_location(self):
        uploaded = SimpleUploadedFile("image.png", b"fake-png", content_type="image/png")

        response = self.client.post("/admin/tinymce/upload/image/", {"file": uploaded})

        self.assertEqual(response.status_code, 200)
        self.assertIn("/media/tinymce/images/", response.json()["location"])

    def test_video_upload_returns_tinymce_location(self):
        uploaded = SimpleUploadedFile("video.mp4", b"fake-mp4", content_type="video/mp4")

        response = self.client.post("/admin/tinymce/upload/video/", {"file": uploaded})

        self.assertEqual(response.status_code, 200)
        self.assertIn("/media/tinymce/videos/", response.json()["location"])

    def test_upload_rejects_unsupported_content_type(self):
        uploaded = SimpleUploadedFile("script.js", b"alert(1)", content_type="application/javascript")

        response = self.client.post("/admin/tinymce/upload/image/", {"file": uploaded})

        self.assertEqual(response.status_code, 400)

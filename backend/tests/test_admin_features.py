from django.contrib.admin.sites import AdminSite
from django.test import SimpleTestCase
from tinymce.widgets import TinyMCE

from apps.activities.admin import ActivityAdmin
from apps.activities.models import Activity
from apps.elder_services.admin import ElderServiceFeedbackAdmin
from apps.elder_services.models import ElderServiceFeedback
from apps.learning.admin import LearningContentAdmin
from apps.learning.models import LearningContent
from apps.merchants.admin import MerchantProductAdmin
from apps.merchants.models import MerchantProduct
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

    def test_learning_content_other_text_fields_keep_default_widget(self):
        model_admin = LearningContentAdmin(LearningContent, self.site)
        field = LearningContent._meta.get_field("title")

        form_field = model_admin.formfield_for_dbfield(field, request=None)

        self.assertNotIsInstance(form_field.widget, TinyMCE)

    def test_admin_image_preview_outputs_thumbnail_and_original_link(self):
        cases = [
            (ReportAdmin(Report, self.site), Report(image="reports/example.jpg"), "image_preview"),
            (
                ElderServiceFeedbackAdmin(ElderServiceFeedback, self.site),
                ElderServiceFeedback(image="elder-services/feedbacks/example.jpg"),
                "image_preview",
            ),
            (LearningContentAdmin(LearningContent, self.site), LearningContent(cover="learning/covers/example.jpg"), "cover_preview"),
            (
                MerchantProductAdmin(MerchantProduct, self.site),
                MerchantProduct(image="merchant-products/example.jpg"),
                "image_preview",
            ),
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

from django.test import TestCase

from apps.reports.models import Report


class ReportCategoryEnumTests(TestCase):
    def test_enum_contains_good_deed(self):
        self.assertIn("good_deed", [v for v, _ in Report.CategoryCode.choices])
        self.assertIn("safety_hazard", [v for v, _ in Report.CategoryCode.choices])

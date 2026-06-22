from django.test import SimpleTestCase

from shared.api import success_response
from shared.pagination import normalise_page, normalise_page_size, paginate_queryset


class ListQuerySet:
    def __init__(self, values):
        self.values = list(values)

    def count(self):
        return len(self.values)

    def __getitem__(self, item):
        return self.values[item]


class SharedBasicsTests(SimpleTestCase):
    def test_success_response_wraps_data(self):
        self.assertEqual(
            success_response({"status": "ok"}),
            {
                "code": 0,
                "message": "success",
                "data": {"status": "ok"},
            },
        )

    def test_normalise_page_uses_minimum_one(self):
        self.assertEqual(normalise_page(None), 1)
        self.assertEqual(normalise_page(0), 1)
        self.assertEqual(normalise_page(-5), 1)
        self.assertEqual(normalise_page("3"), 3)
        self.assertEqual(normalise_page("bad"), 1)

    def test_normalise_page_size_defaults_and_caps_at_one_hundred(self):
        self.assertEqual(normalise_page_size(None), 20)
        self.assertEqual(normalise_page_size(0), 20)
        self.assertEqual(normalise_page_size("bad"), 20)
        self.assertEqual(normalise_page_size(200), 100)

    def test_paginate_queryset_returns_page_metadata(self):
        items, meta = paginate_queryset(ListQuerySet(range(25)), page=2, page_size=10)

        self.assertEqual(items, list(range(10, 20)))
        self.assertEqual(meta, {"total": 25, "page": 2, "page_size": 10})

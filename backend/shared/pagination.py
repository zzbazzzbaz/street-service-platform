from __future__ import annotations


MAX_PAGE_SIZE = 100


def normalise_page(page: int | str | None) -> int:
    try:
        value = int(page or 1)
    except (TypeError, ValueError):
        return 1
    return max(value, 1)


def normalise_page_size(
    page_size: int | str | None,
    *,
    default: int = 20,
    maximum: int = MAX_PAGE_SIZE,
) -> int:
    try:
        value = int(page_size or default)
    except (TypeError, ValueError):
        return default
    return min(max(value, 1), maximum)


def paginate_queryset(queryset, *, page: int | str | None = 1, page_size: int | str | None = 20) -> tuple[list, dict]:
    page = normalise_page(page)
    page_size = normalise_page_size(page_size)
    total = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    return list(queryset[start:end]), {"total": total, "page": page, "page_size": page_size}

from __future__ import annotations

from typing import Generic, TypeVar

from django.http import JsonResponse
from ninja import Schema


T = TypeVar("T")


class SuccessResponse(Schema, Generic[T]):
    code: int = 0
    message: str = "success"
    data: T


class ErrorResponse(Schema):
    code: int
    message: str
    errors: dict | list | None = None


class ItemsData(Schema, Generic[T]):
    items: list[T]


class PaginatedData(ItemsData[T], Generic[T]):
    total: int
    page: int
    page_size: int


def success_response(data=None) -> dict:
    return {"code": 0, "message": "success", "data": data}


def error_response(code: int, message: str, *, status: int = 400, errors=None) -> JsonResponse:
    return JsonResponse({"code": code, "message": message, "errors": errors}, status=status)

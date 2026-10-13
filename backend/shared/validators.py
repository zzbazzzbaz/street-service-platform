from __future__ import annotations

import re

from shared.exceptions import BusinessError


PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
PHONE_ERROR_MESSAGE = "手机号格式不正确"


def clean_phone(value: str, *, field: str = "phone") -> str:
    value = (value or "").strip()
    if not PHONE_PATTERN.match(value):
        raise BusinessError(
            PHONE_ERROR_MESSAGE,
            errors={field: [PHONE_ERROR_MESSAGE]},
        )
    return value

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from django.conf import settings

logger = logging.getLogger("street.auth")


class TokenError(Exception):
    pass


@dataclass(frozen=True)
class TokenIdentity:
    subject_type: str
    expires_at: int
    openid: str = ""
    user_id: int | None = None


def issue_token(*, subject_type: str, openid: str) -> tuple[str, int]:
    subject_type = subject_type.strip()
    openid = openid.strip()
    if subject_type not in {"member", "merchant"}:
        raise TokenError("token 主体类型不支持")
    if not openid:
        raise TokenError("openid 不能为空")

    expires_in = settings.ACCESS_TOKEN_EXPIRES_SECONDS
    now = int(time.time())
    payload = {
        "subject_type": subject_type,
        "openid": openid,
        "iat": now,
        "exp": now + expires_in,
    }
    return _encode_jwt(payload), expires_in


def issue_admin_token(*, user_id: int) -> tuple[str, int]:
    if not user_id:
        raise TokenError("用户ID不能为空")

    expires_in = settings.ACCESS_TOKEN_EXPIRES_SECONDS
    now = int(time.time())
    payload = {
        "subject_type": "admin",
        "user_id": int(user_id),
        "iat": now,
        "exp": now + expires_in,
    }
    return _encode_jwt(payload), expires_in


def parse_token(token: str) -> TokenIdentity:
    try:
        payload = _decode_jwt(token)
    except TokenError:
        logger.warning("token 解析失败")
        raise
    subject_type = str(payload.get("subject_type") or "").strip()
    openid = str(payload.get("openid") or "").strip()
    user_id = payload.get("user_id")
    expires_at = int(payload.get("exp") or 0)

    if subject_type not in {"member", "merchant", "admin"}:
        logger.warning("token 主体类型不支持 subject_type=%s", subject_type)
        raise TokenError("token 主体类型不支持")
    if subject_type in {"member", "merchant"} and not openid:
        logger.warning("token 缺少身份 subject_type=%s", subject_type)
        raise TokenError("token 缺少身份")
    if subject_type == "admin":
        try:
            user_id = int(user_id)
        except (TypeError, ValueError) as exc:
            logger.warning("token 管理员身份无效")
            raise TokenError("token 缺少身份") from exc
        if user_id <= 0:
            logger.warning("token 管理员 ID 无效 user_id=%s", user_id)
            raise TokenError("token 缺少身份")
    if expires_at <= int(time.time()):
        logger.warning("token 已过期 subject_type=%s", subject_type)
        raise TokenError("token 已过期")
    return TokenIdentity(subject_type=subject_type, openid=openid, user_id=user_id, expires_at=expires_at)


def get_bearer_token(request) -> str:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise TokenError("缺少 Bearer token")
    return token.strip()


def get_token_identity(request) -> TokenIdentity:
    return parse_token(get_bearer_token(request))


def _encode_jwt(payload: dict[str, Any]) -> str:
    header_segment = _base64url_json({"alg": "HS256", "typ": "JWT"})
    payload_segment = _base64url_json(payload)
    signing_input = f"{header_segment}.{payload_segment}".encode()
    signature = _sign(signing_input)
    return f"{header_segment}.{payload_segment}.{_base64url_encode(signature)}"


def _decode_jwt(token: str) -> dict[str, Any]:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise TokenError("token 格式错误") from exc

    signing_input = f"{header_segment}.{payload_segment}".encode()
    expected_signature = _base64url_encode(_sign(signing_input))
    if not hmac.compare_digest(signature_segment, expected_signature):
        raise TokenError("token 签名无效")

    header = _base64url_json_loads(header_segment)
    if header.get("alg") != "HS256":
        raise TokenError("token 算法不支持")
    return _base64url_json_loads(payload_segment)


def _sign(value: bytes) -> bytes:
    return hmac.new(settings.ACCESS_TOKEN_SECRET.encode(), value, hashlib.sha256).digest()


def _base64url_json(value: dict[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return _base64url_encode(raw)


def _base64url_json_loads(value: str) -> dict[str, Any]:
    try:
        return json.loads(_base64url_decode(value))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise TokenError("token 载荷无效") from exc


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except (ValueError, base64.binascii.Error) as exc:
        raise TokenError("token base64 无效") from exc

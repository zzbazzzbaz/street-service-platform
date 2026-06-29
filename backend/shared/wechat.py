from __future__ import annotations

import json
from urllib import parse, request

from django.conf import settings

from shared.exceptions import BusinessError


def code_to_openid(login_code: str) -> str:
    login_code = login_code.strip()
    if not login_code:
        raise BusinessError("缺少微信登录 code")
    data = _get_json(
        "https://api.weixin.qq.com/sns/jscode2session",
        {
            "appid": settings.WECHAT_MINIAPP_APPID,
            "secret": settings.WECHAT_MINIAPP_SECRET,
            "js_code": login_code,
            "grant_type": "authorization_code",
        },
    )
    openid = str(data.get("openid") or "").strip()
    if not openid:
        raise BusinessError("微信登录换取 openid 失败")
    return openid


def phone_code_to_phone(phone_code: str) -> str:
    phone_code = phone_code.strip()
    if not phone_code:
        raise BusinessError("缺少手机号授权 code")
    access_token = _stable_access_token()
    data = _post_json(
        f"https://api.weixin.qq.com/wxa/business/getuserphonenumber?access_token={parse.quote(access_token)}",
        {"code": phone_code},
    )
    phone_info = data.get("phone_info") or {}
    phone = str(phone_info.get("phoneNumber") or phone_info.get("purePhoneNumber") or "").strip()
    if not phone:
        raise BusinessError("微信手机号换取失败")
    return phone


def _stable_access_token() -> str:
    data = _get_json(
        "https://api.weixin.qq.com/cgi-bin/token",
        {
            "grant_type": "client_credential",
            "appid": settings.WECHAT_MINIAPP_APPID,
            "secret": settings.WECHAT_MINIAPP_SECRET,
        },
    )
    token = str(data.get("access_token") or "").strip()
    if not token:
        raise BusinessError("微信 access_token 获取失败")
    return token


def _get_json(url: str, params: dict) -> dict:
    query = parse.urlencode(params)
    with request.urlopen(f"{url}?{query}", timeout=8) as response:
        return _parse_wechat_response(response.read())


def _post_json(url: str, payload: dict) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode()
    req = request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=8) as response:
        return _parse_wechat_response(response.read())


def _parse_wechat_response(raw: bytes) -> dict:
    try:
        data = json.loads(raw.decode())
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise BusinessError("微信接口返回异常")
    errcode = data.get("errcode")
    if errcode not in (None, 0):
        errmsg = data.get("errmsg") or "微信接口调用失败"
        raise BusinessError(str(errmsg))
    return data

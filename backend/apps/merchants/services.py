from __future__ import annotations

from apps.merchants.models import Merchant
from shared.auth import issue_token
from shared.exceptions import BusinessError


def merchant_data(merchant: Merchant) -> dict:
    return {
        "id": merchant.id,
        "openid": merchant.openid,
        "name": merchant.name,
        "contact_name": merchant.contact_name,
        "phone": merchant.phone,
        "address": merchant.address,
        "is_active": merchant.is_active,
    }


def test_login(openid: str) -> dict:
    openid = openid.strip()
    if not openid:
        raise BusinessError("openid 不能为空")
    merchant, _ = Merchant.objects.get_or_create(openid=openid, defaults={"name": f"测试商户-{openid}"})
    token, expires_in = issue_token(subject_type="merchant", openid=openid)
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "merchant": merchant_data(merchant),
    }

from apps.members.models import Member
from apps.merchants.models import Merchant
from shared.auth import issue_token


def create_member(openid: str = "member-openid", **kwargs) -> Member:
    defaults = {
        "nickname": "测试用户",
        "phone": "13800000000",
    }
    defaults.update(kwargs)
    return Member.objects.create(openid=openid, **defaults)


def create_merchant(openid: str = "merchant-openid", **kwargs) -> Merchant:
    defaults = {
        "name": "测试商户",
        "contact_name": "商户联系人",
        "phone": "13900000000",
        "address": "测试地址",
    }
    defaults.update(kwargs)
    return Merchant.objects.create(openid=openid, **defaults)


def auth_header(subject_type: str, openid: str) -> dict:
    token, _ = issue_token(subject_type=subject_type, openid=openid)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

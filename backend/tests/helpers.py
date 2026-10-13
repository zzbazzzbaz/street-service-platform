from itertools import count

from apps.members.models import Member
from apps.merchants.models import Merchant
from django.contrib.auth import get_user_model
from shared.auth import issue_admin_token, issue_token


_generated_phone_seq = count(1)


def _generated_phone() -> str:
    """生成进程内唯一、格式合法的测试手机号（199 开头，避开用例里手写的 138/139 号段）。"""
    return f"199{next(_generated_phone_seq):08d}"


def create_admin_user(username: str = "admin", password: str = "admin123456", **kwargs):
    defaults = {
        "is_backend_manager": True,
        "is_active": True,
    }
    defaults.update(kwargs)
    user = get_user_model().objects.create_user(username=username, password=password, **defaults)
    return user


def create_member(openid: str = "member-openid", **kwargs) -> Member:
    defaults = {
        "nickname": "测试用户",
        "phone": _generated_phone(),
        "audit_status": Member.AuditStatus.APPROVED,
    }
    defaults.update(kwargs)
    return Member.objects.create(openid=openid, **defaults)


def create_merchant(openid: str = "merchant-openid", **kwargs) -> Merchant:
    defaults = {
        "name": "测试商户",
        "contact_name": "商户联系人",
        "phone": _generated_phone(),
        "address": "测试地址",
        "audit_status": Merchant.AuditStatus.APPROVED,
    }
    defaults.update(kwargs)
    return Merchant.objects.create(openid=openid, **defaults)


def auth_header(subject_type: str, openid: str) -> dict:
    token, _ = issue_token(subject_type=subject_type, openid=openid)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def admin_auth_header(user=None) -> dict:
    user = user or create_admin_user()
    token, _ = issue_admin_token(user_id=user.id)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

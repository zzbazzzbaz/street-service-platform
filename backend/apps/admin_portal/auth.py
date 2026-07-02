from __future__ import annotations

from django.contrib.auth import get_user_model

from shared.auth import TokenError, get_token_identity
from shared.exceptions import BusinessError


User = get_user_model()


def authenticate_admin(request):
    try:
        identity = get_token_identity(request)
    except TokenError as exc:
        raise _auth_business_error(exc) from exc
    if identity.subject_type != "admin":
        raise BusinessError("当前账号无权限访问", code=40301, status=403)
    user = User.objects.filter(pk=identity.user_id).first()
    if user is None or not user.is_active or not user.is_staff or not user.is_backend_manager:
        raise BusinessError("当前账号无权限访问", code=40301, status=403)
    return user


def _auth_business_error(exc: TokenError) -> BusinessError:
    message = str(exc)
    if "缺少 Bearer token" in message:
        return BusinessError("缺少登录凭证", code=40102, status=401)
    return BusinessError("登录已过期，请重新登录", code=40101, status=401)

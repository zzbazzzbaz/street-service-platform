"""初始密码与首次登录强制改密的统一约定。

设计上不新增任何数据库字段：登录时用户已经把明文密码提交上来了，
直接判断「提交的密码是否就是初始密码」即可，不需要额外的标志位，
也不需要额外做一次 PBKDF2 校验。
"""

from __future__ import annotations

INITIAL_PASSWORD = "000000"
MIN_PASSWORD_LENGTH = 6


def is_initial_password(password: str) -> bool:
    """判断提交的明文密码是否仍是初始密码。"""
    return (password or "") == INITIAL_PASSWORD

from datetime import datetime

from ninja import Schema


class WechatLoginIn(Schema):
    openid: str = ""
    code: str = ""


class WechatPhoneLoginIn(Schema):
    login_code: str = ""
    phone_code: str = ""
    encrypted_data: str = ""
    iv: str = ""
    platform: str = "user_mp"


class PasswordLoginIn(Schema):
    username: str
    password: str


class MemberOut(Schema):
    id: int
    openid: str
    username: str | None = None
    nickname: str
    phone: str
    real_name: str
    identity_type: str
    audit_status: str
    audit_remark: str
    audit_submitted_at: datetime | None = None
    is_active: bool


class LoginOut(Schema):
    access_token: str
    token_type: str
    expires_in: int
    member: MemberOut


class ProfileIn(Schema):
    nickname: str = ""
    phone: str = ""


class AuditProfileIn(Schema):
    real_name: str
    identity_type: str

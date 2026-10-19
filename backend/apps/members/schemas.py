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


class MemberRegisterIn(Schema):
    real_name: str
    wechat_id: str
    gender: str
    occupation: str
    address: str
    phone: str = ""
    is_party_member: bool = False
    phone_code: str = ""
    login_code: str = ""


class MemberRegisterInfoIn(Schema):
    real_name: str
    wechat_id: str
    gender: str
    occupation: str
    address: str
    is_party_member: bool = False
    phone: str = ""


class PasswordChangeIn(Schema):
    current_password: str
    new_password: str


class MemberOut(Schema):
    id: int
    openid: str
    username: str | None = None
    nickname: str
    phone: str
    real_name: str
    wechat_id: str
    gender: str
    occupation: str
    is_party_member: bool
    address: str
    audit_status: str
    audit_remark: str
    audit_submitted_at: datetime | None = None
    is_active: bool


class LoginOut(Schema):
    access_token: str
    token_type: str
    expires_in: int
    must_change_password: bool = False
    member: MemberOut


class MemberRegisterOut(LoginOut):
    need_audit: bool = True


class ProfileIn(Schema):
    nickname: str = ""
    phone: str = ""

from ninja import Schema


class TestLoginIn(Schema):
    openid: str


class WechatLoginIn(Schema):
    code: str


class MemberOut(Schema):
    id: int
    openid: str
    nickname: str
    phone: str
    is_active: bool


class LoginOut(Schema):
    access_token: str
    token_type: str
    expires_in: int
    member: MemberOut


class ProfileIn(Schema):
    nickname: str = ""
    phone: str = ""

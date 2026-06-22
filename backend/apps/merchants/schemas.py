from ninja import Schema


class MerchantTestLoginIn(Schema):
    openid: str


class MerchantOut(Schema):
    id: int
    openid: str
    name: str
    contact_name: str
    phone: str
    address: str
    is_active: bool


class MerchantLoginOut(Schema):
    access_token: str
    token_type: str
    expires_in: int
    merchant: MerchantOut

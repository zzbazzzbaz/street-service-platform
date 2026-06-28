from datetime import datetime

from ninja import Schema


class MerchantWechatLoginIn(Schema):
    openid: str = ""
    code: str = ""


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


class PublicMerchantOut(Schema):
    id: int
    name: str
    contact_name: str
    phone: str
    address: str
    is_active: bool


class PublicMerchantsData(Schema):
    items: list[PublicMerchantOut]
    total: int
    page: int
    page_size: int


class MerchantFixedCodeOut(Schema):
    merchant_id: int
    merchant_name: str
    code_content: str


class MerchantPaymentInfoOut(Schema):
    merchant_id: int
    merchant_name: str
    phone: str
    address: str
    points_per_yuan: int
    balance: int


class MerchantPointPaymentIn(Schema):
    points: int
    request_no: str = ""


class MerchantPointPaymentOut(Schema):
    id: int
    merchant_id: int
    merchant_name: str
    points: int
    yuan_amount: str
    balance_after: int
    request_no: str
    created_at: datetime


class MerchantPointRecordOut(Schema):
    id: int
    merchant_id: int
    merchant_name: str
    member_id: int
    member_name_masked: str
    member_phone_masked: str
    points: int
    yuan_amount: str
    balance_after: int | None = None
    request_no: str
    created_at: datetime


class MerchantPointRecordsData(Schema):
    items: list[MerchantPointRecordOut]
    total: int
    page: int
    page_size: int

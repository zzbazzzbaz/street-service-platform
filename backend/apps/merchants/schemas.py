from ninja import Schema
from datetime import datetime


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


class MerchantFixedCodeOut(Schema):
    merchant_id: int
    merchant_name: str
    qr_payload: str
    qrcode_url: str
    mode: str


class MerchantProductOut(Schema):
    id: int
    merchant_id: int
    merchant_name: str
    name: str
    image: str
    description: str
    points_required: int
    is_active: bool
    created_at: datetime


class MerchantProductsData(Schema):
    items: list[MerchantProductOut]
    total: int
    page: int
    page_size: int


class ProductRedemptionOut(Schema):
    id: int
    merchant_id: int
    merchant_name: str
    product_id: int
    product_name: str
    member_id: int
    member_name_masked: str
    member_phone_masked: str
    points_spent: int
    status: str
    point_record_id: int | None = None
    created_at: datetime


class ProductRedemptionsData(Schema):
    items: list[ProductRedemptionOut]
    total: int
    page: int
    page_size: int


class MerchantRedemptionSummaryOut(Schema):
    month: str
    redemption_count: int
    product_count: int
    points_total: int

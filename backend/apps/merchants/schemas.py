from datetime import datetime

from ninja import Schema


class MerchantWechatLoginIn(Schema):
    openid: str = ""
    code: str = ""


class MerchantWechatPhoneLoginIn(Schema):
    login_code: str = ""
    phone_code: str = ""
    platform: str = "merchant_mp"


class MerchantPasswordLoginIn(Schema):
    username: str
    password: str


class MerchantOut(Schema):
    id: int
    openid: str
    username: str | None = None
    name: str
    contact_name: str
    phone: str
    address: str
    community: str
    merchant_nature: str
    latitude: float | None = None
    longitude: float | None = None
    category_code: str
    business_hours: str
    service_content: str
    audit_status: str
    audit_remark: str
    is_active: bool


class MerchantRegisterIn(Schema):
    shop_name: str
    shop_address: str
    service_content: str
    community: str
    merchant_nature: str
    contact_name: str
    contact_phone: str
    business_hours: str


class MerchantRegisterInfoIn(Schema):
    shop_name: str
    shop_address: str
    service_content: str
    community: str
    merchant_nature: str
    contact_name: str
    business_hours: str
    contact_phone: str = ""


class MerchantLoginOut(Schema):
    access_token: str
    token_type: str
    expires_in: int
    merchant: MerchantOut


class MerchantRegisterOut(MerchantLoginOut):
    need_audit: bool = True


class MerchantPasswordChangeIn(Schema):
    current_password: str
    new_password: str


class PublicMerchantOut(Schema):
    id: int
    name: str
    contact_name: str
    phone: str
    address: str
    latitude: float | None = None
    longitude: float | None = None
    category_code: str
    business_hours: str
    service_content: str
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
    summary: dict | None = None
    total: int
    page: int
    page_size: int


class MerchantSettlementOut(Schema):
    id: int
    period_type: str
    period_label: str
    date_from: str
    date_to: str
    record_count: int
    total_points: int
    total_yuan_amount: str
    status: str
    processed_at: datetime | None = None
    processor_name: str
    remark: str
    created_at: datetime


class MerchantSettlementsData(Schema):
    items: list[MerchantSettlementOut]
    total: int
    page: int
    page_size: int


class MerchantPointCodeOut(Schema):
    id: int
    merchant_id: int
    merchant_name: str
    points: int
    code: str
    code_content: str
    is_active: bool
    remark: str
    created_at: datetime
    updated_at: datetime


class MerchantPointCodePreviewOut(Schema):
    code: str
    merchant_id: int
    merchant_name: str
    points: int
    points_per_yuan: int
    yuan_amount: str
    balance: int


class MerchantPointCodeScanIn(Schema):
    request_no: str = ""


class MerchantPointCodeScanOut(Schema):
    id: int
    merchant_id: int
    merchant_name: str
    points: int
    yuan_amount: str
    balance_after: int
    request_no: str
    created_at: datetime


class MerchantPointCodeItemOut(Schema):
    id: int
    points: int
    code: str
    code_content: str
    remark: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MerchantPointCodesData(Schema):
    items: list[MerchantPointCodeItemOut]

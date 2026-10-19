"""后台账号 / 会员 / 商户 三套 Excel 导入。

统一策略（与《01-账号导入模板字段.md》一致）：

- **整批拒绝**：任何一处问题（格式、文件内重复、与系统冲突）都不写入任何数据，
  返回逐行错误清单，由人工改完再传。
- **不改表结构**：本模块不需要任何 migration。
- **模板按列名匹配**：不依赖列顺序，多余列忽略，缺必填列整包报错。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.members.models import Member
from apps.merchants.models import Merchant
from apps.merchants.services import BUSINESS_HOURS_PATTERN
from shared.excel import (
    IssueCollector,
    SheetRow,
    TemplateColumn,
    build_template_workbook,
    cell_is_blank,
    cell_text,
    is_sane_datetime,
    parse_cell_float,
    parse_cn_bool,
    parse_datetime_text,
    parse_workbook,
)
from shared.exceptions import BusinessError
from shared.passwords import INITIAL_PASSWORD
from shared.validators import PHONE_PATTERN

User = get_user_model()

CN_BOOL_CHOICES = ("是", "否")
YES_NO_HINT = "只能填 是 或 否"


class _PasswordHasher:
    """同一批导入里，每个不同的明文密码只计算一次 PBKDF2。

    Django 默认 PBKDF2-SHA256 是 100 万次迭代、单次约 0.3 秒；500 行逐行
    ``make_password`` 要 2 分钟以上，必然触发网关超时。同批相同明文共用一份
    哈希（salt 也相同）不会降低安全性：这批账号本来就是同一个初始密码，
    而且首次登录强制改密。
    """

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def hash(self, raw: str) -> str:
        if raw not in self._cache:
            self._cache[raw] = make_password(raw)
        return self._cache[raw]


class _RowFailures:
    """单行的问题收集器：任一处不合格，这一行就不入库。"""

    __slots__ = ("issues", "ok", "row")

    def __init__(self, issues: IssueCollector, row: int) -> None:
        self.issues = issues
        self.row = row
        self.ok = True

    def add(self, column: str, value: Any, message: str) -> None:
        self.ok = False
        self.issues.add(self.row, column, value, message)


def _backfill_created_at(model, pairs: Sequence[tuple[int, datetime | None]]) -> None:
    """``created_at`` 是 auto_now_add，bulk_create 只能写成"当前时间"，需要回填。"""
    grouped: dict[datetime, list[int]] = {}
    for pk, created_at in pairs:
        if pk and created_at is not None:
            grouped.setdefault(created_at, []).append(pk)
    for created_at, pks in grouped.items():
        model.objects.filter(pk__in=pks).update(created_at=created_at)


def _import_result(imported: int, *, noun: str) -> dict:
    return {
        "imported": imported,
        "message": f"导入成功，共新增 {imported} 个{noun}",
    }


# ---------------------------------------------------------------------------
# 会员导入
# ---------------------------------------------------------------------------


MEMBER_COLUMNS: tuple[TemplateColumn, ...] = (
    TemplateColumn(
        "手机号",
        required=True,
        example="13800138000",
        note="11 位手机号，同时作为登录用户名；文件内不能重复，系统里也不能已存在；初始密码 000000",
    ),
    TemplateColumn("姓名", required=True, example="张三", note="2-10 个字"),
    TemplateColumn("性别", required=True, kind="choice", choices=tuple(Member.Gender.values), example="男"),
    TemplateColumn(
        "职业",
        required=True,
        kind="choice",
        choices=tuple(Member.Occupation.values),
        example="美团快递",
    ),
    TemplateColumn("住址", required=True, example="西城区东松树10号", note="最多 255 字"),
    TemplateColumn("是否党员", required=True, kind="choice", choices=CN_BOOL_CHOICES, example="否"),
    TemplateColumn("昵称", example="张三", note="选填，最多 64 字；留空则与姓名相同"),
    TemplateColumn("微信号", example="zhangsan_wx", note="选填，最多 64 字"),
    TemplateColumn(
        "注册时间",
        example="2026-01-01 09:00:00",
        note="选填，格式 YYYY-MM-DD HH:MM:SS；留空则用导入时间",
    ),
)
MEMBER_REQUIRED_COLUMNS = tuple(column.header for column in MEMBER_COLUMNS if column.required)
MEMBER_KNOWN_COLUMNS = tuple(column.header for column in MEMBER_COLUMNS)
MEMBER_TEMPLATE_NOTES = (
    "导入的会员一律是「审核通过」状态，可以直接登录小程序。",
    "初始密码统一是 000000，首次登录会要求修改密码。",
    "手机号列已锁定为文本格式，请直接输入 11 位数字，不要用公式或空格。",
    "只要有一行不合格，整批都会被驳回，不会有部分数据写入。",
)


@dataclass
class _MemberDraft:
    row: int
    phone: str
    real_name: str
    gender: str
    occupation: str
    address: str
    is_party_member: bool
    nickname: str
    wechat_id: str
    created_at: datetime | None


def member_import_template() -> bytes:
    return build_template_workbook(
        sheet_title="会员导入",
        columns=MEMBER_COLUMNS,
        notes=MEMBER_TEMPLATE_NOTES,
    )


def _build_member_drafts(rows: Sequence[SheetRow], issues: IssueCollector) -> list[_MemberDraft]:
    drafts: list[_MemberDraft] = []
    seen_phones: dict[str, int] = {}

    for row in rows:
        values = row.values
        failures = _RowFailures(issues, row.number)

        phone = cell_text(values.get("手机号"))
        real_name = cell_text(values.get("姓名"))
        gender = cell_text(values.get("性别"))
        occupation = cell_text(values.get("职业"))
        address = cell_text(values.get("住址"))
        party_raw = values.get("是否党员")
        nickname = cell_text(values.get("昵称"))
        wechat_id = cell_text(values.get("微信号"))
        created_raw = values.get("注册时间")

        if not phone:
            failures.add("手机号", phone, "手机号不能为空")
        elif not PHONE_PATTERN.match(phone):
            failures.add("手机号", phone, "手机号格式不正确（11 位、1 开头）")
        elif phone in seen_phones:
            failures.add("手机号", phone, f"手机号与第 {seen_phones[phone]} 行重复")
        else:
            seen_phones[phone] = row.number

        if not real_name:
            failures.add("姓名", real_name, "姓名不能为空")
        elif not 2 <= len(real_name) <= 10:
            failures.add("姓名", real_name, "姓名需为 2-10 个字")

        if not gender:
            failures.add("性别", gender, "性别不能为空")
        elif gender not in Member.Gender.values:
            failures.add("性别", gender, "性别只能填 男 或 女")

        if not occupation:
            failures.add("职业", occupation, "职业不能为空")
        elif occupation not in Member.Occupation.values:
            failures.add("职业", occupation, f"职业只能填：{' / '.join(Member.Occupation.values)}")

        if not address:
            failures.add("住址", address, "住址不能为空")
        elif len(address) > 255:
            failures.add("住址", address, "住址最多 255 字")

        is_party_member = parse_cn_bool(party_raw)
        if cell_is_blank(party_raw):
            failures.add("是否党员", party_raw, "是否党员不能为空")
        elif is_party_member is None:
            failures.add("是否党员", party_raw, f"是否党员{YES_NO_HINT}")

        if len(nickname) > 64:
            failures.add("昵称", nickname, "昵称最多 64 字")
        if len(wechat_id) > 64:
            failures.add("微信号", wechat_id, "微信号最多 64 字")

        created_at: datetime | None = None
        if not cell_is_blank(created_raw):
            created_at = parse_datetime_text(created_raw)
            if created_at is None:
                failures.add("注册时间", created_raw, "注册时间格式应为 YYYY-MM-DD HH:MM:SS")
            elif not is_sane_datetime(created_at):
                failures.add("注册时间", created_raw, "注册时间不合理，请检查是否填成了 Excel 日期序列号")
                created_at = None

        if failures.ok:
            drafts.append(
                _MemberDraft(
                    row=row.number,
                    phone=phone,
                    real_name=real_name,
                    gender=gender,
                    occupation=occupation,
                    address=address,
                    is_party_member=bool(is_party_member),
                    nickname=nickname,
                    wechat_id=wechat_id,
                    created_at=created_at,
                )
            )
    return drafts


def _member_conflict_message(member: Member) -> str:
    display = member.real_name or member.nickname or member.username or f"ID {member.id}"
    status_label = dict(Member.AuditStatus.choices).get(member.audit_status, member.audit_status)
    created = timezone.localtime(member.created_at).strftime("%Y-%m-%d") if member.created_at else "未知时间"
    return f"该手机号已存在（会员「{display}」，{status_label}，{created} 注册）"


def _check_member_conflicts(drafts: Sequence[_MemberDraft], issues: IssueCollector) -> None:
    if not drafts:
        return
    phones = [draft.phone for draft in drafts]
    phone_set = set(phones)
    existing = Member.objects.filter(Q(phone__in=phones) | Q(username__in=phones))
    matched: dict[str, Member] = {}
    for member in existing:
        for key in (member.phone, member.username):
            if key and key in phone_set and key not in matched:
                matched[key] = member
    for draft in drafts:
        member = matched.get(draft.phone)
        if member is not None:
            issues.add(draft.row, "手机号", draft.phone, _member_conflict_message(member))


def import_members(uploaded_file) -> dict:
    rows = parse_workbook(
        uploaded_file,
        required_columns=MEMBER_REQUIRED_COLUMNS,
        known_columns=MEMBER_KNOWN_COLUMNS,
    )
    issues = IssueCollector()
    drafts = _build_member_drafts(rows, issues)
    if drafts:
        _check_member_conflicts(drafts, issues)
    issues.raise_if_any(noun="会员")

    hasher = _PasswordHasher()
    password = hasher.hash(INITIAL_PASSWORD)
    imported_at = timezone.now()
    objects = [
        Member(
            openid=None,
            username=draft.phone,
            password=password,
            nickname=draft.nickname or draft.real_name,
            phone=draft.phone,
            real_name=draft.real_name,
            wechat_id=draft.wechat_id,
            gender=draft.gender,
            occupation=draft.occupation,
            is_party_member=draft.is_party_member,
            address=draft.address,
            audit_status=Member.AuditStatus.APPROVED,
            audit_remark="",
            audit_submitted_at=draft.created_at or imported_at,
            is_active=True,
        )
        for draft in drafts
    ]

    try:
        with transaction.atomic():
            created = Member.objects.bulk_create(objects, batch_size=200)
            _backfill_created_at(
                Member,
                [(obj.pk, draft.created_at) for obj, draft in zip(created, drafts)],
            )
    except IntegrityError as exc:
        raise BusinessError("导入失败：手机号与系统内已有账号冲突，请重新下载模板核对后重试") from exc

    return _import_result(len(created), noun="会员")


# ---------------------------------------------------------------------------
# 商户导入
# ---------------------------------------------------------------------------


MERCHANT_CATEGORY_BY_LABEL = {label: value for value, label in Merchant.CategoryCode.choices}

MERCHANT_COLUMNS: tuple[TemplateColumn, ...] = (
    TemplateColumn("店铺名称", required=True, example="便民超市", note="最多 100 字"),
    TemplateColumn("联系人", required=True, example="王店长", note="最多 50 字"),
    TemplateColumn(
        "联系电话",
        required=True,
        example="13900139000",
        note="手机号或座机号都行，最长 20 个字符；不校验格式；文件内和系统内都不能重复",
    ),
    TemplateColumn(
        "商户分类",
        required=True,
        kind="choice",
        choices=tuple(label for _, label in Merchant.CategoryCode.choices),
        example="零售商超",
    ),
    TemplateColumn("经营地址", example="西城区东松树10号", note="选填，最多 255 字"),
    TemplateColumn("所属社区", example="东松树社区", note="选填，最多 100 字"),
    TemplateColumn("商户性质", example="个体工商户", note="选填，最多 100 字"),
    TemplateColumn("营业时间", example="08:00-20:00", note="选填，格式 HH:MM-HH:MM，结束时间要晚于开始时间"),
    TemplateColumn("服务内容", example="日用百货、粮油副食", note="选填，最多 500 字"),
    TemplateColumn("纬度", example="39.910000", note="选填，-90 ~ 90；留空则与经度一起留空"),
    TemplateColumn("经度", example="116.380000", note="选填，-180 ~ 180；留空则与纬度一起留空"),
    TemplateColumn(
        "登录用户名",
        example="",
        note="选填，最多 64 字符；不填则商户只能用微信手机号登录；填了则「初始密码」必填",
    ),
    TemplateColumn("初始密码", example="", note="选填，至少 6 位；填了「登录用户名」就必填；建议统一 000000"),
)
MERCHANT_REQUIRED_COLUMNS = tuple(column.header for column in MERCHANT_COLUMNS if column.required)
MERCHANT_KNOWN_COLUMNS = tuple(column.header for column in MERCHANT_COLUMNS)
MERCHANT_TEMPLATE_NOTES = (
    "导入的商户一律是「审核通过 + 已启用」状态。",
    "联系电话必填，手机号或座机号都可以、不校验格式；商户用手机号做微信登录时，账号必须先在系统里存在。",
    "「登录用户名 / 初始密码」是备用通道，可以不填；填了初始密码建议统一用 000000，首次登录会要求改密。",
    "只要有一行不合格，整批都会被驳回，不会有部分数据写入。",
)


@dataclass
class _MerchantDraft:
    row: int
    name: str
    contact_name: str
    phone: str
    category_code: str
    address: str
    community: str
    merchant_nature: str
    business_hours: str
    service_content: str
    latitude: float | None
    longitude: float | None
    username: str
    password: str


def merchant_import_template() -> bytes:
    return build_template_workbook(
        sheet_title="商户导入",
        columns=MERCHANT_COLUMNS,
        notes=MERCHANT_TEMPLATE_NOTES,
    )


def _duplicate_key_message(column: str, previous_row: int, previous_column: str) -> str:
    if previous_column == column:
        return f"{column}与第 {previous_row} 行重复"
    return f"{column}与第 {previous_row} 行的{previous_column}重复"


def _clean_import_business_hours(text: str) -> tuple[str, str | None]:
    if not text:
        return "", None
    match = BUSINESS_HOURS_PATTERN.match(text)
    if match is None:
        return "", "营业时间格式必须为 HH:MM-HH:MM（24 小时制）"
    start_hour, start_minute, end_hour, end_minute = (int(part) for part in match.groups())
    if end_hour * 60 + end_minute <= start_hour * 60 + start_minute:
        return "", "营业时间结束时间必须晚于开始时间"
    return text, None


def _build_merchant_drafts(rows: Sequence[SheetRow], issues: IssueCollector) -> list[_MerchantDraft]:
    drafts: list[_MerchantDraft] = []
    # 联系电话和登录用户名共用一张表：商户侧两者都不能互相撞号（与 validate_merchant_phone 一致）
    seen_keys: dict[str, tuple[int, str]] = {}

    for row in rows:
        values = row.values
        failures = _RowFailures(issues, row.number)

        name = cell_text(values.get("店铺名称"))
        contact_name = cell_text(values.get("联系人"))
        phone = cell_text(values.get("联系电话"))
        category_label = cell_text(values.get("商户分类"))
        address = cell_text(values.get("经营地址"))
        community = cell_text(values.get("所属社区"))
        merchant_nature = cell_text(values.get("商户性质"))
        business_hours_raw = cell_text(values.get("营业时间"))
        service_content = cell_text(values.get("服务内容"))
        latitude_raw = values.get("纬度")
        longitude_raw = values.get("经度")
        username = cell_text(values.get("登录用户名"))
        password = cell_text(values.get("初始密码"))

        if not name:
            failures.add("店铺名称", name, "店铺名称不能为空")
        elif len(name) > 100:
            failures.add("店铺名称", name, "店铺名称最多 100 字")

        if not contact_name:
            failures.add("联系人", contact_name, "联系人不能为空")
        elif len(contact_name) > 50:
            failures.add("联系人", contact_name, "联系人最多 50 字")

        if not phone:
            failures.add("联系电话", phone, "联系电话不能为空")
        elif len(phone) > 20:
            failures.add("联系电话", phone, "联系电话最长 20 个字符")
        else:
            previous = seen_keys.get(phone)
            if previous is not None and previous[0] != row.number:
                failures.add("联系电话", phone, _duplicate_key_message("联系电话", *previous))
            else:
                seen_keys[phone] = (row.number, "联系电话")

        category_code = MERCHANT_CATEGORY_BY_LABEL.get(category_label, "")
        if not category_label:
            failures.add("商户分类", category_label, "商户分类不能为空")
        elif not category_code:
            failures.add("商户分类", category_label, f"商户分类只能填：{' / '.join(MERCHANT_CATEGORY_BY_LABEL)}")

        if len(address) > 255:
            failures.add("经营地址", address, "经营地址最多 255 字")
        if len(community) > 100:
            failures.add("所属社区", community, "所属社区最多 100 字")
        if len(merchant_nature) > 100:
            failures.add("商户性质", merchant_nature, "商户性质最多 100 字")
        if len(service_content) > 500:
            failures.add("服务内容", service_content, "服务内容最多 500 字")

        business_hours, hours_error = _clean_import_business_hours(business_hours_raw)
        if hours_error:
            failures.add("营业时间", business_hours_raw, hours_error)

        latitude = parse_cell_float(latitude_raw)
        longitude = parse_cell_float(longitude_raw)
        lat_blank = cell_is_blank(latitude_raw)
        lng_blank = cell_is_blank(longitude_raw)
        if not lat_blank and latitude is None:
            failures.add("纬度", latitude_raw, "纬度必须是数字")
        if not lng_blank and longitude is None:
            failures.add("经度", longitude_raw, "经度必须是数字")
        if lat_blank != lng_blank:
            failures.add("纬度", latitude_raw, "纬度和经度必须同时填写或同时留空")
        elif latitude is not None and longitude is not None:
            if not -90 <= latitude <= 90:
                failures.add("纬度", latitude_raw, "纬度范围为 -90 ~ 90")
            if not -180 <= longitude <= 180:
                failures.add("经度", longitude_raw, "经度范围为 -180 ~ 180")

        if username:
            if len(username) > 64:
                failures.add("登录用户名", username, "登录用户名最多 64 字符")
            else:
                previous = seen_keys.get(username)
                if previous is not None and previous[0] != row.number:
                    failures.add("登录用户名", username, _duplicate_key_message("登录用户名", *previous))
                else:
                    seen_keys[username] = (row.number, "登录用户名")

        if username and not password:
            failures.add("初始密码", password, "填写了登录用户名就必须填写初始密码")
        if password and not username:
            failures.add("登录用户名", username, "填写了初始密码就必须填写登录用户名")
        if password and len(password) < 6:
            failures.add("初始密码", password, "初始密码长度至少 6 位")

        if failures.ok:
            drafts.append(
                _MerchantDraft(
                    row=row.number,
                    name=name,
                    contact_name=contact_name,
                    phone=phone,
                    category_code=category_code,
                    address=address,
                    community=community,
                    merchant_nature=merchant_nature,
                    business_hours=business_hours,
                    service_content=service_content,
                    latitude=latitude if not lat_blank else None,
                    longitude=longitude if not lng_blank else None,
                    username=username,
                    password=password,
                )
            )
    return drafts


def _merchant_conflict_message(merchant: Merchant, *, column: str) -> str:
    status_label = dict(Merchant.AuditStatus.choices).get(merchant.audit_status, merchant.audit_status)
    if column == "联系电话":
        return f"该手机号已被商户「{merchant.name}」使用（{status_label}）"
    return f"该用户名已被商户「{merchant.name}」使用（{status_label}）"


def _check_merchant_conflicts(drafts: Sequence[_MerchantDraft], issues: IssueCollector) -> None:
    if not drafts:
        return
    values: set[str] = set()
    for draft in drafts:
        values.add(draft.phone)
        if draft.username:
            values.add(draft.username)
    if not values:
        return
    value_list = list(values)
    existing = Merchant.objects.filter(Q(phone__in=value_list) | Q(username__in=value_list))
    matched: dict[str, Merchant] = {}
    for merchant in existing:
        for key in (merchant.phone, merchant.username):
            if key and key in values and key not in matched:
                matched[key] = merchant
    for draft in drafts:
        conflict = matched.get(draft.phone)
        if conflict is not None:
            issues.add(draft.row, "联系电话", draft.phone, _merchant_conflict_message(conflict, column="联系电话"))
        if draft.username:
            conflict = matched.get(draft.username)
            if conflict is not None:
                issues.add(
                    draft.row,
                    "登录用户名",
                    draft.username,
                    _merchant_conflict_message(conflict, column="登录用户名"),
                )


def import_merchants(uploaded_file) -> dict:
    rows = parse_workbook(
        uploaded_file,
        required_columns=MERCHANT_REQUIRED_COLUMNS,
        known_columns=MERCHANT_KNOWN_COLUMNS,
    )
    issues = IssueCollector()
    drafts = _build_merchant_drafts(rows, issues)
    if drafts:
        _check_merchant_conflicts(drafts, issues)
    issues.raise_if_any(noun="商户")

    hasher = _PasswordHasher()
    objects = [
        Merchant(
            openid=None,
            username=draft.username or None,
            password=hasher.hash(draft.password) if draft.username else "",
            name=draft.name,
            contact_name=draft.contact_name,
            phone=draft.phone,
            address=draft.address,
            community=draft.community,
            merchant_nature=draft.merchant_nature,
            latitude=draft.latitude,
            longitude=draft.longitude,
            category_code=draft.category_code,
            business_hours=draft.business_hours,
            service_content=draft.service_content,
            audit_status=Merchant.AuditStatus.APPROVED,
            audit_remark="",
            is_active=True,
        )
        for draft in drafts
    ]

    try:
        with transaction.atomic():
            created = Merchant.objects.bulk_create(objects, batch_size=200)
    except IntegrityError as exc:
        raise BusinessError("导入失败：联系电话或用户名与系统内已有商户冲突，请重新下载模板核对后重试") from exc

    return _import_result(len(created), noun="商户")


# ---------------------------------------------------------------------------
# 后台账号导入
# ---------------------------------------------------------------------------


ADMIN_USER_COLUMNS: tuple[TemplateColumn, ...] = (
    TemplateColumn("登录用户名", required=True, example="yangning", note="最多 150 字符；文件内和系统内都不能重复"),
    TemplateColumn("姓名", required=True, example="杨宁", note="最多 150 字符"),
    TemplateColumn("初始密码", required=True, example="000000", note="至少 6 位；建议统一 000000，首次登录会要求改密"),
    TemplateColumn("邮箱", example="yangning@example.com", note="选填，需要符合邮箱格式"),
    TemplateColumn("是否启用", required=True, kind="choice", choices=CN_BOOL_CHOICES, example="是"),
)
ADMIN_USER_REQUIRED_COLUMNS = tuple(column.header for column in ADMIN_USER_COLUMNS if column.required)
ADMIN_USER_KNOWN_COLUMNS = tuple(column.header for column in ADMIN_USER_COLUMNS)
ADMIN_USER_TEMPLATE_NOTES = (
    "导入的后台账号一律具备「业务管理员」权限，可以登录管理端。",
    "「姓名」会写进账号的姓氏之外的姓名字段（first_name），登录后的显示名就是这个。",
    "初始密码建议统一 000000，首次登录会要求修改密码。",
    "只要有一行不合格，整批都会被驳回，不会有部分数据写入。",
)


@dataclass
class _AdminUserDraft:
    row: int
    username: str
    first_name: str
    password: str
    email: str
    is_active: bool


def admin_user_import_template() -> bytes:
    return build_template_workbook(
        sheet_title="后台账号导入",
        columns=ADMIN_USER_COLUMNS,
        notes=ADMIN_USER_TEMPLATE_NOTES,
    )


def _build_admin_user_drafts(rows: Sequence[SheetRow], issues: IssueCollector) -> list[_AdminUserDraft]:
    drafts: list[_AdminUserDraft] = []
    seen_usernames: dict[str, int] = {}

    for row in rows:
        values = row.values
        failures = _RowFailures(issues, row.number)

        username = cell_text(values.get("登录用户名"))
        first_name = cell_text(values.get("姓名"))
        password = cell_text(values.get("初始密码"))
        email = cell_text(values.get("邮箱"))
        active_raw = values.get("是否启用")

        if not username:
            failures.add("登录用户名", username, "登录用户名不能为空")
        elif len(username) > 150:
            failures.add("登录用户名", username, "登录用户名最多 150 字符")
        elif username in seen_usernames:
            failures.add("登录用户名", username, f"登录用户名与第 {seen_usernames[username]} 行重复")
        else:
            seen_usernames[username] = row.number

        if not first_name:
            failures.add("姓名", first_name, "姓名不能为空")
        elif len(first_name) > 150:
            failures.add("姓名", first_name, "姓名最多 150 字符")

        if not password:
            failures.add("初始密码", password, "初始密码不能为空")
        elif len(password) < 6:
            failures.add("初始密码", password, "初始密码长度至少 6 位")

        if email:
            try:
                validate_email(email)
            except DjangoValidationError:
                failures.add("邮箱", email, "邮箱格式不正确")

        is_active = parse_cn_bool(active_raw)
        if cell_is_blank(active_raw):
            failures.add("是否启用", active_raw, "是否启用不能为空")
        elif is_active is None:
            failures.add("是否启用", active_raw, f"是否启用{YES_NO_HINT}")

        if failures.ok:
            drafts.append(
                _AdminUserDraft(
                    row=row.number,
                    username=username,
                    first_name=first_name,
                    password=password,
                    email=email,
                    is_active=bool(is_active),
                )
            )
    return drafts


def _check_admin_user_conflicts(drafts: Sequence[_AdminUserDraft], issues: IssueCollector) -> None:
    if not drafts:
        return
    usernames = [draft.username for draft in drafts]
    existing = {user.username for user in User.objects.filter(username__in=usernames)}
    for draft in drafts:
        if draft.username in existing:
            issues.add(draft.row, "登录用户名", draft.username, "该登录用户名已存在，请换一个")


def import_admin_users(uploaded_file) -> dict:
    rows = parse_workbook(
        uploaded_file,
        required_columns=ADMIN_USER_REQUIRED_COLUMNS,
        known_columns=ADMIN_USER_KNOWN_COLUMNS,
    )
    issues = IssueCollector()
    drafts = _build_admin_user_drafts(rows, issues)
    if drafts:
        _check_admin_user_conflicts(drafts, issues)
    issues.raise_if_any(noun="后台账号")

    hasher = _PasswordHasher()
    objects = [
        User(
            username=draft.username,
            password=hasher.hash(draft.password),
            email=draft.email,
            first_name=draft.first_name,
            last_name="",
            is_backend_manager=True,
            # bulk_create 不会调用 User.save()，is_staff 的联动必须显式写死
            is_staff=True,
            is_active=draft.is_active,
            is_superuser=False,
        )
        for draft in drafts
    ]

    try:
        with transaction.atomic():
            created = User.objects.bulk_create(objects, batch_size=200)
    except IntegrityError as exc:
        raise BusinessError("导入失败：登录用户名与系统内已有账号冲突，请重新下载模板核对后重试") from exc

    return _import_result(len(created), noun="后台账号")

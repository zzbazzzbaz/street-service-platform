"""Excel 导入解析与模板生成的通用工具。

约定：

- 上传文件仅支持 ``.xlsx``，≤ 2MB，≤ 500 行数据。
- 表头固定在第 1 行，按「列名」匹配，不依赖列顺序；多余列忽略，缺必填列整包报错。
- 行号一律使用 Excel 实际行号（表头 = 1，数据从 2 开始），不要用数组下标。
- 单元格统一走 :func:`cell_text` 归一化，兼容数字型/日期型单元格。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Any

from django.utils import timezone
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from shared.exceptions import BusinessError

MAX_IMPORT_FILE_SIZE = 2 * 1024 * 1024
MAX_IMPORT_ROWS = 500
MAX_ISSUE_COUNT = 200
MAX_ISSUE_VALUE_LENGTH = 50

EXCEL_TEXT_FORMAT = "@"
TEMPLATE_DATA_SHEET_TITLE = "导入数据"
TEMPLATE_HELP_SHEET_TITLE = "填写说明"

_HEADER_FILL = PatternFill("solid", fgColor="DDEBF7")
_HEADER_FONT = Font(bold=True)
_HELP_HEADERS = ("列名", "是否必填", "填写说明", "示例")

_TRUE_WORDS = {"是", "true", "yes", "y", "1", "对", "有"}
_FALSE_WORDS = {"否", "false", "no", "n", "0", "无"}

_DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d",
)


@dataclass(frozen=True)
class SheetRow:
    """一行数据；``number`` 是 Excel 实际行号。"""

    number: int
    values: dict[str, Any]


@dataclass
class IssueCollector:
    """收集整批校验问题，最后一次性抛出（整批拒绝）。"""

    items: list[dict] = field(default_factory=list)
    truncated: int = 0

    def add(self, row: int, column: str, value: Any, message: str) -> None:
        if len(self.items) >= MAX_ISSUE_COUNT:
            self.truncated += 1
            return
        text = cell_text(value)
        if len(text) > MAX_ISSUE_VALUE_LENGTH:
            text = f"{text[:MAX_ISSUE_VALUE_LENGTH]}…"
        self.items.append({"row": row, "column": column, "value": text, "message": message})

    @property
    def total(self) -> int:
        return len(self.items) + self.truncated

    @property
    def has_issues(self) -> bool:
        return self.total > 0

    def raise_if_any(self, *, noun: str = "数据") -> None:
        if not self.has_issues:
            return
        message = f"校验未通过，共 {self.total} 处问题，已全部驳回，未写入任何{noun}"
        if self.truncated:
            message += f"（仅展示前 {MAX_ISSUE_COUNT} 条）"
        raise BusinessError(message, errors=self.items)


def cell_is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip().strip("\u3000").strip()
    return False


def cell_text(value: Any) -> str:
    """把单元格值归一化成去空白的字符串，兼容数字/日期型单元格。"""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, str):
        return value.strip().strip("\u3000").strip()
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:g}"
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return str(int(value))
        return f"{value:g}"
    return str(value).strip()


def parse_cn_bool(value: Any) -> bool | None:
    """解析「是 / 否」列；空值返回 ``None``。"""
    text = cell_text(value)
    if not text:
        return None
    lowered = text.lower()
    if lowered in _TRUE_WORDS:
        return True
    if lowered in _FALSE_WORDS:
        return False
    return None


def parse_cell_float(value: Any) -> float | None:
    text = cell_text(value)
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def parse_datetime_text(value: Any) -> datetime | None:
    """解析 ``YYYY-MM-DD[ HH:MM[:SS]]``，返回带时区的 datetime；空值返回 ``None``。

    模板里推荐 ``YYYY-MM-DD HH:MM:SS``，同时容忍 ISO 写法（``2026-03-01T10:30:00``、
    带 ``+08:00`` 偏移）、``2026/03/01`` 以及省略秒/时分。没有时区的一律按
    ``settings.TIME_ZONE``（Asia/Shanghai）解释。
    """
    text = cell_text(value)
    if not text:
        return None
    parsed = _parse_iso_datetime(text)
    if parsed is None:
        for fmt in _DATETIME_FORMATS:
            try:
                parsed = datetime.strptime(text, fmt)  # noqa: DTZ007 - 紧接着按 TIME_ZONE 补时区
            except ValueError:
                continue
            break
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


def _parse_iso_datetime(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def is_sane_datetime(value: datetime, *, earliest_year: int = 2000) -> bool:
    if value.year < earliest_year:
        return False
    return value <= timezone.now() + timedelta(days=1)


def parse_workbook(
    uploaded_file,
    *,
    required_columns: Sequence[str],
    known_columns: Sequence[str],
    max_rows: int = MAX_IMPORT_ROWS,
) -> list[SheetRow]:
    """读取上传的 ``.xlsx`` 首个工作表，返回按列名索引的数据行。"""
    filename = (getattr(uploaded_file, "name", "") or "").strip()
    if not filename.lower().endswith(".xlsx"):
        raise BusinessError(
            "只支持 .xlsx 格式，请使用下载的模板填写",
            errors=[{"row": 1, "column": "文件", "value": filename, "message": "只支持 .xlsx 格式"}],
        )
    size = getattr(uploaded_file, "size", 0) or 0
    if size <= 0:
        raise BusinessError(
            "上传的文件是空的",
            errors=[{"row": 1, "column": "文件", "value": filename, "message": "文件内容为空"}],
        )
    if size > MAX_IMPORT_FILE_SIZE:
        raise BusinessError(
            f"文件不能超过 {MAX_IMPORT_FILE_SIZE // 1024 // 1024}MB",
            errors=[{"row": 1, "column": "文件", "value": filename, "message": f"文件超过 {MAX_IMPORT_FILE_SIZE} 字节"}],
        )

    try:
        raw = uploaded_file.read()
    except Exception as exc:  # pragma: no cover - 读取失败属于环境问题
        raise BusinessError("文件读取失败，请重新上传") from exc

    try:
        workbook = load_workbook(BytesIO(raw), data_only=True, read_only=True)
    except Exception as exc:
        raise BusinessError(
            "文件无法解析，请确认是通过模板填写并另存为 .xlsx 格式",
            errors=[{"row": 1, "column": "文件", "value": filename, "message": "文件不是有效的 .xlsx"}],
        ) from exc

    try:
        worksheet = workbook.worksheets[0]
        raw_rows = list(worksheet.iter_rows(values_only=True))
    finally:
        workbook.close()

    if not raw_rows:
        raise BusinessError(
            "模板里没有表头",
            errors=[{"row": 1, "column": "表头", "value": "", "message": "模板缺少表头行"}],
        )

    header_index: dict[str, int] = {}
    for index, header in enumerate(raw_rows[0]):
        name = cell_text(header)
        if name and name not in header_index:
            header_index[name] = index

    missing = [column for column in required_columns if column not in header_index]
    if missing:
        raise BusinessError(
            f"模板缺少必填列：{'、'.join(missing)}",
            errors=[{"row": 1, "column": column, "value": "", "message": "模板缺少该列"} for column in missing],
        )

    allowed = set(known_columns)
    rows: list[SheetRow] = []
    for offset, raw_row in enumerate(raw_rows[1:]):
        if all(cell_is_blank(value) for value in raw_row):
            continue
        values = {
            name: raw_row[index] if index < len(raw_row) else None
            for name, index in header_index.items()
            if name in allowed
        }
        rows.append(SheetRow(number=offset + 2, values=values))

    if not rows:
        raise BusinessError(
            "模板里没有数据行，请填写后再上传",
            errors=[{"row": 2, "column": "数据", "value": "", "message": "没有可导入的数据行"}],
        )
    if len(rows) > max_rows:
        raise BusinessError(
            f"单次最多导入 {max_rows} 行，当前 {len(rows)} 行，请拆分后重试",
            errors=[{"row": 2, "column": "数据", "value": str(len(rows)), "message": f"超过 {max_rows} 行"}],
        )
    return rows


@dataclass(frozen=True)
class TemplateColumn:
    header: str
    required: bool = False
    kind: str = "text"
    choices: tuple[str, ...] = ()
    example: str = ""
    note: str = ""


def build_template_workbook(
    *,
    sheet_title: str,
    columns: Sequence[TemplateColumn],
    notes: Sequence[str] = (),
    max_rows: int = MAX_IMPORT_ROWS,
) -> bytes:
    """生成导入模板：主 sheet 只有表头，示例与说明放第二个 sheet。"""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_title or TEMPLATE_DATA_SHEET_TITLE

    for index, column in enumerate(columns, start=1):
        letter = get_column_letter(index)
        header_cell = sheet.cell(row=1, column=index, value=column.header)
        header_cell.font = _HEADER_FONT
        header_cell.fill = _HEADER_FILL
        header_cell.alignment = Alignment(horizontal="center", vertical="center")

        dimension = sheet.column_dimensions[letter]
        dimension.width = max(12, min(30, len(column.header) * 2 + 8))
        if column.kind in {"text", "choice"}:
            # 锁定为文本格式，避免手机号变成 1.38722E+10、日期变成序列号
            dimension.number_format = EXCEL_TEXT_FORMAT

        if column.kind == "choice" and column.choices:
            validation = DataValidation(
                type="list",
                formula1=f'"{",".join(column.choices)}"',
                allow_blank=not column.required,
                showErrorMessage=True,
                errorTitle="输入有误",
                error=f"{column.header}只能填：{' / '.join(column.choices)}",
            )
            sheet.add_data_validation(validation)
            validation.add(f"{letter}2:{letter}{max_rows + 1}")

    sheet.freeze_panes = "A2"

    help_sheet = workbook.create_sheet(TEMPLATE_HELP_SHEET_TITLE)
    help_sheet.append(list(_HELP_HEADERS))
    for cell in help_sheet[1]:
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
    for column in columns:
        requirement = "必填" if column.required else "选填"
        description = column.note
        if column.kind == "choice" and column.choices:
            options = " / ".join(column.choices)
            description = f"{description}（可选值：{options}）" if description else f"可选值：{options}"
        help_sheet.append([column.header, requirement, description, column.example])
    for index, width in enumerate((18, 8, 62, 26), start=1):
        help_sheet.column_dimensions[get_column_letter(index)].width = width
        help_sheet.column_dimensions[get_column_letter(index)].number_format = EXCEL_TEXT_FORMAT

    if notes:
        help_sheet.append([])
        help_sheet.append(["填写须知"])
        help_sheet.cell(row=help_sheet.max_row, column=1).font = _HEADER_FONT
        for note in notes:
            help_sheet.append([note])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()

from datetime import UTC, datetime
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.utils import timezone
from openpyxl import Workbook, load_workbook

from shared.excel import (
    MAX_ISSUE_COUNT,
    IssueCollector,
    TemplateColumn,
    build_template_workbook,
    cell_is_blank,
    cell_text,
    parse_cell_float,
    parse_cn_bool,
    parse_datetime_text,
    parse_workbook,
)
from shared.exceptions import BusinessError

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def build_upload(headers, rows, *, filename="导入.xlsx") -> SimpleUploadedFile:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(headers))
    for row in rows:
        sheet.append(list(row))
    buffer = BytesIO()
    workbook.save(buffer)
    return SimpleUploadedFile(filename, buffer.getvalue(), content_type=XLSX_CONTENT_TYPE)


class CellNormalizationTests(SimpleTestCase):
    def test_cell_text_handles_excel_value_types(self):
        self.assertEqual(cell_text(None), "")
        self.assertEqual(cell_text("  张三  "), "张三")
        self.assertEqual(cell_text("\u3000李四\u3000"), "李四")
        self.assertEqual(cell_text(13800138000), "13800138000")
        self.assertEqual(cell_text(13800138000.0), "13800138000")
        self.assertEqual(cell_text(True), "是")
        self.assertEqual(cell_text(False), "否")
        self.assertEqual(cell_text(datetime(2026, 3, 1, 10, 30, 0, tzinfo=UTC)), "2026-03-01 10:30:00")

    def test_cell_is_blank_treats_whitespace_as_blank(self):
        self.assertTrue(cell_is_blank(None))
        self.assertTrue(cell_is_blank("   "))
        self.assertFalse(cell_is_blank("0"))

    def test_parse_cn_bool(self):
        self.assertIs(parse_cn_bool("是"), True)
        self.assertIs(parse_cn_bool("否"), False)
        self.assertIs(parse_cn_bool("TRUE"), True)
        self.assertIsNone(parse_cn_bool(""))
        self.assertIsNone(parse_cn_bool("未知"))

    def test_parse_cell_float(self):
        self.assertEqual(parse_cell_float("39.91"), 39.91)
        self.assertEqual(parse_cell_float(116), 116.0)
        self.assertIsNone(parse_cell_float(""))
        self.assertIsNone(parse_cell_float("东经116"))

    def test_parse_datetime_text_supports_common_formats(self):
        def normalized(text):
            parsed = parse_datetime_text(text)
            return parsed.strftime("%Y-%m-%d %H:%M:%S") if parsed else None

        self.assertEqual(normalized("2026-03-01 10:30:00"), "2026-03-01 10:30:00")
        self.assertEqual(normalized("2026-03-01 10:30"), "2026-03-01 10:30:00")
        self.assertEqual(normalized("2026/03/01 10:30:00"), "2026-03-01 10:30:00")
        self.assertEqual(normalized("2026-03-01"), "2026-03-01 00:00:00")
        self.assertEqual(normalized("2026-03-01T10:30:00"), "2026-03-01 10:30:00")
        self.assertIsNone(normalized("45123"))
        self.assertIsNone(normalized(""))

    def test_parse_datetime_text_keeps_explicit_timezone(self):
        # 旧系统导出的数据常带 +08 偏移：按 Asia/Shanghai 落库后本地时间应原样保留
        parsed = parse_datetime_text("2026-05-28 14:46:43+08")
        self.assertIsNotNone(parsed)
        self.assertEqual(timezone.localtime(parsed).strftime("%Y-%m-%d %H:%M:%S"), "2026-05-28 14:46:43")
        self.assertEqual(timezone.localtime(parsed).utcoffset().total_seconds(), 8 * 3600)


class ParseWorkbookTests(SimpleTestCase):
    def test_columns_are_matched_by_name_not_order(self):
        upload = build_upload(
            ["姓名", "多余列", "手机号"],
            [["张三", "忽略", "13800138000"]],
        )
        rows = parse_workbook(upload, required_columns=["手机号", "姓名"], known_columns=["手机号", "姓名"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].number, 2)
        self.assertEqual(rows[0].values, {"姓名": "张三", "手机号": "13800138000"})

    def test_blank_rows_are_skipped_without_shifting_row_numbers(self):
        upload = build_upload(
            ["手机号", "姓名"],
            [["13800138000", "张三"], ["   ", None], ["13900139000", "李四"]],
        )
        rows = parse_workbook(upload, required_columns=["手机号"], known_columns=["手机号", "姓名"])
        self.assertEqual([row.number for row in rows], [2, 4])

    def test_missing_required_column_raises_with_errors_list(self):
        upload = build_upload(["手机号"], [["13800138000"]])
        with self.assertRaises(BusinessError) as ctx:
            parse_workbook(upload, required_columns=["手机号", "职业"], known_columns=["手机号"])
        self.assertIn("模板缺少必填列：职业", ctx.exception.message)
        self.assertEqual(ctx.exception.errors[0]["column"], "职业")

    def test_non_xlsx_is_rejected(self):
        upload = build_upload(["手机号"], [["13800138000"]], filename="导入.csv")
        with self.assertRaises(BusinessError):
            parse_workbook(upload, required_columns=["手机号"], known_columns=["手机号"])

    def test_empty_file_is_rejected(self):
        upload = SimpleUploadedFile("导入.xlsx", b"", content_type=XLSX_CONTENT_TYPE)
        with self.assertRaises(BusinessError) as ctx:
            parse_workbook(upload, required_columns=["手机号"], known_columns=["手机号"])
        self.assertIn("空", ctx.exception.message)

    def test_header_only_file_is_rejected(self):
        upload = build_upload(["手机号"], [])
        with self.assertRaises(BusinessError) as ctx:
            parse_workbook(upload, required_columns=["手机号"], known_columns=["手机号"])
        self.assertIn("没有数据行", ctx.exception.message)

    def test_too_many_rows_are_rejected(self):
        upload = build_upload(
            ["手机号"],
            [["13800138001"], ["13800138002"], ["13800138003"]],
        )
        with self.assertRaises(BusinessError) as ctx:
            parse_workbook(upload, required_columns=["手机号"], known_columns=["手机号"], max_rows=2)
        self.assertIn("最多导入 2 行", ctx.exception.message)


class IssueCollectorTests(SimpleTestCase):
    def test_issues_are_capped_but_total_count_is_reported(self):
        issues = IssueCollector()
        for index in range(MAX_ISSUE_COUNT + 5):
            issues.add(index + 2, "手机号", "13800138000", "格式不正确")
        self.assertEqual(len(issues.items), MAX_ISSUE_COUNT)
        self.assertEqual(issues.total, MAX_ISSUE_COUNT + 5)
        with self.assertRaises(BusinessError) as ctx:
            issues.raise_if_any(noun="会员")
        self.assertIn(f"共 {MAX_ISSUE_COUNT + 5} 处问题", ctx.exception.message)
        self.assertIn("未写入任何会员", ctx.exception.message)
        self.assertIn("仅展示前", ctx.exception.message)

    def test_no_issues_does_not_raise(self):
        IssueCollector().raise_if_any(noun="会员")


class TemplateWorkbookTests(SimpleTestCase):
    def test_template_has_text_formatted_columns_and_help_sheet(self):
        content = build_template_workbook(
            sheet_title="会员导入",
            columns=(
                TemplateColumn("手机号", required=True, example="13800138000", note="11 位"),
                TemplateColumn("性别", required=True, kind="choice", choices=("男", "女"), example="男"),
            ),
            notes=("整批驳回",),
        )
        workbook = load_workbook(BytesIO(content))
        self.assertEqual(workbook.sheetnames, ["会员导入", "填写说明"])

        sheet = workbook["会员导入"]
        self.assertEqual([cell.value for cell in sheet[1]], ["手机号", "性别"])
        self.assertEqual(sheet.max_row, 1, "主 sheet 只能有表头，不能有示例行")
        self.assertEqual(sheet.column_dimensions["A"].number_format, "@")

        validations = sheet.data_validations.dataValidation
        self.assertEqual(len(validations), 1)
        self.assertEqual(validations[0].formula1, '"男,女"')
        self.assertEqual(str(validations[0].sqref), "B2:B501")

        help_sheet = workbook["填写说明"]
        rows = list(help_sheet.iter_rows(values_only=True))
        self.assertEqual(rows[0], ("列名", "是否必填", "填写说明", "示例"))
        self.assertEqual(rows[1][:2], ("手机号", "必填"))
        self.assertEqual(rows[2][:2], ("性别", "必填"))
        self.assertIn("可选值：男 / 女", rows[2][2])
        self.assertIn("整批驳回", [row[0] for row in rows])

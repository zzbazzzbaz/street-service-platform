from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from openpyxl import Workbook, load_workbook

from apps.members.models import Member
from apps.merchants.models import Merchant
from tests.helpers import (
    admin_auth_header,
    create_admin_user,
    create_member,
    create_merchant,
)

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

MEMBER_HEADERS = ["手机号", "姓名", "性别", "职业", "住址", "是否党员", "昵称", "微信号", "注册时间"]
MERCHANT_HEADERS = [
    "店铺名称",
    "联系人",
    "联系电话",
    "商户分类",
    "经营地址",
    "所属社区",
    "商户性质",
    "营业时间",
    "服务内容",
    "纬度",
    "经度",
    "登录用户名",
    "初始密码",
]
ADMIN_USER_HEADERS = ["登录用户名", "姓名", "初始密码", "邮箱", "是否启用"]


def build_upload(headers, rows, *, filename="导入.xlsx") -> SimpleUploadedFile:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(headers))
    for row in rows:
        sheet.append(list(row))
    buffer = BytesIO()
    workbook.save(buffer)
    return SimpleUploadedFile(filename, buffer.getvalue(), content_type=XLSX_CONTENT_TYPE)


class ImportApiTestBase(TestCase):
    def setUp(self):
        self.admin = create_admin_user()
        self.headers = admin_auth_header(self.admin)

    def upload(self, url, columns, rows, filename="导入.xlsx"):
        return self.client.post(url, {"file": build_upload(columns, rows, filename=filename)}, **self.headers)


class TemplateDownloadTests(ImportApiTestBase):
    def test_member_template_download(self):
        response = self.client.get("/api/admin/imports/members/template", **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], XLSX_CONTENT_TYPE)
        self.assertIn("attachment", response["Content-Disposition"])
        workbook = load_workbook(BytesIO(response.content))
        self.assertEqual(workbook.sheetnames, ["会员导入", "填写说明"])
        self.assertEqual([cell.value for cell in workbook["会员导入"][1]], MEMBER_HEADERS)

    def test_merchant_template_download(self):
        response = self.client.get("/api/admin/imports/merchants/template", **self.headers)
        self.assertEqual(response.status_code, 200)
        workbook = load_workbook(BytesIO(response.content))
        self.assertEqual([cell.value for cell in workbook["商户导入"][1]], MERCHANT_HEADERS)

    def test_admin_user_template_download(self):
        response = self.client.get("/api/admin/imports/admin-users/template", **self.headers)
        self.assertEqual(response.status_code, 200)
        workbook = load_workbook(BytesIO(response.content))
        self.assertEqual([cell.value for cell in workbook["后台账号导入"][1]], ADMIN_USER_HEADERS)

    def test_template_download_requires_admin(self):
        response = self.client.get("/api/admin/imports/members/template")
        self.assertEqual(response.status_code, 401)


class MemberImportTests(ImportApiTestBase):
    def test_import_success(self):
        response = self.upload(
            "/api/admin/imports/members",
            MEMBER_HEADERS,
            [
                ["13800138001", "张三", "男", "美团快递", "示例区示例路10号", "是", "", "zs_wx", "2025-03-01 10:00:00"],
                ["13800138002", "李四", "女", "顺丰快递", "西单大街1号", "否", "小李", "", ""],
            ],
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["data"]["imported"], 2)

        first = Member.objects.get(phone="13800138001")
        self.assertEqual(first.username, "13800138001")
        self.assertEqual(first.real_name, "张三")
        self.assertEqual(first.gender, "男")
        self.assertEqual(first.occupation, "美团快递")
        self.assertEqual(first.is_party_member, True)
        self.assertEqual(first.nickname, "张三")
        self.assertEqual(first.wechat_id, "zs_wx")
        self.assertEqual(first.audit_status, Member.AuditStatus.APPROVED)
        self.assertTrue(first.is_active)
        self.assertIsNone(first.openid)
        self.assertTrue(check_password("000000", first.password))
        self.assertEqual(
            timezone.localtime(first.created_at).strftime("%Y-%m-%d %H:%M:%S"),
            "2025-03-01 10:00:00",
        )
        self.assertEqual(first.audit_submitted_at, first.created_at)

        second = Member.objects.get(phone="13800138002")
        self.assertEqual(second.nickname, "小李")
        self.assertEqual(second.is_party_member, False)

    def test_imported_member_can_login_with_initial_password(self):
        self.upload(
            "/api/admin/imports/members",
            MEMBER_HEADERS,
            [["13800138003", "王五", "男", "美团快递", "示例区示例路10号", "否", "", "", ""]],
        )
        response = self.client.post(
            "/api/auth/login",
            {"username": "13800138003", "password": "000000"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["data"]["must_change_password"])

    def test_conflict_rejects_whole_batch(self):
        create_member(nickname="老会员", phone="13800009999")
        response = self.upload(
            "/api/admin/imports/members",
            MEMBER_HEADERS,
            [
                ["13800138001", "张三", "男", "美团快递", "示例区示例路10号", "否", "", "", ""],
                ["13800009999", "李四", "男", "美团快递", "示例区示例路10号", "否", "", "", ""],
            ],
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["code"], 40000)
        self.assertEqual(len(payload["errors"]), 1)
        self.assertEqual(payload["errors"][0]["row"], 3)
        self.assertEqual(payload["errors"][0]["column"], "手机号")
        self.assertIn("老会员", payload["errors"][0]["message"])
        self.assertIn("已全部驳回", payload["message"])
        self.assertFalse(Member.objects.filter(phone="13800138001").exists(), "整批拒绝时不能有部分写入")
        self.assertEqual(Member.objects.count(), 1)

    def test_format_issues_are_collected_per_row(self):
        response = self.upload(
            "/api/admin/imports/members",
            MEMBER_HEADERS,
            [
                ["1380000", "张", "中", "程序员", "", "也许", "", "", ""],
                ["13800138001", "张三", "男", "美团快递", "示例区示例路10号", "否", "", "", ""],
                ["13800138001", "李四", "女", "顺丰快递", "西单大街1号", "是", "", "", ""],
            ],
        )
        self.assertEqual(response.status_code, 400)
        errors = response.json()["errors"]
        columns = {error["column"] for error in errors}
        self.assertTrue({"手机号", "姓名", "性别", "职业", "住址", "是否党员"} <= columns, columns)
        self.assertTrue(any(error["row"] == 4 and "与第 3 行重复" in error["message"] for error in errors), errors)
        self.assertEqual(Member.objects.count(), 0)

    def test_missing_required_column_is_rejected(self):
        headers = [column for column in MEMBER_HEADERS if column != "职业"]
        response = self.upload(
            "/api/admin/imports/members",
            headers,
            [["13800138001", "张三", "男", "示例区示例路10号", "否", "", "", ""]],
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("模板缺少必填列", response.json()["message"])
        self.assertIn("职业", response.json()["message"])

    def test_non_xlsx_file_is_rejected(self):
        response = self.upload(
            "/api/admin/imports/members",
            MEMBER_HEADERS,
            [["13800138001", "张三", "男", "美团快递", "示例区示例路10号", "否", "", "", ""]],
            filename="导入.csv",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(".xlsx", response.json()["message"])

    def test_import_requires_admin(self):
        upload = build_upload(MEMBER_HEADERS, [["13800138001", "张三", "男", "美团快递", "示例区示例路10号", "否", "", "", ""]])
        response = self.client.post("/api/admin/imports/members", {"file": upload})
        self.assertEqual(response.status_code, 401)


class MerchantImportTests(ImportApiTestBase):
    def test_import_success(self):
        response = self.upload(
            "/api/admin/imports/merchants",
            MERCHANT_HEADERS,
            [
                [
                    "便民超市",
                    "王店长",
                    "13900139001",
                    "零售商超",
                    "示例区示例路10号",
                    "示例社区",
                    "个体工商户",
                    "08:00-20:00",
                    "日用百货",
                    "39.91",
                    "116.38",
                    "shop_a",
                    "shop123456",
                ],
                ["老王理发", "王师傅", "13900139002", "生活服务", "", "", "", "", "", "", "", "", ""],
            ],
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["data"]["imported"], 2)

        first = Merchant.objects.get(phone="13900139001")
        self.assertEqual(first.name, "便民超市")
        self.assertEqual(first.category_code, Merchant.CategoryCode.RETAIL)
        self.assertEqual(first.community, "示例社区")
        self.assertEqual(first.business_hours, "08:00-20:00")
        self.assertEqual(first.latitude, 39.91)
        self.assertEqual(first.longitude, 116.38)
        self.assertEqual(first.username, "shop_a")
        self.assertTrue(check_password("shop123456", first.password))
        self.assertEqual(first.audit_status, Merchant.AuditStatus.APPROVED)
        self.assertTrue(first.is_active)
        self.assertIsNone(first.openid)

        second = Merchant.objects.get(phone="13900139002")
        self.assertEqual(second.category_code, Merchant.CategoryCode.LIFE_SERVICE)
        self.assertIsNone(second.username)
        self.assertEqual(second.password, "")

    def test_phone_conflict_rejects_whole_batch(self):
        create_merchant(openid="existing-merchant", name="既有商户", phone="13900009999")
        response = self.upload(
            "/api/admin/imports/merchants",
            MERCHANT_HEADERS,
            [["新店", "新店长", "13900009999", "餐饮商户", "", "", "", "", "", "", "", "", ""]],
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("既有商户", response.json()["errors"][0]["message"])
        self.assertEqual(Merchant.objects.count(), 1)

    def test_username_conflict_is_detected(self):
        create_merchant(openid="existing-merchant", name="既有商户", phone="13900008888", username="shop_a")
        response = self.upload(
            "/api/admin/imports/merchants",
            MERCHANT_HEADERS,
            [["新店", "新店长", "13900139005", "餐饮商户", "", "", "", "", "", "", "", "shop_a", "123456"]],
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"][0]["column"], "登录用户名")
        self.assertIn("既有商户", response.json()["errors"][0]["message"])

    def test_landline_phone_is_accepted(self):
        response = self.upload(
            "/api/admin/imports/merchants",
            MERCHANT_HEADERS,
            [["老张修车", "张师傅", "010-63081234", "维修服务", "", "", "", "", "", "", "", "laozhang", "123456"]],
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Merchant.objects.get(username="laozhang").phone, "010-63081234")

    def test_overlong_phone_is_rejected(self):
        response = self.upload(
            "/api/admin/imports/merchants",
            MERCHANT_HEADERS,
            [["超长电话店", "店长", "010-63081234-12345678", "维修服务", "", "", "", "", "", "", "", "", ""]],
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"][0]["column"], "联系电话")
        self.assertIn("最长 20 个字符", response.json()["errors"][0]["message"])

    def test_phone_and_username_cannot_collide_across_rows(self):
        response = self.upload(
            "/api/admin/imports/merchants",
            MERCHANT_HEADERS,
            [
                ["甲店", "甲店长", "13900139101", "餐饮商户", "", "", "", "", "", "", "", "", ""],
                ["乙店", "乙店长", "13900139102", "餐饮商户", "", "", "", "", "", "", "", "13900139101", "123456"],
            ],
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"][0]["row"], 3)
        self.assertEqual(response.json()["errors"][0]["column"], "登录用户名")
        self.assertIn("与第 2 行的联系电话重复", response.json()["errors"][0]["message"])
        self.assertEqual(Merchant.objects.count(), 0)

    def test_username_may_equal_own_phone(self):
        response = self.upload(
            "/api/admin/imports/merchants",
            MERCHANT_HEADERS,
            [["丙店", "丙店长", "13900139103", "餐饮商户", "", "", "", "", "", "", "", "13900139103", "123456"]],
        )
        self.assertEqual(response.status_code, 200, response.content)
        merchant = Merchant.objects.get(phone="13900139103")
        self.assertEqual(merchant.username, "13900139103")

    def test_username_requires_password(self):
        response = self.upload(
            "/api/admin/imports/merchants",
            MERCHANT_HEADERS,
            [["新店", "新店长", "13900139006", "餐饮商户", "", "", "", "", "", "", "", "shop_b", ""]],
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"][0]["column"], "初始密码")

    def test_password_requires_username(self):
        response = self.upload(
            "/api/admin/imports/merchants",
            MERCHANT_HEADERS,
            [["新店", "新店长", "13900139010", "餐饮商户", "", "", "", "", "", "", "", "", "123456"]],
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"][0]["column"], "登录用户名")
        self.assertEqual(Merchant.objects.count(), 0)

    def test_business_hours_and_coordinates_are_validated(self):
        response = self.upload(
            "/api/admin/imports/merchants",
            MERCHANT_HEADERS,
            [
                ["新店", "新店长", "13900139007", "餐饮商户", "", "", "", "20:00-08:00", "", "39.91", "", "", ""],
                ["新店二", "新店长", "13900139008", "餐饮商户", "", "", "", "", "", "东经116", "116.38", "", ""],
            ],
        )
        self.assertEqual(response.status_code, 400)
        errors = response.json()["errors"]
        self.assertTrue(any(error["column"] == "营业时间" and "晚于开始时间" in error["message"] for error in errors), errors)
        self.assertTrue(any(error["column"] == "纬度" and "同时填写" in error["message"] for error in errors), errors)
        self.assertTrue(any(error["column"] == "纬度" and "必须是数字" in error["message"] for error in errors), errors)
        self.assertEqual(Merchant.objects.count(), 0)

    def test_category_must_be_known(self):
        response = self.upload(
            "/api/admin/imports/merchants",
            MERCHANT_HEADERS,
            [["新店", "新店长", "13900139009", "咖啡店", "", "", "", "", "", "", "", "", ""]],
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("商户分类只能填", response.json()["errors"][0]["message"])


class AdminUserImportTests(ImportApiTestBase):
    def test_import_success_and_login(self):
        response = self.upload(
            "/api/admin/imports/admin-users",
            ADMIN_USER_HEADERS,
            [
                ["newadmin", "李管理", "000000", "li@example.com", "是"],
                ["disabledadmin", "停用账号", "pass123456", "", "否"],
            ],
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["data"]["imported"], 2)

        user = get_user_model().objects.get(username="newadmin")
        self.assertEqual(user.first_name, "李管理")
        self.assertEqual(user.email, "li@example.com")
        self.assertTrue(user.is_backend_manager)
        self.assertTrue(user.is_staff, "bulk_create 绕过了 save()，is_staff 必须显式写死")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_superuser)

        disabled = get_user_model().objects.get(username="disabledadmin")
        self.assertFalse(disabled.is_active)

        login = self.client.post(
            "/api/admin/auth/login",
            {"username": "newadmin", "password": "000000"},
            content_type="application/json",
        )
        self.assertEqual(login.status_code, 200, login.content)
        self.assertTrue(login.json()["data"]["must_change_password"])

    def test_username_conflict_rejects_whole_batch(self):
        create_admin_user(username="taken")
        response = self.upload(
            "/api/admin/imports/admin-users",
            ADMIN_USER_HEADERS,
            [["fresh", "新人", "000000", "", "是"], ["taken", "老人", "000000", "", "是"]],
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"][0]["row"], 3)
        self.assertFalse(get_user_model().objects.filter(username="fresh").exists())

    def test_short_password_is_rejected(self):
        response = self.upload(
            "/api/admin/imports/admin-users",
            ADMIN_USER_HEADERS,
            [["shortpwd", "新人", "12345", "", "是"]],
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("至少 6 位", response.json()["errors"][0]["message"])

    def test_invalid_email_is_rejected(self):
        response = self.upload(
            "/api/admin/imports/admin-users",
            ADMIN_USER_HEADERS,
            [["bademail", "新人", "000000", "not-an-email", "是"]],
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"][0]["column"], "邮箱")


class ForcedPasswordChangeTests(ImportApiTestBase):
    def test_member_flag_disappears_after_password_change(self):
        member = create_member(nickname="改密用户", phone="13800001111")
        member.username = "13800001111"
        member.password = make_password("000000")
        member.save(update_fields=["username", "password"])

        first = self.client.post(
            "/api/auth/login",
            {"username": "13800001111", "password": "000000"},
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["data"]["must_change_password"])

        member.password = make_password("newpass123")
        member.save(update_fields=["password"])
        second = self.client.post(
            "/api/auth/login",
            {"username": "13800001111", "password": "newpass123"},
            content_type="application/json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.json()["data"]["must_change_password"])

    def test_merchant_flag_disappears_after_password_change(self):
        merchant = create_merchant(openid="merchant-openid", username="shop_login", password=make_password("000000"))
        first = self.client.post(
            "/api/merchant/auth/login",
            {"username": "shop_login", "password": "000000"},
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200, first.content)
        self.assertTrue(first.json()["data"]["must_change_password"])

        merchant.password = make_password("newpass123")
        merchant.save(update_fields=["password"])
        second = self.client.post(
            "/api/merchant/auth/login",
            {"username": "shop_login", "password": "newpass123"},
            content_type="application/json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.json()["data"]["must_change_password"])

    def test_admin_flag_disappears_after_password_change(self):
        self.assertTrue(self.client.post(
            "/api/admin/auth/login",
            {"username": self.admin.username, "password": "admin123456"},
            content_type="application/json",
        ).json()["data"]["must_change_password"] is False)

        self.admin.set_password("000000")
        self.admin.save(update_fields=["password"])
        response = self.client.post(
            "/api/admin/auth/login",
            {"username": self.admin.username, "password": "000000"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["must_change_password"])


class SixCharacterPasswordTests(ImportApiTestBase):
    def test_admin_user_can_be_created_with_six_character_password(self):
        response = self.client.post(
            "/api/admin/admin-users",
            {"username": "sixpwd", "password": "abc123", "is_backend_manager": True, "is_active": True},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(check_password("abc123", get_user_model().objects.get(username="sixpwd").password))

    def test_merchant_can_be_created_with_six_character_password(self):
        response = self.client.post(
            "/api/admin/merchants",
            {"name": "六位密码商户", "contact_name": "店长", "phone": "13900001234", "username": "sixshop", "password": "abc123"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(check_password("abc123", Merchant.objects.get(username="sixshop").password))

    def test_merchant_password_reset_accepts_six_characters(self):
        merchant = create_merchant(openid="merchant-openid", username="shop_reset", password=make_password("oldpass123"))
        response = self.client.post(
            f"/api/admin/merchants/{merchant.id}/password",
            {"password": "abc123"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200, response.content)
        merchant.refresh_from_db()
        self.assertTrue(check_password("abc123", merchant.password))

    def test_admin_password_reset_accepts_six_characters(self):
        target = create_admin_user(username="target_admin")
        response = self.client.post(
            f"/api/admin/admin-users/{target.id}/password",
            {"password": "abc123"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200, response.content)
        target.refresh_from_db()
        self.assertTrue(check_password("abc123", target.password))

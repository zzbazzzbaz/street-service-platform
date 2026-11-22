# 街道服务数字化平台 · 后端

街道服务数字化平台的后端服务，面向小程序用户端、商户端和独立前端后台。当前仓库重点实现一期 MVP 后端能力，包括用户登录、学习宣传、随手拍、活动报名签到、助老服务、积分、商户固定码、积分支付和 `/api/admin/*` 后台管理 API。

## 技术栈

- Python 3.12
- Django 5.2
- Django Ninja
- SQLite
- django-simpleui
- django-tinymce
- uv

## 目录结构

```text
backend/                  Django 后端项目
backend/apps/             业务应用
backend/config/           Django 配置和 API 路由入口
backend/shared/           统一响应、认证、分页、Admin 公共能力
backend/tests/            后端测试
docs/文档/                 API、架构、数据库与部署文档
```

## 本地启动

进入后端目录：

```bash
cd backend
```

安装依赖：

```bash
uv sync
```

如需本地环境变量：

```bash
cp .env.example .env
```

如果通过反向代理域名访问后台，并且 `.env` 中显式设置了 `DJANGO_ALLOWED_HOSTS`，需要把域名一起写入，例如：

```env
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,8000.example.com
```

初始化数据库：

```bash
uv run python manage.py migrate
```

填充前端开发测试数据：

```bash
uv run python manage.py seed_mvp
```

启动服务：

```bash
uv run python manage.py runserver 0.0.0.0:8000
```

常用入口：

- 正式后台 API：`http://127.0.0.1:8000/api/admin/*`
- Django Admin 调试入口：`http://127.0.0.1:8000/admin/`
- API 文档：`http://127.0.0.1:8000/api/docs`
- OpenAPI：`http://127.0.0.1:8000/api/openapi.json`
- 健康检查：`http://127.0.0.1:8000/api/health`

## 开发测试账号

执行 `uv run python manage.py seed_mvp` 后可用：

后台账号：

```text
username: admin
password: admin123456
```

用户端登录：

```json
{
  "openid": "test-openid"
}
```

接口：

```text
POST /api/auth/wechat-login
```

商户端登录：

```json
{
  "openid": "merchant-openid"
}
```

接口：

```text
POST /api/merchant/auth/wechat-login
```

> 2026-10-13 起用户端/商户端支持注册提交审核：
> - 用户端注册 `POST /api/auth/register`（姓名/微信号/性别/手机号/职业/是否党员/住址），商户端注册 `POST /api/merchant/auth/register`（店铺名称/地址/服务内容/所属社区/商户性质/联系人/联系电话/营业时间）；
> - 注册即登录，账号密码登录名 = 手机号，初始密码统一 `000000`，可在小程序内自助改密；
> - 注册后 `audit_status=pending`，后台审核通过（`approved`）才是可用账户；被驳回后可在小程序内重新提交资料；
> - 详情见 `docs/文档/后端API接口文档.md`。

种子数据会创建学习内容、积分余额、活动报名和签到、助老反馈、随手拍上报、商户、积分兑换比例和商户积分支付流水，方便前端联调完整流程。

## 核心业务流程

用户端：

1. 注册提交审核 `POST /api/auth/register`（或使用 `POST /api/auth/wechat-login` 获取用户 token）。
2. 审核通过前可使用学习、积分、活动、商户消费等基础功能；随手拍、反馈、助老服务需 `approved`。
3. 提交随手拍、报名活动、扫码签到、提交助老服务反馈。
4. 查看积分余额和流水。
5. 扫商户固定码后使用积分支付。

商户端：

1. 注册提交审核 `POST /api/merchant/auth/register`，或使用 `POST /api/merchant/auth/wechat-login` 获取商户 token。
2. 审核通过后调用 `GET /api/merchant/fixed-code` 获取固定码内容。
3. 调用 `GET /api/merchant/point-records` 查看本商户积分支付流水。

后台：

1. 调用 `POST /api/admin/auth/login` 获取后台管理员 token。
2. 通过 `/api/admin/admin-users`、`/api/admin/members` 管理后台账号、用户资料和用户注册审核。
3. 通过 `/api/admin/merchants` 和 `POST /api/admin/merchants/{id}/audit` 完成商户注册审核。
4. 通过 `/api/admin/learning/*`、`/api/admin/activities/*`、`/api/admin/elder-services/*` 维护内容、活动和助老服务。
5. 通过 `/api/admin/reports`、`/api/admin/civic-feedbacks`、`/api/admin/problem-feedbacks` 完成审核和回复。
6. 通过 `/api/admin/points/*`、`/api/admin/merchants/*` 完成积分、人工加分、兑换比例、商户和结算管理。

Django Admin 仍保留作为开发调试和应急排查入口，不作为正式运营后台。

## 测试

运行全部测试：

```bash
cd backend
uv run python manage.py test -v 2
```

运行指定测试：

```bash
uv run python manage.py test tests.test_seed_mvp -v 2
```

## 接口文档

详细接口说明见：

```text
docs/文档/后端API接口文档.md
```

服务启动后也可以访问：

```text
/api/docs
/api/openapi.json
```

## 说明

- 本仓库为求职作品集展示版：已移除真实客户数据、内部需求文档与部署密钥，示例数据均为虚构。
- 正式微信登录当前只保留请求形态，开发期使用测试 `openid` 登录。
- SQLite 数据库和媒体文件位于 `backend/data/`，默认不提交到 Git。
- Django Admin 是开发调试和应急排查入口，不是正式业务管理入口。

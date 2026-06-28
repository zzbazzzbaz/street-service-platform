# 街道服务数字化操作系统

街道服务数字化操作系统后端，面向小程序用户端、商户端和开发阶段 Django Admin。当前仓库重点实现一期 MVP 后端能力，包括用户登录、学习宣传、随手拍、活动报名签到、助老服务、积分、商户固定码和积分支付。

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
docs/API接口文档.md        API 联调文档
docs/superpowers/         规格和实施计划
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

如果通过 frp 域名访问后台，并且 `.env` 中显式设置了 `DJANGO_ALLOWED_HOSTS`，需要把域名一起写入，例如：

```env
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,8000.frp.chatgqt.top
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

- 后台：`http://127.0.0.1:8000/admin/`
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

种子数据会创建学习内容、积分余额、活动报名和签到、助老反馈、随手拍上报、商户、积分兑换比例和商户积分支付流水，方便前端联调完整流程。

## 核心业务流程

用户端：

1. 使用 `POST /api/auth/wechat-login` 获取用户 token。
2. 查看学习内容并完成学习获取积分。
3. 提交随手拍、报名活动、扫码签到、提交助老服务反馈。
4. 查看积分余额和流水。
5. 扫商户固定码后使用积分支付。

商户端：

1. 使用 `POST /api/merchant/auth/wechat-login` 获取商户 token。
2. 调用 `GET /api/merchant/fixed-code` 获取固定码内容。
3. 调用 `GET /api/merchant/point-records` 查看本商户积分支付流水。

后台：

1. 通过 Django Admin 管理学习内容、活动、助老任务、商户和积分兑换比例。
2. 审核随手拍、活动签到和助老反馈。
3. 通过人工加分入口补发用户积分。
4. 查看图片、二维码预览和积分流水。

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
docs/API接口文档.md
```

服务启动后也可以访问：

```text
/api/docs
/api/openapi.json
```

## 说明

- 正式微信登录当前只保留请求形态，开发期使用测试 `openid` 登录。
- SQLite 数据库和媒体文件位于 `backend/data/`，默认不提交到 Git。
- Django Admin 是开发调试和一期验收入口，不是独立正式管理前端。

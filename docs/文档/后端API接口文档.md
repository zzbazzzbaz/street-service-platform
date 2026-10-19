# 后端 API 接口文档

- 项目：街道服务数字化操作系统
- 版本：v1.0（对应代码当前状态，Django Ninja 自动生成）
- Base URL：`http://<host>:8000/api`
- 更新时间：2026-08-25
- 在线文档：`/api/docs`（Swagger UI）、`/api/openapi.json`

## 1. 通用约定

### 1.1 认证方式

所有接口（除健康检查和公开列表外）均需携带请求头：

```text
Authorization: Bearer <access_token>
```

Token 由登录接口签发，默认有效期 7200 秒（`ACCESS_TOKEN_EXPIRES_SECONDS` 可配），过期后返回 `40101`。

Token 主体分三类，互不通用：

| 主体 | 签发接口 | 可访问范围 |
| --- | --- | --- |
| `member` | `/api/auth/*` | 用户端 `/api/members|learning|reports|activities|points|...` |
| `merchant` | `/api/merchant/auth/*` | 商户端 `/api/merchant/*` |
| `admin` | `/api/admin/auth/login` | 后台 `/api/admin/*` |

### 1.2 统一响应格式

成功：

```json
{
  "code": 0,
  "message": "success",
  "data": { }
}
```

失败：

```json
{
  "code": 40000,
  "message": "请求参数错误",
  "errors": null
}
```

### 1.3 错误码

| 错误码 | HTTP | 说明 |
| --- | --- | --- |
| 0 | 200 | 成功 |
| 40000 | 400 | 请求参数错误 / 业务校验失败 |
| 40003 | 403 | 业务受限（余额不足、停用、每日限额等） |
| 40101 | 401 | 登录已过期，请重新登录 |
| 40102 | 401 | 缺少登录凭证 |
| 40301 | 403 | 无权限访问 |
| 40400 | 404 | 资源不存在 |
| 42900 | 429 | 请求过于频繁（限流） |
| 50000 | 500 | 服务器内部错误 |

### 1.4 分页

列表接口通用查询参数：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| page | int | 1 | 页码（从 1 开始） |
| page_size | int | 20 | 每页条数（最大 100） |

分页响应统一结构：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [ ... ],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

### 1.5 限流

| 接口 | 限流策略 |
| --- | --- |
| 各类登录（`/auth/*`、`/admin/auth/login`） | 每 IP 5 次/分钟 |
| 用户积分支付、固定码扫码 | 每用户 20 次/分钟 |
| 后台人工调分 | 每操作人 20 次/分钟 |
| 单用户单商户积分支付 | 每日最多 2 次（业务限额，错误码 40003） |

### 1.6 文件上传

- 用户端：`POST /api/uploads/images`（multipart/form-data，字段名 `files`，可多个）
- 后台：`POST /api/admin/uploads/images`、`POST /api/admin/uploads/videos`

上传返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "files": [
      {
        "file_id": "x",
        "url": "https://host/media/uploads/xxx.jpg",
        "original_name": "a.jpg",
        "size": 12345,
        "mime_type": "image/jpeg",
        "created_at": "2026-08-25T10:00:00+08:00"
      }
    ]
  }
}
```

业务提交接口中的 `image_urls / material_urls` 直接使用上传返回的 `url` 数组。

## 2. 系统

### 2.1 健康检查

`GET /api/health`（无需认证）

```json
{ "code": 0, "message": "success", "data": { "status": "ok" } }
```

## 3. 用户端 API

### 3.1 认证

#### 微信登录（测试 / 占位）

`POST /api/auth/wechat-login`

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| openid | string | 否 | 测试登录：传入任意 openid 即创建/登录用户并签发 token |
| code | string | 否 | 正式登录：传 code（当前未接入，配置 appid/secret 后返回未接入提示） |

响应（`LoginOut`）：

```json
{
  "code": 0, "message": "success",
  "data": {
    "access_token": "eyJ...",
    "token_type": "Bearer",
    "expires_in": 7200,
    "must_change_password": false,
    "member": {
      "id": 1, "openid": "test-openid", "username": null,
      "nickname": "", "phone": "", "real_name": "",
      "wechat_id": "", "gender": "", "occupation": "",
      "is_party_member": false, "address": "",
      "audit_status": "none",
      "audit_remark": "", "audit_submitted_at": null, "is_active": true
    }
  }
}
```

#### 注册提交审核

`POST /api/auth/register`（限流 5/分钟/IP，注册即登录）

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| real_name | string | 是 | 姓名，2-10 字 |
| wechat_id | string | 是 | 微信号，最长 64 字 |
| gender | string | 是 | `男` / `女` |
| occupation | string | 是 | 顺丰快递 / 京东快递 / 美团快递 / 达达快递 / 申通快递 / 淘宝闪购 / 中通快递 / 其他 |
| address | string | 是 | 住址，最长 255 字 |
| phone | string | 是 | 手机号（同时作为登录名）；传 `phone_code` 时以微信返回号码为准 |
| is_party_member | boolean | 否 | 是否党员，默认 false |
| phone_code / login_code | string | 否 | 微信手机号授权 / 登录 code |

响应在 `LoginOut` 基础上增加 `need_audit: true`；账号 `audit_status=pending`、密码初始化为 `000000`，需后台审核通过后才可使用"发布类"功能。

#### 微信手机号登录

`POST /api/auth/wechat-phone-login`

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| login_code | string | 是 | 微信登录 code |
| phone_code | string | 是 | 手机号授权 code |
| encrypted_data / iv | string | 否 | 预留 |
| platform | string | 否 | 默认 `user_mp` |

登录后自动按手机号匹配账号并绑定 openid（已绑定其他微信返回 403），返回 `LoginOut`。

#### 账号密码登录

`POST /api/auth/login`（限流 5/分钟/IP）

| 参数 | 类型 | 必填 |
| --- | --- | --- |
| username | string | 是 |
| password | string | 是 |

错误时统一提示"用户名或密码错误"；停用账号返回 `40301 当前账号已停用`。审核中/已驳回的用户仍可登录查看审核状态。

### 3.2 用户信息

#### 当前用户信息

`GET /api/members/me`

响应 `MemberOut`（同登录接口中的 `member` 字段），用于展示审核状态与驳回原因（`audit_status` / `audit_remark`）。

#### 重新提交注册资料（驳回后重提）

`POST /api/members/register-info`（限流 5/分钟/账号）

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| real_name / wechat_id / gender / occupation / address | - | 是 | 同注册表单 |
| is_party_member | boolean | 否 | 是否党员 |
| phone | string | 条件 | 仅账号尚未绑定手机号时必填（首次绑定） |

`pending` 返回 400 `资料审核中，请等待审核结果`；`approved` 返回 400 `审核已通过，如需修改资料请联系街道工作人员`。

#### 修改密码

`POST /api/members/password`（限流 5/分钟/账号）

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| current_password | string | 是 | 当前密码（注册初始密码 `000000`） |
| new_password | string | 是 | 至少 6 位，且与当前密码不同 |

#### 更新资料

`POST /api/members/profile`

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| nickname | string | 否 | 昵称 |
| phone | string | 否 | 手机号（与他人重复返回 400 `该手机号已被其他账号使用`，改手机号同步登录名） |

> 原「提交实名审核」接口 `POST /api/members/audit-profile` 与小哥身份已废弃，改为注册/重提审核流程（2026-10-13）。

> 注意：随手拍、社情民意、问题反馈、助老服务等"发布类"接口要求用户已审核通过（`approved`），否则返回 `40301 当前用户资料未审核通过`；学习、积分、活动、商户消费等基础功能不受限。

### 3.3 学习宣传

#### 学习内容列表

`GET /api/learning/contents?page=1&page_size=20&is_announcement=true&is_pinned=true`

仅返回已上架内容；支持 `is_announcement`、`is_pinned` 布尔过滤。每项附 `is_completed / completed_at`（当前用户是否已完成）。

#### 置顶公告

`GET /api/learning/announcements/pinned`（无需认证）

返回置顶公告列表（最多 3 条，按 `pin_order` 排序）。

#### 学习详情

`GET /api/learning/contents/{content_id}`

#### 完成学习

`POST /api/learning/contents/{content_id}/complete`

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| learned_seconds | int | 是 | 本次学习秒数 |

当累计学习秒数达到 `required_seconds` 时记为完成并发放积分（每人每内容一次）。响应：

```json
{
  "code": 0, "message": "success",
  "data": {
    "id": 1, "content_id": 1, "learned_seconds": 60,
    "is_completed": true, "completed_at": "2026-08-25T10:00:00+08:00",
    "point_record_id": 123
  }
}
```

#### 学习记录

`GET /api/learning/records?page=1&page_size=20`

### 3.4 随手拍

#### 提交随手拍

`POST /api/reports`（需审核通过）

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| category_code | string | 否 | `safety_hazard` / `environmental_hygiene` / `public_facility` / `other` / `good_deed`，默认 other |
| description | string | 否 | 描述 |
| location | string | 是 | 位置 |
| image_urls | array[string] | 否 | 上传接口返回的 URL 列表 |

#### 我的随手拍

`GET /api/reports?page=1&page_size=20&status=&report_type=`

`report_type`：`report`（排除爱心善举）/ `good_deed`（仅爱心善举）。

#### 随手拍详情

`GET /api/reports/{report_id}`

### 3.5 社情民意

#### 提交反馈

`POST /api/civic-feedbacks`（需审核通过）

| 参数 | 类型 | 必填 |
| --- | --- | --- |
| title | string | 是 |
| content | string | 是 |
| material_urls | array[string] | 否 |

#### 我的反馈列表 / 详情

`GET /api/civic-feedbacks?page=&page_size=&status=`、`GET /api/civic-feedbacks/{feedback_id}`

### 3.6 问题反馈

#### 提交反馈

`POST /api/problem-feedbacks`（需审核通过）

| 参数 | 类型 | 必填 |
| --- | --- | --- |
| title | string | 是 |
| content | string | 是 |

#### 公开反馈广场

`GET /api/problem-feedbacks/public?page=&page_size=`（无需认证）

仅返回后台审核通过且公开的反馈。

#### 我的反馈列表 / 详情

`GET /api/problem-feedbacks?page=&page_size=&status=`、`GET /api/problem-feedbacks/{feedback_id}`

### 3.7 活动

#### 活动列表

`GET /api/activities?page=1&page_size=20&activity_type=volunteer|offline`

仅返回已发布活动。每项附当前用户状态：

```json
{
  "code": 0, "message": "success",
  "data": {
    "items": [{
      "id": 1, "title": "志愿任务", "body": "", "location": "xx",
      "latitude": 39.9, "longitude": 116.4,
      "start_time": "2026-08-25T09:00:00+08:00",
      "end_time": "2026-08-25T12:00:00+08:00",
      "points": 10, "status": "published", "activity_type": "volunteer",
      "user_signup_id": 5, "signup_status": "joined",
      "checkin_status": "pending", "point_status": "not_granted"
    }],
    "total": 1, "page": 1, "page_size": 20
  }
}
```

`signup_status`：`not_joined` / `joined` / `cancelled`；`checkin_status`：`not_checked` / `pending` / `confirmed` / `rejected`；`point_status`：`not_granted` / `granted`。

#### 我报名的活动

`GET /api/activities/my-signups?page=&page_size=&activity_type=`

#### 活动详情

`GET /api/activities/{activity_id}`

#### 报名活动

`POST /api/activities/{activity_id}/signup`（重复报名返回业务错误；已取消可重新报名）

#### 取消报名

`DELETE /api/activities/{activity_id}/signup`

```json
{ "code": 0, "message": "success", "data": { "activity_id": 1, "signup_status": "cancelled", "cancelled_at": "..." } }
```

#### 扫码签到

`POST /api/activities/{activity_id}/checkin`

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| checkin_code | string | 是 | 活动签到码（后台查看/扫码） |

签到后状态为 `pending`，后台确认后发放积分。

### 3.8 助老服务

#### 我的对口关系

`GET /api/elder-services/my-relation`（需审核通过；所有审核通过用户均可参与助老服务）

返回当前用户（帮扶人）的有效老人关系，无则为 `null`。

#### 任务广场

`GET /api/elder-services/tasks?page=&page_size=`（已发布任务）

#### 我的任务

`GET /api/elder-services/my-tasks?page=&page_size=&feedback_status=`

返回与我（结对帮扶人）对口关系关联的已发布任务，附最新反馈状态。`feedback_status`：`none`（未反馈）/ `pending` / `approved` / `rejected`。

#### 任务详情

`GET /api/elder-services/tasks/{task_id}`

#### 提交任务反馈

`POST /api/elder-services/tasks/{task_id}/feedback`

| 参数 | 类型 | 必填 |
| --- | --- | --- |
| content | string | 是 |
| image_urls | array[string] | 否 |

#### 直接提交助老反馈

`POST /api/elder-services/feedbacks`（需审核通过；不关联任务，适用于扫小程序直接反馈）

#### 我的反馈列表

`GET /api/elder-services/feedbacks?page=&page_size=&status=`

### 3.9 积分

#### 积分余额

`GET /api/points/balance`

```json
{ "code": 0, "message": "success", "data": { "balance": 100 } }
```

#### 积分流水

`GET /api/points/records?page=&page_size=`

```json
{
  "code": 0, "message": "success",
  "data": {
    "items": [{
      "id": 1, "amount": -20, "change_type": "expense",
      "source_type": "merchant_payment", "source_id": "3",
      "reason": "商户积分支付：xx店", "balance_after": 80,
      "merchant_id": 3, "merchant_name": "xx店",
      "yuan_amount": "2.00", "request_no": "no-123", "created_at": "..."
    }],
    "total": 1, "page": 1, "page_size": 20
  }
}
```

### 3.10 商户与积分支付

#### 商户列表（用户端可见）

`GET /api/merchants?page=&page_size=`（需用户 token）

#### 商户支付信息（预览）

`GET /api/merchants/{merchant_id}/payment-info`

```json
{
  "code": 0, "message": "success",
  "data": {
    "merchant_id": 3, "merchant_name": "xx店",
    "phone": "010-xxxx", "address": "xx路1号",
    "points_per_yuan": 10, "balance": 100
  }
}
```

`points_per_yuan` 为当前启用兑换比例（积分/元）。

#### 积分支付

`POST /api/merchants/{merchant_id}/point-payments`（限流 20 次/分钟/用户；单商户每日限 2 次）

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| points | int | 是 | 支付积分数（>0） |
| request_no | string | 否 | 幂等请求号，重试时返回原流水 |

```json
{
  "code": 0, "message": "success",
  "data": {
    "id": 10, "merchant_id": 3, "merchant_name": "xx店",
    "points": 20, "yuan_amount": "2.00", "balance_after": 80,
    "request_no": "no-123", "created_at": "..."
  }
}
```

#### 固定积分码预览

`GET /api/merchants/point-codes/{code}`

按面额返回兑换金额与当前余额：

```json
{
  "code": 0, "message": "success",
  "data": {
    "code": "abc123", "merchant_id": 3, "merchant_name": "xx店",
    "points": 50, "points_per_yuan": 10, "yuan_amount": "5.00", "balance": 100
  }
}
```

#### 固定积分码扫码支付

`POST /api/merchants/point-codes/{code}/scan`（限流 20 次/分钟/用户；单商户每日限 2 次）

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| request_no | string | 否 | 幂等请求号 |

### 3.11 统一服务记录

#### 我的服务记录

`GET /api/service-records?page=&page_size=`

聚合随手拍、活动报名、活动签到、社情民意、问题反馈、助老反馈、学习记录，按时间倒序：

```json
{
  "code": 0, "message": "success",
  "data": {
    "items": [{
      "record_type": "report", "source_id": 3,
      "title": "井盖损坏", "status": "pending", "status_label": "待审核",
      "points": 5, "occurred_at": "..."
    }],
    "total": 1, "page": 1, "page_size": 20
  }
}
```

`record_type`：`report` / `activity_signup` / `activity_checkin` / `civic_feedback` / `problem_feedback` / `elder_service` / `learning`。

#### 服务记录详情

`GET /api/service-records/{record_type}/{source_id}`

`source_id` 为该类型记录的主键 ID。

### 3.12 服务阵地

#### 服务阵地列表

`GET /api/service-locations?page=1&page_size=50`（无需认证）

```json
{
  "code": 0, "message": "success",
  "data": {
    "items": [{
      "id": 1, "name": "暖新驿站", "address": "xx路2号",
      "business_hours": "09:00-18:00", "service_content": "饮水、充电",
      "latitude": 39.9, "longitude": 116.4,
      "is_active": true, "created_at": "...", "updated_at": "..."
    }],
    "total": 1, "page": 1, "page_size": 50
  }
}
```

## 4. 商户端 API

### 4.1 认证

| 接口 | 说明 |
| --- | --- |
| `POST /api/merchant/auth/wechat-login` | 微信登录（测试传 `openid`；正式传 `code`，当前未接入） |
| `POST /api/merchant/auth/wechat-phone-login` | 手机号授权登录（`login_code` + `phone_code`，`platform=merchant_mp`；按手机号匹配商户并绑定 openid） |
| `POST /api/merchant/auth/login` | 账号密码登录（`username` + `password`），登录名 = 联系电话，注册初始密码 `000000` |
| `POST /api/merchant/auth/register` | **注册提交审核**（公开，限流 5/分钟/IP），字段见下 |

#### 注册提交审核

`POST /api/merchant/auth/register`

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| shop_name | string | 是 | 店铺名称，最长 100 字 |
| shop_address | string | 是 | 店铺地址，最长 255 字 |
| service_content | string | 是 | 服务内容，最长 500 字 |
| community | string | 是 | 所属社区，最长 100 字 |
| merchant_nature | string | 是 | 商户性质，最长 100 字 |
| contact_name | string | 是 | 联系人，最长 50 字 |
| contact_phone | string | 是 | 联系电话（= 登录名），11 位手机号 |
| business_hours | string | 是 | `HH:MM-HH:MM`，结束须晚于开始 |

注册即登录（响应含 `need_audit: true` 与 `access_token`），账号 `audit_status=pending`、`is_active=false`：可登录查看审核状态、被驳回后重提、修改密码；工作台接口在审核通过前返回 `40301 商户资料审核中，请等待审核`。

登录放行规则：`pending` / `rejected` 允许登录（仅状态页）；`approved` 且未停用正常登录；已通过但被后台停用返回 `40301 当前账号已停用`。

响应结构同用户端（`merchant` 替换 `member`）：

```json
{
  "code": 0, "message": "success",
  "data": {
    "access_token": "eyJ...", "token_type": "Bearer", "expires_in": 7200,
    "must_change_password": false,
    "need_audit": true,
    "merchant": { "id": 1, "openid": "", "username": "13712345678", "name": "xx店",
      "contact_name": "王店长", "phone": "13712345678", "address": "", "community": "幸福社区",
      "merchant_nature": "个体工商户", "latitude": null,
      "longitude": null, "category_code": "other", "business_hours": "",
      "service_content": "", "audit_status": "pending", "audit_remark": "", "is_active": false }
  }
}
```

### 4.2 商户信息与审核资料

| 接口 | 说明 |
| --- | --- |
| `GET /api/merchant/me` | 当前商户信息（含 `audit_status / audit_remark`，审核中/已驳回也可访问） |
| `POST /api/merchant/register-info` | **驳回后重新提交资料**（同注册 8 字段，联系电话不可改；`pending` 报 400 `资料审核中，请等待审核结果`，`approved` 报 400 `审核已通过，如需修改资料请联系街道工作人员`） |
| `POST /api/merchant/password` | 修改密码（`current_password` / `new_password`，规则同用户端） |

以下工作台接口需审核通过（`approved`）且账号启用：`/api/merchant/fixed-code`、`/api/merchant/point-codes`、`/api/merchant/point-records`、`/api/merchant/settlements`。

### 4.3 固定码（旧，单码）

`GET /api/merchant/fixed-code`

```json
{
  "code": 0, "message": "success",
  "data": { "merchant_id": 1, "merchant_name": "xx店", "code_content": "street-service://merchant-pay?merchant_id=1" }
}
```

### 4.4 固定积分码列表（新，多面额）

`GET /api/merchant/point-codes?include_inactive=false`

```json
{
  "code": 0, "message": "success",
  "data": {
    "items": [{
      "id": 1, "points": 50, "code": "abc123",
      "code_content": "street-service://merchant-point-pay?code=abc123",
      "remark": "", "is_active": true, "created_at": "...", "updated_at": "..."
    }]
  }
}
```

### 4.5 本商户积分支付流水

`GET /api/merchant/point-records?page=&page_size=&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&month=YYYY-MM`

响应含 `summary`：

```json
{
  "code": 0, "message": "success",
  "data": {
    "items": [{
      "id": 10, "merchant_id": 1, "merchant_name": "xx店",
      "member_id": 5, "member_name_masked": "张*",
      "member_phone_masked": "138****1234",
      "points": 20, "yuan_amount": "2.00", "balance_after": null,
      "request_no": "", "created_at": "..."
    }],
    "summary": { "record_count": 1, "total_points": 20, "total_yuan_amount": "2.00" },
    "total": 1, "page": 1, "page_size": 20
  }
}
```

用户姓名、手机号已脱敏。

### 4.6 商户结算单

`GET /api/merchant/settlements?page=&page_size=&year=2026&status=pending`

## 5. 后台管理 API（/api/admin）

### 5.1 认证

#### 登录

`POST /api/admin/auth/login`（限流 5 次/分钟/IP）

| 参数 | 类型 | 必填 |
| --- | --- | --- |
| username | string | 是 |
| password | string | 是 |

```json
{
  "code": 0, "message": "success",
  "data": {
    "access_token": "eyJ...", "token_type": "Bearer", "expires_in": 7200,
    "must_change_password": false,
    "admin": { "id": 1, "username": "admin", "email": "", "first_name": "",
      "last_name": "", "is_active": true, "is_staff": true,
      "is_backend_manager": true, "is_superuser": true, "last_login": null }
  }
}
```

> 三端（用户端 / 商户端 / 后台）登录响应都有一个 `must_change_password` 字段：本次提交的密码仍然是初始密码 `000000` 时为 `true`，前端应引导用户跳转改密；改密后该字段自动变回 `false`。它不阻断其他接口（软拦截）。详见 `16-10.19账号Excel导入与强制改密.md`。

#### 当前管理员信息

`GET /api/admin/auth/me`

### 5.2 公共

#### 枚举字典

`GET /api/admin/enums`

返回全部下拉选项，键为：`member_audit_statuses`、`member_genders`、`member_occupations`、`learning_content_types`、`report_category_codes`、`report_statuses`、`civic_feedback_statuses`、`problem_feedback_statuses`、`activity_statuses`、`activity_types`、`activity_checkin_statuses`、`elder_task_statuses`、`elder_feedback_statuses`、`point_change_types`、`point_source_types`、`merchant_settlement_period_types`、`merchant_settlement_statuses`、`merchant_category_codes`、`merchant_audit_statuses`。

#### 工作台汇总

`GET /api/admin/dashboard/summary`

```json
{
  "code": 0, "message": "success",
  "data": {
    "pending_member_audits": 3, "pending_merchant_audits": 2, "pending_reports": 5,
    "pending_civic_feedbacks": 2, "pending_problem_feedbacks": 1,
    "pending_activity_checkins": 4, "pending_elder_service_feedbacks": 2,
    "today_merchant_payment_count": 8, "today_merchant_payment_points": 160,
    "pending_merchant_settlements": 1
  }
}
```

### 5.3 后台账号

| 接口 | 说明 |
| --- | --- |
| `GET /api/admin/admin-users?keyword=&page=&page_size=` | 列表（仅后台业务管理员） |
| `POST /api/admin/admin-users` | 创建（username/password/email/姓名/is_backend_manager/is_active） |
| `GET /api/admin/admin-users/{user_id}` | 详情 |
| `PATCH /api/admin/admin-users/{user_id}` | 修改（email/姓名/is_backend_manager） |
| `POST /api/admin/admin-users/{user_id}/status` | 启用/停用 `{ "is_active": false }` |
| `POST /api/admin/admin-users/{user_id}/password` | 重置密码 `{ "password": "..." }` |

### 5.4 用户管理

| 接口 | 说明 |
| --- | --- |
| `GET /api/admin/members?keyword=&audit_status=&is_active=&page=&page_size=` | 列表（keyword 匹配昵称/姓名/手机号/微信号/住址） |
| `GET /api/admin/members/{member_id}` | 详情（含完整手机号） |
| `PATCH /api/admin/members/{member_id}` | 修改（nickname/phone/real_name/wechat_id/gender/occupation/is_party_member/address） |
| `POST /api/admin/members/{member_id}/status` | 启用/停用 `{ "is_active": bool }` |
| `POST /api/admin/members/{member_id}/audit` | 注册审核 `{ "action": "approve"|"reject", "remark": "" }`（reject 必填 remark，即用户端展示的驳回原因） |
| `GET /api/admin/members/{member_id}/points` | 积分账户与流水 |

### 5.5 学习管理

| 接口 | 说明 |
| --- | --- |
| `GET /api/admin/learning/contents?keyword=&status=active|inactive&is_announcement=&is_active=&page=&page_size=` | 内容列表 |
| `POST /api/admin/learning/contents` | 创建（title/cover/image/video/body/content_type/points/required_seconds/is_active/is_announcement） |
| `GET /api/admin/learning/contents/{content_id}` | 详情 |
| `PATCH /api/admin/learning/contents/{content_id}` | 修改 |
| `DELETE /api/admin/learning/contents/{content_id}` | 删除 |
| `POST /api/admin/learning/contents/{content_id}/status` | 上架/下架 `{ "is_active": bool }`（下架时自动取消置顶） |
| `POST /api/admin/learning/announcements/pinned` | 设置置顶公告 `{ "items": [{ "content_id": 1, "pin_order": 1 }, ...] }`（最多 3 条，顺序从 1 连续） |
| `GET /api/admin/learning/records?page=&page_size=` | 学习记录列表 |
| `GET /api/admin/learning/records/{record_id}` | 学习记录详情 |

### 5.6 服务阵地管理

| 接口 | 说明 |
| --- | --- |
| `GET /api/admin/service-locations?keyword=&is_active=&page=&page_size=` | 列表 |
| `POST /api/admin/service-locations` | 创建（name/address/business_hours/service_content/latitude/longitude/is_active） |
| `GET /api/admin/service-locations/{location_id}` | 详情 |
| `PATCH /api/admin/service-locations/{location_id}` | 修改 |
| `POST /api/admin/service-locations/{location_id}/status` | 展示/隐藏 `{ "is_active": bool }` |

### 5.7 随手拍管理

| 接口 | 说明 |
| --- | --- |
| `GET /api/admin/reports?keyword=&category_code=&status=&page=&page_size=` | 列表 |
| `GET /api/admin/reports/{report_id}` | 详情 |
| `PATCH /api/admin/reports/{report_id}` | 修改（category_code/title/description/location/points/image_urls） |
| `POST /api/admin/reports/{report_id}/review` | 审核 `{ "action": "approve"|"reject", "comment": "" }`（通过时发放积分） |

### 5.8 社情民意管理

| 接口 | 说明 |
| --- | --- |
| `GET /api/admin/civic-feedbacks?keyword=&status=&page=&page_size=` | 列表 |
| `GET /api/admin/civic-feedbacks/{feedback_id}` | 详情 |
| `PATCH /api/admin/civic-feedbacks/{feedback_id}` | 修改（title/content/material_urls/points） |
| `POST /api/admin/civic-feedbacks/{feedback_id}/review` | 处理 `{ "action": "accept"|"reject", "reply": "", "points": 0 }`（采纳时发放积分） |

### 5.9 问题反馈管理

| 接口 | 说明 |
| --- | --- |
| `GET /api/admin/problem-feedbacks?keyword=&status=&visibility_status=&member_id=&page=&page_size=` | 列表 |
| `GET /api/admin/problem-feedbacks/{feedback_id}` | 详情 |
| `PATCH /api/admin/problem-feedbacks/{feedback_id}` | 修改状态 |
| `POST /api/admin/problem-feedbacks/{feedback_id}/reply` | 回复 `{ "reply": "..." }`（自动置为已回复） |
| `POST /api/admin/problem-feedbacks/{feedback_id}/status` | 状态流转 `{ "status": "submitted|processing|replied|closed" }` |
| `POST /api/admin/problem-feedbacks/{feedback_id}/visibility` | 公开审核 `{ "visibility_status": "approved|rejected", "is_public": true }` |

### 5.10 活动管理

| 接口 | 说明 |
| --- | --- |
| `GET /api/admin/activities?status=&activity_type=&page=&page_size=` | 列表（含签到码等内部字段） |
| `POST /api/admin/activities` | 创建（title/body/location/坐标/start_time/end_time/points/activity_type/status） |
| `GET /api/admin/activities/{activity_id}` | 详情 |
| `PATCH /api/admin/activities/{activity_id}` | 修改 |
| `DELETE /api/admin/activities/{activity_id}` | 删除 |
| `POST /api/admin/activities/{activity_id}/status` | 状态 `{ "status": "draft|published|closed" }` |
| `GET /api/admin/activities/{activity_id}/checkin-code` | 签到码与二维码 |
| `GET /api/admin/activities/signups?activity_type=&page=&page_size=` | 报名记录 |
| `GET /api/admin/activities/signups/{signup_id}` | 报名详情 |
| `GET /api/admin/activities/checkins?activity_type=&page=&page_size=` | 签到记录 |
| `GET /api/admin/activities/checkins/{checkin_id}` | 签到详情 |
| `POST /api/admin/activities/checkins/{checkin_id}/review` | 签到审核 `{ "action": "confirm"|"reject", "comment": "" }`（确认时发放积分） |

### 5.11 助老服务管理

| 接口 | 说明 |
| --- | --- |
| `GET /api/admin/elder-services/relations?page=&page_size=` | 对口关系列表 |
| `POST /api/admin/elder-services/relations` | 创建 `{ "member_id": 1, "elder_name": "", "elder_address": "", "is_active": true }` |
| `GET /api/admin/elder-services/relations/{relation_id}` | 详情 |
| `PATCH /api/admin/elder-services/relations/{relation_id}` | 修改 |
| `DELETE /api/admin/elder-services/relations/{relation_id}` | 删除 |
| `POST /api/admin/elder-services/relations/{relation_id}/status` | 有效/无效 `{ "is_active": bool }` |
| `GET /api/admin/elder-services/tasks?page=&page_size=` | 任务列表 |
| `POST /api/admin/elder-services/tasks` | 创建（title/relation_id/description/location/points/status） |
| `GET /api/admin/elder-services/tasks/{task_id}` | 详情 |
| `PATCH /api/admin/elder-services/tasks/{task_id}` | 修改 |
| `DELETE /api/admin/elder-services/tasks/{task_id}` | 删除 |
| `POST /api/admin/elder-services/tasks/{task_id}/status` | 状态 `{ "status": "draft|published|closed" }` |
| `GET /api/admin/elder-services/feedbacks?status=&member_id=&relation_id=&keyword=&page=&page_size=` | 反馈列表 |
| `GET /api/admin/elder-services/feedbacks/{feedback_id}` | 反馈详情 |
| `PATCH /api/admin/elder-services/feedbacks/{feedback_id}` | 修改积分 `{ "points": 10 }` |
| `POST /api/admin/elder-services/feedbacks/{feedback_id}/review` | 审核 `{ "action": "approve"|"reject", "comment": "" }`（通过时发放积分） |

### 5.12 积分管理

| 接口 | 说明 |
| --- | --- |
| `GET /api/admin/points/accounts?page=&page_size=` | 积分账户列表 |
| `GET /api/admin/points/accounts/{account_id}` | 账户详情 |
| `GET /api/admin/points/records?page=&page_size=` | 积分流水列表 |
| `GET /api/admin/points/records/{record_id}` | 流水详情 |
| `GET /api/admin/points/manual-adjustments?page=&page_size=` | 人工调分记录 |
| `POST /api/admin/points/manual-adjustments` | 人工调分（限流 20/分钟）`{ "member_id": 1, "amount": 10, "reason": "..." }`（正加负扣） |
| `GET /api/admin/points/manual-adjustments/{adjustment_id}` | 调分详情 |
| `GET /api/admin/points/exchange-rules?page=&page_size=` | 兑换比例列表 |
| `POST /api/admin/points/exchange-rules` | 新建 `{ "points_per_yuan": 10, "is_active": true }` |
| `GET /api/admin/points/exchange-rules/{rule_id}` | 详情 |
| `PATCH /api/admin/points/exchange-rules/{rule_id}` | 修改 |
| `POST /api/admin/points/exchange-rules/{rule_id}/status` | 启用/停用 `{ "is_active": bool }` |

### 5.13 商户管理

| 接口 | 说明 |
| --- | --- |
| `GET /api/admin/merchants?keyword=&is_active=&audit_status=&page=&page_size=` | 列表（keyword 匹配名称/联系人/手机号/openid/用户名/所属社区；`audit_status` 为新增筛选） |
| `POST /api/admin/merchants` | 创建（openid/username/password/name/contact_name/phone/address/community/merchant_nature/坐标/category_code/business_hours/service_content/is_active）；后台自建商户直接 `audit_status=approved` |
| `GET /api/admin/merchants/{merchant_id}` | 详情 |
| `PATCH /api/admin/merchants/{merchant_id}` | 修改（支持 community/merchant_nature；手机号撞号返回 400） |
| `DELETE /api/admin/merchants/{merchant_id}` | 删除 |
| `POST /api/admin/merchants/{merchant_id}/audit` | **审核** `{ "action": "approve"\|"reject", "remark": "" }`；`approve` → `approved` + 启用，`reject` 必须带 `remark`（驳回原因）→ `rejected` + 停用 |
| `POST /api/admin/merchants/{merchant_id}/status` | 启用/停用 `{ "is_active": bool }` |
| `POST /api/admin/merchants/{merchant_id}/password` | 重置密码 |
| `GET /api/admin/merchants/{merchant_id}/fixed-code` | 商户固定码（旧） |
| `GET /api/admin/merchants/point-records?keyword=&merchant_id=&month=&date_from=&date_to=&page=&page_size=` | 商户支付流水（含 summary） |
| `GET /api/admin/merchants/{merchant_id}/point-records?month=&date_from=&date_to=&page=&page_size=` | 指定商户支付流水 |
| `GET /api/admin/merchants/point-codes?merchant_id=&is_active=&page=&page_size=` | 固定积分码列表 |
| `POST /api/admin/merchants/point-codes` | 新建固定码 `{ "merchant_id": 1, "points": 50, "remark": "" }` |
| `GET /api/admin/merchants/point-codes/{code_id}` | 固定码详情 |
| `PATCH /api/admin/merchants/point-codes/{code_id}` | 修改（points/remark/is_active） |
| `POST /api/admin/merchants/point-codes/{code_id}/status` | 启用/停用 `{ "is_active": bool }` |
| `DELETE /api/admin/merchants/point-codes/{code_id}` | 删除固定码 |
| `GET /api/admin/merchants/settlements?merchant_id=&status=&page=&page_size=` | 结算单列表 |
| `POST /api/admin/merchants/settlements` | 新建结算单 |
| `POST /api/admin/merchants/settlements/generate` | 按周期自动生成 `{ "merchant_id": 1, "period_type": "month", "period_label": "2026-08", "date_from": "2026-08-01", "date_to": "2026-08-31" }` |
| `GET /api/admin/merchants/settlements/{settlement_id}` | 结算单详情 |
| `PATCH /api/admin/merchants/settlements/{settlement_id}` | 修改 |
| `POST /api/admin/merchants/settlements/{settlement_id}/process` | 标记已处理 `{ "processor_name": "", "remark": "" }` |

### 5.14 账号 Excel 导入

批量初始化账号。**整批拒绝**：只要有一条不合格，一行都不写库，返回逐行错误清单；**不需要 migration**。详细字段与前端对接说明见 `16-10.19账号Excel导入与强制改密.md`。

| 接口 | 说明 |
| --- | --- |
| `GET /api/admin/imports/members/template` | 下载会员导入模板（xlsx 二进制） |
| `POST /api/admin/imports/members` | 导入会员，`multipart/form-data`，文件字段名 `file` |
| `GET /api/admin/imports/merchants/template` | 下载商户导入模板 |
| `POST /api/admin/imports/merchants` | 导入商户 |
| `GET /api/admin/imports/admin-users/template` | 下载后台账号导入模板 |
| `POST /api/admin/imports/admin-users` | 导入后台账号 |

文件限制：仅 `.xlsx`、≤2MB、≤500 行数据；按列名匹配表头，不看列顺序（多余列忽略，缺必填列整包报错）。

成功响应：

```json
{ "code": 0, "message": "success", "data": { "imported": 216, "message": "导入成功，共新增 216 个会员" } }
```

失败响应（HTTP 400）：`errors` 是**数组**，`row` 是 Excel 实际行号（表头 = 第 1 行）：

```json
{
  "code": 40000,
  "message": "校验未通过，共 2 处问题，已全部驳回，未写入任何会员",
  "errors": [
    { "row": 3, "column": "手机号", "value": "13800138000", "message": "该手机号已存在（会员「张三」，已通过，2026-08-12 注册）" },
    { "row": 7, "column": "性别", "value": "未知", "message": "性别只能填 男 或 女" }
  ]
}
```

导入结果：会员 / 商户一律 `audit_status=approved`、`is_active=true`，初始密码 `000000`；后台账号 `is_backend_manager=true`、`is_staff=true`。冲突键为手机号（会员 / 商户）与登录用户名（商户 / 后台账号）。

## 6. 附录：枚举取值

| 枚举 | 取值 |
| --- | --- |
| 用户审核 | `none` / `pending` / `approved` / `rejected` |
| 用户性别 | `男` / `女` |
| 用户职业 | `顺丰快递` / `京东快递` / `美团快递` / `达达快递` / `申通快递` / `淘宝闪购` / `中通快递` / `其他` |
| 商户审核 | `none` / `pending` / `approved` / `rejected` |
| 学习类型 | `article` / `image` / `video` |
| 随手拍分类 | `safety_hazard` / `environmental_hygiene` / `public_facility` / `other` / `good_deed` |
| 随手拍状态 | `pending` / `approved` / `rejected` |
| 社情民意状态 | `submitted` / `accepted` / `rejected` |
| 问题反馈状态 | `submitted` / `processing` / `replied` / `closed` |
| 问题反馈公开审核 | `pending` / `approved` / `rejected` |
| 活动状态 | `draft` / `published` / `closed` |
| 活动类型 | `volunteer` / `offline` |
| 签到状态 | `pending` / `confirmed` / `rejected` |
| 助老任务状态 | `draft` / `published` / `closed` |
| 助老反馈状态 | `pending` / `approved` / `rejected` |
| 积分变动 | 收入 `income` / 扣减 `expense` |
| 积分来源 | `learning` / `report` / `activity` / `elder_service` / `civic_feedback` / `manual` / `merchant_payment` |
| 商户分类 | `food` / `retail` / `repair` / `healthcare` / `life_service` / `other` |
| 结算周期 | `month` / `custom` |
| 结算状态 | `pending` / `processed` |

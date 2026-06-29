# 前端 API 需求文档（小程序端）

更新时间：2026-06-29

本文档只整理用户端小程序和商户端小程序仍需后端补齐或修正的接口。街道管理后台 H5、技术管理网站、后台审核操作类接口不放在本文档中，后续应单独整理。

> 说明：本文中的“审核状态、回复、积分发放、结算状态”等字段，是小程序端需要读取和展示的结果字段，不代表后台管理端接口定义。

## 一、统一约定

### 1. 基础约定

| 属性 | 建议值 |
|------|--------|
| 服务前缀 | `/api` |
| 数据格式 | `application/json`，上传接口使用 `multipart/form-data` |
| 认证方式 | `Authorization: Bearer <access_token>` |
| 时间格式 | ISO 8601，如 `2026-06-29T10:30:00+08:00` |
| 分页参数 | `page`、`page_size` |
| 分页响应 | `{ items, total, page, page_size }` |

### 2. 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

### 3. 错误响应

```json
{
  "code": 40001,
  "message": "错误信息",
  "errors": null
}
```

### 4. 统一登录过期错误

前端已经做了 token 过期引导，但需要后端统一错误结构，避免不同接口返回文案不一致。

| HTTP 状态 | code | message | 前端处理 |
|-----------|------|---------|----------|
| `401` | `40101` | `登录已过期，请重新登录` | 清空 token，弹登录引导 |
| `401` | `40102` | `缺少登录凭证` | 清空 token，弹登录引导 |
| `403` | `40301` | `当前账号无权限访问` | 提示无权限 |

## 二、优先级总览

| 优先级 | 模块 | 需求 |
|--------|------|------|
| P0 | 微信登录 | 用户端、商户端手机号一键登录正式接口 |
| P0 | 用户审核 | 用户资料提交、审核状态查询字段 |
| P0 | 随手拍 | 多图、分类、位置字段和审核结果展示字段 |
| P0 | 社情民意 | 用户提交、列表、回复、采纳状态和积分字段 |
| P0 | 问题反馈 | 用户提交、列表、处理状态和回复字段 |
| P0 | 老人服务 | 本人分配任务、反馈提交、反馈状态和重新提交规则 |
| P0 | 志愿活动 | 活动列表带当前用户报名状态、签到二维码格式、签到状态口径 |
| P0 | 商户积分支付 | 固定码、积分支付、流水筛选汇总、商户端结算记录 |
| P0 | 学习积分 | 学习内容媒体字段、视频可播放地址、完成学习服务端校验 |
| P1 | 上传资源 | 多图上传稳定性、完整 URL、业务关联 |
| P1 | 积分明细 | 商户支付、学习、随手拍、老人服务、活动签到等来源字段统一 |

## 三、认证与手机号登录

### 3.1 用户端手机号一键登录

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | POST |
| 接口路径 | `/api/auth/wechat-phone-login` |
| 认证方式 | 无 |
| 权限要求 | 微信小程序手机号授权后调用 |

## 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `login_code` | string | 否 | `uni.login` 获取的微信登录 code |
| `phone_code` | string | 是 | `getPhoneNumber` 返回的手机号授权 code |
| `encrypted_data` | string | 否 | 兼容旧版微信加密数据 |
| `iv` | string | 否 | 兼容旧版微信加密数据 |
| `platform` | string | 否 | 固定传 `user_mp` |

## 请求示例

```json
{
  "login_code": "wx-login-code",
  "phone_code": "wx-phone-code",
  "platform": "user_mp"
}
```

## 响应数据

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "token",
    "token_type": "Bearer",
    "expires_in": 604800,
    "member": {
      "id": 1,
      "openid": "openid",
      "nickname": "李师傅",
      "phone": "13800000000",
      "real_name": "李建国",
      "identity_type": "courier",
      "service_area_code": "east",
      "service_area_name": "东片区",
      "audit_status": "approved",
      "audit_remark": "",
      "is_elderly_care_worker": true,
      "is_active": true
    }
  }
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `member.audit_status` | string | `none`、`pending`、`approved`、`rejected` |
| `member.identity_type` | string | 建议值：`normal_user`、`courier` |
| `member.service_area_code` | string | 服务区域编码 |
| `member.service_area_name` | string | 服务区域名称 |
| `member.is_elderly_care_worker` | boolean | 是否已配置对口老人服务关系 |

## 错误响应

| HTTP 状态 | message |
|-----------|---------|
| 400 | `缺少手机号授权 code` |
| 400 | `微信手机号解析失败` |
| 403 | `用户已被禁用` |

### 3.2 商户端手机号一键登录

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | POST |
| 接口路径 | `/api/merchant/auth/wechat-phone-login` |
| 认证方式 | 无 |
| 权限要求 | 微信小程序手机号授权后调用 |

## 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `login_code` | string | 否 | `uni.login` 获取的微信登录 code |
| `phone_code` | string | 是 | `getPhoneNumber` 返回的手机号授权 code |
| `platform` | string | 否 | 固定传 `merchant_mp` |

## 响应数据

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "token",
    "token_type": "Bearer",
    "expires_in": 604800,
    "merchant": {
      "id": 1,
      "openid": "merchant-openid",
      "name": "暖心早餐店",
      "contact_name": "王店长",
      "phone": "13900000000",
      "address": "椿树街道便民服务点",
      "is_active": true
    }
  }
}
```

## 四、用户资料和审核状态

当前前端的信息审核页仍不能完全接入后端。小程序端需要提交姓名、身份类型、服务区域，并读取后端审核状态。

### 4.1 当前用户信息扩展

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | GET |
| 接口路径 | `/api/members/me` |
| 认证方式 | 用户 Bearer Token |
| 权限要求 | 当前登录用户 |

## 需补充响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `real_name` | string | 真实姓名 |
| `identity_type` | string | `normal_user`、`courier` |
| `service_area_code` | string | 服务区域编码 |
| `service_area_name` | string | 服务区域名称 |
| `audit_status` | string | `none`、`pending`、`approved`、`rejected` |
| `audit_remark` | string | 审核说明或驳回原因 |
| `is_elderly_care_worker` | boolean | 是否配置对口老人服务 |

### 4.2 提交或重新提交用户审核资料

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | POST |
| 接口路径 | `/api/members/audit-profile` |
| 认证方式 | 用户 Bearer Token |
| 权限要求 | 当前登录用户 |

## 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `real_name` | string | 是 | 真实姓名 |
| `identity_type` | string | 是 | `normal_user`、`courier` |
| `service_area_code` | string | 是 | 服务区域编码 |

## 响应数据

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 12,
    "member_id": 1,
    "real_name": "李建国",
    "identity_type": "courier",
    "service_area_code": "east",
    "service_area_name": "东片区",
    "audit_status": "pending",
    "audit_remark": "信息已提交，等待审核。",
    "submitted_at": "2026-06-29T10:00:00+08:00"
  }
}
```

## 业务规则

- `approved` 状态下不允许用户自行修改，需状态变为 `rejected` 后再改。
- `pending` 或 `rejected` 状态下允许重新提交，后一次覆盖前一次待审资料。
- 用户端业务操作应以后端 `audit_status = approved` 为准，后端也需要做权限校验，不能只依赖前端拦截。

## 五、上传资源能力

当前已有 `/api/uploads/images`，但前端在随手拍、社情民意、老人服务反馈中都需要稳定的多图和业务关联能力。

### 5.1 图片上传接口修正

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | POST |
| 接口路径 | `/api/uploads/images` |
| 认证方式 | 用户 Bearer Token |
| 请求格式 | `multipart/form-data` |

## 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `files` | file[] | 是 | 支持 1-10 张，单图也使用 `files` 字段 |
| `business_type` | string | 否 | `report`、`civic_feedback`、`elder_service_feedback`、`general` |
| `related_id` | string | 否 | 已存在业务记录 ID；新增提交前可为空 |

## 响应数据

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "files": [
      {
        "file_id": "uploads/report/20260629/a.png",
        "url": "https://8000.frp.chatgqt.top/media/uploads/report/20260629/a.png",
        "original_name": "a.png",
        "size": 123456,
        "mime_type": "image/png",
        "width": 1280,
        "height": 720,
        "created_at": "2026-06-29T10:00:00+08:00"
      }
    ]
  }
}
```

## 业务规则

- 单张图片最大 `10MB`。
- 一次最多 `10` 张。
- `url` 必须是小程序可访问的完整 URL，不能只返回相对路径。
- 后端应校验 MIME 类型，不应只看文件后缀。

## 六、随手拍上报

当前问题：前端页面支持问题分类、位置、问题描述和最多 10 张图片，但后端正式字段仍偏单图模型。需要后端支持分类和多图，小程序端读取审核结果。

### 6.1 提交随手拍

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | POST |
| 接口路径 | `/api/reports` |
| 认证方式 | 用户 Bearer Token |
| 权限要求 | 已登录且用户审核通过 |

## 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `category_code` | string | 是 | `road_light`、`well_cover`、`water_leak`、`road_damage`、`tree_fall`、`other` |
| `category_name` | string | 是 | 页面展示分类名 |
| `description` | string | 否 | 问题描述 |
| `location` | string | 是 | 用户填写的位置文本 |
| `image_urls` | string[] | 是 | 1-10 张现场图片 URL |

## 请求示例

```json
{
  "category_code": "road_light",
  "category_name": "路灯损坏",
  "description": "路口路灯夜间不亮，影响通行。",
  "location": "椿树街道东口人行道",
  "image_urls": [
    "https://8000.frp.chatgqt.top/media/uploads/report/a.png"
  ]
}
```

## 响应数据

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1001,
    "category_code": "road_light",
    "category_name": "路灯损坏",
    "title": "路灯损坏",
    "description": "路口路灯夜间不亮，影响通行。",
    "location": "椿树街道东口人行道",
    "image_urls": [
      "https://8000.frp.chatgqt.top/media/uploads/report/a.png"
    ],
    "points": 0,
    "status": "pending",
    "review_comment": "",
    "point_record_id": null,
    "created_at": "2026-06-29T10:00:00+08:00"
  }
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | `pending`、`approved`、`rejected` |
| `points` | integer | 审核通过后实际发放积分 |
| `review_comment` | string | 审核说明或驳回原因 |
| `point_record_id` | integer/null | 审核通过后生成的积分流水 ID |

### 6.2 我的随手拍列表和详情

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | GET |
| 接口路径 | `/api/reports`、`/api/reports/{report_id}` |
| 认证方式 | 用户 Bearer Token |
| 权限要求 | 只能查看当前用户自己的记录 |

## 查询参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `page` | integer | 否 | 1 | 页码 |
| `page_size` | integer | 否 | 20 | 每页数量 |
| `status` | string | 否 | 全部 | `pending`、`approved`、`rejected` |

返回字段与提交响应一致。

## 七、社情民意

当前前端社情民意页面仍是静态演示，需要用户端提交、列表、回复、采纳状态和积分字段。

### 7.1 提交社情民意

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | POST |
| 接口路径 | `/api/civic-feedbacks` |
| 认证方式 | 用户 Bearer Token |
| 权限要求 | 已登录且用户审核通过 |

## 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `title` | string | 是 | 提报标题 |
| `content` | string | 是 | 提报内容 |
| `material_urls` | string[] | 否 | 图片材料，最多 6 张 |

## 响应数据

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 301,
    "title": "建议增设临时停车引导牌",
    "content": "学校门口早高峰停车较乱，建议增加引导牌。",
    "material_urls": [],
    "material_count": 0,
    "status": "submitted",
    "reply": "",
    "points": 0,
    "point_record_id": null,
    "created_at": "2026-06-29T10:00:00+08:00",
    "reviewed_at": null
  }
}
```

### 7.2 我的社情民意列表和详情

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | GET |
| 接口路径 | `/api/civic-feedbacks`、`/api/civic-feedbacks/{id}` |
| 认证方式 | 用户 Bearer Token |
| 权限要求 | 只能查看当前用户自己的记录 |

## 查询参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `page` | integer | 否 | 页码 |
| `page_size` | integer | 否 | 每页数量 |
| `status` | string | 否 | `submitted`、`accepted`、`rejected` |

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | `submitted`、`accepted`、`rejected` |
| `reply` | string | 处理回复 |
| `points` | integer | 采纳后发放积分 |
| `point_record_id` | integer/null | 积分流水 ID |

## 八、问题反馈

当前前端问题反馈页面仍是静态演示，需要提交、列表、处理状态和回复字段。问题反馈不一定发积分。

### 8.1 提交问题反馈

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | POST |
| 接口路径 | `/api/problem-feedbacks` |
| 认证方式 | 用户 Bearer Token |
| 权限要求 | 已登录且用户审核通过 |

## 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `title` | string | 是 | 反馈标题 |
| `content` | string | 是 | 反馈内容 |

## 响应数据

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 401,
    "title": "积分明细展示疑问",
    "content": "学习完成后积分明细刷新较慢。",
    "status": "submitted",
    "reply": "",
    "created_at": "2026-06-29T10:00:00+08:00",
    "replied_at": null
  }
}
```

### 8.2 我的反馈列表和详情

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | GET |
| 接口路径 | `/api/problem-feedbacks`、`/api/problem-feedbacks/{id}` |
| 认证方式 | 用户 Bearer Token |
| 权限要求 | 当前用户 |

## 查询参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `page` | integer | 否 | 页码 |
| `page_size` | integer | 否 | 每页数量 |
| `status` | string | 否 | `submitted`、`processing`、`replied`、`closed` |

## 状态说明

| 状态 | 说明 |
|------|------|
| `submitted` | 已提交 |
| `processing` | 处理中 |
| `replied` | 已回复 |
| `closed` | 已关闭 |

## 九、老人服务

当前业务口径：老人服务不是公开领取任务，而是配置小哥与老人对口关系，小哥端只查看本人被分配的服务并提交反馈。

### 9.1 我的对口老人服务任务

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | GET |
| 接口路径 | `/api/elder-services/my-tasks` |
| 认证方式 | 用户 Bearer Token |
| 权限要求 | 审核通过且已配置对口老人关系的用户 |

## 查询参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `page` | integer | 否 | 1 | 页码 |
| `page_size` | integer | 否 | 20 | 每页数量 |
| `feedback_status` | string | 否 | 全部 | `none`、`pending`、`approved`、`rejected` |

## 响应数据

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "task_id": 501,
        "relation_id": 88,
        "title": "刘阿姨每周关爱探访",
        "description": "完成一次上门或电话关怀后提交反馈。",
        "elder_name_masked": "刘阿姨",
        "elder_address": "东里 3 号楼",
        "service_area_name": "东片区",
        "frequency": "每周一次",
        "points": 20,
        "task_status": "published",
        "feedback_status": "none",
        "latest_feedback": null
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `feedback_status` | string | `none`、`pending`、`approved`、`rejected` |
| `latest_feedback` | object/null | 最近一次反馈，包含审核状态和驳回原因 |

### 9.2 提交老人服务反馈

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | POST |
| 接口路径 | `/api/elder-services/tasks/{task_id}/feedback` |
| 认证方式 | 用户 Bearer Token |
| 权限要求 | 只能提交本人分配的服务任务 |

## 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `content` | string | 是 | 服务情况说明 |
| `image_urls` | string[] | 否 | 服务图片，建议最多 3 张 |

## 响应数据

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 601,
    "task_id": 501,
    "relation_id": 88,
    "content": "已完成电话关怀，老人状态稳定。",
    "image_urls": [],
    "status": "pending",
    "review_comment": "",
    "point_record_id": null,
    "created_at": "2026-06-29T10:00:00+08:00"
  }
}
```

## 业务规则

- `pending` 和 `approved` 状态下不允许重复提交。
- `rejected` 状态允许重新提交，新反馈进入 `pending`。
- 审核通过后生成积分流水，`source_type = elder_service`。

### 9.3 我的老人服务反馈记录

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | GET |
| 接口路径 | `/api/elder-services/feedbacks` |
| 认证方式 | 用户 Bearer Token |
| 权限要求 | 当前用户 |

需返回 `task_title`、`elder_name_masked`、`points`、`status`、`review_comment`、`point_record_id` 等字段，便于“服务记录”页展示。

## 十、志愿活动

当前用户端活动列表和我的任务页已接入部分接口，但仍存在状态口径和二维码格式不明确的问题。

### 10.1 活动列表补充当前用户参与状态

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | GET |
| 接口路径 | `/api/activities` |
| 认证方式 | 用户 Bearer Token |
| 权限要求 | 当前用户 |

## 需补充响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `user_signup_id` | integer/null | 当前用户报名记录 ID |
| `signup_status` | string | `not_joined`、`joined`、`cancelled` |
| `checkin_status` | string | `not_checked`、`pending`、`confirmed`、`rejected` |
| `checkin_at` | datetime/null | 签到时间 |
| `point_status` | string | `not_granted`、`granted` |

## 业务说明

- 如果用户已报名，活动列表不能仍显示“可报名”。
- 前端目前把 `pending` 和 `confirmed` 都展示为“已签到”，避免用户重复扫码。
- 建议后端明确：`pending` = 已签到待审核，`confirmed` = 签到审核通过并可发积分。

### 10.2 活动报名与取消报名

已存在接口仍需确保返回字段完整。

| 请求方式 | 接口路径 | 说明 |
|----------|----------|------|
| POST | `/api/activities/{activity_id}/signup` | 报名活动 |
| DELETE | `/api/activities/{activity_id}/signup` | 取消报名 |
| GET | `/api/activities/my-signups` | 我的活动记录 |

`GET /api/activities/my-signups` 需要返回：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | integer | 报名记录 ID |
| `activity_id` | integer | 活动 ID |
| `title` | string | 活动标题 |
| `body` | string | 活动说明 |
| `location` | string | 活动地点 |
| `start_time` | datetime | 活动开始时间 |
| `end_time` | datetime | 活动结束时间 |
| `points` | integer | 活动积分 |
| `signup_status` | string | `joined`、`cancelled` |
| `checkin_status` | string | `not_checked`、`pending`、`confirmed`、`rejected` |
| `checkin_at` | datetime/null | 签到时间 |
| `point_status` | string | `not_granted`、`granted` |
| `point_record_id` | integer/null | 积分流水 ID |

### 10.3 活动签到二维码格式

活动签到二维码内容建议统一为：

```text
street-service://activity-checkin?activity_id=<活动ID>&checkin_code=<签到码>
```

字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| `activity_id` | integer | 活动 ID |
| `checkin_code` | string | 签到码，后端校验 |

如需防伪，可以扩展：

```text
street-service://activity-checkin?activity_id=1&checkin_code=abc&expires_at=2026-06-29T12:00:00+08:00&signature=xxx
```

### 10.4 活动签到接口修正

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | POST |
| 接口路径 | `/api/activities/{activity_id}/checkin` |
| 认证方式 | 用户 Bearer Token |
| 权限要求 | 已报名当前活动 |

## 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `checkin_code` | string | 是 | 从二维码解析出的签到码 |
| `qr_content` | string | 否 | 二维码原始内容，便于后端兼容校验 |

## 响应数据

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 701,
    "activity_id": 100,
    "signup_id": 200,
    "status": "pending",
    "review_comment": "",
    "point_record_id": null,
    "checkin_at": "2026-06-29T10:00:00+08:00"
  }
}
```

## 错误响应

| HTTP 状态 | message |
|-----------|---------|
| 400 | `签到码无效` |
| 400 | `当前活动未报名` |
| 400 | `当前活动已签到` |
| 400 | `不在签到时间范围内` |

## 十一、学习积分

当前前端已按 `content_type` 展示图文、图片、视频，但需要后端确保媒体字段、视频地址和完成规则可靠。

### 11.1 学习内容列表和详情字段修正

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | GET |
| 接口路径 | `/api/learning/contents`、`/api/learning/contents/{content_id}` |
| 认证方式 | 用户 Bearer Token |

## 必需字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | integer | 内容 ID |
| `title` | string | 标题 |
| `content_type` | string | `article`、`image`、`video` |
| `cover_url` | string/null | 封面图完整 URL |
| `body` | string | 正文，支持 HTML 或小程序 rich-text 可解析内容 |
| `image_urls` | string[] | 图片内容的图片列表 |
| `video_url` | string/null | 视频完整 URL |
| `points` | integer | 完成后积分 |
| `required_seconds` | integer | 最低学习秒数 |
| `is_completed` | boolean | 当前用户是否已完成 |
| `completed_at` | datetime/null | 完成时间 |

## 业务规则

- 前端不使用副标题字段，后端可以不返回 `subtitle`。
- `cover_url`、`image_urls`、`video_url` 必须返回完整可访问 URL。
- `video_url` 所在域名必须已配置到微信小程序合法下载或 request 域名，否则小程序无法播放。
- `content_type = video` 时必须有 `video_url`；无视频地址时前端只能显示异常提示。

### 11.2 完成学习接口修正

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | POST |
| 接口路径 | `/api/learning/contents/{content_id}/complete` |
| 认证方式 | 用户 Bearer Token |

## 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `learned_seconds` | integer | 是 | 前端记录学习秒数 |
| `reached_bottom` | boolean | 否 | 图文/图片内容是否到达底部 |

## 响应数据

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 801,
    "content_id": 12,
    "learned_seconds": 35,
    "is_completed": true,
    "completed_at": "2026-06-29T10:00:00+08:00",
    "point_record_id": 9001,
    "points_granted": 12
  }
}
```

## 业务规则

- 接口必须幂等：同一用户同一内容重复完成，不重复发积分。
- 后端应校验 `learned_seconds >= required_seconds`。
- 如果内容已下架，不能继续完成学习。

### 11.3 我的学习记录

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | GET |
| 接口路径 | `/api/learning/records` |
| 认证方式 | 用户 Bearer Token |

需返回当前用户每个学习内容的完成记录，包含 `content_id`、`learned_seconds`、`is_completed`、`completed_at`、`point_record_id`。

## 十二、积分余额和积分明细

### 12.1 当前积分余额

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | GET |
| 接口路径 | `/api/points/balance` |
| 认证方式 | 用户 Bearer Token |

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "balance": 2680
  }
}
```

### 12.2 积分明细字段统一

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | GET |
| 接口路径 | `/api/points/records` |
| 认证方式 | 用户 Bearer Token |

## 需要稳定返回的字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | integer | 流水 ID |
| `amount` | integer | 变动积分 |
| `change_type` | string | `income`、`expense` |
| `source_type` | string | `learning`、`report`、`activity`、`elder_service`、`civic_feedback`、`merchant_payment`、`manual_adjust` |
| `source_id` | string | 来源业务 ID |
| `reason` | string | 页面展示文案 |
| `balance_after` | integer/null | 变动后余额 |
| `merchant_id` | integer/null | 商户积分支付对应商户 ID |
| `merchant_name` | string | 商户名称 |
| `yuan_amount` | string/null | 商户积分支付折算金额 |
| `request_no` | string | 商户积分支付请求号 |
| `created_at` | datetime | 创建时间 |

## 十三、商户积分支付

### 13.1 商户固定码接口补充字段

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | GET |
| 接口路径 | `/api/merchant/fixed-code` |
| 认证方式 | 商户 Bearer Token |

## 需补充响应字段

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "merchant_id": 1,
    "merchant_name": "暖心早餐店",
    "code_content": "street-service://merchant-pay?merchant_id=1",
    "code_status": "active",
    "points_per_yuan": 100,
    "rule_version": "2026-H1",
    "updated_at": "2026-06-29T10:00:00+08:00"
  }
}
```

### 13.2 用户端扫码支付信息

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | GET |
| 接口路径 | `/api/merchants/{merchant_id}/payment-info` |
| 认证方式 | 用户 Bearer Token |

## 响应数据

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "merchant_id": 1,
    "merchant_name": "暖心早餐店",
    "phone": "13900000000",
    "address": "椿树街道便民服务点",
    "points_per_yuan": 100,
    "balance": 120
  }
}
```

### 13.3 用户端提交商户积分支付

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | POST |
| 接口路径 | `/api/merchants/{merchant_id}/point-payments` |
| 认证方式 | 用户 Bearer Token |

## 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `points` | integer | 是 | 本次要抵扣的积分 |
| `request_no` | string | 否 | 前端请求号；同一商户同一请求号幂等 |

## 响应数据

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 12,
    "merchant_id": 1,
    "merchant_name": "暖心早餐店",
    "points": 100,
    "yuan_amount": "1.00",
    "balance_after": 20,
    "request_no": "mpay_1_123",
    "created_at": "2026-06-29T10:00:00+08:00"
  }
}
```

## 业务规则

- 商户必须启用。
- `points` 必须大于 0。
- 用户积分余额必须足够。
- 必须存在启用的积分兑元比例。
- `request_no` 非空时，同一商户重复提交同一请求号返回原流水，不重复扣分。

## 十四、商户端积分流水和结算

### 14.1 商户积分流水筛选和汇总

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | GET |
| 接口路径 | `/api/merchant/point-records` |
| 认证方式 | 商户 Bearer Token |

## 查询参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `page` | integer | 否 | 1 | 页码 |
| `page_size` | integer | 否 | 20 | 每页数量 |
| `date_from` | date | 否 | 空 | 开始日期 |
| `date_to` | date | 否 | 空 | 结束日期 |
| `month` | string | 否 | 空 | `YYYY-MM`，用于月度汇总 |

## 响应数据

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 12,
        "merchant_id": 1,
        "merchant_name": "暖心早餐店",
        "member_id": 3,
        "member_name_masked": "李*",
        "member_phone_masked": "138****0000",
        "points": 100,
        "yuan_amount": "1.00",
        "balance_after": 20,
        "request_no": "mpay_1_123",
        "created_at": "2026-06-29T10:00:00+08:00"
      }
    ],
    "summary": {
      "record_count": 1,
      "total_points": 100,
      "total_yuan_amount": "1.00"
    },
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

### 14.2 商户端结算记录

## 接口信息

| 属性 | 值 |
|------|-----|
| 请求方式 | GET |
| 接口路径 | `/api/merchant/settlements` |
| 认证方式 | 商户 Bearer Token |

## 查询参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `page` | integer | 否 | 页码 |
| `page_size` | integer | 否 | 每页数量 |
| `year` | integer | 否 | 年份 |
| `status` | string | 否 | `pending`、`processed` |

## 响应数据

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 100,
        "merchant_id": 1,
        "merchant_name": "暖心早餐店",
        "period_type": "half_year",
        "period_label": "2026 年上半年",
        "date_from": "2026-01-01",
        "date_to": "2026-06-30",
        "record_count": 126,
        "total_points": 15120,
        "total_yuan_amount": "151.20",
        "status": "pending",
        "processed_at": null,
        "processor_name": "",
        "remark": ""
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

## 业务说明

- 商户端“结清页”不能只靠前端从流水临时汇总，应由后端返回结算批次。
- 商户端只查看自己的结算记录。

## 十五、当前不应继续使用的旧接口

以下接口已不符合当前扫码优惠业务口径，不应作为用户端或商户端主链路继续开发：

| 方法 | 路径 | 原用途 |
|------|------|--------|
| GET | `/api/merchant-products` | 商品列表 |
| GET | `/api/merchant-products/{product_id}` | 商品详情 |
| POST | `/api/merchant-products/{product_id}/redeem` | 商品兑换 |
| GET | `/api/product-redemptions` | 用户商品兑换记录 |
| GET | `/api/merchant/redemptions` | 商户商品兑换记录 |
| POST | `/api/merchant/redemptions/{redemption_id}/complete` | 商户确认交付 |
| GET | `/api/merchant/redemptions/summary` | 商户月度兑换汇总 |

## 十六、建议后端优先交付顺序

1. 先补用户端和商户端手机号正式登录，统一 token 过期错误。
2. 补用户审核资料和审核状态字段，保证前端业务权限不再只靠本地状态。
3. 补随手拍多图、分类、位置字段，解决当前上报与记录展示闭环。
4. 补老人服务本人分配任务、反馈状态和重新提交规则。
5. 补志愿活动列表用户状态、签到二维码格式和签到状态口径。
6. 补商户积分流水日期筛选、汇总和商户端结算记录接口。
7. 补社情民意、问题反馈接口，替换当前静态演示。
8. 修正学习内容媒体字段和视频可播放地址，并完成学习服务端幂等校验。

# 前端对接-后端 MVP 接口补充说明

本文档只说明本轮后端 MVP 新增接口和已有接口字段变更。基础响应结构、登录认证、分页规则仍以 `docs/API接口文档.md` 为准。

## 1. 基础约定

- API 前缀：`/api`
- 认证方式：`Authorization: Bearer <access_token>`
- 成功响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

- 错误响应：

```json
{
  "code": 40001,
  "message": "错误信息",
  "errors": null
}
```

## 2. 新增接口

### 2.1 上传图片

`POST /api/uploads/images`

认证：用户 token 或商户 token。

请求格式：`multipart/form-data`

请求字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `files` | file[] | 是 | 图片文件列表；单图也使用 `files` |
| `business_type` | string | 否 | 业务类型，默认 `general` |
| `related_id` | string | 否 | 已存在业务记录 ID；新增业务提交前可为空 |

`business_type` 可用值：

| 值 | 说明 |
| --- | --- |
| `report` | 随手拍 |
| `elder_service_feedback` | 助老服务反馈 |
| `merchant_product` | 商户商品 |
| `learning_content` | 学习内容 |
| `general` | 通用上传 |

限制：

- 允许 MIME：`image/jpeg`、`image/png`、`image/webp`
- 单张图片最大：`10MB`
- 单次最多：`10` 张

响应 `data` 示例：

```json
{
  "files": [
    {
      "file_id": "uploads/report/xxx.jpg",
      "url": "https://example.com/media/uploads/report/xxx.jpg",
      "original_name": "photo.jpg",
      "size": 12345,
      "mime_type": "image/jpeg",
      "created_at": "2026-06-26T10:00:00+08:00"
    }
  ]
}
```

前端对接建议：

- 随手拍和助老反馈当前仍是单图业务字段，上传后取 `data.files[0].url` 传给业务接口的 `image`。
- 本轮没有新增随手拍/助老反馈多图正式模型。

### 2.2 取消活动报名

`DELETE /api/activities/{activity_id}/signup`

认证：用户 token。

路径参数：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `activity_id` | integer | 活动 ID |

响应 `data` 示例：

```json
{
  "activity_id": 10,
  "signup_status": "cancelled",
  "cancelled_at": "2026-06-26T10:00:00+08:00"
}
```

业务规则：

- 只能取消当前登录用户自己的报名。
- 已签到的报名不能取消。
- MVP 采用删除报名记录的方式，不保留取消历史列表。

### 2.3 商户列表

`GET /api/merchants`

认证：用户 token。

说明：用于用户端普通入口展示可兑换商户列表。用户点击某个商户后，再进入该商户商品列表。

查询参数：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `page` | integer | 否 | 页码 |
| `page_size` | integer | 否 | 每页数量 |

响应 `data` 示例：

```json
{
  "items": [
    {
      "id": 1,
      "name": "便民超市",
      "contact_name": "张三",
      "phone": "13900000000",
      "address": "街道服务中心一楼",
      "is_active": true
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

响应 `data.items[]` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | integer | 商户 ID |
| `name` | string | 商户名称 |
| `contact_name` | string | 联系人 |
| `phone` | string | 手机号 |
| `address` | string | 经营地址 |
| `is_active` | boolean | 是否启用 |

前端对接建议：

- 商品兑换入口采用普通页面流转：商户列表 -> 商户商品列表 -> 商品兑换。
- 点击某个商户后调用 `GET /api/merchant-products?merchant_id=<商户ID>`。
- MVP 不提供商户商品兑换入口码，不做扫码进入兑换列表。

## 3. 已有接口字段变更

### 3.1 学习内容列表/详情

接口：

- `GET /api/learning/contents`
- `GET /api/learning/contents/{content_id}`

新增返回字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `content_type` | string | 内容类型：`article`、`image`、`video` |
| `cover_url` | string | 封面 URL，当前与 `cover` 一致 |
| `image_urls` | string[] | 图片 URL 数组；MVP 暂返回空数组 |
| `video_url` | string | 视频 URL；MVP 暂返回空字符串 |

响应项示例：

```json
{
  "id": 1,
  "title": "安全宣传",
  "cover": "https://example.com/media/learning/covers/a.jpg",
  "cover_url": "https://example.com/media/learning/covers/a.jpg",
  "body": "正文",
  "content_type": "article",
  "image_urls": [],
  "video_url": "",
  "points": 5,
  "required_seconds": 60,
  "is_active": true
}
```

### 3.2 活动报名和我的报名

接口：

- `POST /api/activities/{activity_id}/signup`
- `GET /api/activities/my-signups`

新增返回字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `title` | string | 活动标题 |
| `body` | string | 活动正文 |
| `location` | string | 活动地点 |
| `start_time` | datetime | 活动开始时间 |
| `end_time` | datetime | 活动结束时间 |
| `points` | integer | 活动积分 |
| `signup_status` | string | `joined` |
| `cancelled_at` | datetime/null | 列表中通常为 `null` |
| `checkin_status` | string | `not_checked`、`pending`、`confirmed`、`rejected` |
| `checkin_at` | datetime/null | 签到提交时间 |
| `point_status` | string | `not_granted`、`granted` |
| `point_record_id` | integer/null | 关联积分流水 ID |

响应项示例：

```json
{
  "id": 1,
  "activity_id": 10,
  "title": "社区活动",
  "body": "活动说明",
  "location": "街道服务中心",
  "start_time": "2026-06-26T09:00:00+08:00",
  "end_time": "2026-06-26T11:00:00+08:00",
  "points": 10,
  "signup_status": "joined",
  "created_at": "2026-06-25T10:00:00+08:00",
  "cancelled_at": null,
  "checkin_status": "pending",
  "checkin_at": "2026-06-26T09:30:00+08:00",
  "point_status": "not_granted",
  "point_record_id": null
}
```

### 3.3 积分明细

接口：

- `GET /api/points/records`

新增返回字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `balance_after` | integer/null | 本次变动后的余额；历史记录可能为空 |

响应项示例：

```json
{
  "id": 1,
  "amount": 10,
  "change_type": "income",
  "source_type": "learning",
  "source_id": "5",
  "reason": "完成学习：安全宣传",
  "balance_after": 30,
  "created_at": "2026-06-26T10:00:00+08:00"
}
```

### 3.4 商品列表按商户筛选

接口：

- `GET /api/merchant-products`

新增查询参数：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `merchant_id` | integer | 否 | 商户 ID；传入后只返回该商户上架商品 |

前端流程：

- 商户列表页：调用 `GET /api/merchants`。
- 商户商品页：调用 `GET /api/merchant-products?merchant_id=<商户ID>`。
- 商品兑换：调用 `POST /api/merchant-products/{product_id}/redeem`。

### 3.5 商品兑换记录

接口：

- `POST /api/merchant-products/{product_id}/redeem`
- `GET /api/product-redemptions`
- `GET /api/merchant/redemptions`
- `POST /api/merchant/redemptions/{redemption_id}/complete`

新增返回字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `merchant_name` | string | 商户名称 |
| `member_name_masked` | string | 用户昵称脱敏 |
| `member_phone_masked` | string | 用户手机号脱敏 |
| `point_record_id` | integer/null | 关联积分流水 ID |

响应项示例：

```json
{
  "id": 1,
  "merchant_id": 2,
  "merchant_name": "便民超市",
  "product_id": 3,
  "product_name": "兑换商品",
  "member_id": 4,
  "member_name_masked": "张*",
  "member_phone_masked": "138****0000",
  "points_spent": 20,
  "status": "pending",
  "point_record_id": 9,
  "created_at": "2026-06-26T10:00:00+08:00"
}
```

## 4. 本轮仍未实现的能力

- 微信手机号解密登录。
- 用户信息审核、后台审核 API。
- 助老服务对口老人关系和任务分配。
- 固定二维码积分抵扣、固定优惠规则、抵扣流水。
- 商户结算金额和历史结清。
- 社情民意、问题反馈。
- 随手拍分类、多图正式模型。

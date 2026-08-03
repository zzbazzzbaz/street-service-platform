# 前端 API 需求文档（甲方需求变更）

> 版本：1.2  
> 日期：2026-08-03  
> 适用范围：用户端微信小程序、街道管理后台 H5  
> 本次范围：结对帮扶主动上传、公共留言板、后台来源识别

## 1. 变更背景

本次甲方需求对两项业务做了实质性调整：

1. 结对帮扶不再由后台发布任务。街道后台只维护“小哥-老人”固定关系，小哥完成一次帮扶后随时上传一条独立记录，后台审核记录。
2. 留言反馈改为公共留言板。本人始终可以查看自己的留言，只有后台公开审核通过的留言才能进入公共列表。

旧的老人服务任务接口不能继续作为新业务主流程：

- `GET /api/elder-services/my-tasks`
- `GET /api/elder-services/tasks`
- `GET /api/elder-services/tasks/{task_id}`
- `POST /api/elder-services/tasks/{task_id}/feedback`
- 后台老人服务任务创建、编辑、发布和关闭接口

旧接口可以暂时保留用于历史数据兼容，但新数据不得再依赖 `task_id`。

### 1.1 当前线上接口核对结果

2026-08-03 已对照线上 OpenAPI：`https://commu.iloveminmeng.com/api/openapi.json`。当前后端仍以旧任务模型为主，本文件要求的新业务接口尚未完整上线：

- 尚无 `GET /api/elder-services/my-relation`。
- 尚无不带任务 ID 的 `POST /api/elder-services/feedbacks`，目前只有 `POST /api/elder-services/tasks/{task_id}/feedback`。
- 现有 `GET /api/elder-services/feedbacks` 返回结构仍要求 `task_id`，需要改造成关系快照模式。
- 尚无 `GET /api/problem-feedbacks/public`。
- 尚无 `POST /api/admin/problem-feedbacks/{feedback_id}/visibility`，现有留言响应也没有正式声明 `visibility_status` 和 `is_public`。
- 后台对口关系接口仍保留 `frequency` 字段，后台和小程序现已隐藏该字段，新业务不应再依赖它。
- 后台仍存在可修改用户原始留言、帮扶正文和图片的 PATCH 能力，应按本文 4.4 和 5.4 的要求收紧。帮扶记录 PATCH 可以保留积分配置能力，但只能修改 `points`。

因此，本文件仍是待后端实现/修正的 API 需求，不代表线上接口已经具备这些能力。前端当前出现“结对帮扶同步失败”时，根因是 `my-relation` 接口尚未上线，不能将其当作“用户未配置关系”。

## 2. 通用约定

### 2.1 基础地址

- 小程序及后台 API 基础地址：`https://commu.iloveminmeng.com/api`
- 文档下方均使用包含 `/api` 的完整业务路径。

### 2.2 响应格式

成功响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

分页响应的 `data`：

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

失败响应：

```json
{
  "code": 40001,
  "message": "具体业务错误说明",
  "data": null,
  "errors": null
}
```

### 2.3 鉴权规则

- 小程序用户接口：`Authorization: Bearer <user_access_token>`。
- 后台接口：`Authorization: Bearer <admin_access_token>`。
- 公共留言列表允许未登录访问，不要求 token。
- 写操作必须在后端校验用户是否启用、资料是否审核通过，以及是否具备对应身份。

### 2.4 分页参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | integer | 否 | `1` | 页码，从 1 开始 |
| `page_size` | integer | 否 | `20` | 每页数量，建议最大 100 |

## 3. 接口清单

| 优先级 | 类型 | 接口 | 用途 | 2026-08-03 线上状态 |
| --- | --- | --- | --- | --- |
| P0 | 新增 | `GET /api/elder-services/my-relation` | 查询当前小哥的有效对口关系 | 缺失 |
| P0 | 新增/改造 | `POST /api/elder-services/feedbacks` | 不依赖任务，主动提交帮扶记录 | 缺失，仅有旧任务反馈接口 |
| P0 | 调整 | `GET /api/elder-services/feedbacks` | 查询本人全部帮扶记录 | 已有，但仍返回旧任务结构 |
| P0 | 调整 | `GET /api/admin/elder-services/feedbacks` | 后台查询帮扶记录 | 已有，筛选参数和返回字段待补齐 |
| P0 | 调整 | `GET /api/admin/elder-services/feedbacks/{feedback_id}` | 后台查看帮扶记录详情 | 已有，返回字段待核实/补齐 |
| P0 | 调整 | `POST /api/admin/elder-services/feedbacks/{feedback_id}/review` | 后台审核帮扶记录 | 已有，需保证幂等和新业务规则 |
| P0 | 调整 | `/api/admin/elder-services/relations` 相关接口 | 维护固定对口关系 | 已有，但仍保留旧 `frequency` 字段 |
| P0 | 新增 | `GET /api/problem-feedbacks/public` | 查询公开留言板 | 缺失 |
| P0 | 调整 | `POST /api/problem-feedbacks` | 新留言默认进入公开待审核 | 已有，但缺少公开审核字段 |
| P0 | 调整 | `GET /api/problem-feedbacks` | 查询本人全部留言及公开状态 | 已有，但缺少公开审核字段 |
| P0 | 调整 | `GET /api/admin/problem-feedbacks` | 后台查询留言及公开状态 | 已有，公开状态筛选和返回字段待补齐 |
| P0 | 新增 | `POST /api/admin/problem-feedbacks/{feedback_id}/visibility` | 后台审核留言是否公开 | 缺失 |
| P0 | 权限收紧 | 后台留言、帮扶记录 PATCH 接口 | 禁止修改用户提交的原始内容；帮扶 PATCH 仅允许配置积分 | 现有接口仍允许修改，需修正 |

## 4. 结对帮扶接口

### 4.1 查询我的对口关系

`GET /api/elder-services/my-relation`

认证：用户 token。

权限：当前用户应为审核通过的小哥。

响应 `data`：

```json
{
  "id": 12,
  "member_id": 35,
  "elder_name": "张阿姨",
  "elder_address": "椿树街道幸福里 2 号楼",
  "is_active": true,
  "created_at": "2026-07-24T09:00:00+08:00",
  "updated_at": "2026-07-24T09:00:00+08:00"
}
```

字段说明：

| 字段 | 类型 | 必须返回 | 说明 |
| --- | --- | --- | --- |
| `id` | integer | 是 | 对口关系 ID |
| `member_id` | integer | 是 | 当前小哥用户 ID |
| `elder_name` | string | 是 | 老人姓名 |
| `elder_address` | string | 是 | 老人服务地址 |
| `is_active` | boolean | 是 | 关系是否有效 |
| `created_at` | datetime | 否 | 创建时间 |
| `updated_at` | datetime | 否 | 更新时间 |

业务规则：

- 只能返回当前 token 所属用户的关系，禁止由前端传入 `member_id` 查询其他人的老人信息。
- 当前没有有效关系时返回 HTTP `200` 且 `data: null`，不要返回 `404`。
- 本期前端按“一个小哥同时只有一条有效关系”实现，后端应限制重复创建有效关系。
- 停用关系后，该接口返回 `null`，历史帮扶记录不受影响。

### 4.2 主动提交帮扶记录

`POST /api/elder-services/feedbacks`

认证：用户 token，用户资料审核通过，身份为小哥。

请求体：

```json
{
  "content": "今天上门看望老人，协助整理房间并检查了用电安全。",
  "image_urls": [
    "https://commu.iloveminmeng.com/media/uploads/elder_service/20260724-001.jpg"
  ]
}
```

| 字段 | 类型 | 必填 | 约束 |
| --- | --- | --- | --- |
| `content` | string | 是 | 去除首尾空格后 1-500 字 |
| `image_urls` | string[] | 是 | 1-10 张；每项必须为平台上传接口返回的有效图片地址 |

响应 `data`：

```json
{
  "id": 86,
  "relation_id": 12,
  "member_id": 35,
  "elder_name": "张阿姨",
  "elder_address": "椿树街道幸福里 2 号楼",
  "content": "今天上门看望老人，协助整理房间并检查了用电安全。",
  "image_urls": [
    "https://commu.iloveminmeng.com/media/uploads/elder_service/20260724-001.jpg"
  ],
  "status": "pending",
  "review_comment": "",
  "point_record_id": null,
  "created_at": "2026-07-24T10:30:00+08:00"
}
```

业务规则：

- 请求体不接收 `task_id`、`member_id`、`relation_id`、老人姓名或老人地址。
- 后端根据当前 token 查找有效关系，并自动绑定 `member_id` 和 `relation_id`。
- 至少上传 1 张帮扶现场照片；缺少图片时后端应拒绝提交并返回明确字段错误。
- 建议在记录中保存提交时的 `elder_name`、`elder_address` 快照，避免后续调整关系导致历史记录内容变化。
- 没有有效对口关系时拒绝提交，建议返回 HTTP `403` 和明确提示“暂未配置有效的结对帮扶关系”。
- 每次提交创建一条新记录。同一用户、同一关系允许重复提交，不得沿用“同一任务只能反馈一次”的旧限制。
- 新记录状态固定为 `pending`。
- 后端必须校验图片 URL 属于平台允许的上传目录，不能直接信任任意外部 URL。

### 4.3 查询我的帮扶记录

`GET /api/elder-services/feedbacks`

认证：用户 token。

查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `page` | integer | 否 | 页码 |
| `page_size` | integer | 否 | 每页数量 |
| `status` | string | 否 | `pending`、`approved`、`rejected` |

响应：分页结构，`items[]` 使用 4.2 的响应字段，并增加以下审核字段：

| 字段 | 类型 | 必须返回 | 说明 |
| --- | --- | --- | --- |
| `review_comment` | string | 是 | 未审核时返回空字符串 |
| `reviewed_at` | datetime/null | 否 | 审核时间 |
| `point_record_id` | integer/null | 是 | 实际产生的积分流水 ID；未发积分时为 `null` |
| `points` | integer/null | 否 | 实际发放积分；没有则返回 `null` 或 `0` |

业务规则：

- 只能返回当前用户自己的记录。
- 按 `created_at` 倒序返回。
- 不应再要求或依赖 `task_id`、`task_title`。
- 对口关系停用后，历史记录仍然可以查询。

### 4.4 后台查询帮扶记录

#### 列表

`GET /api/admin/elder-services/feedbacks`

查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `page` | integer | 否 | 页码 |
| `page_size` | integer | 否 | 每页数量 |
| `status` | string | 否 | `pending`、`approved`、`rejected` |
| `member_id` | integer | 否 | 按小哥筛选 |
| `relation_id` | integer | 否 | 按对口关系筛选 |
| `keyword` | string | 否 | 搜索小哥姓名、手机号或老人姓名 |

#### 详情

`GET /api/admin/elder-services/feedbacks/{feedback_id}`

列表和详情至少返回：

```json
{
  "id": 86,
  "relation_id": 12,
  "member_id": 35,
  "member_name": "李师傅",
  "member_phone": "138****5678",
  "elder_name": "张阿姨",
  "elder_address": "椿树街道幸福里 2 号楼",
  "content": "今天上门看望老人，协助整理房间并检查了用电安全。",
  "image_urls": [],
  "status": "pending",
  "review_comment": "",
  "reviewed_at": null,
  "point_record_id": null,
  "created_at": "2026-07-24T10:30:00+08:00",
  "source_type": "elder_service"
}
```

要求：

- `member_name` 优先返回实名，手机号返回脱敏值。
- 返回老人姓名和地址，不要要求前端通过旧 `task_id` 二次查询。
- `image_urls` 统一返回数组，没有图片时返回 `[]`。
- `source_type` 固定为 `elder_service`，用于后台识别记录来源。
- 帮扶正文、图片、提交人和老人信息快照均为用户提交记录，后台只能查看和审核，不得修改。
- 线上现有 `PATCH /api/admin/elder-services/feedbacks/{feedback_id}` 暴露了 `content`、`image`、`image_urls` 修改能力。请移除这些可写字段，该接口仅保留 `points` 配置能力，供后台像随手拍一样在审核前设置本条记录的奖励积分。

后台配置帮扶积分：

`PATCH /api/admin/elder-services/feedbacks/{feedback_id}`

```json
{
  "points": 10
}
```

要求：

- `points` 为大于或等于 0 的整数。
- 只有 `pending` 状态的记录允许修改积分值。
- 该接口不得接受或修改 `content`、`image`、`image_urls`、提交人、老人信息或创建时间。
- 街道管理后台的帮扶记录详情中需要提供积分输入控件，交互方式与随手拍审核一致。

### 4.5 后台审核帮扶记录

`POST /api/admin/elder-services/feedbacks/{feedback_id}/review`

通过：

```json
{
  "action": "approve",
  "comment": "记录完整，审核通过"
}
```

驳回：

```json
{
  "action": "reject",
  "comment": "现场照片不清晰，请重新提交"
}
```

业务规则：

- 只有 `pending` 状态可以审核。
- `reject` 时 `comment` 必填。
- 审核通过时，读取后台为该条帮扶记录配置的 `points`，给提交用户发放积分并生成积分流水。
- 审核驳回时不得发放积分。
- 积分值不再从老人服务任务读取，完全以帮扶记录审核页面配置的值为准。
- 状态更新、积分入账和 `point_record_id` 回写必须在同一事务中完成。
- 已审核记录重复审核返回 HTTP `409`，不得重复发放积分。
- 积分流水建议使用 `source_type = elder_service`、`source_id = feedback_id`，并建立唯一约束保证幂等。

### 4.6 后台维护对口关系

继续使用以下接口：

- `GET /api/admin/elder-services/relations`
- `POST /api/admin/elder-services/relations`
- `PATCH /api/admin/elder-services/relations/{relation_id}`
- `POST /api/admin/elder-services/relations/{relation_id}/status`

新增/修改请求字段：

```json
{
  "member_id": 35,
  "elder_name": "张阿姨",
  "elder_address": "椿树街道幸福里 2 号楼",
  "is_active": true
}
```

要求：

- `member_id` 必须是已启用、审核通过且身份为小哥的用户。
- 同一小哥同时只能存在一条有效关系。
- 当前业务固定为一对一：一名小哥同一时间只能对应一名老人，一名老人同一时间也只能对应一名小哥。
- 不再要求 `frequency`、任务标题、任务描述、任务地点、任务积分或任务状态字段。
- 停用关系后禁止继续提交新记录，但不得删除历史记录。

## 5. 公共留言板接口

留言需要区分两个相互独立的状态：

- `status`：业务处理状态，取值为 `submitted`、`processing`、`replied`、`closed`。
- `visibility_status`：公开审核状态，取值为 `pending`、`approved`、`rejected`。

后台回复留言不代表自动公开；公开审核通过也不代表留言已经处理完成。

### 5.1 发布留言

`POST /api/problem-feedbacks`

认证：用户 token，用户资料审核通过。

请求体：

```json
{
  "title": "建议增加社区活动",
  "content": "希望周末可以增加适合老年人的书法活动。"
}
```

响应 `data`：

```json
{
  "id": 108,
  "title": "建议增加社区活动",
  "content": "希望周末可以增加适合老年人的书法活动。",
  "status": "submitted",
  "visibility_status": "pending",
  "is_public": false,
  "reply": "",
  "replied_at": null,
  "created_at": "2026-07-24T11:00:00+08:00"
}
```

业务规则：

- `title` 和 `content` 必填，后端应限制合理长度并过滤危险 HTML。
- 新留言默认 `status = submitted`。
- 新留言默认 `visibility_status = pending`、`is_public = false`。
- 留言提交后本人应立即能在“我的留言”中看到。

### 5.2 查询我的留言

`GET /api/problem-feedbacks`

认证：用户 token。

查询参数：`page`、`page_size`、可选 `status`。

业务规则：

- 返回当前用户自己的全部留言，不受公开审核状态限制。
- 每项必须返回 `visibility_status` 和 `is_public`。
- 按 `created_at` 倒序返回。

### 5.3 查询公共留言

`GET /api/problem-feedbacks/public`

认证：不需要 token。

查询参数：`page`、`page_size`。

响应示例：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 108,
        "title": "建议增加社区活动",
        "content": "希望周末可以增加适合老年人的书法活动。",
        "status": "replied",
        "visibility_status": "approved",
        "is_public": true,
        "reply": "已纳入下月活动计划。",
        "replied_at": "2026-07-25T09:00:00+08:00",
        "created_at": "2026-07-24T11:00:00+08:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

安全规则：

- 只返回 `visibility_status = approved` 且 `is_public = true` 的留言。
- 公共接口不能返回 `member_id`、手机号、openid、真实姓名等用户隐私字段。
- 不接受前端传入用户 ID 或公开状态绕过过滤。
- 已公开留言被后台改为不公开后，应立即从公共列表消失。

### 5.4 后台查询留言

`GET /api/admin/problem-feedbacks`

查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `page` | integer | 否 | 页码 |
| `page_size` | integer | 否 | 每页数量 |
| `status` | string | 否 | 业务处理状态 |
| `visibility_status` | string | 否 | `pending`、`approved`、`rejected` |
| `member_id` | integer | 否 | 按用户筛选 |
| `keyword` | string | 否 | 搜索标题、正文或用户名 |

列表和详情必须返回：

- 留言基础字段：`id`、`title`、`content`、`status`、`reply`、`replied_at`、`created_at`。
- 用户字段：`member_id`、`member_name`、`member_phone`。
- 公开字段：`visibility_status`、`is_public`。
- 来源字段：`source_type = problem_feedback`。

权限要求：

- 留言标题、正文、提交人和提交时间属于用户原始提交信息，后台只能查看，不得修改。
- 后台只允许通过独立接口更新处理状态、回复内容和公开审核状态。
- 线上现有 `PATCH /api/admin/problem-feedbacks/{feedback_id}` 允许修改 `title` 和 `content`，请移除这两个可写字段，或停用该 PATCH 接口。

### 5.5 后台审核留言公开状态

`POST /api/admin/problem-feedbacks/{feedback_id}/visibility`

审核通过并公开：

```json
{
  "visibility_status": "approved",
  "is_public": true
}
```

审核不通过，仅本人可见：

```json
{
  "visibility_status": "rejected",
  "is_public": false
}
```

重新设为待审核：

```json
{
  "visibility_status": "pending",
  "is_public": false
}
```

业务规则：

- `approved` 必须对应 `is_public = true`。
- `pending`、`rejected` 必须对应 `is_public = false`。
- 后端应以 `visibility_status` 推导并校验 `is_public`，防止字段矛盾。
- 需要记录审核人和审核时间，建议返回 `visibility_reviewer_id`、`visibility_reviewed_at`。
- 该接口只控制是否进入公共留言板，不修改业务处理状态和回复内容。

## 6. 后台来源识别

甲方要求后台能够确认信息由哪个功能提交。当前业务可以通过独立模块和接口区分，但建议所有后台记录响应统一返回 `source_type`：

| 功能 | `source_type` |
| --- | --- |
| 随手拍 | `report` |
| 社情民意 | `civic_feedback` |
| 留言反馈 | `problem_feedback` |
| 结对帮扶记录 | `elder_service` |
| 志愿活动签到 | `activity` |

要求：

- `source_type` 由后端根据业务表或接口确定，不能由普通用户前端自行指定。
- 图片上传继续使用现有 `business_type` 区分目录：`report`、`civic_feedback`、`elder_service_feedback`。
- 后台各模块列表和详情应保持来源字段一致，便于后续统一统计或导出。

## 7. 不需要新增的接口

以下甲方需求可复用现有接口，不要求后端新增接口：

### 7.1 积分收支与我的任务合并

- `GET /api/points/balance`
- `GET /api/points/records`
- `GET /api/activities/my-signups`

前端仅将三组现有数据合并到同一页面展示。

### 7.2 服务地点

- `GET /api/activities`：读取已发布志愿活动的文字地址。
- `GET /api/merchants`：读取已启用兑换商家地址。

当前只展示志愿活动和兑换商家的文字地址，不需要地图、经纬度或地图 SDK 接口。为避免在结对帮扶入口外暴露老人个人信息，“服务地点”不读取、不展示对口老人姓名和地址。

### 7.3 积分兑换名称调整

“扫码优惠”改名为“积分兑换”属于前端文案调整，不需要新增接口，继续使用现有商户固定积分码和积分支付接口。

## 8. 错误处理要求

| HTTP 状态 | 场景 | 建议提示 |
| --- | --- | --- |
| `400` | 请求格式错误 | 返回具体字段错误 |
| `401` | token 缺失或过期 | `登录状态已失效` |
| `403` | 用户未审核通过、身份不符或无有效关系 | 返回明确业务原因 |
| `404` | 指定记录不存在 | `记录不存在` |
| `409` | 重复审核或状态冲突 | `当前记录已处理，请刷新后重试` |
| `422` | 字段校验失败 | 返回字段级错误信息 |

不要把“当前没有对口关系”处理成接口不存在的 `404`；查询本人关系时应返回 `200 + data: null`。

## 9. 联调验收清单

### 9.1 结对帮扶

- 未配置关系的小哥查询得到 `data: null`，不会看到其他小哥或老人信息。
- 配置有效关系后，小程序能够显示老人姓名和地址。
- 未配置关系时，点击外部入口得到通用说明且不进入内部页面；关系接口异常时必须与“未配置”明确区分。
- 小哥可以连续提交多条独立帮扶记录，不需要任务 ID。
- 未上传帮扶照片时前后端均拒绝提交；上传 1-10 张图片时可以正常提交。
- 关系停用后不能提交新记录，但历史记录仍能查询。
- 后台列表能看到提交人、对口老人、地址、正文、图片、时间和审核状态。
- 后台可以像随手拍一样为待审核记录配置积分值。
- 审核通过后按配置值发放积分并生成一条流水；审核驳回不发积分。
- 审核驳回必须填写原因，重复审核不会重复产生积分流水。
- 后台和数据库均阻止一名小哥或一名老人同时存在多条有效关系。

### 9.2 公共留言板

- 新留言立即出现在本人列表，公开状态为待审核。
- 待审核和审核不通过的留言不会出现在公共接口。
- 后台公开审核通过后，未登录用户也能在公共列表看到留言。
- 后台取消公开后，留言立即从公共列表消失，但本人仍能查看。
- 公共接口不泄露用户 ID、手机号、openid 或实名信息。
- 留言业务处理状态与公开审核状态能够分别修改，互不覆盖。

## 10. 已确认的结对帮扶规则

1. 每条帮扶记录必须至少上传 1 张现场照片，并填写帮扶记录正文。
2. 帮扶记录审核通过后发放积分，积分值由街道管理后台在该条记录的审核页面配置，交互和随手拍一致。
3. 当前采用一对一关系：一名小哥同一时间只对应一名老人，一名老人同一时间也只对应一名小哥。

## 11. 唯一待确认事项：旧记录是否保留

旧版本按“后台发布老人服务任务，小哥针对任务提交反馈”的方式保存过数据；新版本改为“小哥直接上传帮扶记录”，不再使用任务 ID。

需要确认旧任务模式产生的记录是否还要继续显示：

- 如果旧数据只是开发测试数据，可以不迁移，正式上线前清理测试数据即可。
- 如果旧数据需要作为历史记录保留，后端需要让新的帮扶记录列表兼容旧数据，或将旧记录转换为新结构，并补齐提交人、老人姓名、老人地址等历史快照。

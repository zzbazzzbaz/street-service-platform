# API 变更接口文档（甲方需求变更 v1.2）

> 版本：1.2  
> 日期：2026-08-03  
> 适用范围：用户端微信小程序、街道管理后台 H5  
> 对应需求文档：`docs/前端API需求文档（甲方需求变更）.md`  
> 变更分支：`feat/frontend-api-requirement-changes`

## 1. 变更总览

### 1.1 新增接口（4 个）

| 接口 | 方法 | 用途 | 认证 |
| --- | --- | --- | --- |
| `/api/elder-services/my-relation` | GET | 查询当前小哥的有效对口关系 | 用户 token |
| `/api/elder-services/feedbacks` | POST | 不依赖任务，主动提交帮扶记录 | 用户 token |
| `/api/problem-feedbacks/public` | GET | 查询公共留言板 | 无需认证 |
| `/api/admin/problem-feedbacks/{feedback_id}/visibility` | POST | 后台审核留言是否公开 | 后台 token |

### 1.2 改造接口（9 个）

| 接口 | 方法 | 改造内容 |
| --- | --- | --- |
| `/api/elder-services/feedbacks` | GET | 移除 task_id 依赖，增加 status 筛选，返回快照字段 |
| `/api/admin/elder-services/feedbacks` | GET | 增加 status/member_id/relation_id/keyword 筛选 |
| `/api/admin/elder-services/feedbacks/{feedback_id}` | PATCH | 移除 content/image/image_urls 可写，仅保留 points |
| `/api/admin/elder-services/feedbacks/{feedback_id}/review` | POST | 积分来源改为 feedback.points，重复审核返回 409 |
| `/api/admin/elder-services/relations` 相关 | POST/PATCH | 移除 frequency 字段 |
| `/api/problem-feedbacks` | POST | 新留言默认 visibility_status=pending, is_public=false |
| `/api/problem-feedbacks` | GET | 响应增加 visibility_status 和 is_public 字段 |
| `/api/admin/problem-feedbacks` | GET | 增加 visibility_status 筛选，返回 source_type |
| `/api/admin/problem-feedbacks/{feedback_id}` | PATCH | 移除 title/content 可写字段 |

### 1.3 数据模型变更

| 模型 | 新增字段 | 变更字段 |
| --- | --- | --- |
| `ElderServiceFeedback` | `points`(int)、`elder_name`(str快照)、`elder_address`(str快照)、`reviewed_at`(datetime) | `task` 改为 nullable |
| `ProblemFeedback` | `visibility_status`(str)、`is_public`(bool)、`visibility_reviewer`(FK)、`visibility_reviewed_at`(datetime) | - |
| `ElderCareRelation` | - | 新增 `uniq_active_relation_per_member` 和 `uniq_active_elder` 唯一约束 |

### 1.4 后台来源识别（source_type）

所有后台模块的列表和详情响应统一返回 `source_type` 字段：

| 功能 | source_type |
| --- | --- |
| 随手拍 | `report` |
| 社情民意 | `civic_feedback` |
| 留言反馈 | `problem_feedback` |
| 结对帮扶记录 | `elder_service` |
| 志愿活动签到 | `activity` |

---

## 2. 结对帮扶接口

### 2.1 查询我的对口关系（新增）

`GET /api/elder-services/my-relation`

**认证：** 用户 token，当前用户应为审核通过的小哥（identity_type=courier）。

**响应 data（有有效关系时）：**

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

**响应 data（无有效关系时）：**

```json
null
```

**字段说明：**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | integer | 对口关系 ID |
| `member_id` | integer | 当前小哥用户 ID |
| `elder_name` | string | 老人姓名 |
| `elder_address` | string | 老人服务地址 |
| `is_active` | boolean | 关系是否有效 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

**业务规则：**

- 只能返回当前 token 所属用户的关系，禁止由前端传入 member_id 查询其他人的老人信息。
- 当前没有有效关系时返回 HTTP 200 且 `data: null`，不返回 404。
- 停用关系后，该接口返回 `null`，历史帮扶记录不受影响。
- 非小哥身份返回 403。

---

### 2.2 主动提交帮扶记录（新增）

`POST /api/elder-services/feedbacks`

**认证：** 用户 token，用户资料审核通过，身份为小哥。

**请求体：**

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
| `image_urls` | string[] | 是 | 1-10 张；至少 1 张 |

**响应 data：**

```json
{
  "id": 86,
  "relation_id": 12,
  "member_id": 35,
  "task_id": null,
  "task_title": "",
  "elder_name": "张阿姨",
  "elder_address": "椿树街道幸福里 2 号楼",
  "content": "今天上门看望老人，协助整理房间并检查了用电安全。",
  "image_urls": [
    "https://commu.iloveminmeng.com/media/uploads/elder_service/20260724-001.jpg"
  ],
  "points": 0,
  "status": "pending",
  "review_comment": "",
  "reviewed_at": null,
  "point_record_id": null,
  "created_at": "2026-07-24T10:30:00+08:00"
}
```

**业务规则：**

- 请求体不接收 `task_id`、`member_id`、`relation_id`、老人姓名或老人地址。
- 后端根据当前 token 查找有效关系，自动绑定 `member_id` 和 `relation_id`。
- 提交时保存 `elder_name`、`elder_address` 快照到记录中，避免后续调整关系导致历史记录变化。
- 至少上传 1 张帮扶现场照片；缺少图片时后端拒绝提交并返回 400。
- 没有有效对口关系时拒绝提交，返回 HTTP 403 和提示"暂未配置有效的结对帮扶关系"。
- 每次提交创建一条新记录，允许重复提交。
- 新记录状态固定为 `pending`，`points` 默认为 0（待后台配置）。

---

### 2.3 查询我的帮扶记录（改造）

`GET /api/elder-services/feedbacks`

**认证：** 用户 token。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `page` | integer | 否 | 页码，默认 1 |
| `page_size` | integer | 否 | 每页数量，默认 20 |
| `status` | string | 否 | `pending`、`approved`、`rejected` |

**响应 data（分页结构）：**

```json
{
  "items": [
    {
      "id": 86,
      "relation_id": 12,
      "member_id": 35,
      "task_id": null,
      "task_title": "",
      "elder_name": "张阿姨",
      "elder_address": "椿树街道幸福里 2 号楼",
      "content": "今天上门看望老人",
      "image_urls": ["https://example.com/a.jpg"],
      "points": 10,
      "status": "approved",
      "review_comment": "记录完整，审核通过",
      "reviewed_at": "2026-07-24T14:00:00+08:00",
      "point_record_id": 201,
      "created_at": "2026-07-24T10:30:00+08:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

**变更说明（与旧版对比）：**

| 字段 | 旧版 | 新版 |
| --- | --- | --- |
| `task_id` | 必须有值 | 可为 `null`（新记录不依赖任务） |
| `task_title` | 总是返回 | 旧记录有值，新记录为空字符串 |
| `relation_id` | 不返回 | 新增，始终返回 |
| `member_id` | 不返回 | 新增，始终返回 |
| `elder_address` | 不返回 | 新增，从快照或关系动态读取 |
| `reviewed_at` | 不返回 | 新增，审核时间 |
| `points` | 来自 `task.points` | 优先 `feedback.points`，为 0 时回退到 `task.points` |
| `status` 筛选 | 不支持 | 新增筛选参数 |

**业务规则：**

- 只能返回当前用户自己的记录。
- 按 `created_at` 倒序返回。
- 对口关系停用后，历史记录仍然可以查询。

---

### 2.4 后台查询帮扶记录（改造）

#### 列表

`GET /api/admin/elder-services/feedbacks`

**查询参数：**

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

**响应 data（列表项和详情统一结构）：**

```json
{
  "id": 86,
  "relation_id": 12,
  "member_id": 35,
  "task_id": null,
  "task_title": "",
  "elder_name": "张阿姨",
  "elder_address": "椿树街道幸福里 2 号楼",
  "content": "今天上门看望老人",
  "image_urls": ["https://example.com/a.jpg"],
  "points": 10,
  "status": "pending",
  "review_comment": "",
  "reviewed_at": null,
  "point_record_id": null,
  "created_at": "2026-07-24T10:30:00+08:00",
  "member_name": "李师傅",
  "member_phone": "138****5678",
  "source_type": "elder_service"
}
```

**变更说明：**

- 新增 `member_id`、`relation_id`、`elder_address`、`reviewed_at`、`source_type` 字段。
- `member_name` 优先返回实名，手机号返回脱敏值。
- 列表新增 `status`、`member_id`、`relation_id`、`keyword` 筛选参数。
- `source_type` 固定为 `elder_service`。

---

### 2.5 后台配置帮扶积分（改造）

`PATCH /api/admin/elder-services/feedbacks/{feedback_id}`

**请求体：**

```json
{
  "points": 10
}
```

| 字段 | 类型 | 必填 | 约束 |
| --- | --- | --- | --- |
| `points` | integer | 否 | 大于或等于 0 的整数 |

**变更说明（与旧版对比）：**

| 可写字段 | 旧版 | 新版 |
| --- | --- | --- |
| `content` | 可写 | **已移除** |
| `image` | 可写 | **已移除** |
| `image_urls` | 可写 | **已移除** |
| `points` | 不存在 | **新增，唯一可写字段** |

**业务规则：**

- 只有 `pending` 状态的记录允许修改积分值，非 pending 返回 400。
- 该接口不接受或修改 `content`、`image`、`image_urls`、提交人、老人信息或创建时间。

---

### 2.6 后台审核帮扶记录（改造）

`POST /api/admin/elder-services/feedbacks/{feedback_id}/review`

**请求体：**

```json
{
  "action": "approve",
  "comment": "记录完整，审核通过"
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `action` | string | 是 | `approve` 或 `reject` |
| `comment` | string | reject 时必填 | 审核意见 |

**变更说明：**

| 行为 | 旧版 | 新版 |
| --- | --- | --- |
| 积分来源 | `feedback.task.points` | `feedback.points`（为 0 时回退到 `task.points`） |
| 重复审核 | 返回 400 | **返回 409** |
| 审核时间 | 不记录 | **记录 `reviewed_at`** |
| 积分原因 | "老人服务审核通过：{task.title}" | "结对帮扶审核通过：{elder_name}" |

**业务规则：**

- 只有 `pending` 状态可以审核。
- `reject` 时 `comment` 必填。
- 审核通过时，读取后台为该条帮扶记录配置的 `points`，给提交用户发放积分并生成积分流水。
- 审核驳回时不得发放积分。
- 已审核记录重复审核返回 HTTP 409，不得重复发放积分。
- 积分流水使用 `source_type = elder_service`、`source_id = feedback_id`。

---

### 2.7 后台维护对口关系（改造）

继续使用以下接口：

- `GET /api/admin/elder-services/relations`
- `POST /api/admin/elder-services/relations`
- `PATCH /api/admin/elder-services/relations/{relation_id}`
- `POST /api/admin/elder-services/relations/{relation_id}/status`

**请求体（创建/修改）：**

```json
{
  "member_id": 35,
  "elder_name": "张阿姨",
  "elder_address": "椿树街道幸福里 2 号楼",
  "is_active": true
}
```

**变更说明：**

| 字段 | 旧版 | 新版 |
| --- | --- | --- |
| `frequency` | 存在（可选） | **已移除** |

**响应 data：**

```json
{
  "id": 12,
  "member_id": 35,
  "member_name": "李师傅",
  "member_phone": "138****5678",
  "elder_name": "张阿姨",
  "elder_address": "椿树街道幸福里 2 号楼",
  "is_active": true,
  "created_at": "2026-07-24T09:00:00+08:00",
  "updated_at": "2026-07-24T09:00:00+08:00"
}
```

**业务规则：**

- `member_id` 必须是已启用、审核通过且身份为小哥的用户。
- 同一小哥同时只能存在一条有效关系（数据库级唯一约束 `uniq_active_relation_per_member`）。
- 同一老人同时只能对应一名小哥（数据库级唯一约束 `uniq_active_elder`，按 elder_name + elder_address 判定）。
- 不再要求 `frequency` 字段。
- 停用关系后禁止继续提交新记录，但不得删除历史记录。

---

## 3. 公共留言板接口

### 3.1 状态体系

留言需要区分两个相互独立的状态：

| 状态字段 | 取值 | 说明 |
| --- | --- | --- |
| `status` | `submitted`、`processing`、`replied`、`closed` | 业务处理状态 |
| `visibility_status` | `pending`、`approved`、`rejected` | 公开审核状态 |

后台回复留言不代表自动公开；公开审核通过也不代表留言已经处理完成。

`is_public` 由 `visibility_status` 推导：
- `approved` → `is_public = true`
- `pending`、`rejected` → `is_public = false`

---

### 3.2 发布留言（改造）

`POST /api/problem-feedbacks`

**认证：** 用户 token，用户资料审核通过。

**请求体：**

```json
{
  "title": "建议增加社区活动",
  "content": "希望周末可以增加适合老年人的书法活动。"
}
```

**响应 data：**

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

**变更说明：**

| 字段 | 旧版 | 新版 |
| --- | --- | --- |
| `visibility_status` | 不存在 | **新增，默认 `pending`** |
| `is_public` | 不存在 | **新增，默认 `false`** |

**业务规则：**

- 新留言默认 `status = submitted`。
- 新留言默认 `visibility_status = pending`、`is_public = false`。
- 留言提交后本人应立即能在"我的留言"中看到。

---

### 3.3 查询我的留言（改造）

`GET /api/problem-feedbacks`

**认证：** 用户 token。

**查询参数：** `page`、`page_size`、可选 `status`。

**响应 data（分页结构，items 每项）：**

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

**变更说明：** 每项新增返回 `visibility_status` 和 `is_public` 字段。

**业务规则：**

- 返回当前用户自己的全部留言，不受公开审核状态限制。
- 按 `created_at` 倒序返回。

---

### 3.4 查询公共留言（新增）

`GET /api/problem-feedbacks/public`

**认证：** 不需要 token。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `page` | integer | 否 | 页码，默认 1 |
| `page_size` | integer | 否 | 每页数量，默认 20 |

**响应 data：**

```json
{
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
```

**安全规则：**

- 只返回 `visibility_status = approved` 且 `is_public = true` 的留言。
- 公共接口**不返回** `member_id`、`member_name`、`member_phone`、`openid`、真实姓名等用户隐私字段。
- 不接受前端传入用户 ID 或公开状态绕过过滤。
- 已公开留言被后台改为不公开后，立即从公共列表消失。

---

### 3.5 后台查询留言（改造）

`GET /api/admin/problem-feedbacks`

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `page` | integer | 否 | 页码 |
| `page_size` | integer | 否 | 每页数量 |
| `status` | string | 否 | 业务处理状态 |
| `visibility_status` | string | 否 | `pending`、`approved`、`rejected` |
| `member_id` | integer | 否 | 按用户筛选 |
| `keyword` | string | 否 | 搜索标题、正文或用户名 |

**响应 data（列表项和详情统一结构）：**

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
  "created_at": "2026-07-24T11:00:00+08:00",
  "member_id": 35,
  "member_name": "李师傅",
  "member_phone": "138****5678",
  "source_type": "problem_feedback"
}
```

**变更说明：**

| 字段 | 旧版 | 新版 |
| --- | --- | --- |
| `visibility_status` | 不返回 | **新增** |
| `is_public` | 不返回 | **新增** |
| `source_type` | 不返回 | **新增，固定 `problem_feedback`** |
| `visibility_status` 筛选 | 不支持 | **新增** |
| `keyword` 搜索范围 | openid、nickname、title | **扩展为** openid、nickname、real_name、title、content |

---

### 3.6 后台修改留言状态（改造）

`PATCH /api/admin/problem-feedbacks/{feedback_id}`

**请求体：**

```json
{
  "status": "processing"
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `status` | string | 否 | 业务处理状态 |

**变更说明：**

| 可写字段 | 旧版 | 新版 |
| --- | --- | --- |
| `title` | 可写 | **已移除** |
| `content` | 可写 | **已移除** |
| `status` | 可写 | 保留 |

**业务规则：**

- 留言标题、正文、提交人和提交时间属于用户原始提交信息，后台只能查看，不得修改。
- 后台只允许通过独立接口更新处理状态（此接口）、回复内容（`/reply`）和公开审核状态（`/visibility`）。

---

### 3.7 后台审核留言公开状态（新增）

`POST /api/admin/problem-feedbacks/{feedback_id}/visibility`

**认证：** 后台 token。

**请求体：**

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

**响应 data：** 同 3.5 后台查询留言结构。

**业务规则：**

- `approved` 必须对应 `is_public = true`，否则返回 400。
- `pending`、`rejected` 必须对应 `is_public = false`，否则返回 400。
- 后端以 `visibility_status` 推导并校验 `is_public`，防止字段矛盾。
- 记录审核人（`visibility_reviewer`）和审核时间（`visibility_reviewed_at`）。
- 该接口只控制是否进入公共留言板，不修改业务处理状态和回复内容。

---

## 4. 错误处理

| HTTP 状态 | 场景 | 建议提示 |
| --- | --- | --- |
| `400` | 请求格式错误、字段校验失败、PATCH 非 pending 记录 | 返回具体字段错误 |
| `401` | token 缺失或过期 | `登录状态已失效` |
| `403` | 用户未审核通过、身份不符、无有效关系 | 返回明确业务原因 |
| `404` | 指定记录不存在 | `记录不存在` |
| `409` | 重复审核或状态冲突 | `当前记录已处理，请刷新后重试` |

注意：查询本人关系时返回 `200 + data: null`，不返回 `404`。

---

## 5. 旧接口兼容说明

以下旧接口保留用于历史数据兼容，新数据不得再依赖 `task_id`：

- `GET /api/elder-services/tasks` - 任务列表（旧）
- `GET /api/elder-services/my-tasks` - 我的对口任务（旧）
- `GET /api/elder-services/tasks/{task_id}` - 任务详情（旧）
- `POST /api/elder-services/tasks/{task_id}/feedback` - 提交服务反馈（旧）
- 后台老人服务任务创建、编辑、发布和关闭接口

新版帮扶记录（通过 `POST /api/elder-services/feedbacks` 提交）的 `task_id` 为 `null`，`task_title` 为空字符串。旧版记录的 `task_id` 和 `task_title` 仍然有值，`feedback_data` 序列化时做了兼容处理：

- `elder_name`/`elder_address`：优先使用快照字段，为空时回退到 relation 动态读取
- `points`：优先使用 feedback 自身的 points，为 0 时回退到 task.points

---

## 6. 联调验收清单

### 6.1 结对帮扶

- [ ] 未配置关系的小哥查询 `GET /my-relation` 得到 `data: null`
- [ ] 配置有效关系后，小程序能够显示老人姓名和地址
- [ ] 未配置关系时 `POST /feedbacks` 返回 403
- [ ] 小哥可以连续提交多条独立帮扶记录，不需要任务 ID
- [ ] 未上传帮扶照片时前后端均拒绝提交
- [ ] 关系停用后不能提交新记录，但历史记录仍能查询
- [ ] 后台列表能看到提交人、对口老人、地址、正文、图片、时间和审核状态
- [ ] 后台可以像随手拍一样为待审核记录配置积分值
- [ ] 审核通过后按配置值发放积分并生成一条流水
- [ ] 审核驳回必须填写原因，重复审核返回 409
- [ ] 数据库阻止一名小哥或一名老人同时存在多条有效关系

### 6.2 公共留言板

- [ ] 新留言立即出现在本人列表，公开状态为待审核
- [ ] 待审核和审核不通过的留言不会出现在公共接口
- [ ] 后台公开审核通过后，未登录用户也能在公共列表看到留言
- [ ] 后台取消公开后，留言立即从公共列表消失，但本人仍能查看
- [ ] 公共接口不泄露用户 ID、手机号、openid 或实名信息
- [ ] 留言业务处理状态与公开审核状态能够分别修改，互不覆盖
- [ ] `approved` + `is_public=false` 组合被后端拒绝

### 6.3 后台来源识别

- [ ] 随手拍列表/详情返回 `source_type: "report"`
- [ ] 社情民意列表/详情返回 `source_type: "civic_feedback"`
- [ ] 留言反馈列表/详情返回 `source_type: "problem_feedback"`
- [ ] 结对帮扶记录列表/详情返回 `source_type: "elder_service"`
- [ ] 志愿活动签到列表/详情返回 `source_type: "activity"`

# GPT 业务自动化流程文档

## 概述

本文档描述 GPT 业务模块的三大核心自动化功能：
1. **自动开通** - 注册 OpenAI 账号并开通 Team 订阅
2. **自动邀请** - 将账号邀请加入 Team 工作区
3. **自动入池** - 将账号授权并添加到 Sub2API 账号池

实现细节、维护要点、日志/截图排查入口见：
- `docs/AUTO_INVITE_MAINTENANCE.md`

---

## 一、自动开通 (Self Register + Team Onboarding)

### 1.1 功能说明

自动完成新账号的注册和 Team 订阅开通全流程。

维护/实现细节见：
- `docs/AUTO_INVITE_MAINTENANCE.md`

### 1.2 流程步骤

```
┌─────────────────────────────────────────────────────────────────┐
│                        自动开通完整流程                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 准备阶段                                                     │
│     ├── 从域名邮箱系统获取邮箱地址                                 │
│     ├── 生成随机密码                                              │
│     └── 创建 Geekez 浏览器 Profile                               │
│                                                                 │
│  2. 账号注册 (register_openai_account)                           │
│     ├── 打开 chatgpt.com                                         │
│     ├── 点击 Sign up 按钮                                        │
│     ├── 弹窗模式: 输入邮箱 → Continue                             │
│     ├── 跳转 auth.openai.com                                     │
│     │   ├── /log-in-or-create-account → 输入邮箱                 │
│     │   ├── /create-account/password → 输入密码                  │
│     │   ├── /email-verification → 获取验证码并填入                │
│     │   └── /about-you → 填写姓名和生日                          │
│     └── 注册完成，返回 chatgpt.com                                │
│                                                                 │
│  3. 等待虚拟卡 (最多 300 秒)                                      │
│     ├── 查询可用虚拟卡                                            │
│     ├── 有卡 → 继续开通流程                                       │
│     └── 无卡 → 跳过开通，更新状态为 "registered"                  │
│                                                                 │
│  4. Team 开通 (run_onboarding_flow)                              │
│     ├── 处理弹窗 (跳过/Skip)                                      │
│     ├── 注入 JS 调用 /backend-api/payments/checkout               │
│     │   └── 带优惠码: team-1-month-free                          │
│     ├── 跳转 pay.openai.com 填写表单                              │
│     │   ├── #email → 邮箱                                        │
│     │   ├── #cardNumber → 卡号                                   │
│     │   ├── #cardExpiry → 有效期                                 │
│     │   ├── #cardCvc → CVV                                       │
│     │   ├── #billingName → 持卡人                                │
│     │   ├── #billingAddressLine1 → 地址                          │
│     │   ├── #billingLocality → 城市                              │
│     │   ├── #billingPostalCode → 邮编                            │
│     │   └── #billingAdministrativeArea → 州                      │
│     ├── 点击订阅按钮                                              │
│     ├── 等待 chatgpt.com/payments/success                        │
│     ├── 点击继续                                                  │
│     └── 跳过团队名称                                              │
│                                                                 │
│  5. 完成                                                         │
│     ├── 更新账号状态: activated / registered / failed            │
│     ├── 标记虚拟卡使用状态                                        │
│     └── 关闭浏览器                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 账号状态说明

| 状态 | 说明 |
|------|------|
| `activated` | 已开通 - 注册成功且 Team 开通成功 |
| `registered` | 已注册 - 注册成功但未开通 Team |
| `failed` | 失败 - 注册或开通过程中出错 |

### 1.4 关键代码文件

| 文件 | 说明 |
|------|------|
| `tasks.py` | Celery 任务入口 `self_register_task` |
| `services/openai_register.py` | 注册逻辑 `register_openai_account` |
| `services/onboarding_flow.py` | Team 开通逻辑 `run_onboarding_flow` |
| `storage.py` | 账号状态存储 `patch_account` |

### 1.5 虚拟卡要求

自动开通需要一张可用的虚拟卡，卡信息字段：

```python
{
    "card_id": int,           # 卡 ID
    "card_number": str,       # 卡号 (16位)
    "card_expiry": str,       # 有效期 (MM/YY)
    "card_cvc": str,          # CVV (3位)
    "cardholder_name": str,   # 持卡人姓名
    "address_line1": str,     # 账单地址
    "city": str,              # 城市
    "postal_code": str,       # 邮编
    "state": str,             # 州 (如 NY)
}
```

---

## 二、自动邀请 (Team Invite)

### 2.1 功能说明

将已注册的账号邀请加入指定的 Team 工作区。

更详细的实现细节、日志/截图说明、常见故障排查见：
- `docs/AUTO_INVITE_MAINTENANCE.md`

### 2.2 流程步骤

```
┌─────────────────────────────────────────────────────────────────┐
│                        自动邀请流程                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  0. 子号补齐（可选）                                              │
│     ├── 若母号无子号 / 子号数量不足 seat_total                     │
│     ├── 且 seat_total > 0                                         │
│     └── 自动从 CloudMail 创建子号并写入账号列表                    │
│     └── 若 seat_total == 0：不自动创建（避免无上限），会直接报错    │
│                                                                 │
│  1. 获取管理员 Token / Account ID                                │
│     ├── 优先复用母号已保存的 auth_token / account_id              │
│     ├── 若缺失：使用 Geekez + DrissionPage 登录 chatgpt.com       │
│     │   └── 调用 /api/auth/session 拿到 accessToken              │
│     └── 调用 /backend-api/accounts/check 获取 account_id         │
│                                                                 │
│  2. 发送邀请                                                     │
│     ├── API: POST /backend-api/accounts/{account_id}/invites     │
│     ├── Headers:                                                 │
│     │   ├── Authorization: Bearer {auth_token}                   │
│     │   └── chatgpt-account-id: {account_id}                    │
│     └── Payload:                                                 │
│         ├── email_addresses: [邮箱列表]                          │
│         ├── role: "standard-user"                                │
│         └── resend_emails: true                                  │
│                                                                 │
│  3. 处理结果                                                     │
│     ├── account_invites → 邀请成功列表                           │
│     └── errored_emails → 邀请失败列表                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 关键 API

#### 获取 Team 信息
```
GET https://chatgpt.com/backend-api/accounts/check/v4-2023-04-27
Headers:
  Authorization: Bearer {auth_token}

#### 获取 accessToken（登录态）

```
GET https://chatgpt.com/api/auth/session
```
```

#### 发送邀请
```
POST https://chatgpt.com/backend-api/accounts/{account_id}/invites
Headers:
  Authorization: Bearer {auth_token}
  chatgpt-account-id: {account_id}
Body:
  {
    "email_addresses": ["user@example.com"],
    "role": "standard-user",
    "resend_emails": true
  }
```

#### 获取 Team 统计
```
GET https://chatgpt.com/backend-api/subscriptions?account_id={account_id}
返回: seats_in_use, seats_entitled, pending_invites
```

### 2.4 参考代码

来源: `oai-team-auto-provisioner/team_service.py`

| 函数 | 说明 |
|------|------|
| `fetch_account_id()` | 获取 Team 的 account_id |
| `invite_single_email()` | 邀请单个邮箱 |
| `batch_invite_to_team()` | 批量邀请多个邮箱 |
| `check_available_seats()` | 检查可用席位 |
| `get_team_stats()` | 获取 Team 统计 |

---

## 三、自动入池 (Sub2API Sink)

### 3.1 功能说明

将 ChatGPT 账号授权并添加到 Sub2API 账号池，供 API 网关使用。

维护/实现细节见：
- `docs/AUTO_INVITE_MAINTENANCE.md`

### 3.2 流程步骤

自动入池支持两种模式（前端弹窗选择，对应后端参数 `mode` / `pool_mode`）。

说明：
- 前端弹窗使用更简单的值：`crs` / `s2a`
- 后端内部逻辑会归一化为：`crs_sync` / `s2a_oauth`（同时兼容两套写法）

幂等/跳过规则：
- 若子号本地状态 `pool_status=success`，本次任务会直接跳过该子号（不会重复授权/重复入池，也不会先置为 running）
- 如需强制重跑某个子号：先把该子号的 `pool_status` 手动重置为非 success（例如 `not_started`），再执行入池

| 模式 | 值（前端/请求） | 是否依赖 CRS | 适用场景 |
|------|----|-------------|----------|
| CRS 同步入池（推荐） | `crs`（或 `crs_sync`） | 依赖 | 已有 CRS 存的 OpenAI OAuth 凭据，直接同步到 Sub2API |
| S2A OAuth 入池 | `s2a`（或 `s2a_oauth`） | 不依赖 | 不从 CRS 拉取，直接通过 Sub2API 的 OpenAI OAuth 接口为子号生成/写入凭据 |

#### 3.2.1 CRS 同步入池（`crs_sync`）

```
┌─────────────────────────────────────────────────────────────────┐
│                    CRS 同步入池（crs_sync）                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 读取子号邮箱列表                                              │
│     └── 从母号下挂载的 child accounts 收集 emails                 │
│                                                                 │
│  2. 连接校验（推荐）                                              │
│     ├── 校验 S2A api_base 可访问                                 │
│     └── 校验 admin_key/admin_token 生效                          │
│     └── 后端接口：POST /settings/s2a/test                          │
│                                                                 │
│  3. 从 CRS 拉取 OpenAI OAuth 凭据                                 │
│     └── GET {CRS_API_BASE}/admin/openai-accounts                  │
│                                                                 │
│  4. 写入 Sub2API                                                  │
│     └── POST {S2A_API_BASE}/admin/accounts (platform=openai,type=oauth)
│                                                                 │
│  5. 完成                                                         │
│     ├── 生成 sub2api_sink_result.json (ok/skip/fail)              │
│     ├── 写回母号 pool_status=success/failed                        │
│     └── 写回子号 pool_status=success/failed（ok/skipped 视为成功） │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2.2 S2A OAuth 入池（`s2a_oauth`，不依赖 CRS）

说明：该模式会在服务端启动浏览器（Geekez/DrissionPage），登录子号 ChatGPT 后访问 Sub2API 返回的 `auth_url` 完成授权，并从回调 URL 提取 `code`。

```text
┌─────────────────────────────────────────────────────────────────┐
│                  S2A OAuth 入池（s2a_oauth）                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 读取子号邮箱列表                                              │
│     └── 从母号下挂载的 child accounts 收集 emails                 │
│                                                                 │
│  2. 连接校验（推荐）                                              │
│     ├── 校验 S2A api_base 可访问                                 │
│     └── 校验 admin_key/admin_token 生效                          │
│     └── 后端接口：POST /settings/s2a/test                          │
│                                                                 │
│  3. 为每个子号生成授权 URL                                        │
│     └── POST {S2A_API_BASE}/admin/openai/generate-auth-url        │
│                                                                 │
│  4. 浏览器授权拿 code（服务端自动化）                              │
│     ├── 打开 auth_url（auth.openai.com 登录/授权页）                │
│     ├── 如需登录：输入子号邮箱/密码（需要 account_password）         │
│     ├── 点击 Allow/Authorize/Continue 等授权按钮                    │
│     └── 从回调 URL 提取 code                                      │
│                                                                 │
│  5. 用 code 换 token 并创建账号（Sub2API）                          │
│     ├── 优先：POST /admin/openai/create-from-oauth                 │
│     └── 回退：POST /admin/openai/exchange-code -> POST /admin/accounts
│                                                                 │
│  6. 完成                                                         │
│     ├── 生成 sub2api_sink_result.json (ok/skip/fail)              │
│     ├── 写回母号 pool_status=success/failed                        │
│     └── 写回子号 pool_status=success/failed（ok/skipped 视为成功） │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 认证方式

S2A 支持两种认证方式：

| 方式 | Header | 说明 |
|------|--------|------|
| Admin API Key | `x-api-key: {key}` | 推荐，永久有效 |
| JWT Token | `Authorization: Bearer {token}` | 需要定期刷新 |

### 3.3.1 单目标 / 多目标入池

默认（前端弹窗）使用单目标配置：
- `s2a`: `{ api_base, admin_key/admin_token, concurrency, priority, group_ids, group_names }`

如果需要配置多个 Sub2API 目标（仅后端/接口支持，前端默认不暴露）：

支持在插件 settings 中配置多个 Sub2API 目标：
- `s2a_targets`: `[{ key, label?, config }]`
- `s2a_default_target`: 默认选中的 `key`（例如 `sub2`）

触发入池时可通过请求体传入：
```json
{ "target_key": "sub2" }
```

### 3.3.2 CRS 配置（crs_sync 模式）

CRS 配置格式（示例，勿提交真实 token）：

```toml
[crs]
api_base = "https://crs.example.com"
admin_token = "REDACTED"
```

说明：
- 前端 token 输入框支持“留空表示不修改”，后端会保留已保存的脱敏 secret
- `s2a_oauth` 模式不需要 CRS 配置

### 3.4 关键 API

#### 触发入池（本系统后端）

```
POST /plugins/gpt-business/accounts/{mother_id}/sub2api_sink/
Body:
  {
    "mode": "crs" | "s2a" | "crs_sync" | "s2a_oauth",
    "target_key": "sub2"  // 可选：仅多目标配置时需要
  }
```

#### 连接测试（本系统后端）

```
POST /plugins/gpt-business/settings/s2a/test/
POST /plugins/gpt-business/settings/crs/test/
```

#### CRS 拉取账号列表
```
GET {CRS_API_BASE}/admin/openai-accounts
Headers:
  Authorization: Bearer {crs_admin_token}
```

#### Sub2API OpenAI OAuth（S2A OAuth 模式）

```
POST {S2A_API_BASE}/admin/openai/generate-auth-url
POST {S2A_API_BASE}/admin/openai/exchange-code
POST {S2A_API_BASE}/admin/openai/create-from-oauth  # 新版本可用（推荐）
```

#### Sub2API 创建 OAuth 账号
```
POST {S2A_API_BASE}/admin/accounts
Headers:
  x-api-key: {admin_key}
Body:
  {
    "name": "child@example.com",
    "platform": "openai",
    "type": "oauth",
    "credentials": {
      "access_token": "...",
      "refresh_token": "...",
      "expires_at": "..."
    },
    "concurrency": 5,
    "priority": 50,
    "group_ids": [2]
  }
```

#### Sub2API 连接测试（建议）
```
GET {S2A_API_BASE}/admin/accounts?platform=openai&type=oauth&page=1&page_size=1
Headers:
  x-api-key: {admin_key}
```

### 3.5 参考代码

本仓库对应实现：

| 文件 | 说明 |
|------|------|
| `tasks.py` | Celery 任务入口 `sub2api_sink_task`（按 `pool_mode` 分支执行） |
| `services/sub2api_sink_service.py` | CRS/S2A API 封装（test、list、exchange-code、create-from-oauth 等） |
| `views.py` | 入池/连接测试 API 路由（`/accounts/{id}/sub2api_sink/`、`/settings/*/test/`） |

---

## 四、配置要求

### 4.1 邮箱系统

```python
# CloudMail 域名邮箱配置
CLOUDMAIL_API_BASE = "https://mail.example.com"
CLOUDMAIL_API_TOKEN = "xxx"
CLOUDMAIL_DOMAIN = "example.com"
```

### 4.2 浏览器环境

```python
# Geekez 浏览器配置
GEEKEZ_API_BASE = "http://127.0.0.1:12138"
GEEKEZ_CONTROL_BASE = "http://127.0.0.1:19527"
```

### 4.3 虚拟卡系统

需要在 `apps/cards` 模块中配置可用的虚拟卡。

### 4.4 Team 管理

```python
# Team 配置
TEAMS = [
    {
        "name": "Team 1",
        "auth_token": "Bearer xxx",
        "account_id": "xxx"  # 可选，会自动获取
    }
]
```

### 4.5 Sub2API 系统

```python
# S2A 配置
S2A_API_BASE = "https://api.example.com"
S2A_ADMIN_KEY = "xxx"  # 或 S2A_ADMIN_TOKEN
S2A_CONCURRENCY = 1
S2A_PRIORITY = 0
S2A_GROUP_IDS = [1, 2]  # 或 S2A_GROUP_NAMES = ["group1", "group2"]
```

---

## 五、错误处理

### 5.1 常见错误

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| 验证码获取超时 | 邮件未到达或格式不匹配 | 检查邮箱配置和正则匹配 |
| 点击了 Continue with Google | 选择器匹配错误 | 使用 `button[type="submit"]` |
| Team 开通失败 | 优惠码无效或卡被拒 | 检查卡信息和优惠码 |
| 邀请失败 | auth_token 过期或席位满 | 刷新 token 或检查席位 |
| S2A 授权失败 | session 过期或 code 无效 | 重新生成授权 URL |

### 5.2 日志和截图

每个任务会生成：
- `run.log` - 完整执行日志
- `*.png` - 每个关键步骤的截图
 - `logs/trace/trace_<celery_task_id>_<email>.log` - 实时 trace（json line + human line）

自动入池（Sub2API Sink）额外产物：
- `sub2api_sink_result.json` - ok/skip/fail 统计与每个子号的原因
- `oauth_<email>_<attempt>_<ts>.png` - S2A OAuth 模式授权失败时的截图（文件名已做安全字符处理）

存储路径: `MEDIA_ROOT/gpt_business/jobs/{task_id}/`

trace 文件路径: `backend/logs/trace/trace_<celery_task_id>_<email>.log`

### 5.3 Trace 清理策略

默认策略（可通过 `PluginState.settings.trace_cleanup` 覆盖）：

- `max_age_days`: 7
- `max_total_size_mb`: 1024
- `max_files`: 2000
- `min_keep_files`: 20
- `pattern`: `trace_*.log`

清理顺序：超期 -> 超数量 -> 超容量（总量上限）

触发方式：

- 管理命令（默认 dry-run）：
  - `python manage.py cleanup_trace`
  - `python manage.py cleanup_trace --apply`
- 后端接口：
  - `GET /api/v1/plugins/gpt-business/settings/trace-cleanup/`（dry-run）
  - `POST /api/v1/plugins/gpt-business/settings/trace-cleanup/`，body 传 `{"apply": true}`
- 定时任务：Celery beat 每天 03:30 执行（可用 `GPT_TRACE_CLEANUP_ENABLED=false` 关闭）

---

## 六、参考项目

本实现参考了 `oai-team-auto-provisioner` 项目：

| 文件 | 对应功能 |
|------|----------|
| `browser_automation.py` | 浏览器自动化基础 |
| `tools/batch_register.py` | 批量注册主流程 |
| `tools/onboarding_flow.py` | Team 开通流程 |
| `team_service.py` | Team 邀请服务 |
| `s2a_service.py` | Sub2API 入池服务 |
| `email_service.py` | 邮箱服务 |

# GPT专区 - 自动化执行流程与维护指南

本文档覆盖 GPT专区三类自动化能力（母号维度）：
- 自动开通：注册/登录并尝试完成 Team 开通（`self_register_task`）
- 自动邀请：母号邀请子号加入 Team，并让子号自动入队（`auto_invite_task`）
- 自动入池：将账号的 OAuth 凭据同步到 Sub2API 账号池（`sub2api_sink_task`）

目标：
- 让维护者能快速理解端到端执行链路
- 快速定位失败点（网络/登录/验证码/接受邀请）
- 为二次开发提供清晰的代码落点

---

## 1. 触发入口（从页面到 Celery）

### 1.1 前端触发

GPT专区页面的三个按钮分别调用后端 API：

- `POST /api/v1/plugins/gpt-business/accounts/{mother_id}/self_register/`
- `POST /api/v1/plugins/gpt-business/accounts/{mother_id}/auto_invite/`
- `POST /api/v1/plugins/gpt-business/accounts/{mother_id}/sub2api_sink/`

前端封装：`Auto_All_System_Web/frontend/src/api/gpt_business.ts`

### 1.2 后端接口

后端入口：

- `Auto_All_System_Web/backend/plugins/gpt_business/views.py`
  - `AccountsViewSet.self_register`
  - `AccountsViewSet.auto_invite`
  - `AccountsViewSet.sub2api_sink`

职责：
- 创建 task record（写入 PluginState.settings）
- 异步触发 Celery

### 1.3 Celery 任务

任务实现：

- `Auto_All_System_Web/backend/plugins/gpt_business/tasks.py`
  - `self_register_task(record_id: str)`
  - `auto_invite_task(record_id: str)`
  - `sub2api_sink_task(record_id: str)`

执行产物目录：
- `MEDIA_ROOT/gpt_business/jobs/<record_id>/`

---

## 2. 数据结构（PluginState.settings）

GPT专区所有状态都存储在 `PluginState.settings` 的 JSON 中。

### 2.1 accounts（母号/子号）关键字段

母号（type=mother）常用字段：
- `id`
- `email`
- `account_password`：ChatGPT 登录密码
- `email_password`：邮箱密码（CloudMail 使用）
- `cloudmail_config_id`：CloudMail 配置
- `auth_token`：ChatGPT accessToken（Bearer token，来自 `/api/auth/session`）
- `account_id`：Team 的 account_id（来自 `/backend-api/accounts/check/...`）
- `invite_status` / `invite_last_task` / `invite_updated_at`

状态字段（用于前端展示/任务跳过策略，建议二次开发沿用这些 key）：
- `register_status` / `register_updated_at`：注册状态
- `login_status` / `login_updated_at`：登录状态
- `pool_status` / `pool_last_task` / `pool_updated_at`：入池状态（主要母号）
- `invite_status` / `invite_last_task` / `invite_updated_at`：邀请状态（主要母号）

状态值约定（string）：
- `not_started` | `running` | `success` | `failed`

子号（type=child）常用字段：
- `id`
- `email`
- `account_password`
- `cloudmail_config_id`
- `team_join_status` / `team_join_task` / `team_join_updated_at`
- `team_account_id`（如果已入队）

状态字段（子号侧）：
- `register_status` / `register_updated_at`
- `login_status` / `login_updated_at`
- `team_join_status` / `team_join_task` / `team_join_updated_at`

写入/更新都通过 `Auto_All_System_Web/backend/plugins/gpt_business/storage.py` 中的 `patch_account` 等函数完成。

兼容性说明：
- 旧数据可能缺少上述状态字段，`AccountsViewSet.list` 会兜底补默认值（避免前端 undefined）。

### 2.2 tasks（任务记录）关键字段

task record 关键字段：
- `id`（record_id）
- `type`：`auto_invite`
- `mother_id`
- `status`：running/completed/failed
- `celery_task_id`
- `result`：包含 invited 列表、child join 结果、artifacts 列表
- `error`

### 2.3 状态字段写回点（维护入口）

初始化（创建账号时写默认状态）：
- `Auto_All_System_Web/backend/plugins/gpt_business/views.py`
  - `AccountsViewSet.create_mother`
  - `AccountsViewSet.create_child`

自动开通（母号注册/登录状态）：
- `Auto_All_System_Web/backend/plugins/gpt_business/tasks.py:self_register_task`
  - 任务开始：`register_status=running` / `login_status=running`
  - 任务结束：按结果写 `success/failed`

自动邀请（母号邀请状态 + 子号入队状态 + 子号登录/注册状态）：
- `Auto_All_System_Web/backend/plugins/gpt_business/tasks.py:auto_invite_task`
  - 母号：`invite_status` 从 `running` -> `success/failed`；拿到 token 时会写 `login_status=success`
  - 子号：`team_join_status` 从 `running` -> `success/failed`；登录成功写 `login_status=success`；进入注册分支写 `register_status=running/success/failed`

自动入池（母号入池状态）：
- `Auto_All_System_Web/backend/plugins/gpt_business/tasks.py:sub2api_sink_task`
  - `pool_status` 从 `running` -> `success/failed`

---

## 3. 产物、日志、截图命名

### 3.1 目录

默认目录：`MEDIA_ROOT/gpt_business/jobs/<record_id>/`

在本仓库默认 settings 下（`config/settings/base.py`）：
- `MEDIA_ROOT = BASE_DIR / "media"`

因此常见本地路径是：
- `Auto_All_System_Web/backend/media/gpt_business/jobs/<record_id>/`

### 3.2 文件

每次任务至少有：
- `run.log`：全流程日志（按 timestamp 记录）

常见截图：
- 母号登录/邀请阶段：`mother_*` / `mother_invite_login_*`
- 子号登录/注册阶段：`child_<email_sanitized>_*`
- 子号登录调试：`child_<email>_invite_login_*`（ensure_access_token 的截图）
- 接受邀请阶段：`child_<email>_accept_01_before.png` / `accept_02_after_click.png`

注意：Geekez profile 在 `with BrowserService(...)` 结束后会自动关闭，这是正常行为。

---

## 4. 自动邀请详细流程（母号 -> 邀请 -> 子号入队）

核心实现：`Auto_All_System_Web/backend/plugins/gpt_business/tasks.py:auto_invite_task`

整个任务可分为 2 个阶段：

补充：子号自动补齐
- 若母号当前子号数量 < `seat_total` 且 `seat_total > 0`，`auto_invite_task` 会自动创建缺少的子号（通过 CloudMail），再进入邀请/入队流程。
- 若 `seat_total == 0`（未配置/无限制），不会自动创建（避免无上限生成），此时没有子号会直接报错。

### 4.1 阶段 A：母号拿 token + account_id，并发送 invites

关键点：
- 不能在 Celery 容器里用 `requests` 直连 `chatgpt.com`（可能出现 `Network is unreachable`）
- 因此所有 ChatGPT backend-api 调用都改为“浏览器内 fetch”

步骤：
1) 启动母号 Geekez profile
   - `Auto_All_System_Web/backend/plugins/gpt_business/services/browser_service.py:BrowserService`

2) 获取母号 `auth_token`
   - `Auto_All_System_Web/backend/plugins/gpt_business/services/chatgpt_session.py:ensure_access_token`
   - 调用 `GET https://chatgpt.com/api/auth/session`（浏览器内 fetch）拿 `accessToken`
   - 如果卡在 `https://chatgpt.com/auth/login`：
     - 点击 `button[data-testid="login-button"]`
     - 若仍卡住：强制打开 `https://auth.openai.com/log-in-or-create-account`

3) 获取 `account_id`
   - `Auto_All_System_Web/backend/plugins/gpt_business/services/chatgpt_backend_api.py:browser_fetch_account_id`
   - `GET /backend-api/accounts/check/v4-2023-04-27`

4) 发邀请
   - `Auto_All_System_Web/backend/plugins/gpt_business/services/chatgpt_backend_api.py:browser_invite_emails`
   - `POST /backend-api/accounts/{account_id}/invites`

产物：
- 写回母号 `auth_token` / `account_id`
- task.result.details 里记录 success/failed

### 4.2 阶段 B：子号自动注册/登录 + 接受邀请 + 验证入队

对每个子号循环执行：

跳过策略（避免重复跑，提升稳定性）：
- 若子号已入队（`team_join_status=success` 或已有 `team_account_id`），直接 skip（不再登录/不再点邀请）
- 若子号标记为已登录（`login_status=success`），会优先尝试直接读取 `/api/auth/session` 复用 session，拿不到才走完整登录流程

1) 启动子号 Geekez profile
   - profile_name 使用 `gpt_<child_email>`，便于复用 cookies

2) 尝试直接登录（优先复用 cookies）
   - `ensure_access_token` -> `/api/auth/session`
   - 如果遇到以下页面，会抛出 NeedsRegistrationError 并走注册分支：
     - `auth.openai.com/create-account/password`
     - `auth.openai.com/email-verification`

3) 注册分支（失败才走）
   - `Auto_All_System_Web/backend/plugins/gpt_business/services/openai_register.py:register_openai_account`
   - 关键步骤：
     - `https://chatgpt.com/auth/login` 页面卡住时，点击 `button[data-testid="signup-button"]`（Sign up for free）
     - `email-verification`：通过 CloudMail 拉验证码并输入
     - `about-you / Let's confirm your age`：填写 Full name + Birthday 并 Continue

   验证码获取：
   - `apps.integrations.email.services.client.CloudMailClient.wait_for_verification_code`
   - auto_invite 已将 timeout 拉长，并且不强依赖 sender_contains

   注册后 token 获取策略：
   - 先用 `fetch_auth_session` 轻量读取 token（减少二次跳转/断连）
   - 不行再 fallback `ensure_access_token`

4) 判断是否已入队
   - `browser_fetch_account_id(child_token)`
   - 如果能拿到 team account_id，则视为“已入队”

5) 未入队则接受邀请
   - 先等邀请邮件：CloudMail `list_emails` 轮询，并从邮件内容中提取 invite/join/workspace 链接
   - 打开 invite link 后尝试点击 Join/Accept（英文/中文文案）
   - 再次 `browser_fetch_account_id` 校验是否入队

6) 写回子号状态
    - `team_join_status=success/failed`
    - `team_account_id`（如成功）

---

## 5. 常见问题与排查

### 5.1 卡在 https://chatgpt.com/auth/login

现象：`probe` 显示 inputs=0 且 URL 一直不变。

处理：
- 登录：点 `data-testid=login-button`
- 注册：点 `data-testid=signup-button`
- 仍卡：直接打开 `https://auth.openai.com/log-in-or-create-account`

### 5.2 进入 email-verification 但一直不拉验证码

确认点：
- `run.log` 是否出现 `wait verification code start`
- CloudMail 配置是否正确（child 的 `cloudmail_config_id`）
- 邮件是否真的到达（用 CloudMail 的 list_emails 手动验证）

### 5.3 DrissionPage 报 "disconnected"

现象：`The connection to the page has been disconnected`。

处理：
- auto_invite 已对该类错误做了一次重试（重新启动子号浏览器）
- 若仍频繁出现：
  - 检查 Geekez 稳定性/端口
  - 减少并发（一次只跑少量子号）
  - 延长某些等待时间

### 5.4 about-you / Let's confirm your age 页面无法继续

现象：Continue 按钮灰色，要求 Full name + Birthday。

处理：
- `register_openai_account` 已支持此页面：自动填 name + birthday 并点击 Continue
- 若页面形态变化：优先改 `openai_register.py:_complete_about_you_page()` 的 selector

---

## 6. 二次开发建议（最容易改动的地方）

1) 登录/注册 selector 变化
- `Auto_All_System_Web/backend/plugins/gpt_business/services/chatgpt_session.py`（登录）
- `Auto_All_System_Web/backend/plugins/gpt_business/services/openai_register.py`（注册/验证码/about-you）

2) 邀请邮件解析
- `Auto_All_System_Web/backend/plugins/gpt_business/tasks.py` 内 `_wait_invite_link` / `_extract_urls` / `_pick_invite_url`

3) 安全与日志
- 不要在日志中输出密码/token
- 截图文件可能包含敏感信息，按需控制保存范围

---

## 7. 关键代码索引

- 任务入口：`Auto_All_System_Web/backend/plugins/gpt_business/tasks.py:auto_invite_task`
- Geekez 浏览器：`Auto_All_System_Web/backend/plugins/gpt_business/services/browser_service.py:BrowserService`
- ChatGPT 登录态：`Auto_All_System_Web/backend/plugins/gpt_business/services/chatgpt_session.py:ensure_access_token` / `fetch_auth_session`
- 浏览器内调用 backend-api（绕过容器网络）：`Auto_All_System_Web/backend/plugins/gpt_business/services/chatgpt_backend_api.py`
- 子号注册：`Auto_All_System_Web/backend/plugins/gpt_business/services/openai_register.py:register_openai_account`
- 邮箱验证码/收信：`Auto_All_System_Web/backend/apps/integrations/email/services/client.py:CloudMailClient`

---

## 8. 自动开通（self_register）执行流程与维护点

自动开通的目标是：
- 确保母号完成注册（必要时走邮箱验证码）
- 在配置允许的情况下尝试完成 Team/订阅开通（涉及绑卡/支付）

入口：
- API：`POST /api/v1/plugins/gpt-business/accounts/{mother_id}/self_register/`
- Celery：`Auto_All_System_Web/backend/plugins/gpt_business/tasks.py:self_register_task`

关键步骤（高层）：
1) 启动 Geekez 浏览器 profile
2) 注册/登录：`services/openai_register.py:register_openai_account`
   - 处理 chatgpt.com 弹窗/跳转到 auth.openai.com
   - `email-verification`：通过 CloudMail 拉验证码并输入
   - `about-you / Let's confirm your age`：填写 Full name + Birthday 并 Continue
3) 开通/入会（如果配置了支付能力）：`services/onboarding_flow.py:run_onboarding_flow`
4) 写回状态并落产物

状态写回（维护要点）：
- `register_status` / `login_status`：在任务开始写 `running`，结束写 `success/failed`
- `open_status`：历史字段（activated/registered/failed），仍会写回；建议前端展示以 `register_status/login_status` 为准

常见故障排查：
- 卡在 `/auth/login`：通常需要点击 `data-testid=signup-button` 进入注册
- 卡在 `email-verification`：确认 CloudMail 配置、邮件是否到达，日志是否出现 `wait verification code start`
- 卡在 `about-you`：Continue disabled，多半是生日输入形态变化，优先调整 `openai_register.py:_complete_about_you_page()`

关键代码索引：
- `Auto_All_System_Web/backend/plugins/gpt_business/tasks.py:self_register_task`
- `Auto_All_System_Web/backend/plugins/gpt_business/services/openai_register.py:register_openai_account`
- `Auto_All_System_Web/backend/plugins/gpt_business/services/onboarding_flow.py:run_onboarding_flow`

---

## 9. 自动入池（sub2api_sink）执行流程与维护点

自动入池目标：把 CRS 中已存在的 OpenAI OAuth 凭据（access/refresh token）同步到 Sub2API 后台，形成可用账号池。

入口：
- API：`POST /api/v1/plugins/gpt-business/accounts/{mother_id}/sub2api_sink/`
- Celery：`Auto_All_System_Web/backend/plugins/gpt_business/tasks.py:sub2api_sink_task`

实现方式（当前为纯接口内置，不再依赖外部 repo/subprocess）：
- `Auto_All_System_Web/backend/plugins/gpt_business/services/sub2api_sink_service.py`
  - 从 CRS 拉取账号列表（`/admin/openai-accounts`）
  - 找到与邮箱匹配的账号，读取 `openaiOauth.accessToken/refreshToken/expires_in`
  - 调用 Sub2API 管理接口创建 oauth account（`/api/v1/admin/accounts`）

必要配置（Plugin settings）：
- CRS：`crs.api_base`、`crs.admin_token`
- Sub2API：`s2a.api_base`，二选一认证（字段名兼容 oai-team-auto-provisioner 的 [s2a]）：
  - `s2a.admin_key`（推荐，对应 Header `x-api-key`）
  - `s2a.admin_token`（备选，对应 Header `Authorization: Bearer ...`）
- 账号参数：`s2a.group_ids`、`s2a.concurrency`、`s2a.priority`

多目标配置（已实现，用于“入到哪里”下拉框）：
- `s2a_targets`: `[{ key, label?, config: { api_base, admin_key/admin_token, concurrency, priority, group_ids, group_names } }]`
- `s2a_default_target`: 默认选择的 `key`（例如 `sub2`）

安全注意（已实现）：
- `GET /settings/current/` 返回的 `admin_key/admin_token` 会脱敏。
- 保存配置时：如果未重新输入 `admin_key/admin_token`，后端会保留旧值（不会被空字符串覆盖）。

配置示例（来源：oai-team-auto-provisioner [s2a]，字段名保持一致便于迁移）：
```toml
[s2a]
api_base = "https://sub2.pigll.site/api/v1"
admin_key = "admin-xxxx"
admin_token = ""
concurrency = 5
priority = 50
group_ids = [2]
group_names = []
```

连接测试（已实现）：
- 后端接口：`POST /api/v1/plugins/gpt-business/settings/s2a/test/`
  - 支持 `target_key`（从 settings.s2a_targets 取 config）
  - 也支持 `config`（不保存直接测）
- 测试通过后再执行入池任务（前端已做强制要求）

状态展示（已实现）：
- 子号列表增加 `已入池`（使用 `pool_status` / `pool_updated_at` 字段）
- 入池任务会对每个 email 记录 ok/skip/fail，并逐个写回对应账号的 `pool_status`：
  - `ok` / `skipped` -> `pool_status=success`
  - `failed` -> `pool_status=failed`

前端交互（已实现）：
- 点击“入池”/“批量入池”会弹出对话框：
  - 选择“入到哪里”（默认 `s2a_default_target`，若无则 fallback `sub2`）
  - 编辑并保存配置
  - 测试连接通过后才允许点击“开始入池”

状态写回（维护要点）：
- `pool_status`：任务开始写 `running`，结束写 `success/failed`
- 产物：会在 job_dir 写 `sub2api_sink_result.json`（ok/skip/fail + 逐邮箱细节）

常见故障排查：
- CRS list 为空：检查 `crs.api_base`/`crs.admin_token` 是否正确、服务是否可达
- Sub2API 创建失败：检查认证方式（x-api-key vs Bearer jwt）、group_ids 是否有效
- 账号已存在：会被标记为 skipped（属于正常行为）

关键代码索引：
- `Auto_All_System_Web/backend/plugins/gpt_business/tasks.py:sub2api_sink_task`
- `Auto_All_System_Web/backend/plugins/gpt_business/services/sub2api_sink_service.py:sink_openai_oauth_from_crs_to_sub2api`

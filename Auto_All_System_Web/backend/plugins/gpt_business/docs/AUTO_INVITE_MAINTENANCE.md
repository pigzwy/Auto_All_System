# GPT专区 - 自动邀请(auto_invite)执行流程与维护指南

本文档聚焦 GPT专区的“自动邀请”按钮（母号邀请子号加入 Team，并让子号自动完成入队/接受邀请/登录）。

目标：
- 让维护者能快速理解端到端执行链路
- 快速定位失败点（网络/登录/验证码/接受邀请）
- 为二次开发提供清晰的代码落点

---

## 1. 触发入口（从页面到 Celery）

### 1.1 前端触发

GPT专区页面点击“自动邀请”按钮后，调用后端 API：

- `POST /api/v1/plugins/gpt-business/accounts/{mother_id}/auto_invite/`

前端封装：`Auto_All_System_Web/frontend/src/api/gpt_business.ts`（`autoInvite(id)`）

### 1.2 后端接口

后端入口：

- `Auto_All_System_Web/backend/plugins/gpt_business/views.py`
  - `AccountsViewSet.auto_invite`

职责：
- 创建 task record（写入 PluginState.settings）
- 异步触发 Celery

### 1.3 Celery 任务

任务实现：

- `Auto_All_System_Web/backend/plugins/gpt_business/tasks.py`
  - `auto_invite_task(record_id: str)`

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

子号（type=child）常用字段：
- `id`
- `email`
- `account_password`
- `cloudmail_config_id`
- `team_join_status` / `team_join_task` / `team_join_updated_at`
- `team_account_id`（如果已入队）

写入/更新都通过 `Auto_All_System_Web/backend/plugins/gpt_business/storage.py` 中的 `patch_account` 等函数完成。

### 2.2 tasks（任务记录）关键字段

task record 关键字段：
- `id`（record_id）
- `type`：`auto_invite`
- `mother_id`
- `status`：running/completed/failed
- `celery_task_id`
- `result`：包含 invited 列表、child join 结果、artifacts 列表
- `error`

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

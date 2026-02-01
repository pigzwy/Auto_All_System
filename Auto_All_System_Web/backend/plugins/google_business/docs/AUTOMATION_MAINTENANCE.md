# Google专区（Google Business 插件）自动化执行流程与维护指南

本文档是 `google-zone`（`/google-zone`）对应后端插件 `plugins.google_business` 的自动化维护主文档。

覆盖范围：
- 账号任务流（login / get_link / verify / bind_card / one_click）
- 安全设置自动化（修改 2FA、修改辅助邮箱、获取备份码、一键安全更新）
- 订阅自动化（验证订阅状态、点击订阅按钮、截图输出）
- 日志/trace/截图产物与排查方式

原则：
- 先给出“入口 -> 任务 -> 产物”的最短路径
- 再给出每个自动化的关键代码点与排查路径

---

## 1. 触发入口（从页面到 Celery）

### 1.1 前端入口

Google 专区页面：
- `Auto_All_System_Web/frontend/src/views/zones/GoogleBusinessZone.vue`
  - 顶部操作栏只做事件分发（`window.dispatchEvent(CustomEvent)`）
- `Auto_All_System_Web/frontend/src/views/zones/google-modules/GoogleAccountsModule.vue`
  - 接收事件并调用后端 API

前端 API 封装：
- `Auto_All_System_Web/frontend/src/api/google.ts`（Google 专区当前主要使用）
- `Auto_All_System_Web/frontend/src/api/google_business.ts`（历史/管理后台/部分页面使用）

### 1.2 后端 API 前缀

插件 API 统一挂载在：
- `/api/v1/plugins/google-business/`

路由注册：
- `Auto_All_System_Web/backend/plugins/google_business/plugin.py`
- `Auto_All_System_Web/backend/plugins/google_business/urls.py`

### 1.3 Celery 任务入口

两类自动化：

1) **账号任务流**（批量任务）
- `POST /api/v1/plugins/google-business/tasks/`
- 后端创建 `GoogleTask`，触发 Celery：`batch_process_task.delay(task_id, account_ids, task_type, config)`
- 实现：`Auto_All_System_Web/backend/plugins/google_business/tasks.py`
  - `batch_process_task`
  - `process_single_account`（单账号实际执行 login/get_link/verify/bind_card/one_click）

2) **安全/订阅模块**（直接触发 Celery，按 account_ids 批处理）
- 安全：`/security/*` -> `security_*.delay(...)`
- 订阅：`/subscription/*` -> `subscription_*.delay(...)`
- 任务状态通过 `/celery-tasks/{task_id}/` 查询

---

## 2. 核心数据模型与状态

### 2.1 GoogleAccount（账号）

模型（集成层）：
- `Auto_All_System_Web/backend/apps/integrations/google_accounts/models.py:GoogleAccount`

常用字段（按维护需要）：
- `email`
- `password`（加密存储，任务里会解密；解密失败会回退 raw）
- `two_fa_secret`（加密存储）
- `recovery_email`
- `status`（资格/订阅状态：pending/pending_check/logged_in/link_ready/verified/subscribed/ineligible/error 等）
- `sheerid_link` / `sheerid_verified`
- `card_bound`
- `gemini_status`（前端展示用）
- `metadata`（扩展字段，重要：`metadata.google_zone_actions` 存储安全/订阅动作记录）

前端展示字段（serializer 派生）：
- `type_tag`：ineligible / unbound_card / success / other
- `new_2fa_display` / `new_2fa_updated_at`：安全更新后写入 metadata
- `geekez_profile_exists` / `geekez_env`

serializer：
- `Auto_All_System_Web/backend/plugins/google_business/serializers.py:GoogleAccountSerializer`

### 2.2 GoogleTask / GoogleTaskAccount（批量任务）

任务模型：
- `Auto_All_System_Web/backend/plugins/google_business/models.py:GoogleTask`
  - `task_type`: `login` / `get_link` / `verify` / `bind_card` / `one_click`
  - `status`: pending/running/paused/completed/failed/cancelled
  - `config`: JSON（并发、卡池策略、SheerID key、安全增项等）
  - `celery_task_id`
  - `log`：任务聚合日志（`GET /tasks/{id}/log/`）

单账号执行记录：
- `Auto_All_System_Web/backend/plugins/google_business/models.py:GoogleTaskAccount`
  - `status`: processing/success/failed/skipped
  - `result_message` / `error_message`
  - `started_at` / `completed_at`

---

## 3. 产物：日志 / Trace / 截图

### 3.1 任务日志（DB）

批量任务 `GoogleTask.log`：
- `GET /api/v1/plugins/google-business/tasks/{id}/log/`

### 3.2 Trace 文件（文件系统）

`process_single_account` 会创建 `TaskLogger`，同时写：
- DB log（聚合到 GoogleTask.log）
- 文件 trace：`logs/trace/trace_<celery_task_id>_<safe_email>.log`

对应 API（按 cursor 分段读取，适合大文件）：
- `GET /api/v1/plugins/google-business/celery-tasks/{task_id}/trace/`
  - 参数：`cursor`、`direction`、`limit`、`email`

实现：
- `Auto_All_System_Web/backend/plugins/google_business/views.py:CeleryTaskViewSet.trace`

### 3.3 订阅截图（文件系统）

订阅验证任务会把截图写到：
- `BASE_DIR/screenshots/*.png`

读取截图 API：
- `GET /api/v1/plugins/google-business/subscription/screenshot/?file=xxx.png`

注意：该接口做了 basename 校验与目录校验，禁止路径穿越。

---

## 4. 浏览器与自动化运行时

### 4.1 运行方式

该插件使用 Playwright 通过 CDP 连接到浏览器实例：
- `playwright.chromium.connect_over_cdp(ws_endpoint)`

单账号执行入口：
- `Auto_All_System_Web/backend/plugins/google_business/tasks.py:process_single_account`

浏览器池/实例分配：
- `Auto_All_System_Web/backend/plugins/google_business/services/browser_pool.py`

默认浏览器类型：
- `apps.integrations.browser_base.get_browser_manager()._default_type`
  - 当前项目里优先 GeekezBrowser；BitBrowser 作为兼容选项（由 `browser_type` 参数控制）

### 4.2 并发与窗口回收

批量任务默认策略：
- 账号级并发由 `batch_process_task` 控制（`config.max_concurrency` 等）
- `process_single_account` 完成后会 `browser.close()`（避免大量窗口堆积）

---

## 5. 自动化：账号任务流（GoogleTask）

统一入口：
- `POST /api/v1/plugins/google-business/tasks/`
  - payload: `{ task_type, account_ids, config }`

### 5.1 task_type=login（登录）

代码：
- `tasks.py:process_single_account` -> `GoogleLoginService.login(page, account_info, task_logger)`

输入：
- email/password/totp_secret/recovery_email（由 GoogleAccount 解密得到）

输出：
- `success` / `message`
- 更新 task_account.status

### 5.2 task_type=get_link（提取资格/SheerID 链接）

代码：
- `GoogleOneLinkService.get_verification_link(...)`

行为：
- 返回 `(status, link, message)`
- status 典型值：`link_ready` / `verified` / `subscribed` / `ineligible`
- 如拿到 link，会写回：`GoogleAccount.sheerid_link = link`

### 5.3 task_type=verify（SheerID API 验证）

代码：
- `SheerIDVerifyService(api_key=...)` + `verify_batch([...])`

前置：
- 需要 `GoogleAccount.sheerid_link` 可解析出 verification_id

写回：
- 成功：`GoogleAccount.sheerid_verified = True`

### 5.4 task_type=bind_card（绑卡 + 订阅）

代码：
- `GoogleOneBindCardService.bind_and_subscribe(page, card_info, account_info, task_logger)`

卡选择：
- `tasks.py:_select_card_for_task` 从统一卡池 `apps.cards.models.Card` 选卡（支持 pool_type + max_use_count + random/least_used/sequential）
- 任务结束会 `_mark_card_used`，失败也会增加 use_count（便于轮换/风控）

写回：
- 成功：`GoogleAccount.card_bound = True`

### 5.5 task_type=one_click（一键全自动）

主流程（`tasks.py` 明确写为 6 步）：
1) 登录
2) 打开 Google One 页面（不强依赖，失败会继续）
3) 检查学生资格（获取 SheerID link 或判定 verified）
4) 如需要则 SheerID 验证（API key 来自 config）
5) 绑卡订阅（会选卡并标记使用情况）
6) 完成

可选增项（默认关闭，由 config 控制）：
- `security_change_2fa: true` -> 在主流程结束后顺带修改 2FA
- `security_new_recovery_email: "xxx@xxx.com"`（兼容字段：new_recovery_email/new_recovery_email/new_email/new_email）-> 修改辅助邮箱

---

## 6. 自动化：安全设置（SecurityViewSet）

入口：
- `Auto_All_System_Web/backend/plugins/google_business/views.py:SecurityViewSet`

特点：
- 直接触发 Celery task（不走 GoogleTask），返回 celery_task_id
- 同时把动作写入 `GoogleAccount.metadata.google_zone_actions`，用于前端“任务记录”展示
- 前端用 `GET /celery-tasks/{task_id}/` 轮询状态，必要时用 `trace` 看细节

端点：
- `POST /security/change_2fa/` -> `google_business.security_change_2fa`
- `POST /security/change_recovery_email/` -> `google_business.security_change_recovery_email`
- `POST /security/get_backup_codes/` -> `google_business.security_get_backup_codes`
- `POST /security/one_click_update/` -> `google_business.security_one_click`

实现：
- `Auto_All_System_Web/backend/plugins/google_business/tasks.py`
  - `security_change_2fa_task`
  - `security_change_recovery_email_task`
  - `security_get_backup_codes_task`
  - `security_one_click_task`
- `Auto_All_System_Web/backend/plugins/google_business/services/security_service.py:GoogleSecurityService`

敏感信息注意：
- 修改 2FA 会产生新的 secret，必须确保只落库/脱敏展示（避免在 API 返回里回传明文）。

---

## 7. 自动化：订阅（SubscriptionViewSet）

入口：
- `Auto_All_System_Web/backend/plugins/google_business/views.py:SubscriptionViewSet`

端点：
- `POST /subscription/verify_status/` -> `google_business.subscription_verify_status`
- `POST /subscription/click_subscribe/` -> `google_business.subscription_click_subscribe`
- `GET /subscription/screenshot/?file=xxx.png` -> 读取截图

实现：
- `Auto_All_System_Web/backend/plugins/google_business/tasks.py`
  - `subscription_verify_status_task`
  - `subscription_click_subscribe_task`
- `Auto_All_System_Web/backend/plugins/google_business/services/subscription_service.py:SubscriptionVerifyService`

---

## 8. 常见问题与排查

### 8.1 任务卡住/无进展

优先排查：
- Celery worker 是否加载最新代码（重启 celery）
- CDP 是否能连上（看 trace 是否有 connect_over_cdp 重试/超时）

### 8.2 Google 登录失败

常见原因：
- 触发验证码/人机验证（需要人工介入，自动化不可控）
- 账号地区/语言导致 selector 变化
- 2FA / 恢复邮箱信息不正确

排查路径：
- `GET /celery-tasks/{task_id}/trace/?email=<target>` 看账号级 trace
- `GET /tasks/{id}/log/` 看聚合日志

### 8.3 SheerID 验证失败

常见原因：
- `sheerid_link` 不存在或无法解析 verification_id
- API key 未配置（config 里 api_key/sheerid_api_key）

### 8.4 绑卡失败

常见原因：
- 卡池无可用卡（max_use_count/过期/状态 in_use）
- 页面风控/卡被拒绝

---

## 9. 代码索引（维护入口）

后端：
- `Auto_All_System_Web/backend/plugins/google_business/views.py`
- `Auto_All_System_Web/backend/plugins/google_business/urls.py`
- `Auto_All_System_Web/backend/plugins/google_business/tasks.py`
- `Auto_All_System_Web/backend/plugins/google_business/services/login_service.py`
- `Auto_All_System_Web/backend/plugins/google_business/services/link_service.py`
- `Auto_All_System_Web/backend/plugins/google_business/services/verify_service.py`
- `Auto_All_System_Web/backend/plugins/google_business/services/bind_card_service.py`
- `Auto_All_System_Web/backend/plugins/google_business/services/security_service.py`
- `Auto_All_System_Web/backend/plugins/google_business/services/subscription_service.py`
- `Auto_All_System_Web/backend/plugins/google_business/services/browser_pool.py`

前端：
- `Auto_All_System_Web/frontend/src/views/zones/GoogleBusinessZone.vue`
- `Auto_All_System_Web/frontend/src/views/zones/google-modules/GoogleAccountsModule.vue`
- `Auto_All_System_Web/frontend/src/api/google.ts`

---

## 10. Dev 验证（E2E / Smoke）

这部分用于验证：Security / Subscription 模块是否真实走后端 Celery + GeekezBrowser 自动化（而不是前端假轮询）。

前置条件：
- Docker dev 环境已启动
- GeekezBrowser 在宿主机运行，且容器内可访问（常见：`http://host.docker.internal:19527`）

启动服务（示例）：
```bash
cd Auto_All_System_Web
docker compose -f docker-compose.dev.yml up -d
```

获取登录 token（示例账号）：
```bash
python - <<"PY"
import requests
BASE='http://localhost:8000'
print(r.status_code)
print(r.json())
PY
```

Security / Subscription 任务触发（示例）：
- `POST /api/v1/plugins/google-business/security/get_backup_codes/`
- `POST /api/v1/plugins/google-business/security/change_2fa/`
- `POST /api/v1/plugins/google-business/subscription/verify_status/`
- `POST /api/v1/plugins/google-business/subscription/click_subscribe/`

轮询 Celery task 状态：
- `GET /api/v1/plugins/google-business/celery-tasks/{task_id}/`

读取 trace（账号级详细日志）：
- `GET /api/v1/plugins/google-business/celery-tasks/{task_id}/trace/?email=<target>`

常见问题：
- `429 Too Many Requests`：降低轮询频率
- task 长期 PROGRESS：优先重启 celery worker 确认代码已加载

---

## 11. 补充：修改 2FA 的实现要点（安全）

入口 API：
- `POST /api/v1/plugins/google-business/security/change_2fa/`

后端链路：
- `views.py:SecurityViewSet.change_2fa` -> `tasks.py:security_change_2fa_task`

对每个账号的高层步骤：
1) 读 GoogleAccount 并解密 password / old 2FA secret
2) `browser_pool.acquire_by_email(...)` 获取浏览器实例（Geekez/BitBrowser）
3) 检查登录态，不满足则先登录
4) `GoogleSecurityService.change_2fa_secret(page, account)` 执行页面自动化
5) 成功则把 new_secret 加密写回 DB，并将动作记录追加到 `metadata.google_zone_actions`

敏感信息注意：
- new_secret 属于敏感数据；不建议在 Celery result / API 直接回传明文。
- 推荐策略：只落库；前端展示掩码；导出时再由有权限的后端进行解密输出。

---

## 12. 补充：登录状态/资格检测优化建议（可选）

这部分属于“可选优化”，用于提升稳定性（避免纯文本判断 + sleep）。

登录检测建议：
- 访问 `https://accounts.google.com/` 后，通过头像元素判断已登录：
  - 示例 selector：`a[aria-label*="Google Account"] img`

资格/订阅检测建议：
- 访问 Google One 学生页面后，优先通过拦截 API 响应判断订阅态（减少页面文案变化影响）：
  - 典型 rpc：`rpcids=GI6Jdd`
  - 响应包含 `2 TB` / `Antigravity` 等关键字可判定 subscribed
- 未订阅时，再 fallback 到页面元素 `jsname` 检测：
  - `jsname="hSRGPd"` -> link_ready
  - `jsname="V67aGc"` -> verified

等待策略建议：
- 尽量用 Playwright 的 auto-wait（locator/expect），减少 `sleep()`
- 对“必须等接口返回”的点用 `page.wait_for_response()`

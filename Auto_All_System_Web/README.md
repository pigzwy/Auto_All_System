# Auto All System Web

多专区自动化任务平台，采用插件化架构，支持 Google 账号自动化（SheerID 学生验证 + Gemini 订阅）、GPT 账号批量管理等业务。

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Vue 3 + TypeScript + Vite 5 + Tailwind CSS + shadcn-vue (reka-ui) + Pinia + Vue Router 4 |
| 后端 | Django 5.0 + Django REST Framework + Celery 5.3 + Channels 4.0 (WebSocket) |
| 数据库 | PostgreSQL 14 + Redis 7 (缓存/消息队列) |
| 浏览器自动化 | Playwright 1.40 + DrissionPage 4.1 |
| 浏览器环境 | GeekezBrowser（主用） / BitBrowser（兼容） |
| 部署 | Docker Compose (5 服务) + Nginx |

---

## 目录结构

```
Auto_All_System_Web/
├── backend/
│   ├── apps/                          # 核心应用（共享资源层）
│   │   ├── accounts/                  # 用户 + 余额 + 余额日志
│   │   ├── cards/                     # 虚拟卡池（Card / CardUsageLog / CardApiConfig）
│   │   ├── integrations/              # 第三方集成
│   │   │   ├── google_accounts/       # Google 账号池（GoogleAccount / SheerIDVerification / GeminiSubscription）
│   │   │   ├── geekez/                # GeekezBrowser API 封装
│   │   │   ├── bitbrowser/            # BitBrowser API 封装
│   │   │   ├── proxies/               # 代理管理
│   │   │   └── email/                 # CloudMail 域名邮箱集成
│   │   ├── plugins/                   # 插件管理器（发现/加载/生命周期）
│   │   ├── tasks/                     # 通用任务系统（Task / TaskLog / TaskStatistics）
│   │   ├── zones/                     # 专区管理（Zone / ZoneConfig / UserZoneAccess）
│   │   ├── payments/                  # 支付模块
│   │   └── admin_panel/               # 管理后台
│   ├── plugins/                       # 业务插件（各专区核心逻辑）
│   │   ├── google_business/           # Google 专区插件 ★ 主业务
│   │   │   ├── services/              # 自动化服务
│   │   │   │   ├── login_service.py          # Google 登录（2FA/验证码处理）
│   │   │   │   ├── link_service.py           # SheerID 链接提取
│   │   │   │   ├── verify_service.py         # SheerID API 验证
│   │   │   │   ├── bind_card_service.py      # 绑卡订阅
│   │   │   │   ├── security_service.py       # 2FA/辅助邮箱修改
│   │   │   │   ├── subscription_service.py   # 订阅状态验证
│   │   │   │   └── robust_google_auth.py     # 鲁棒登录（验证码/人机检测）
│   │   │   ├── tasks.py               # Celery 异步任务（process_single_account / batch）
│   │   │   ├── views.py               # API 视图
│   │   │   ├── models.py              # GoogleTask / GoogleTaskAccount / GoogleCardInfo
│   │   │   ├── urls.py                # API 路由
│   │   │   ├── utils.py               # TaskLogger / EncryptionUtil
│   │   │   └── docs/                  # 插件维护文档
│   │   │       └── AUTOMATION_MAINTENANCE.md  # ★ Google 专区自动化维护主文档
│   │   └── gpt_business/             # GPT 专区插件
│   │       ├── services/              # 自动化服务
│   │       ├── tasks.py               # Celery 任务
│   │       └── docs/                  # 插件维护文档
│   ├── config/
│   │   └── settings/                  # Django 分环境配置
│   │       ├── base.py                # 基础配置（INSTALLED_APPS / DB / Cache / Celery）
│   │       ├── development.py         # 开发环境
│   │       └── production.py          # 生产环境
│   ├── core/                          # 核心工具（权限/分页/异常处理）
│   └── requirements/                  # Python 依赖
│       ├── base.txt                   # 基础依赖
│       └── development.txt            # 开发依赖
├── frontend/
│   └── src/
│       ├── api/                       # API 接口层（按模块拆分 20+ 文件）
│       ├── components/
│       │   ├── ui/                    # shadcn-vue 基础组件
│       │   ├── app/                   # Element Plus 兼容层封装
│       │   └── zones/                 # 专区业务组件
│       ├── composables/               # 组合式函数
│       ├── layouts/                   # 布局组件
│       ├── router/modules/            # 模块化路由
│       ├── stores/                    # Pinia 状态管理
│       ├── types/                     # TypeScript 类型定义
│       └── views/                     # 页面视图
│           ├── admin/                 # 管理后台
│           ├── auth/                  # 认证页面
│           ├── cards/                 # 虚拟卡管理
│           ├── google/                # Google 账号管理
│           └── zones/                 # 专区页面
├── docker-compose.yml                 # Docker 编排（db/redis/backend/celery/frontend）
├── docs/                              # 系统级文档
└── README.md                          # 本文件
```

---

## 核心数据模型

### 关系图

```
User (用户)
  ├─1:1─ UserBalance (余额)
  ├─1:N─ BalanceLog (充值/消费/退款)
  ├─1:N─ GoogleAccount (Google 账号池，通过 owner_user)
  ├─1:N─ Card (私有虚拟卡，通过 owner_user)
  ├─1:N─ Task (通用任务)
  └─1:N─ UserZoneAccess (专区权限)

GoogleAccount (Google 账号)
  ├─ 字段: email(唯一), password(加密), recovery_email, two_fa_secret(加密)
  ├─ 状态: status(ACTIVE/LOCKED/DISABLED/PENDING_VERIFY)
  ├─ 订阅: gemini_status, sheerid_verified, card_bound, sheerid_link
  ├─ 元数据: metadata(JSON, 含 google_one_status / geekez_profile 等)
  ├─N:1─ Card (bound_card)
  ├─1:N─ SheerIDVerification (验证记录)
  └─1:N─ GeminiSubscription (订阅记录)

Card (虚拟卡)
  ├─ 字段: card_number, expiry_month/year, cvv, card_type
  ├─ 卡池: pool_type(PUBLIC/PRIVATE), owner_user
  ├─ 状态: status(AVAILABLE/IN_USE/USED/INVALID/EXPIRED)
  ├─ 统计: use_count, success_count, max_use_count
  └─1:N─ CardUsageLog (使用记录)

GoogleTask (Google 专区任务)
  ├─ 类型: LOGIN / GET_LINK / VERIFY / BIND_CARD / ONE_CLICK
  ├─ 状态: PENDING / RUNNING / COMPLETED / FAILED / CANCELLED
  ├─ 进度: total_count, success_count, failed_count
  ├─ Celery: celery_task_id
  └─1:N─ GoogleTaskAccount (任务-账号关联)

Zone (专区)
  ├─ 字段: name, code(唯一), plugin_class(插件类路径)
  ├─1:N─ ZoneConfig (专区配置 KV)
  └─1:N─ UserZoneAccess (用户权限)
```

### 密码/密钥加密

- `GoogleAccount.password` 和 `GoogleAccount.two_fa_secret` 使用 `EncryptionUtil`（AES-256 对称加密）
- 解密：`EncryptionUtil.decrypt(account.password)` — 可能失败（明文存储或 key 不匹配时回退原始值）
- 2FA 码生成：`pyotp.TOTP(secret).now()`

---

## Google 专区核心业务流程

### 一键到底（ONE_CLICK）6 步流程

这是最核心的业务逻辑，位于 `plugins/google_business/tasks.py` → `process_single_account()` → `task_type == "one_click"`：

```
步骤 1/6: 登录账号
  ├─ check_login_status() → 已登录则跳过
  ├─ login() → 成功则标记 ACTIVE
  ├─ 失败分类：
  │   ├─ 机器人验证(captcha) → 标记 LOCKED，中止
  │   ├─ 密码错误 → 标记 LOCKED，中止
  │   └─ 2FA超时 → 尝试 check_login_status 恢复
  └─ 登录成功后清理历史失败标记 (clear_login_failure_notes)

步骤 2/6: 打开 Google One 页面
  └─ 导航到 /about/plans/ai-premium/student

步骤 2.5/6: 快速检查订阅状态
  ├─ 访问 /about/plans 检查页面文案
  ├─ "Choose a plan" + "By upgrading" → 已订阅 Pro → 直接完成
  └─ "Try Google One" + "By subscribing" → 未订阅 → 继续

步骤 3/6: 检查学生资格
  ├─ GoogleOneLinkService.get_verification_link()
  ├─ 返回状态: link_ready / verified / subscribed / ineligible
  ├─ ineligible → 跳过后续步骤
  └─ 获取 SheerID 验证链接

步骤 4/6: 学生验证（带取消+刷新重试，最多 3 次）
  ├─ SheerIDVerifyService.verify_batch([verification_id])
  ├─ 成功 → 标记 sheerid_verified = True
  ├─ 失败 → 取消旧验证 cancel_verification()
  │         → 刷新页面 page.reload()
  │         → 重新获取链接 check_google_one_status()
  │         → 用新链接重试
  └─ 全部失败 → 返回失败，不继续到步骤 5

步骤 5/6: 绑卡订阅
  ├─ _select_card_for_task() → 从卡池选卡（SELECT FOR UPDATE + skip_locked）
  ├─ GoogleOneBindCardService.bind_and_subscribe()
  ├─ 错误类型区分：
  │   ├─ CARD_INVALID: 新卡被拒 → 标记卡为 invalid
  │   └─ REBIND_NEEDED: 旧卡问题 → 不标记新卡
  └─ _mark_card_used() → 更新卡使用统计

步骤 6/6: 完成处理
  ├─ 安全设置增项（可选）：修改 2FA / 修改辅助邮箱
  └─ 返回结果
```

### 卡池选卡策略

```python
# 位于 tasks.py → _select_card_for_task()
# 使用 SELECT FOR UPDATE (skip_locked) 防止并发重复选卡
# 策略: sequential（默认，按最后使用时间排序）/ least_used / random
# 过滤: pool_type(public/private) + status(available) + 未过期 + 未达上限
```

### 任务调度模型

```
batch_process_task (入口)
  └─ dispatch_task_batch (分批派发，chord 门控)
       ├─ process_single_account × N (一批并发)
       ├─ 等待全部完成
       ├─ 休息 rest_min~rest_max 分钟
       └─ dispatch_task_batch (下一批，递归)
```

关键参数：
- `max_concurrency`: 每批并发数 (1-20)
- `stagger_seconds`: 同批内错开启动秒数
- `rest_min_minutes` / `rest_max_minutes`: 批间休息时间

### 浏览器环境

每个账号任务在子任务 `process_single_account` 内按需创建浏览器环境：
1. 通过 `GeekezBrowserManager.ensure_profile_for_account()` 确保浏览器配置文件存在
2. 通过 `launch_by_email()` 启动浏览器获取 `ws_endpoint`
3. 通过 `playwright.chromium.connect_over_cdp(ws_endpoint)` 连接
4. 任务完成后 `GeekezBrowserAPI().close_profile()` 关闭

### resume_mode（续跑机制）

one_click 默认开启 `resume_mode`：根据账号当前状态自动跳过已完成步骤：

```python
# 判断逻辑（tasks.py 一键到底核心）
has_open_one = google_one_status in ["link_ready","verified","subscribed","ineligible"] or sheerid_link or sheerid_verified
has_verify   = sheerid_verified or google_one_status in ["verified","subscribed"]
has_subscribe= card_bound or gemini_status == "active" or google_one_status == "subscribed"

step2_needed = not has_open_one    # 打开 Google One
step3_needed = not has_eligibility # 检查学生资格
step4_needed = not has_verify      # 学生验证
step5_needed = not has_subscribe   # 绑卡订阅
```

可通过 `config.force_rerun=True` 强制全部重新执行。

### 独立安全设置任务

除一键到底外，还有 4 个独立 Celery 任务（位于 `tasks.py`）：

| 任务名 | Celery Name | 说明 |
|--------|------------|------|
| `security_change_2fa_task` | `google_business.security_change_2fa` | 批量修改 2FA 密钥 |
| `security_change_recovery_email_task` | `google_business.security_change_recovery_email` | 批量修改辅助邮箱 |
| `security_get_backup_codes_task` | `google_business.security_get_backup_codes` | 批量获取备份验证码 |
| `security_one_click_task` | `google_business.security_one_click` | 一键安全设置（2FA + 辅助邮箱） |
| `subscription_verify_status_task` | `google_business.subscription_verify_status` | 批量验证订阅状态 |
| `subscription_click_subscribe_task` | `google_business.subscription_click_subscribe` | 批量点击订阅按钮 |

这些任务使用 `ThreadPoolExecutor` + `asyncio.run()` 模型（每个线程独立 event loop），支持 `max_concurrency` / `stagger_seconds` / `rest_min/max_minutes` 批次参数。

---

## 前端路由

```
/google/dashboard     → GoogleDashboard.vue       # 工作台（统计/快速操作）
/google/accounts      → AccountManage.vue         # 账号管理（导入/筛选/批量操作）
/google/sheerid       → SheerIDManage.vue         # SheerID 验证管理
/google/bind-card     → AutoBindCard.vue          # 自动绑卡
/google/auto-all      → AutoAllInOne.vue          # 一键全自动

/gpt-zone             → GptBusinessZone.vue       # GPT 专区（模块化子页面）

/cards                → CardManage.vue            # 虚拟卡管理
/admin/*              → admin/ 系列页面            # 管理后台
```

---

## 插件架构

### 目录约定

```
plugins/<plugin_name>/
├── __init__.py           # 插件入口（继承 BasePlugin）
├── models.py             # 数据模型
├── views.py              # API 视图
├── urls.py               # URL 路由
├── tasks.py              # Celery 异步任务
├── services/             # 业务逻辑服务
├── serializers.py        # DRF 序列化器
└── docs/                 # 插件维护文档
```

### 注册方式

在 `config/settings/base.py` 的 `INSTALLED_APPS` 中添加：
```python
INSTALLED_APPS = [
    ...
    'plugins.google_business',
    'plugins.gpt_business',
]
```

---

## 开发规范

### 后端

1. **async/sync 边界**：Playwright 操作在 `async def _process()` 中执行，Django ORM 写入在 `asyncio.run()` 之后同步执行。需要在 async 中调用 ORM 时使用 `sync_to_async`。

2. **日志规范**：使用 `TaskLogger`（写入数据库 + 文件双通道），文件日志位于 `logs/trace/trace_<celery_id>_<email>.log`

3. **加密**：`EncryptionUtil.encrypt()` / `EncryptionUtil.decrypt()`，密钥来自 Django `SECRET_KEY`

4. **Celery 任务**：
   - `@shared_task(bind=True, max_retries=3)` — 失败自动重试
   - 任务内不要跨 `asyncio.run()` 传递 Playwright 对象
   - 使用 `transaction.atomic()` + `select_for_update()` 更新任务计数

5. **account_updates 模式**：one_click 流程中，所有账号字段更新先收集到 `account_updates: Dict` 中，在 `asyncio.run()` 完成后统一 `GoogleAccount.objects.filter(id=account_id).update(**account_updates)` 写入，避免 async 中触发 `SynchronousOnlyOperation`。

6. **绑卡错误前缀约定**：`bind_and_subscribe()` 返回的消息使用前缀区分错误类型：
   - `CARD_INVALID:...` — 新卡被支付网关拒绝，应标记卡为 invalid
   - `REBIND_NEEDED:...` — 旧卡问题（过期/换绑失败），不应标记新卡

### 前端

1. **UI 组件**：基于 shadcn-vue (reka-ui) + Tailwind CSS，不直接依赖 Element Plus
2. **兼容层**：`components/app/` 中有 `ElSwitch` → `Toggle`、`ElTable` → `DataTable` 等映射
3. **API 调用**：`src/api/` 按模块拆分，使用 axios 实例 + JWT 拦截器
4. **路由**：模块化路由在 `src/router/modules/` 中注册
5. **日志清理**：`src/lib/log-utils.ts` 提供统一的日志文本清理（过滤 JSON 重复行、去冗余前缀、简化时间戳），Google/GPT 专区共用

### 常见开发陷阱

| 问题 | 原因 | 解决 |
|------|------|------|
| `SynchronousOnlyOperation` | 在 async 函数中直接调用 Django ORM | 用 `sync_to_async` 包装，或在 `asyncio.run()` 之后同步调用 |
| Playwright 对象跨 loop | 在一个 `asyncio.run()` 中创建的 page 传到另一个 loop | 确保 acquire → 操作 → release 在同一个 `asyncio.run()` 内 |
| captcha 误判 | `detect_captcha()` 匹配到不可见元素 | 必须加 `is_visible()` 检查 |
| 验证失败仍绑卡 | step 4 失败后未 return，继续执行 step 5 | 失败时必须 `return {"success": False, ...}` |
| 并发选到同一张卡 | 没有行锁 | `select_for_update(skip_locked=True)` |

---

## 快速开始

### Docker 一键启动（推荐）

```bash
# 1. 启动所有服务
docker-compose up -d

# 2. 等待数据库就绪后初始化
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser

# 3. 访问
# 前端: http://localhost/
# API: http://localhost:8000/api/
# Swagger: http://localhost:8000/api/docs/
# Admin: http://localhost:8000/admin/
```

### 本地开发

```bash
# 后端
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements/development.txt
cp .env.example .env  # 编辑配置
python manage.py migrate
python manage.py runserver

# Celery
celery -A config worker -l info
celery -A config beat -l info

# 前端
cd frontend
pnpm install
pnpm dev
```

### Docker Compose 服务架构

| 服务 | 镜像 | 端口 | 说明 |
|-----|------|------|-----|
| db | PostgreSQL 14 | 5432 | 主数据库 |
| redis | Redis 7 | 6379 | 缓存 + Celery Broker |
| backend | Django 5.0 | 8000 | Web API + WebSocket |
| celery | 同 backend | - | 异步任务执行器 |
| celery-beat | 同 backend | - | 定时任务调度器 |
| frontend | Vue 3 + Nginx | 80 | 前端静态文件 |

### 关键环境变量

```bash
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# 数据库
POSTGRES_HOST=localhost  # Docker 中: db
POSTGRES_PORT=5432
POSTGRES_DB=auto_all_db
POSTGRES_USER=auto_all_user
POSTGRES_PASSWORD=your-password

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# 浏览器环境（GeekezBrowser）
GEEKEZ_API_HOST=localhost          # Docker 中: host.docker.internal
GEEKEZ_API_PORT=19527
GEEKEZ_DATA_DIR=/geekez-browser/BrowserProfiles

# 浏览器环境（BitBrowser，兼容）
BITBROWSER_API_URL=http://localhost:54345   # Docker 中: http://host.docker.internal:54345

# SheerID
SHEERID_API_KEY=your-api-key
```

---

## API 概览

认证方式：JWT Token（`Authorization: Bearer <token>`）

```
POST /api/v1/auth/login/              # 登录获取 Token
POST /api/v1/auth/refresh/            # 刷新 Token

# Google 专区
GET  /api/v1/plugins/google-business/accounts/           # 账号列表
POST /api/v1/plugins/google-business/accounts/batch_import/  # 批量导入
GET  /api/v1/plugins/google-business/accounts/statistics/    # 统计数据
POST /api/v1/plugins/google-business/tasks/              # 创建任务
GET  /api/v1/plugins/google-business/tasks/{id}/         # 任务详情
POST /api/v1/plugins/google-business/tasks/{id}/cancel/  # 取消任务
GET  /api/v1/plugins/google-business/tasks/{id}/logs/    # 任务日志

# 虚拟卡
GET  /api/v1/cards/                   # 卡列表
POST /api/v1/cards/batch_import/      # 批量导入卡片

# 完整 API 文档
# Swagger UI: http://localhost:8000/api/docs/
```

---

## 文档索引

### 系统级文档（`docs/`）

| 文档 | 说明 | 适合人群 |
|------|------|---------|
| [00-快速开始](docs/00-快速开始.md) | Docker 部署、初始化、健康检查 | 所有人 |
| [01-数据库设计](docs/01-数据库设计.md) | 完整表结构、关系图、索引设计 | 后端开发 |
| [02-系统架构与配置](docs/02-系统架构与配置.md) | 技术栈详解、Docker/HTTPS 配置 | 开发/运维 |
| [03-前端页面功能](docs/03-前端页面功能.md) | 25 个页面功能说明 | 前端开发 |
| [04-API接口文档](docs/04-API接口文档.md) | 50+ API 接口、开发规范、附录 | 前后端开发 |
| [05-插件化架构设计](docs/05-插件化架构设计.md) | 插件系统设计、生命周期、开发指南 | 插件开发 |
| [07-比特浏览器API开发指南](docs/07-比特浏览器API开发指南.md) | BitBrowser API 封装、Docker 集成 | 自动化开发 |
| [08-新增专区开发指南](docs/08-新增专区开发指南.md) | 新增/扩展专区的前后端步骤 | 业务扩展 |
| [09-GPT专区规划](docs/09-GPT专区账号体系与自动化规划.md) | GPT 母号/子号体系、自动化流程 | GPT 开发 |
| [11-GeekezBrowser适配](docs/11-GeekezBrowser_API_变更适配说明.md) | 上游 API 拆分适配 | 后端/运维 |
| [12-统一浏览器池化](docs/12-统一浏览器池化与自动化运行时.md) | browser_base / browser_pool 架构 | 自动化开发 |
| [14-前端UI问题定位](docs/14-前端UI问题快速定位手册.md) | 常见 UI 问题排查 Runbook | 前端开发 |

### 插件级文档

| 文档 | 说明 |
|------|------|
| [Google 专区自动化维护](backend/plugins/google_business/docs/AUTOMATION_MAINTENANCE.md) | **核心参考** — 任务流、数据模型、日志/产物、故障排查 |
| [GPT 专区自动化流程](backend/plugins/gpt_business/docs/AUTOMATION_FLOW.md) | GPT 邀请自动化维护 |
| [BitBrowser 模块](backend/apps/integrations/bitbrowser/README.md) | API 封装说明 |
| [Email 模块](backend/apps/integrations/email/README.md) | CloudMail 域名邮箱集成 |

### 归档文档

| 文档 | 说明 |
|------|------|
| [比特浏览器窗口管理Web化方案](docs/比特浏览器窗口管理Web化方案.md) | 历史迁移方案，已实施完成 |
| [13-前端现代化重构计划](docs/13-前端现代化重构与UI优化计划.md) | Phase 1 已完成，后续阶段待定 |

---

## 联系方式

- QQ: 2738552008
- Telegram: https://t.me/+9zd3YE16NCU3N2Fl
- QQ 群: 330544197

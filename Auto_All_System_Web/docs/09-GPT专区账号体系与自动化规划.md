# GPT专区账号体系与自动化规划

目标：在 `http://localhost:3000/gpt-zone` 的「账号列表」里，围绕"母号/子号/座位"实现一套可视化管理 + 自动化动作：
- 通过域名邮箱（CloudMail）随机生成邮箱
- 母号默认 4 座位，可批量生成
- 子账号挂在母号下，可展开查看
- 列表选中母号后，可触发：自助开通 / 自动邀请 / 自动入池

本规划会尽量复用现有代码与 `oai-team-auto-provisioner` 的实现逻辑：
- 自助开通参考：`/home/pig/github/oai-team-auto-provisioner/tools/batch_register.py`
- 自助拉人邀请参考：`/home/pig/github/oai-team-auto-provisioner/run.py`
- 自动入池参考：`/home/pig/github/oai-team-auto-provisioner/tools/sub2api_sink_run.py`

---

## 现状盘点

1) GPT专区前端已有模块化结构：`frontend/src/views/zones/GptBusinessZone.vue`，目前已有「工作台」模块（已清空待开发）。

2) 域名邮箱（CloudMail）后端已有配置与测试接口：
- 管理：`/api/v1/email/configs/`（admin）
- 默认配置：`/api/v1/email/configs/get_default/`
- 测试创建：`/api/v1/email/configs/{id}/test_email/`（返回随机邮箱+邮箱密码）

3) GPT专区插件后端（gpt_business）当前以 `PluginState.settings` 作为轻量存储，已具备 tasks/产物下载等框架。

4) **已有代码分析**：
   - `create_mother` API 已存在，但只创建邮箱+保存记录，**缺少注册GPT和开通订阅逻辑**
   - domains 字段存在格式解析 bug（嵌套 JSON 字符串 + 末尾多余逗号）- **已修复**

---

## 上游代码分析（oai-team-auto-provisioner）

### batch_register.py 核心逻辑
```python
# 1. 批量创建邮箱
accounts = batch_create_emails(count)

# 2. 逐个浏览器注册
for account in accounts:
    page = init_browser()
    success = register_openai_account(page, email, password)  # 浏览器自动注册
    if success:
        onboarding_success, session_data = run_onboarding_flow(page, skip_checkout=False)
```

**关键依赖**：
- `browser_automation.init_browser()` - 初始化浏览器（Playwright/DrissionPage）
- `browser_automation.register_openai_account(page, email, password)` - 注册流程
- `tools.onboarding_flow.run_onboarding_flow(page)` - 引导页+checkout 流程
- `email_service` - 获取邮箱验证码

### run.py 核心逻辑
```python
# 完整流水线（单个 Team）
def process_single_team(team):
    # 1. 批量创建邮箱
    accounts = batch_create_emails(need_count)
    
    # 2. 批量邀请到 Team
    invite_result = batch_invite_to_team(emails, team)
    
    # 3. 逐个处理：注册 + Codex 授权 + CRS 入库
    for account in invited_accounts:
        register_success, codex_data = register_and_authorize(email, password)
        if register_success and codex_data:
            crs_add_account(email, codex_data)
```

**关键依赖**：
- `team_service.batch_invite_to_team(emails, team)` - 批量邀请（需要 team.auth_token）
- `browser_automation.register_and_authorize(email, password)` - 注册+授权一体
- `crs_service.crs_add_account(email, codex_data)` - 入库 CRS

**配置依赖**：
- `config.toml` - CloudMail/CRS/CPA/S2A 连接信息
- `team.json` - Team 列表（name, auth_token, account_id, owner_email, owner_password）

### sub2api_sink_run.py 核心逻辑
```python
# 1. 从 CSV 读取 email 列表（只读 success 状态）
target_emails = load_emails_from_accounts_csv(csv_path)

# 2. 从 CRS 拉取账号列表
accounts = crs_list_openai_accounts(crs_cfg)

# 3. 逐个导入到 Sub2API
for email in emails:
    acc = crs_find_account_by_email(accounts, email)
    oauth = acc.get("openaiOauth")  # access_token, refresh_token
    sub2api_create_openai_oauth_account(sub2_cfg, email=email, access_token=..., refresh_token=...)
```

**配置依赖**：
- CRS: `--crs-api-base`, `--crs-admin-token`
- Sub2API: `--sub2api-api-base`, `--sub2api-admin-api-key`/`--sub2api-admin-jwt`
- 可选: `--group-ids`, `--concurrency`, `--priority`

---

## 需求拆解与关键约束

### A. 母号创建
- 从 `http://localhost:3000/admin/email` 里选择一条"域名邮箱配置"（CloudMailConfig）
- seat_total 默认 4
- 生成：
  - `email`（随机）
  - `email_password`（邮箱系统密码，CloudMail 返回）
  - `account_password`（用于 OpenAI/ChatGPT 注册登录的密码，需要随机生成并展示）
- 支持一次生成 N 个母号

### B. 母号/子号/座位
- 母号下挂多个子号；展开母号行可查看子号列表
- 座位 = seat_total；seat_used = 子号数量
- 子号邮箱同样由 CloudMail 随机生成（通常也需要 `account_password`，便于后续注册/登录）

### C. 列表动作
列表选中一个母号后，提供三个动作：
1) **自助开通**：注册 OpenAI/ChatGPT 账号 + onboarding/checkout 流程
2) **自动邀请**：基于母号 team 环境邀请子号进入 team（并驱动后续注册/授权）
3) **自动入池**：把 CRS 里的 openaiOauth 导入到 sub2api（oauth 账号池）

### D. 配置来源统一为 Web 配置
约束目标：不再依赖在 `oai-team-auto-provisioner` 仓库里手动维护 `config.toml/team.json`。

实现策略（推荐）：
- 后端以"任务 job_dir"为单位，临时生成 `config.toml`/`team.json`（内容来自 Web 配置 + 选中的 CloudMailConfig + 选中的母号/子号）
- 再以子进程形式调用 `oai-team-auto-provisioner` 的脚本（run.py / tools/*.py）
- 产物（accounts.csv、run.log、tracker.json 等）保存到后端 MEDIA 目录，并回写到插件的 task/account 记录中

---

## 数据结构设计（存储在 PluginState.settings）

### Account（母号/子号通用）
```python
{
    "id": "uuid",
    "type": "mother" | "child",
    "parent_id": "uuid",  # child 用
    
    "cloudmail_config_id": 1,
    "cloudmail_domain": "pigll.site",  # 实际使用的域名
    
    "email": "xxx@pigll.site",
    "email_password": "cloudmail密码",
    "account_password": "OpenAI登录密码",
    
    "seat_total": 4,  # mother 专用
    "note": "",
    
    # 三个动作的状态
    "open_status": "idle" | "running" | "success" | "failed",
    "invite_status": "idle" | "running" | "success" | "failed",
    "pool_status": "idle" | "running" | "success" | "failed",
    
    # 任务关联
    "last_task_ids": {
        "open": "task_id",
        "invite": "task_id",
        "pool": "task_id"
    },
    "last_error": "",
    
    # Team 信息（自助开通后获取）
    "auth_token": "",
    "account_id": "",
    
    "created_at": "2026-01-28T00:00:00Z",
    "updated_at": "2026-01-28T00:00:00Z"
}
```

### Tasks（复用现有 task 框架）
在现有 tasks 列表中新增 task.type：
- `'self_register'` (自助开通)
- `'auto_invite'` (自动邀请)
- `'sub2api_sink'` (自动入池)

每个任务记录：
```python
{
    "id": "uuid",
    "type": "self_register" | "auto_invite" | "sub2api_sink",
    "mother_id": "uuid",
    "status": "pending" | "running" | "success" | "failed",
    "started_at": "...",
    "finished_at": "...",
    "error": "",
    "result": {
        "artifacts": [{"name": "run.log", "path": "..."}],
        "summary": "注册成功"
    }
}
```

### GPT 配置（新增，存储在 PluginState.settings.gpt_config）
```python
{
    "crs_api_base": "https://crs.example.com",
    "crs_admin_token": "xxx",
    
    "sub2api_api_base": "https://s2a.example.com",
    "sub2api_admin_api_key": "xxx",  # 或 admin_jwt
    "sub2api_group_ids": [1, 2],
    "sub2api_concurrency": 3,
    "sub2api_priority": 50,
    
    "oai_provisioner_path": "/home/pig/github/oai-team-auto-provisioner"
}
```

---

## 后端 API 规划

### 1) CloudMail 配置列表（供 GPT专区创建母号时选择）
复用已有：
- `GET /api/v1/email/configs/`（仅管理员）

### 2) 账号树
- `GET /api/v1/plugins/gpt-business/accounts/`
  - 返回 mothers + children
  - 额外返回 cloudmail_configs（或仅返回 ids，让前端自行调用 /email/configs）

### 3) 批量创建母号
**现有** `POST /api/v1/plugins/gpt-business/accounts/mothers/` - 需要修复 domains 解析 ✅ 已修复

Request:
```json
{
  "cloudmail_config_id": 1,
  "domain": "example.com",  // 可选，留空随机
  "count": 10,
  "seat_total": 4,
  "note": "可选"
}
```

Response:
```json
{ "created": [ ...motherAccounts ] }
```

### 4) 创建子号
- `POST /api/v1/plugins/gpt-business/accounts/children/`

Request:
```json
{
  "parent_id": "...",
  "cloudmail_config_id": 1,
  "domain": "example.com",
  "count": 4,
  "note": "可选"
}
```

### 5) 任务动作（3个按钮）
建议每个动作启动一个 celery task，并返回 task record：
- `POST /api/v1/plugins/gpt-business/accounts/{mother_id}/self_register/`
- `POST /api/v1/plugins/gpt-business/accounts/{mother_id}/auto_invite/`
- `POST /api/v1/plugins/gpt-business/accounts/{mother_id}/sub2api_sink/`

### 6) GPT 配置管理
- `GET /api/v1/plugins/gpt-business/config/`
- `PUT /api/v1/plugins/gpt-business/config/`

---

## 后端实现策略（关键：复用 oai-team-auto-provisioner）

### 核心思路
所有动作都按"job_dir"运行，执行步骤统一为：
1) 生成 job_dir（MEDIA 下，例如 `MEDIA/gpt-business/jobs/{task_id}/`）
2) 软链接或 copy `oai-team-auto-provisioner` 到 job_dir/repo
3) 写入 repo/config.toml 与 repo/team.json（内容来自 Web 设置 + 选中账号）
4) 以子进程运行目标脚本，把 stdout/stderr 写入 run.log
5) 收集产物（accounts.csv / tracker.json / 其他）并回写到插件 task result
6) 更新母号/子号状态字段（open_status/invite_status/pool_status）

### config.toml 模板
```toml
[email]
provider = "cloudmail"
api_base = "{cloudmail.api_base}"
api_token = "{cloudmail.api_token}"
domains = {cloudmail.domains}

[crs]
api_base = "{gpt_config.crs_api_base}"
admin_token = "{gpt_config.crs_admin_token}"

[sub2api]
api_base = "{gpt_config.sub2api_api_base}"
admin_api_key = "{gpt_config.sub2api_admin_api_key}"
group_ids = {gpt_config.sub2api_group_ids}
```

### team.json 模板
```json
[
  {
    "name": "{mother.email}",
    "owner_email": "{mother.email}",
    "owner_password": "{mother.account_password}",
    "auth_token": "{mother.auth_token}",
    "account_id": "{mother.account_id}"
  }
]
```

### 自助开通实现
**场景**：母号已有 email + account_password，需要注册 OpenAI 账号

**实现方式**：创建 `tools/web_register_one.py` 脚本
```python
# 1. 读取参数
email = sys.argv[1]
password = sys.argv[2]

# 2. 初始化浏览器
page = init_browser()

# 3. 注册
success = register_openai_account(page, email, password)

# 4. onboarding
if success:
    onboarding_success, session_data = run_onboarding_flow(page)
    # session_data 可能包含 auth_token 等

# 5. 输出结果到 stdout (JSON 格式供后端解析)
print(json.dumps({"success": success, "session": session_data}))
```

### 自动邀请实现
**场景**：母号已注册，需要邀请子号加入 Team

**前置条件**：
- 母号已完成自助开通，获得 auth_token
- 子号已创建邮箱

**实现方式**：
1. 从母号读取 auth_token
2. 生成 team.json（只包含这一个 team）
3. 调用 `team_service.batch_invite_to_team(child_emails, team)`
4. 可选：触发子号的注册+授权流程

### 自动入池实现
**场景**：账号已在 CRS 中，需要导入到 Sub2API

**实现方式**：直接复用 `sub2api_sink_run.py`
```bash
python tools/sub2api_sink_run.py \
  --crs-api-base "{crs_api_base}" \
  --crs-admin-token "{crs_admin_token}" \
  --sub2api-api-base "{sub2api_api_base}" \
  --sub2api-admin-api-key "{sub2api_admin_api_key}" \
  --group-ids "{group_ids}" \
  --input-csv "{job_dir}/accounts.csv"
```

---

## 前端 UI 规划（AccountsModule）

### 1) 创建母号弹窗
- 选择 CloudMailConfig（下拉：name + domains_count + is_default）
- 可选指定 domain（下拉：来自 config.domains）
- seat_total 默认 4
- count（生成数量）默认 1

### 2) 列表展示
- 增加 selection（单选/多选按需求；当前需求是"选中一个" -> 建议单选）
- 母号行：显示 email / account_password / email_password / seat_used/seat_total / 状态
- 子号行：显示 email / account_password / email_password / 状态
- 可展开查看子号

### 3) 动作按钮
当选中一个母号时，展示：
- 自助开通（disabled if open_status == 'success'）
- 自动邀请（disabled if invite_status == 'success' 或 open_status != 'success'）
- 自动入池（disabled if pool_status == 'success'）

触发后：
- toast 提示启动成功
- 在母号行显示最近任务状态（running/success/failed）
- 提供跳转到任务日志/产物下载（复用现有 tasks/artifacts 能力）

---

## 详细实施计划

### Phase 0: 修复现有 Bug（✅ 已完成）
- [x] 修复 CloudMailConfig domains 字段解析问题（嵌套 JSON + 末尾逗号）
- [x] 清理 Google 专区重复菜单
- [x] 清空 GPT 工作台

### Phase 1: 账号创建基础（1-2 天）

#### P1.1 后端 - 完善母号创建 API
- [ ] 修复 `create_mother` API，确保 domains 正确解析
- [ ] 添加 `account_password` 随机生成逻辑
- [ ] 支持 `count` 批量创建
- [ ] 支持指定 `domain` 或留空随机

#### P1.2 后端 - 子号创建 API
- [ ] 新增 `POST /accounts/children/` 接口
- [ ] 关联 parent_id
- [ ] 支持批量创建

#### P1.3 前端 - 账号列表模块
- [ ] 创建 `AccountsModule.vue`
- [ ] 实现母号列表展示（email, password, seat_total）
- [ ] 实现子号展开展示
- [ ] 实现创建母号弹窗
- [ ] 实现创建子号弹窗

### Phase 2: 动作框架（1 天）

#### P2.1 后端 - 任务框架
- [ ] 添加 GPT 配置模型（CRS/Sub2API 连接信息）
- [ ] 添加 `GET/PUT /config/` 接口
- [ ] 创建 Celery Task 基类（job_dir 生成、日志收集、状态更新）

#### P2.2 后端 - 三个动作 API
- [ ] `POST /accounts/{id}/self_register/` - 启动自助开通任务
- [ ] `POST /accounts/{id}/auto_invite/` - 启动自动邀请任务
- [ ] `POST /accounts/{id}/sub2api_sink/` - 启动自动入池任务

#### P2.3 前端 - 动作按钮
- [ ] 添加单选功能
- [ ] 添加三个动作按钮
- [ ] 实现按钮状态控制（根据 open_status/invite_status/pool_status）
- [ ] 实现任务启动和状态轮询

### Phase 3: 自助开通（2-3 天）

#### P3.1 上游适配
- [ ] 在 oai-team-auto-provisioner 创建 `tools/web_register_one.py`
- [ ] 单账号注册脚本，输出 JSON 结果

#### P3.2 后端实现
- [ ] Celery Task: `self_register_task`
  - 生成 job_dir
  - 写入 config.toml
  - 调用 web_register_one.py
  - 收集结果，更新账号状态
  - 保存 auth_token（如果获取到）

#### P3.3 测试验证
- [ ] 手动测试单账号注册
- [ ] 验证邮箱验证码获取
- [ ] 验证 onboarding 流程

### Phase 4: 自动邀请（2 天）

#### P4.1 后端实现
- [ ] Celery Task: `auto_invite_task`
  - 读取母号 auth_token
  - 生成 team.json
  - 调用 team_service.batch_invite_to_team
  - 更新子号状态

#### P4.2 完整流水线（可选）
- [ ] 支持调用 run.py 完整流程
- [ ] 子号自动注册+授权+入库

### Phase 5: 自动入池（1 天）

#### P5.1 后端实现
- [ ] Celery Task: `sub2api_sink_task`
  - 生成 accounts.csv（从母号/子号）
  - 调用 sub2api_sink_run.py
  - 更新状态

#### P5.2 前端 - 配置页面
- [ ] GPT 配置页面（CRS/Sub2API 连接信息）
- [ ] 连接测试功能

### Phase 6: 优化和完善（1-2 天）

- [ ] 日志查看功能
- [ ] 产物下载功能
- [ ] 错误重试机制
- [ ] 批量操作支持
- [ ] 状态自动刷新

### 6) 启动浏览器环境（支持两种模式）

#### 6.1 API 接口
- `POST /api/v1/plugins/gpt-business/accounts/{account_id}/launch_geekez/`

**Request Body（可选）:**
```json
{
  "launch_type": "geekez"  // 默认，远程 GeekezBrowser
  // 或
  "launch_type": "local"   // 本地浏览器无痕模式
}
```

**Response（geekez 模式）:**
```json
{
  "success": true,
  "browser_type": "geekez",
  "profile_id": "xxx",
  "ws_endpoint": "ws://xxx",
  "pid": 12345
}
```

**Response（local 无痕模式）:**
```json
{
  "success": true,
  "launch_type": "local",
  "browser_type": "local",
  "target_url": "https://chatgpt.com/",
  "email": "xxx@domain.com"
}
```

#### 6.2 两种模式说明

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| GeekezBrowser（默认） | 启动远程浏览器环境，保留 Cookie 和登录状态 | 长期使用，需要保持登录状态 |
| 本地无痕模式 | 直接用本地浏览器打开目标 URL | 临时查看，不需要登录状态 |

#### 6.3 目标 URL 规则
- **母号**: `https://chatgpt.com/`
- **子号**: 如果有 team_account_id，则为 `https://chatgpt.com/g/{team_account_id}`，否则为 `https://chatgpt.com/`

### 7) Session 优先策略（已落地）

#### 7.1 安全策略
- 账号列表接口不再返回 `session.accessToken` 明文。
- 前端只接收 `has_session: boolean`，用于展示「有Session/无Session」。

#### 7.2 开通后 Session 校验
- 母号自动开通成功后，后端会持久化 `session` 到账号记录。
- 同步使用 session token 请求 `GET /backend-api/accounts/check/v4-2023-04-27` 校验 Team 权限。
- 校验成功：写回 `team_status=success` 与 `account_id`；失败：`team_status=failed`。

#### 7.3 自动邀请策略
- 母号邀请阶段优先走 session/token 直连请求：
  - 先获取 account_id（若缺失）。
  - 再调用 `POST /backend-api/accounts/{account_id}/invites` 发邀请。
- 仅当直连失败时，才回退到 BrowserService 浏览器流程。

#### 7.4 自动入池说明
- 子号「入队 + 入池（S2A OAuth）」当前仍依赖浏览器授权页流程，不能完全去浏览器化。
- 现阶段已增加子号 session 持久化与复用，减少重复登录；后续可在具备稳定后端 OAuth 直连接口后继续收敛浏览器依赖。

---

## 风险与待确认项

1) **"母号"是否等价于 team owner？**
   - 若是：自动邀请/开通/入池都围绕这个账号执行
   - **建议**：是的，母号 = Team Owner

2) **"自动邀请"是否只做邀请，还是要跑 run.py 的完整流水线？**
   - run.py 会做注册/授权/入库，可能与"自助开通/自动入池"按钮语义重叠
   - **建议**：MVP 只做邀请；后续可选完整流水线

3) **入池目标是否固定为 Sub2API？**
   - **建议**：是的，group_ids/priority/concurrency 由 Web 配置管理

4) **浏览器自动化环境**
   - oai-team-auto-provisioner 依赖 Playwright/DrissionPage
   - 需要确保后端服务器有浏览器环境

5) **auth_token 获取时机**
   - 自助开通后能否自动获取 auth_token？
   - 需要分析 onboarding_flow 的返回数据

---

## 技术依赖

1. **oai-team-auto-provisioner** - 上游自动化脚本
2. **Celery** - 异步任务队列
3. **CloudMail API** - 邮箱创建和验证码获取
4. **CRS API** - 账号管理系统
5. **Sub2API** - OAuth 账号池
6. **Playwright/DrissionPage** - 浏览器自动化

---

## 预计工时

| Phase | 内容 | 预计工时 |
|-------|------|----------|
| Phase 1 | 账号创建基础 | 1-2 天 |
| Phase 2 | 动作框架 | 1 天 |
| Phase 3 | 自助开通 | 2-3 天 |
| Phase 4 | 自动邀请 | 2 天 |
| Phase 5 | 自动入池 | 1 天 |
| Phase 6 | 优化完善 | 1-2 天 |
| **总计** | | **8-11 天** |

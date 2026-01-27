# GPT专区账号体系与自动化规划

目标：在 `http://localhost:3000/gpt-zone` 的「账号列表」里，围绕“母号/子号/座位”实现一套可视化管理 + 自动化动作：
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

1) GPT专区前端已有模块化结构：`frontend/src/views/zones/GptBusinessZone.vue`，目前已有「工作台」模块。

2) 域名邮箱（CloudMail）后端已有配置与测试接口：
- 管理：`/api/v1/email/configs/`（admin）
- 默认配置：`/api/v1/email/configs/get_default/`
- 测试创建：`/api/v1/email/configs/{id}/test_email/`（返回随机邮箱+邮箱密码）

3) GPT专区插件后端（gpt_business）当前以 `PluginState.settings` 作为轻量存储，已具备 tasks/产物下载等框架。

---

## 需求拆解与关键约束

### A. 母号创建
- 从 `http://localhost:3000/admin/email` 里选择一条“域名邮箱配置”（CloudMailConfig）
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
1) 自助开通（参考 batch_register）：注册 OpenAI/ChatGPT 账号（可能包含 onboarding/checkout 流程）
2) 自动邀请（参考 run.py）：基于母号 team 环境邀请子号进入 team（并可能驱动后续注册/授权）
3) 自动入池（参考 sub2api_sink_run）：把 CRS 里的 openaiOauth 导入到 sub2api（oauth 账号池）

### D. 配置来源统一为 Web 配置
约束目标：不再依赖在 `oai-team-auto-provisioner` 仓库里手动维护 `config.toml/team.json`。

实现策略（推荐）：
- 后端以“任务 job_dir”为单位，临时生成 `config.toml`/`team.json`（内容来自 Web 配置 + 选中的 CloudMailConfig + 选中的母号/子号）
- 再以子进程形式调用 `oai-team-auto-provisioner` 的脚本（run.py / tools/*.py）
- 产物（accounts.csv、run.log、tracker.json 等）保存到后端 MEDIA 目录，并回写到插件的 task/account 记录中

---

## 数据结构设计（存储在 PluginState.settings）

### Account（母号/子号通用）
建议字段：
- id: string
- type: 'mother' | 'child'
- parent_id: string (child 用)

- cloudmail_config_id: number
- cloudmail_domain: string (可选，记录本次实际选择的 domain)

- email: string
- email_password: string

- account_password: string  (OpenAI/ChatGPT 登录密码)

- seat_total: number (mother)
- note: string

- open_status: 'idle' | 'running' | 'success' | 'failed'
- invite_status: 'idle' | 'running' | 'success' | 'failed'
- pool_status: 'idle' | 'running' | 'success' | 'failed'

- last_task_ids: { open?: string; invite?: string; pool?: string } (记录 celery task id 或插件 task record id)
- last_error: string

- geekez_profile: object (可选，类似 google_business 的做法)
- geekez_env: object (可选)

- created_at / updated_at

### Tasks（复用现有 task 框架）
在现有 tasks 列表中新增 task.type：
- 'self_register'  (自助开通)
- 'auto_invite'    (自动邀请)
- 'sub2api_sink'   (自动入池)

每个任务记录：
- id
- type
- mother_id
- status / started_at / finished_at / error
- result: { artifacts: [{name,path}], summary, ... }

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
新增（推荐）：
- `POST /api/v1/plugins/gpt-business/accounts/mothers/bulk/`

Request:
```json
{
  "cloudmail_config_id": 1,
  "domain": "example.com",
  "count": 10,
  "seat_total": 4,
  "note": "可选"
}
```

Response:
```json
{ "created": [ ...motherAccounts ] }
```

说明：
- seat_total 默认 4
- account_password 后端随机生成（建议每个账号独立密码）

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

（同样建议支持一次生成 N 个子号）

### 5) 任务动作（3个按钮）
建议每个动作启动一个 celery task，并返回 task record：
- `POST /api/v1/plugins/gpt-business/accounts/{mother_id}/self_register/`
- `POST /api/v1/plugins/gpt-business/accounts/{mother_id}/auto_invite/`
- `POST /api/v1/plugins/gpt-business/accounts/{mother_id}/sub2api_sink/`

---

## 后端实现策略（关键：复用 oai-team-auto-provisioner）

### 核心思路
所有动作都按“job_dir”运行，执行步骤统一为：
1) 生成 job_dir（MEDIA 下，例如 `MEDIA/gpt-business/jobs/{task_id}/`）
2) copy `oai-team-auto-provisioner` 到 job_dir/repo（现有 legacy_runner 已实现类似逻辑）
3) 写入 repo/config.toml 与 repo/team.json（内容来自 Web 设置 + 选中账号）
4) 以子进程运行目标脚本，把 stdout/stderr 写入 run.log
5) 收集产物（accounts.csv / tracker.json / 其他）并回写到插件 task result
6) 更新母号/子号状态字段（open_status/invite_status/pool_status）

### 自助开通（参考 batch_register.py）
batch_register.py 里核心是：
- 批量创建邮箱（batch_create_emails）
- browser 注册（register_openai_account）
- onboarding_flow

但我们的场景是“母号已存在 email + account_password”，不需要再在脚本里创建邮箱。

推荐实现：在 job_dir/repo 下生成一个最小 runner（例如 `tools/web_register_one.py`），复用上游模块：
- 直接调用 `browser_automation.register_openai_account(page, email, password)`
- 邮箱验证码由上游 email_service 从 config.toml 指向 cloudmail 来拉取

### 自动邀请（参考 run.py）
run.py 是“完整流水线”（创建邮箱→邀请→注册→授权→入库）。

我们要拆成可控动作，至少做两层：
1) MVP：只做“邀请”
   - 利用 run.py 的 team_service.batch_invite_to_team 逻辑（它依赖 team.auth_token/account_id）
   - token 来源：
     - 若母号已通过自助开通拿到 token，可写入 team.json（新格式支持 token/account_id 缓存）
     - 或者先通过浏览器登录拿 token（需要额外实现）
2) 完整版：直接跑 run.py，但通过 config.toml 控制仅处理指定 team（team.json 只写一个 team）

### 自动入池（参考 sub2api_sink_run.py）
sub2api_sink_run 逻辑：
- 从 CRS 拉 openaiOauth（需要 crs_api_base + crs_admin_token）
- 把 oauth 写入 sub2api（需要 sub2api_api_base + admin_api_key/jwt + group_ids）
- 可选从 accounts.csv 读取 email 列表（只导入 success 状态）

所以自动入池要求：
- Web 配置里必须有 CRS/S2A(Sub2API) 连接信息
- 并且 CRS 里已经存在对应账号的 openaiOauth

---

## 前端 UI 规划（AccountsModule）

### 1) 创建母号弹窗
- 选择 CloudMailConfig（下拉：name + domains_count + is_default）
- 可选指定 domain（下拉：来自 config.domains）
- seat_total 默认 4
- count（生成数量）默认 1

### 2) 列表展示
- 增加 selection（单选/多选按需求；当前需求是“选中一个” -> 建议单选）
- 母号行：显示 email / account_password / email_password / seat_used/seat_total
- 子号行：显示 email / account_password / email_password

### 3) 动作按钮
当选中一个母号时，展示：
- 自助开通
- 自动邀请
- 自动入池

触发后：
- toast 提示启动成功
- 在母号行显示最近任务状态（running/success/failed）
- 提供跳转到任务日志/产物下载（复用现有 tasks/artifacts 能力）

---

## 里程碑（实施顺序）

M1（账号创建基础）：
- 母号创建改为选择 CloudMailConfig + seat_total=4 默认 + 支持 count 批量
- 子号创建支持 count 批量
- 列表展示密码（email_password + account_password）

M2（动作框架）：
- 列表单选 + 三个动作按钮 + 后端任务记录与日志

M3（自助开通）：
- 跑一个“单账号注册”的 runner（复用 batch_register 的核心注册逻辑）

M4（自动邀请）：
- 优先实现 invite-only（依赖 token/account_id 的获取/保存策略）
- 逐步演进到可选跑 run.py 的完整链路

M5（自动入池）：
- 复用 sub2api_sink_run 的逻辑，按母号/指定 CSV 进行导入

---

## 风险与待确认项

1) “母号”是否等价于 team owner（即 team.json 的 account/password）？
   - 若是：自动邀请/开通/入池都围绕这个账号执行

2) “自动邀请”是否只做邀请，还是要跑 run.py 的完整流水线？
   - run.py 会做注册/授权/入库，可能与“自助开通/自动入池”按钮语义重叠

3) 入池目标是否固定为 Sub2API（S2A）？group_ids/priority/concurrency 由 Web 配置管理。

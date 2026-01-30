# GPT 业务自动化流程文档

## 概述

本文档描述 GPT 业务模块的三大核心自动化功能：
1. **自动开通** - 注册 OpenAI 账号并开通 Team 订阅
2. **自动邀请** - 将账号邀请加入 Team 工作区
3. **自动入池** - 将账号授权并添加到 Sub2API 账号池

---

## 一、自动开通 (Self Register + Team Onboarding)

### 1.1 功能说明

自动完成新账号的注册和 Team 订阅开通全流程。

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

### 2.2 流程步骤

```
┌─────────────────────────────────────────────────────────────────┐
│                        自动邀请流程                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 获取 Team 信息                                               │
│     ├── 使用 Team 管理员的 auth_token                            │
│     ├── 调用 /backend-api/accounts/check 获取 account_id         │
│     └── 检查可用席位数                                            │
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

### 3.2 流程步骤

```
┌─────────────────────────────────────────────────────────────────┐
│                        自动入池流程                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 生成授权 URL                                                 │
│     ├── API: POST /admin/openai/generate-auth-url                │
│     └── 返回: auth_url, session_id                               │
│                                                                 │
│  2. 用户授权 (浏览器自动化)                                       │
│     ├── 打开 auth_url (OpenAI OAuth 页面)                        │
│     ├── 自动登录或使用已登录状态                                  │
│     ├── 同意授权                                                  │
│     └── 回调到 localhost:1455/auth/callback?code=xxx             │
│                                                                 │
│  3. 创建账号                                                     │
│     ├── 从回调 URL 提取 code                                     │
│     ├── API: POST /admin/openai/create-from-oauth                │
│     │   ├── session_id                                           │
│     │   ├── code                                                 │
│     │   ├── concurrency (并发数)                                 │
│     │   ├── priority (优先级)                                    │
│     │   └── group_ids (分组 ID)                                  │
│     └── 返回: 账号数据 (id, name, credentials)                   │
│                                                                 │
│  4. 完成                                                         │
│     └── 账号已添加到 S2A 账号池                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 认证方式

S2A 支持两种认证方式：

| 方式 | Header | 说明 |
|------|--------|------|
| Admin API Key | `x-api-key: {key}` | 推荐，永久有效 |
| JWT Token | `Authorization: Bearer {token}` | 需要定期刷新 |

### 3.4 关键 API

#### 生成授权 URL
```
POST {S2A_API_BASE}/admin/openai/generate-auth-url
Headers:
  x-api-key: {admin_key}
返回:
  {
    "code": 0,
    "data": {
      "auth_url": "https://auth.openai.com/...",
      "session_id": "xxx"
    }
  }
```

#### 从 OAuth 创建账号
```
POST {S2A_API_BASE}/admin/openai/create-from-oauth
Headers:
  x-api-key: {admin_key}
Body:
  {
    "session_id": "xxx",
    "code": "授权码",
    "concurrency": 1,
    "priority": 0,
    "group_ids": [1, 2]
  }
```

#### 获取分组列表
```
GET {S2A_API_BASE}/admin/groups?page=1&page_size=100
```

### 3.5 参考代码

来源: `oai-team-auto-provisioner/s2a_service.py`

| 函数 | 说明 |
|------|------|
| `s2a_verify_connection()` | 验证连接和认证 |
| `s2a_generate_auth_url()` | 生成授权 URL |
| `s2a_create_account_from_oauth()` | 从 OAuth 创建账号 |
| `s2a_add_account()` | 直接添加账号 |
| `s2a_get_groups()` | 获取分组列表 |
| `extract_code_from_url()` | 从回调 URL 提取授权码 |

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

存储路径: `MEDIA_ROOT/gpt_business/jobs/{task_id}/`

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

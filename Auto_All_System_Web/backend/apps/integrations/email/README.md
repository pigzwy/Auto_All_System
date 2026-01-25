# 邮件服务模块

基于 Cloud Mail API 的邮箱管理服务，用于自动创建辅助邮箱和接收验证码。

## 功能

- 自动创建域名邮箱
- 等待并提取验证码
- 与 Google 账号一对一绑定

## 快速开始

### 1. 配置 Cloud Mail

在 Django Admin 中添加 `Cloud Mail配置`:

| 字段 | 示例值 |
|------|--------|
| 名称 | 主服务 |
| API地址 | https://mail.180711.xyz/api/public |
| API Token | 通过 genToken 接口获取 |
| 域名 | ["pigll.site", "example.com"] |
| 默认角色 | gpt-team |
| 是否默认 | ✓ |

### 2. 使用服务

```python
from apps.integrations.email.services import EmailService, CloudMailClient

# 方式一：使用高层服务（推荐）
service = EmailService()

# 为 Google 账号创建辅助邮箱
email, password = service.create_recovery_email(google_account)

# 等待 Google 验证码
code = service.get_google_verification_code(email, timeout=120)
print(f"验证码: {code}")

# 方式二：直接使用客户端
client = CloudMailClient.from_config()

# 创建随机邮箱
email, pwd = client.create_random_user()

# 等待任意验证码
code = client.wait_for_verification_code(email, timeout=60)
```

### 3. 在安全设置流程中使用

```python
async def change_recovery_email_with_verification(page, account_info):
    """修改辅助邮箱并自动验证"""
    from apps.integrations.email.services import EmailService
    
    service = EmailService()
    google_account = get_google_account(account_info['email'])
    
    # 1. 创建新的辅助邮箱
    new_email, password = service.create_recovery_email(google_account)
    
    # 2. 在页面上填写新邮箱
    await fill_recovery_email(page, new_email)
    
    # 3. 等待验证码
    code = service.get_google_verification_code(new_email, timeout=120)
    
    if code:
        # 4. 填写验证码
        await fill_verification_code(page, code)
        return True, new_email
    
    return False, "获取验证码超时"
```

## API 参考

### CloudMailClient

```python
client = CloudMailClient(
    api_base="https://mail.180711.xyz/api/public",
    api_token="your-token",
    domains=["pigll.site"],
    default_role="user"
)

# 或从数据库配置创建
client = CloudMailClient.from_config()
```

**方法:**

| 方法 | 说明 |
|------|------|
| `create_user(email, password?, role?)` | 创建指定邮箱 |
| `create_random_user(domain?)` | 创建随机邮箱，返回 (email, password) |
| `list_emails(to_email, ...)` | 查询邮件列表 |
| `wait_for_email(to_email, timeout)` | 等待新邮件 |
| `wait_for_verification_code(to_email, timeout)` | 等待并提取验证码 |

### EmailService

```python
service = EmailService()
```

**方法:**

| 方法 | 说明 |
|------|------|
| `create_recovery_email(google_account)` | 创建辅助邮箱并绑定 |
| `get_verification_code(email, timeout)` | 获取验证码 |
| `get_google_verification_code(email)` | 获取 Google 验证码（预设过滤） |

## 数据模型

### CloudMailConfig

Cloud Mail API 配置，在 Admin 中管理。

### RecoveryEmail

辅助邮箱记录，与 GoogleAccount 一对一关联。

## 注意事项

1. **Cloud Mail 需要先创建用户才能收信** - 与临时邮箱不同
2. **Token 全局唯一** - 重新生成会使旧 Token 失效
3. **验证码超时** - 默认 120 秒，可根据需要调整

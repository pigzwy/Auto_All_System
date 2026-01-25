"""
邮件服务集成模块

提供基于 Cloud Mail API 的邮箱管理服务：
- 自动创建域名邮箱作为辅助邮箱
- 接收和提取验证码
- 与 Google 账号绑定

使用方法:
    from apps.integrations.email.services import EmailService, CloudMailClient

    # 方式一：使用高层服务
    service = EmailService()
    email, password = service.create_recovery_email(google_account)
    code = service.get_google_verification_code(email)

    # 方式二：直接使用客户端
    client = CloudMailClient.from_config()
    email, pwd = client.create_random_user()
    code = client.wait_for_verification_code(email)
"""

default_app_config = "apps.integrations.email.apps.EmailConfig"

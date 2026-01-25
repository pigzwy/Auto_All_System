"""
邮件服务应用配置
"""

from django.apps import AppConfig


class EmailConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integrations.email"
    verbose_name = "邮件服务"
    label = "email_service"  # 避免与 Django 内置 email 冲突

    def ready(self):
        """应用加载完成后执行"""
        pass

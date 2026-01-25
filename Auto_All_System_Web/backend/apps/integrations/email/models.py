"""
邮件服务数据模型 - 简化版

仅存储 Cloud Mail API 配置和已创建的邮箱账号
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class CloudMailConfig(models.Model):
    """
    Cloud Mail API 配置表
    """

    name = models.CharField(max_length=50, unique=True, verbose_name="配置名称")

    api_base = models.URLField(
        verbose_name="API地址", help_text="如: https://mail.180711.xyz/api/public"
    )

    api_token = models.CharField(max_length=255, verbose_name="API Token")

    # 可用域名列表 (JSON 数组)
    domains = models.JSONField(
        default=list,
        verbose_name="可用域名",
        help_text='如: ["pigll.site", "example.com"]',
    )

    default_role = models.CharField(
        max_length=50, default="user", verbose_name="默认角色"
    )

    is_default = models.BooleanField(default=False, verbose_name="是否默认")

    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "email_cloudmail_configs"
        verbose_name = "Cloud Mail配置"
        verbose_name_plural = "Cloud Mail配置"

    def __str__(self):
        return f"{self.name} {'(默认)' if self.is_default else ''}"

    def save(self, *args, **kwargs):
        if self.is_default:
            CloudMailConfig.objects.filter(is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)

    @classmethod
    def get_default(cls):
        """获取默认配置"""
        return (
            cls.objects.filter(is_active=True, is_default=True).first()
            or cls.objects.filter(is_active=True).first()
        )


class RecoveryEmail(models.Model):
    """
    辅助邮箱记录表
    记录通过 Cloud Mail 创建的辅助邮箱，与 Google 账号一对一绑定
    """

    email = models.EmailField(unique=True, db_index=True, verbose_name="邮箱地址")

    password = models.CharField(max_length=255, verbose_name="密码")

    # 绑定的 Google 账号 (一对一)
    google_account = models.OneToOneField(
        "google_accounts.GoogleAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recovery_email_account",
        verbose_name="绑定的Google账号",
    )

    # 所属用户
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="recovery_emails",
        verbose_name="所有者",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "email_recovery_emails"
        verbose_name = "辅助邮箱"
        verbose_name_plural = "辅助邮箱"

    def __str__(self):
        bound = f" -> {self.google_account.email}" if self.google_account else ""
        return f"{self.email}{bound}"

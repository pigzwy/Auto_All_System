"""
邮件服务 Admin 配置
"""

from django.contrib import admin
from .models import CloudMailConfig, RecoveryEmail


@admin.register(CloudMailConfig)
class CloudMailConfigAdmin(admin.ModelAdmin):
    """Cloud Mail 配置管理"""

    list_display = [
        "name",
        "api_base",
        "is_default",
        "is_active",
        "domains_display",
        "updated_at",
    ]
    list_filter = ["is_active", "is_default"]
    search_fields = ["name", "api_base"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("基本信息", {"fields": ("name", "is_default", "is_active")}),
        ("API 配置", {"fields": ("api_base", "api_token", "default_role")}),
        (
            "域名配置",
            {
                "fields": ("domains",),
                "description": '输入 JSON 数组格式，如: ["pigll.site", "example.com"]',
            },
        ),
        (
            "时间信息",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def domains_display(self, obj):
        """显示域名列表"""
        if obj.domains:
            return ", ".join(obj.domains[:3]) + ("..." if len(obj.domains) > 3 else "")
        return "-"

    domains_display.short_description = "域名"


@admin.register(RecoveryEmail)
class RecoveryEmailAdmin(admin.ModelAdmin):
    """辅助邮箱管理"""

    list_display = ["email", "google_account_email", "owner", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["email", "google_account__email"]
    readonly_fields = ["created_at"]
    raw_id_fields = ["google_account", "owner"]

    def google_account_email(self, obj):
        """显示绑定的 Google 账号"""
        return obj.google_account.email if obj.google_account else "-"

    google_account_email.short_description = "绑定账号"

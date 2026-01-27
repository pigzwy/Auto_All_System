"""
Cloud Mail 配置序列化器
"""

from rest_framework import serializers
from .models import CloudMailConfig


class CloudMailConfigSerializer(serializers.ModelSerializer):
    """Cloud Mail 配置序列化器"""

    domains_count = serializers.SerializerMethodField()

    class Meta:
        model = CloudMailConfig
        fields = [
            "id",
            "name",
            "api_base",
            "api_token",
            "domains",
            "default_role",
            "is_default",
            "is_active",
            "domains_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_domains_count(self, obj):
        return len(obj.domains) if obj.domains else 0


class CloudMailConfigListSerializer(serializers.ModelSerializer):
    """Cloud Mail 配置列表序列化器 - 隐藏敏感信息"""

    domains_count = serializers.SerializerMethodField()
    masked_token = serializers.SerializerMethodField()

    class Meta:
        model = CloudMailConfig
        fields = [
            "id",
            "name",
            "api_base",
            "masked_token",
            "domains",
            "default_role",
            "is_default",
            "is_active",
            "domains_count",
            "created_at",
            "updated_at",
        ]

    def get_domains_count(self, obj):
        return len(obj.domains) if obj.domains else 0

    def get_masked_token(self, obj):
        """遮掩 API Token"""
        if obj.api_token and len(obj.api_token) > 8:
            return obj.api_token[:4] + "****" + obj.api_token[-4:]
        return "****"


class TestEmailSerializer(serializers.Serializer):
    """测试发送邮件请求"""

    config_id = serializers.IntegerField(help_text="配置 ID")
    to_email = serializers.EmailField(help_text="收件人邮箱")
    subject = serializers.CharField(max_length=200, default="测试邮件", help_text="邮件主题")
    content = serializers.CharField(default="这是一封测试邮件", help_text="邮件内容")

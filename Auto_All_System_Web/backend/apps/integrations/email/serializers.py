"""
Cloud Mail 配置序列化器
"""

import json
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

    def validate_domains(self, value):
        """校验并标准化 domains 字段"""
        return self._normalize_domains(value)

    @staticmethod
    def _normalize_domains(value):
        """
        标准化 domains 格式，支持多种输入：
        - 正常数组: ["a.com", "b.com"]
        - 字符串化的数组: '["a.com", "b.com"]'
        - 数组里套字符串化数组: ['["a.com", "b.com"]']
        """
        if not value:
            return []

        # 如果是字符串，尝试解析 JSON
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    raise serializers.ValidationError("domains 格式错误，无法解析 JSON")
            else:
                # 单个域名字符串
                return [value] if value else []

        if not isinstance(value, list):
            raise serializers.ValidationError("domains 必须是数组格式")

        # 递归处理数组中的元素
        result = []
        for item in value:
            if isinstance(item, str):
                item = item.strip()
                # 检查是否是嵌套的 JSON 字符串
                if item.startswith("["):
                    try:
                        nested = json.loads(item)
                        if isinstance(nested, list):
                            result.extend([str(x).strip() for x in nested if str(x).strip()])
                            continue
                    except json.JSONDecodeError:
                        pass
                if item:
                    result.append(item)
            elif item:
                result.append(str(item).strip())

        return result


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

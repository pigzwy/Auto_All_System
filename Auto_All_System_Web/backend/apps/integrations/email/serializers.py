"""
Cloud Mail 配置序列化器
"""

import json
import re
from rest_framework import serializers
from .models import CloudMailConfig
from .services.client import CloudMailClient


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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Normalize for display to tolerate historical bad data.
        data["domains"] = self._normalize_domains(data.get("domains"))
        data["domains_count"] = len(data["domains"]) if data.get("domains") else 0
        return data

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

        def _dedupe_keep_order(items: list[str]) -> list[str]:
            seen: set[str] = set()
            out: list[str] = []
            for x in items:
                if x in seen:
                    continue
                seen.add(x)
                out.append(x)
            return out

        def _extract_domains_loose(text: str) -> list[str]:
            """Best-effort extraction for broken JSON strings.

            Handles cases like:
              [ "a.com", "b.com", ]
            """

            raw = (text or "").lower()
            # Conservative pattern: require at least one dot and TLD length >= 2.
            matches = re.findall(r"[a-z0-9.-]+\.[a-z]{2,}", raw)
            return _dedupe_keep_order([m.strip(". ") for m in matches if m])

        def _try_parse_json_list(text: str) -> list[str] | None:
            t = (text or "").strip()
            if not t.startswith("["):
                return None
            try:
                parsed = json.loads(t)
                return parsed if isinstance(parsed, list) else None
            except json.JSONDecodeError:
                # Try a minimal repair: remove trailing commas before closing brackets.
                repaired = re.sub(r",\s*\]", "]", t)
                repaired = re.sub(r",\s*\}", "}", repaired)
                try:
                    parsed = json.loads(repaired)
                    return parsed if isinstance(parsed, list) else None
                except json.JSONDecodeError:
                    return None

        # 如果是字符串，尝试解析 JSON
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                parsed = _try_parse_json_list(value)
                if parsed is None:
                    # Broken JSON -> best-effort extraction
                    value = _extract_domains_loose(value)
                else:
                    value = parsed
            else:
                # 单个域名字符串
                return [value] if value else []

        if not isinstance(value, list):
            raise serializers.ValidationError("domains 必须是数组格式")

        # 递归处理数组中的元素
        result: list[str] = []
        for item in value:
            if isinstance(item, str):
                item = item.strip()
                # 检查是否是嵌套的 JSON 字符串
                if item.startswith("["):
                    nested = _try_parse_json_list(item)
                    if isinstance(nested, list):
                        result.extend([str(x).strip() for x in nested if str(x).strip()])
                        continue
                    # Broken JSON -> best-effort extraction
                    result.extend(_extract_domains_loose(item))
                    continue
                if item:
                    result.append(item)
            elif item:
                result.append(str(item).strip())

        # Final normalization: reuse CloudMailClient normalization logic.
        normalized: list[str] = []
        for x in result:
            d = CloudMailClient._normalize_domain(x)
            if d:
                normalized.append(d)
        return _dedupe_keep_order(normalized)


class CloudMailConfigListSerializer(serializers.ModelSerializer):
    """Cloud Mail 配置列表序列化器 - 隐藏敏感信息"""

    domains = serializers.SerializerMethodField()
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

    def get_domains(self, obj):
        # Always normalize for display, to tolerate historical bad data.
        return CloudMailConfigSerializer._normalize_domains(obj.domains)

    def get_domains_count(self, obj):
        domains = self.get_domains(obj)
        return len(domains) if domains else 0

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

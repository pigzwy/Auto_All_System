"""
Google Business插件序列化器
"""

from rest_framework import serializers
from apps.integrations.google_accounts.models import GoogleAccount
from .models import (
    GoogleBusinessConfig,
    BusinessTaskLog,
    GoogleTask,
    GoogleCardInfo,
    GoogleTaskAccount,
)
from .utils import mask_card_number


# ==================== Google账号相关 ====================


class GoogleAccountSerializer(serializers.ModelSerializer):
    """Google账号序列化器"""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    google_one_status = serializers.SerializerMethodField()
    type_tag = serializers.SerializerMethodField()
    type_display = serializers.SerializerMethodField()
    geekez_profile_exists = serializers.SerializerMethodField()
    geekez_env = serializers.SerializerMethodField()
    # 不返回敏感字段（密码、密钥）

    class Meta:
        model = GoogleAccount
        fields = [
            "id",
            "email",
            "recovery_email",
            "status",
            "status_display",
            "google_one_status",
            "type_tag",
            "type_display",
            "geekez_profile_exists",
            "geekez_env",
            "sheerid_link",
            "sheerid_verified",
            "gemini_status",
            "card_bound",
            "notes",
            "created_at",
            "updated_at",
            "last_login_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_google_one_status(self, obj: GoogleAccount):
        meta = getattr(obj, "metadata", None) or {}
        return meta.get("google_one_status")

    def get_type_tag(self, obj: GoogleAccount):
        """派生账号类型（用于列表标签/筛选）。

        规则（优先级从高到低）：
        - ineligible: Google One 状态为 ineligible，或历史 status 为 ineligible
        - unbound_card: 已验证 (sheerid_verified 或 google_one_status=verified) 但未绑卡
        - success: 已订阅 (gemini_status=active 或 google_one_status=subscribed)
        - other: 其他
        """

        meta = getattr(obj, "metadata", None) or {}
        google_one_status = meta.get("google_one_status")
        status = getattr(obj, "status", "")

        if google_one_status == "ineligible" or status == "ineligible":
            return "ineligible"

        verified_like = (
            bool(getattr(obj, "sheerid_verified", False))
            or google_one_status == "verified"
        )
        if verified_like and not bool(getattr(obj, "card_bound", False)):
            return "unbound_card"

        if (
            getattr(obj, "gemini_status", "") == "active"
            or google_one_status == "subscribed"
        ):
            return "success"

        return "other"

    def get_type_display(self, obj: GoogleAccount):
        mapping = {
            "ineligible": "无资格",
            "unbound_card": "未绑卡",
            "success": "成功",
            "other": "其他",
        }
        return mapping.get(self.get_type_tag(obj), "其他")

    def get_geekez_profile_exists(self, obj: GoogleAccount):
        """Geekez 环境是否存在（Geekez profiles.json 中是否有同名 profile）。

        为避免 N 次读取 profiles.json：
        - list 接口会在 serializer context 里注入 geekez_profile_names
        - detail 接口没有注入时，才做一次按需检查
        """

        names = self.context.get("geekez_profile_names")
        if isinstance(names, set):
            return obj.email in names

        # fallback: detail 场景
        try:
            from apps.integrations.browser_base import get_browser_manager, BrowserType

            manager = get_browser_manager()
            api = manager.get_api(BrowserType.GEEKEZ)
            profile = api.get_profile_by_name(obj.email)
            return bool(profile)
        except Exception:
            return False

    def get_geekez_env(self, obj: GoogleAccount):
        """已启动并保存过的 Geekez 环境信息（launch 信息）。"""

        meta = getattr(obj, "metadata", None) or {}
        env = meta.get("geekez_env")
        return env if isinstance(env, dict) else None

    def to_representation(self, instance):
        """自定义序列化输出（脱敏）"""
        data = super().to_representation(instance)
        # 恢复邮箱也可能是敏感信息，返回掩码
        if data.get("recovery_email"):
            email = data["recovery_email"]
            parts = email.split("@")
            if len(parts) == 2:
                data["recovery_email"] = f"{parts[0][:2]}***@{parts[1]}"
        return data


class GoogleAccountCreateSerializer(serializers.Serializer):
    """创建Google账号序列化器"""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    recovery_email = serializers.EmailField(required=False, allow_blank=True)
    secret_key = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class GoogleAccountEditSerializer(serializers.Serializer):
    """编辑 Google 账号（包含敏感字段）。

    注意：该 serializer 仅用于受控的自定义 action，不用于 list/retrieve。
    """

    email = serializers.EmailField(required=False)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    recovery_email = serializers.CharField(required=False, allow_blank=True)
    secret_key = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class GoogleAccountImportSerializer(serializers.Serializer):
    """批量导入Google账号序列化器"""

    accounts = serializers.ListField(
        child=serializers.CharField(),
        required=True,
        help_text="账号列表，格式: email----password----recovery----secret",
    )
    format = serializers.CharField(
        default="email----password----recovery----secret", help_text="账号格式"
    )
    match_browser = serializers.BooleanField(
        default=True, help_text="是否自动匹配浏览器ID"
    )
    overwrite_existing = serializers.BooleanField(
        default=False, help_text="是否覆盖已存在的账号"
    )


# ==================== 卡信息相关 ====================


class GoogleCardInfoSerializer(serializers.ModelSerializer):
    """卡信息序列化器"""

    card_number_masked = serializers.SerializerMethodField()
    is_available = serializers.BooleanField(read_only=True)
    remaining_usage = serializers.IntegerField(read_only=True)

    class Meta:
        model = GoogleCardInfo
        fields = [
            "id",
            "card_number_masked",
            "exp_month",
            "exp_year",
            "usage_count",
            "max_usage",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
            "last_used_at",
            "is_available",
            "remaining_usage",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "usage_count",
            "last_used_at",
        ]

    def get_card_number_masked(self, obj):
        """返回掩码后的卡号"""
        # 这里需要解密后再掩码
        try:
            from .utils import EncryptionUtil

            decrypted_number = EncryptionUtil.decrypt(obj.card_number)
            return mask_card_number(decrypted_number)
        except:
            return "****-****-****-****"


class GoogleCardInfoCreateSerializer(serializers.Serializer):
    """创建卡信息序列化器"""

    card_number = serializers.CharField(required=True, write_only=True)
    exp_month = serializers.CharField(required=True)
    exp_year = serializers.CharField(required=True)
    cvv = serializers.CharField(required=True, write_only=True)
    max_usage = serializers.IntegerField(default=1, min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)


class FlexibleCardItemField(serializers.Field):
    def to_internal_value(self, data):
        return data

    def to_representation(self, value):
        return value


class GoogleCardInfoImportSerializer(serializers.Serializer):
    """批量导入卡信息序列化器"""

    cards = serializers.ListField(
        child=FlexibleCardItemField(),
        required=True,
        help_text="卡信息列表，支持字符串或对象格式",
    )
    max_usage = serializers.IntegerField(default=1, help_text="一卡几绑（默认1）")

    def validate_cards(self, value):
        normalized = []
        for item in value:
            if isinstance(item, str):
                parts = item.split()
                if len(parts) < 4:
                    raise serializers.ValidationError(f"卡信息格式不正确: {item}")
                normalized.append(
                    {
                        "card_number": parts[0].strip(),
                        "exp_month": parts[1].strip(),
                        "exp_year": parts[2].strip(),
                        "cvv": parts[3].strip(),
                    }
                )
                continue

            if isinstance(item, dict):
                card_number = item.get("card_number")
                exp_month = item.get("exp_month") or item.get("expiry_month")
                exp_year = item.get("exp_year") or item.get("expiry_year")
                cvv = item.get("cvv")
                if not card_number or not exp_month or not exp_year or not cvv:
                    raise serializers.ValidationError("卡信息缺少必要字段")
                normalized.append(
                    {
                        "card_number": str(card_number).strip(),
                        "exp_month": str(exp_month).strip(),
                        "exp_year": str(exp_year).strip(),
                        "cvv": str(cvv).strip(),
                    }
                )
                continue

            raise serializers.ValidationError("卡信息格式不正确")

        return normalized


# ==================== 任务相关 ====================


class GoogleTaskSerializer(serializers.ModelSerializer):
    """任务序列化器"""

    task_type_display = serializers.CharField(
        source="get_task_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    progress_percentage = serializers.IntegerField(read_only=True)

    class Meta:
        model = GoogleTask
        fields = [
            "id",
            "task_type",
            "task_type_display",
            "status",
            "status_display",
            "config",
            "total_count",
            "success_count",
            "failed_count",
            "skipped_count",
            "progress_percentage",
            "celery_task_id",
            "estimated_cost",
            "actual_cost",
            "log",
            "created_at",
            "started_at",
            "completed_at",
        ]
        read_only_fields = [
            "id",
            "celery_task_id",
            "log",
            "created_at",
            "started_at",
            "completed_at",
            "success_count",
            "failed_count",
            "skipped_count",
            "actual_cost",
        ]


class GoogleTaskCreateSerializer(serializers.Serializer):
    """创建任务序列化器"""

    task_type = serializers.ChoiceField(
        choices=["login", "get_link", "verify", "bind_card", "one_click"], required=True
    )
    account_ids = serializers.ListField(
        child=serializers.IntegerField(), required=True, help_text="要处理的账号ID列表"
    )
    config = serializers.JSONField(
        required=False, default=dict, help_text="任务配置（并发数、延迟、API Key等）"
    )


class GoogleTaskAccountSerializer(serializers.ModelSerializer):
    """任务账号关联序列化器"""

    account_email = serializers.CharField(source="account.email", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    duration = serializers.IntegerField(read_only=True)
    card_masked = serializers.SerializerMethodField()

    class Meta:
        model = GoogleTaskAccount
        fields = [
            "id",
            "task",
            "account",
            "account_email",
            "status",
            "status_display",
            "result_message",
            "error_message",
            "card_used",
            "card_masked",
            "started_at",
            "completed_at",
            "duration",
        ]
        read_only_fields = ["id", "started_at", "completed_at"]

    def get_card_masked(self, obj):
        """返回掩码后的卡号"""
        if obj.card_used:
            try:
                from .utils import EncryptionUtil

                decrypted_number = EncryptionUtil.decrypt(obj.card_used.card_number)
                return mask_card_number(decrypted_number)
            except:
                return None
        return None


# ==================== 配置和日志 ====================


class BusinessTaskLogSerializer(serializers.ModelSerializer):
    """业务任务日志序列化器（向后兼容）"""

    task_type_display = serializers.CharField(
        source="get_task_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = BusinessTaskLog
        fields = [
            "id",
            "user",
            "google_account",
            "task",
            "task_type",
            "task_type_display",
            "status",
            "status_display",
            "started_at",
            "completed_at",
            "duration",
            "result_data",
            "error_message",
            "screenshots",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GoogleBusinessConfigSerializer(serializers.ModelSerializer):
    """Google Business配置序列化器"""

    class Meta:
        model = GoogleBusinessConfig
        fields = [
            "id",
            "key",
            "sheerid_enabled",
            "gemini_enabled",
            "auto_verify",
            "settings",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ==================== 统计和其他 ====================


class StatisticsSerializer(serializers.Serializer):
    """统计数据序列化器"""

    total = serializers.IntegerField(help_text="总账号数")
    pending = serializers.IntegerField(help_text="待处理")
    logged_in = serializers.IntegerField(help_text="已登录")
    link_ready = serializers.IntegerField(help_text="已获取链接")
    verified = serializers.IntegerField(help_text="已验证")
    subscribed = serializers.IntegerField(help_text="已订阅")
    ineligible = serializers.IntegerField(help_text="无资格")
    error = serializers.IntegerField(help_text="错误")


class PricingInfoSerializer(serializers.Serializer):
    """定价信息序列化器"""

    login = serializers.IntegerField(help_text="登录（积分）")
    get_link = serializers.IntegerField(help_text="获取链接（积分）")
    verify = serializers.IntegerField(help_text="SheerID验证（积分）")
    bind_card = serializers.IntegerField(help_text="绑卡订阅（积分）")
    one_click = serializers.IntegerField(help_text="一键到底（积分）")

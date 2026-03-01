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
from .utils import mask_card_number, EncryptionUtil


# ==================== Google账号相关 ====================


class GoogleAccountSerializer(serializers.ModelSerializer):
    """Google账号序列化器"""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    google_one_status = serializers.SerializerMethodField()
    type_tag = serializers.SerializerMethodField()
    type_display = serializers.SerializerMethodField()
    geekez_profile_exists = serializers.SerializerMethodField()
    geekez_env = serializers.SerializerMethodField()
    new_2fa = serializers.SerializerMethodField()
    new_2fa_display = serializers.SerializerMethodField()
    new_2fa_updated_at = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    group_id = serializers.SerializerMethodField()
    password = serializers.SerializerMethodField()  # 解密后的密码
    two_fa = serializers.SerializerMethodField()  # 2FA密钥（优先 new_2fa，否则 two_fa_secret）

    class Meta:
        model = GoogleAccount
        fields = [
            "id",
            "email",
            "password",
            "recovery_email",
            "status",
            "status_display",
            "google_one_status",
            "type_tag",
            "type_display",
            "geekez_profile_exists",
            "geekez_env",
            "new_2fa",
            "new_2fa_display",
            "new_2fa_updated_at",
            "two_fa",
            "sheerid_link",
            "sheerid_verified",
            "gemini_status",
            "card_bound",
            "notes",
            "group_id",
            "group_name",
            "created_at",
            "updated_at",
            "last_login_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_password(self, obj: GoogleAccount):
        """获取解密后的密码"""
        raw = getattr(obj, "password", None)
        if not raw:
            return None
        try:
            return EncryptionUtil.decrypt(raw)
        except Exception:
            return raw

    def get_two_fa(self, obj: GoogleAccount):
        """获取2FA密钥：优先 new_2fa_secret，否则用 two_fa_secret"""
        meta = getattr(obj, "metadata", None) or {}
        new_2fa = meta.get("new_2fa_secret")
        if isinstance(new_2fa, str) and new_2fa.strip():
            return new_2fa.strip()
        # 回退到原始 two_fa_secret
        raw = getattr(obj, "two_fa_secret", None)
        if not raw:
            return None
        try:
            return EncryptionUtil.decrypt(raw)
        except Exception:
            return raw

    def get_group_id(self, obj: GoogleAccount):
        """获取分组ID（已废弃，返回分组名称作为ID）"""
        return getattr(obj, "group_name", "") or None

    def get_group_name(self, obj: GoogleAccount):
        """获取分组名称"""
        return getattr(obj, "group_name", "") or None

    def get_google_one_status(self, obj: GoogleAccount):
        meta = getattr(obj, "metadata", None) or {}
        return meta.get("google_one_status")

    def get_type_tag(self, obj: GoogleAccount):
        """派生账号状态标签（与列表筛选 type_tag 口径尽量一致）。"""
        meta = getattr(obj, "metadata", None) or {}
        google_one_status = meta.get("google_one_status")
        status = getattr(obj, "status", "")
        notes = getattr(obj, "notes", "") or ""
        last_login_at = getattr(obj, "last_login_at", None)
        sheerid_link = (getattr(obj, "sheerid_link", "") or "").strip()
        sheerid_verified = bool(getattr(obj, "sheerid_verified", False))
        card_bound = bool(getattr(obj, "card_bound", False))
        gemini_status = getattr(obj, "gemini_status", "")

        login_failed = (
            status in ["locked", "disabled"]
            or "机器人验证" in notes
            or "验证码" in notes
            or "登录失败" in notes
        )
        verify_failed = "学生验证失败" in notes
        bindcard_failed = (
            "订阅失败" in notes or "绑卡失败" in notes or "绑卡过程出错" in notes
        )

        link_ready_signal = bool(sheerid_link) or google_one_status == "link_ready" or status == "link_ready"
        verified_signal = sheerid_verified or google_one_status == "verified" or status == "verified"
        subscribed_signal = (
            gemini_status == "active"
            or google_one_status == "subscribed"
            or status == "subscribed"
        )
        logged_in_signal = (
            bool(last_login_at)
            or status == "logged_in"
            or google_one_status in ["logged_in", "opened"]
        )

        if google_one_status == "ineligible" or status == "ineligible":
            return "ineligible"

        if login_failed:
            return "login_failed"

        if bindcard_failed:
            return "bindcard_failed"

        if verify_failed:
            return "verify_failed"

        if subscribed_signal:
            return "subscribed"

        if card_bound and not subscribed_signal:
            return "card_bound"

        if verified_signal and not card_bound:
            return "verified"

        if link_ready_signal and not verified_signal and not card_bound:
            return "link_ready"

        if logged_in_signal and not link_ready_signal and not verified_signal and not card_bound:
            return "logged_in"

        return "unopened"

    def get_type_display(self, obj: GoogleAccount):
        mapping = {
            "ineligible": "无资格",
            "login_failed": "登录失败",
            "verify_failed": "验证失败",
            "bindcard_failed": "绑卡失败",
            "subscribed": "完成处理",
            "card_bound": "订阅服务",
            "verified": "学生验证",
            "link_ready": "检查学生资格",
            "logged_in": "登录账号",
            "unopened": "未开",
        }
        return mapping.get(self.get_type_tag(obj), "未开")

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

    def get_new_2fa(self, obj: GoogleAccount):
        """最近一次“修改2FA”生成的新密钥（明文）。

        注意：该字段是敏感信息。目前用于“自己用/快速复制”的需求。
        后续如需加强安全性，可改为：
        - 只返回掩码，或
        - 仅在特定权限下返回，或
        - 只允许查看一次
        """

        meta = getattr(obj, "metadata", None) or {}
        val = meta.get("new_2fa_secret")
        return val if isinstance(val, str) and val.strip() else None

    def get_new_2fa_display(self, obj: GoogleAccount):
        """最近一次“修改2FA”生成的新密钥（Google 展示风格）。

        Google 通常展示为：小写 + 每 4 位一组空格。
        该值与 new_2fa 等价，仅表现形式不同，便于对照网页。
        """

        meta = getattr(obj, "metadata", None) or {}
        val = meta.get("new_2fa_secret_display")
        if isinstance(val, str) and val.strip():
            return val

        # fallback：如果历史数据没有 display 字段，按 new_2fa 动态拼一份
        raw = meta.get("new_2fa_secret")
        if not (isinstance(raw, str) and raw.strip()):
            return None
        s = raw.replace(" ", "").strip().lower()
        return " ".join([s[i : i + 4] for i in range(0, len(s), 4)])

    def get_new_2fa_updated_at(self, obj: GoogleAccount):
        meta = getattr(obj, "metadata", None) or {}
        val = meta.get("new_2fa_updated_at")
        return val if isinstance(val, str) and val.strip() else None

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
    # 分组相关
    group_name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="分组名称前缀，如'售后'、'2FA'。留空则使用当前时间作为前缀",
    )
    group_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="已存在的分组ID，如果提供则直接加入该分组",
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
        except Exception:
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
            except Exception:
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


class AccountGroupSerializer(serializers.ModelSerializer):
    """账号分组序列化器"""

    account_count = serializers.SerializerMethodField()

    class Meta:
        from apps.integrations.google_accounts.models import AccountGroup
        model = AccountGroup
        fields = ["id", "name", "description", "account_count", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_account_count(self, obj):
        if hasattr(obj, "account_count"):
            return obj.account_count
        return GoogleAccount.objects.filter(
            owner_user=obj.owner_user,
            group_name=obj.name
        ).count()

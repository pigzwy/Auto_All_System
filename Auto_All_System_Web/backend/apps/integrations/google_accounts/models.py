"""
Google账号管理模块的数据模型
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class AccountGroup(models.Model):
    """
    账号分组表
    用于对Google账号进行分类管理，如：售后分组、2FA分组等
    """

    name = models.CharField(
        max_length=100, verbose_name="分组名称", help_text="如：售后_10个、2FA_5个"
    )
    description = models.TextField(blank=True, verbose_name="分组描述")
    owner_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="account_groups",
        verbose_name="所有者",
    )

    # 统计信息（冗余字段，方便查询）
    account_count = models.PositiveIntegerField(default=0, verbose_name="账号数量")

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "account_groups"
        verbose_name = "账号分组"
        verbose_name_plural = "账号分组"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner_user", "name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.account_count}个)"

    def update_account_count(self):
        """更新账号数量"""
        self.account_count = self.accounts.count()
        self.save(update_fields=["account_count"])

    @classmethod
    def generate_default_name(cls, prefix: str = None, count: int = 0) -> str:
        """
        生成默认分组名称

        Args:
            prefix: 前缀，如 "售后"、"2FA"
            count: 账号数量

        Returns:
            分组名称，如 "售后_10个" 或 "2025-01-25_10个"
        """
        if prefix:
            return f"{prefix}_{count}个"
        else:
            # 使用当前时间作为默认前缀
            now = timezone.now()
            date_str = now.strftime("%Y-%m-%d_%H%M")
            return f"{date_str}_{count}个"


class GoogleAccountStatus(models.TextChoices):
    """Google账号状态"""

    ACTIVE = "active", "正常"
    LOCKED = "locked", "锁定"
    DISABLED = "disabled", "停用"
    PENDING_VERIFY = "pending_verify", "待验证"


class GeminiStatus(models.TextChoices):
    """Gemini订阅状态"""

    NOT_SUBSCRIBED = "not_subscribed", "未订阅"
    PENDING = "pending", "订阅中"
    ACTIVE = "active", "已订阅"
    EXPIRED = "expired", "已过期"
    CANCELLED = "cancelled", "已取消"


class GoogleAccount(models.Model):
    """
    Google账号表
    管理Google账号及其Gemini订阅状态
    """

    # 账号信息
    email = models.EmailField(unique=True, db_index=True, verbose_name="Google邮箱")
    password = models.CharField(
        max_length=255, verbose_name="密码", help_text="加密存储"
    )
    recovery_email = models.EmailField(blank=True, verbose_name="恢复邮箱")
    phone_number = models.CharField(
        max_length=20, blank=True, verbose_name="绑定手机号"
    )

    # 2FA信息
    two_fa_enabled = models.BooleanField(default=False, verbose_name="是否启用2FA")
    two_fa_secret = models.CharField(
        max_length=255, blank=True, verbose_name="2FA密钥", help_text="加密存储"
    )

    # 账号状态
    status = models.CharField(
        max_length=20,
        choices=GoogleAccountStatus.choices,
        default=GoogleAccountStatus.PENDING_VERIFY,
        db_index=True,
        verbose_name="账号状态",
    )

    # Gemini相关
    gemini_status = models.CharField(
        max_length=20,
        choices=GeminiStatus.choices,
        default=GeminiStatus.NOT_SUBSCRIBED,
        db_index=True,
        verbose_name="Gemini状态",
    )
    sheerid_verified = models.BooleanField(
        default=False, verbose_name="是否通过SheerID验证"
    )
    sheerid_link = models.TextField(blank=True, verbose_name="SheerID验证链接")
    card_bound = models.BooleanField(default=False, verbose_name="是否已绑卡")

    # 所有权（用户自定义功能）
    owner_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="google_accounts",
        verbose_name="账号所有者",
        help_text="如果为空则为平台账号池",
    )

    # 分组
    group = models.ForeignKey(
        AccountGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accounts",
        verbose_name="所属分组",
        help_text="账号分组，如：售后分组、2FA分组等",
    )

    # 使用信息
    last_login_at = models.DateTimeField(
        null=True, blank=True, verbose_name="最后登录时间"
    )
    last_login_ip = models.GenericIPAddressField(
        null=True, blank=True, verbose_name="最后登录IP"
    )

    # 订阅信息
    subscription_start_date = models.DateField(
        null=True, blank=True, verbose_name="订阅开始日期"
    )
    subscription_end_date = models.DateField(
        null=True, blank=True, verbose_name="订阅结束日期"
    )

    # 关联虚拟卡
    bound_card = models.ForeignKey(
        "cards.Card",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="google_accounts",
        verbose_name="绑定的虚拟卡",
    )

    # 备注
    notes = models.TextField(blank=True, verbose_name="备注")

    # 扩展字段
    metadata = models.JSONField(default=dict, blank=True, verbose_name="扩展数据")

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "google_accounts"
        verbose_name = "Google账号"
        verbose_name_plural = "Google账号"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "gemini_status"]),
            models.Index(fields=["owner_user", "status"]),
            models.Index(fields=["gemini_status", "subscription_end_date"]),
        ]

    def __str__(self):
        return f"{self.email} - {self.gemini_status}"

    @property
    def is_subscription_active(self):
        """检查订阅是否有效"""
        from datetime import date

        if self.gemini_status != GeminiStatus.ACTIVE:
            return False
        if self.subscription_end_date and self.subscription_end_date < date.today():
            return False
        return True


class SheerIDVerification(models.Model):
    """
    SheerID验证记录表
    记录每次SheerID学生/教师验证的详细信息
    """

    google_account = models.ForeignKey(
        GoogleAccount,
        on_delete=models.CASCADE,
        related_name="sheerid_verifications",
        verbose_name="Google账号",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sheerid_verifications",
        verbose_name="关联任务",
    )

    # 验证信息
    verification_type = models.CharField(
        max_length=50,
        verbose_name="验证类型",
        help_text="如: student(学生), teacher(教师)",
    )
    verification_link = models.TextField(verbose_name="SheerID验证链接")

    # 提交的信息
    submitted_data = models.JSONField(
        default=dict, verbose_name="提交的验证数据", help_text="姓名、学校、证件等信息"
    )

    # 验证结果
    verified = models.BooleanField(
        default=False, db_index=True, verbose_name="是否通过验证"
    )
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name="通过时间")

    # 失败信息
    error_message = models.TextField(blank=True, verbose_name="失败原因")

    # 额外数据
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="额外数据",
        help_text="存储响应数据、截图等",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "sheerid_verifications"
        verbose_name = "SheerID验证记录"
        verbose_name_plural = "SheerID验证记录"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["google_account", "verified"]),
            models.Index(fields=["task", "verified"]),
        ]

    def __str__(self):
        status = "已验证" if self.verified else "未验证"
        return f"{self.google_account.email} - {self.verification_type} - {status}"


class GeminiSubscription(models.Model):
    """
    Gemini订阅记录表
    记录每次Gemini订阅操作的详细信息
    """

    google_account = models.ForeignKey(
        GoogleAccount,
        on_delete=models.CASCADE,
        related_name="gemini_subscriptions",
        verbose_name="Google账号",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="gemini_subscriptions",
        verbose_name="关联任务",
    )
    card = models.ForeignKey(
        "cards.Card",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gemini_subscriptions",
        verbose_name="使用的虚拟卡",
    )

    # 订阅信息
    subscription_plan = models.CharField(
        max_length=50, default="Advanced", verbose_name="订阅计划"
    )
    start_date = models.DateField(verbose_name="订阅开始日期")
    end_date = models.DateField(null=True, blank=True, verbose_name="订阅结束日期")

    # 费用信息
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="订阅费用(元)",
        help_text="人民币",
    )

    # 订阅结果
    success = models.BooleanField(default=False, db_index=True, verbose_name="是否成功")
    error_message = models.TextField(blank=True, verbose_name="失败原因")

    # 扩展数据
    extra_data = models.JSONField(default=dict, blank=True, verbose_name="额外数据")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "gemini_subscriptions"
        verbose_name = "Gemini订阅记录"
        verbose_name_plural = "Gemini订阅记录"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["google_account", "success"]),
            models.Index(fields=["task", "success"]),
            models.Index(fields=["success", "start_date"]),
        ]

    def __str__(self):
        status = "成功" if self.success else "失败"
        return f"{self.google_account.email} - {self.subscription_plan} - {status}"

"""
邮件服务 - 业务逻辑封装

提供与 Google 账号绑定的辅助邮箱管理功能
"""

import logging
from typing import Optional, Tuple

from .client import CloudMailClient

logger = logging.getLogger(__name__)


class EmailService:
    """
    邮件服务

    封装辅助邮箱创建、验证码获取等业务逻辑

    使用示例:
        service = EmailService()

        # 为 Google 账号创建辅助邮箱
        email, password = service.create_recovery_email(google_account)

        # 获取验证码
        code = service.get_verification_code(email, sender_contains='google')
    """

    def __init__(self, client: Optional[CloudMailClient] = None):
        """
        初始化服务

        Args:
            client: CloudMailClient 实例，不填则从数据库配置创建
        """
        self._client = client

    @property
    def client(self) -> CloudMailClient:
        """延迟加载客户端"""
        if self._client is None:
            self._client = CloudMailClient.from_config()
        return self._client

    def create_recovery_email(
        self, google_account=None, owner_user=None, domain: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        创建辅助邮箱

        Args:
            google_account: GoogleAccount 实例（可选，用于绑定）
            owner_user: User 实例（可选）
            domain: 指定域名（可选）

        Returns:
            (email, password) 元组
        """
        # 创建邮箱
        email, password = self.client.create_random_user(domain=domain)

        # 保存到数据库
        from apps.integrations.email.models import RecoveryEmail

        recovery_email = RecoveryEmail.objects.create(
            email=email,
            password=password,
            google_account=google_account,
            owner=owner_user,
        )

        logger.info(f"Created recovery email: {email}")

        # 更新 GoogleAccount 的 recovery_email 字段
        if google_account:
            google_account.recovery_email = email
            google_account.save(update_fields=["recovery_email", "updated_at"])
            logger.info(f"Bound {email} to {google_account.email}")

        return email, password

    def get_verification_code(
        self,
        email: str,
        timeout: int = 120,
        poll_interval: int = 5,
        sender_contains: Optional[str] = None,
    ) -> Optional[str]:
        """
        获取验证码

        Args:
            email: 接收验证码的邮箱
            timeout: 超时时间（秒）
            poll_interval: 轮询间隔（秒）
            sender_contains: 发件人过滤（如 'google'）

        Returns:
            验证码字符串，失败返回 None
        """
        return self.client.wait_for_verification_code(
            to_email=email,
            timeout=timeout,
            poll_interval=poll_interval,
            sender_contains=sender_contains,
        )

    def get_google_verification_code(
        self, email: str, timeout: int = 120
    ) -> Optional[str]:
        """
        获取 Google 验证码（便捷方法）

        已预设 Google 发件人过滤
        """
        return self.get_verification_code(
            email=email, timeout=timeout, sender_contains="google"
        )

    def create_and_get_code(
        self, google_account=None, owner_user=None, timeout: int = 120
    ) -> Tuple[str, str, Optional[str]]:
        """
        创建辅助邮箱并等待验证码（一站式）

        用于需要立即验证邮箱的场景

        Returns:
            (email, password, verification_code) 元组
        """
        email, password = self.create_recovery_email(
            google_account=google_account, owner_user=owner_user
        )

        # 触发验证邮件的操作需要在外部执行
        # 这里只是等待验证码
        code = self.get_google_verification_code(email, timeout=timeout)

        return email, password, code

    def get_recovery_email_for_account(self, google_account) -> Optional[str]:
        """
        获取 Google 账号绑定的辅助邮箱

        Returns:
            辅助邮箱地址，未绑定返回 None
        """
        from apps.integrations.email.models import RecoveryEmail

        try:
            recovery = RecoveryEmail.objects.get(google_account=google_account)
            return recovery.email
        except RecoveryEmail.DoesNotExist:
            return None

    def close(self):
        """关闭服务"""
        if self._client:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# 便捷函数
def get_email_service() -> EmailService:
    """获取 EmailService 单例"""
    return EmailService()

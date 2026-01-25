"""
Google Business插件工具类
"""

from cryptography.fernet import Fernet
from django.conf import settings
import base64
import hashlib
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class EncryptionUtil:
    """
    数据加密工具类（AES-256）
    用于加密敏感数据：密码、2FA密钥、卡号、CVV等
    """

    @staticmethod
    def get_cipher():
        """获取加密器"""
        # 统一策略：把 ENCRYPTION_KEY 当作“口令/材料”，派生出稳定的 Fernet key。
        # 兼容：如果 ENCRYPTION_KEY 本身已经是合法 Fernet key，则直接使用。
        key_material = getattr(settings, "ENCRYPTION_KEY", None) or getattr(
            settings, "SECRET_KEY", ""
        )

        if not key_material:
            logger.warning(
                "ENCRYPTION_KEY/SECRET_KEY not configured, using temporary key"
            )
            return Fernet(Fernet.generate_key())

        if isinstance(key_material, str):
            key_material_bytes = key_material.encode("utf-8")
        else:
            key_material_bytes = key_material

        # 1) 如果本身是合法 Fernet key，直接用
        try:
            return Fernet(key_material_bytes)
        except Exception:
            pass

        # 2) 否则派生（与 apps.integrations.models.UserAPIKey 的策略一致：sha256 -> urlsafe_b64)
        derived = base64.urlsafe_b64encode(hashlib.sha256(key_material_bytes).digest())
        return Fernet(derived)

    @staticmethod
    def encrypt(data: str) -> str:
        """
        加密敏感数据

        Args:
            data: 原始数据

        Returns:
            加密后的数据（Base64字符串）
        """
        if not data:
            return ""

        try:
            cipher = EncryptionUtil.get_cipher()
            encrypted_data = cipher.encrypt(data.encode())
            return encrypted_data.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    @staticmethod
    def decrypt(encrypted_data: str) -> str:
        """
        解密敏感数据

        Args:
            encrypted_data: 加密的数据

        Returns:
            原始数据
        """
        if not encrypted_data:
            return ""

        # Fernet 加密的数据以 'gAAAAA' 开头
        # 如果不是这个格式，可能是明文存储的（兼容旧数据）
        if not encrypted_data.startswith("gAAAAA"):
            logger.debug(
                f"Data does not look encrypted (no gAAAAA prefix), returning as-is"
            )
            return encrypted_data

        try:
            cipher = EncryptionUtil.get_cipher()
            decrypted_data = cipher.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise


class TaskLogger:
    """
    任务日志记录器
    用于记录任务执行过程中的日志
    """

    def __init__(self, task):
        """
        初始化日志记录器

        Args:
            task: GoogleTask实例
        """
        self.task = task
        self.logger = logging.getLogger(__name__)

    def log(self, message: str, level: str = "info"):
        """
        记录日志

        Args:
            message: 日志消息
            level: 日志级别（info, warning, error）
        """
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"

        def _append_log_db() -> None:
            # 避免并发/跨线程时 self.task 过旧导致覆盖
            task = self.task.__class__.objects.get(pk=self.task.pk)
            task.log = (task.log or "") + formatted_message
            task.save(update_fields=["log"])
            self.task = task

        # 写入数据库：在 async 上下文中用线程执行，避免触发 SynchronousOnlyOperation
        try:
            import asyncio

            asyncio.get_running_loop()
            in_async = True
        except Exception:
            in_async = False

        if in_async:
            try:
                from asgiref.sync import sync_to_async

                async def _write():
                    await sync_to_async(_append_log_db, thread_sensitive=True)()

                asyncio.create_task(_write())
            except Exception:
                # 兜底：不要因为写日志导致主流程失败
                pass
        else:
            _append_log_db()

        # 写入日志文件
        if level == "info":
            self.logger.info(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)

    def info(self, message: str):
        """记录信息日志"""
        self.log(message, "info")

    def warning(self, message: str):
        """记录警告日志"""
        self.log(message, "warning")

    def error(self, message: str):
        """记录错误日志"""
        self.log(message, "error")


class SensitiveDataFilter:
    """
    敏感数据过滤器
    用于日志脱敏
    """

    import re

    PATTERNS = [
        (
            re.compile(r'password["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE),
            r'password="***"',
        ),
        (
            re.compile(r'secret["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE),
            r'secret="***"',
        ),
        (
            re.compile(
                r'card_number["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE
            ),
            r'card_number="****"',
        ),
        (
            re.compile(r'cvv["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE),
            r'cvv="***"',
        ),
        (re.compile(r"\d{13,19}"), r"****-****-****-****"),  # 卡号
    ]

    @staticmethod
    def filter(message: str) -> str:
        """
        过滤敏感数据

        Args:
            message: 原始消息

        Returns:
            脱敏后的消息
        """
        for pattern, replacement in SensitiveDataFilter.PATTERNS:
            message = pattern.sub(replacement, message)
        return message


def extract_verification_id(verification_link: str) -> str:
    """
    从SheerID链接中提取verification_id

    Args:
        verification_link: SheerID验证链接

    Returns:
        verification_id或空字符串
    """
    import re

    if not verification_link:
        return ""

    # 匹配常见的verification_id格式
    patterns = [
        r"verificationId=([a-zA-Z0-9\-]+)",
        r"verification/([a-zA-Z0-9\-]+)",
        r"verify/([a-zA-Z0-9\-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, verification_link)
        if match:
            return match.group(1)

    logger.warning(f"Could not extract verification_id from: {verification_link}")
    return ""


def mask_card_number(card_number: str) -> str:
    """
    掩码卡号（只显示后4位）

    Args:
        card_number: 完整卡号

    Returns:
        掩码后的卡号
    """
    if not card_number or len(card_number) < 4:
        return "****-****-****-****"

    return f"****-****-****-{card_number[-4:]}"


def calculate_task_cost(task_type: str, count: int) -> float:
    """
    计算任务成本

    Args:
        task_type: 任务类型
        count: 账号数量

    Returns:
        总费用
    """
    # 定价规则（单位：积分）
    PRICING = {
        "login": 1,
        "get_link": 2,
        "verify": 5,
        "bind_card": 10,
        "one_click": 18,
    }

    unit_price = PRICING.get(task_type, 0)
    return unit_price * count

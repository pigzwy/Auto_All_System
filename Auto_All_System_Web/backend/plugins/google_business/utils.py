"""Google Business插件工具类。

这里的 TaskLogger 目前是 Google 自动化任务的“可追溯日志”核心：
- 支持把日志落到 DB（GoogleTask.log，批量任务）
- 也支持把日志落到文件（按 celery_task_id + email 归档，适用于安全设置等无 GoogleTask 主表的任务）

目标：任何 Celery 任务只要有 task_id/email，就能查到完整执行轨迹。
"""

import asyncio

from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone
import base64
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def attach_playwright_trace(page: Any, task_logger: "TaskLogger") -> None:
    """把关键 Playwright 事件绑定到 TaskLogger。

    目的：不需要侵入所有业务代码，也能记录“开了什么页面/页面报错/控制台报错”。

    注意：
    - 只记录主 frame 导航，避免子 frame 噪音
    - 只记录 console 的 warning/error
    """

    if not page or not task_logger:
        return

    try:
        # 避免重复绑定
        if getattr(page, "_omo_trace_attached", False):
            return
        setattr(page, "_omo_trace_attached", True)
    except Exception:
        # 某些 page 对象可能不允许 set attribute
        pass

    def _safe_create_task(coro):
        try:
            asyncio.create_task(coro)
        except Exception:
            pass

    try:

        def on_framenavigated(frame):
            try:
                # 仅主 frame
                parent = getattr(frame, "parent_frame", None)
                if callable(parent):
                    if frame.parent_frame is not None:
                        return
                else:
                    if getattr(frame, "parent_frame", None) is not None:
                        return
                url = getattr(frame, "url", "")
                task_logger.event(
                    step="browser",
                    action="navigate",
                    message="frame navigated",
                    url=url,
                )
            except Exception:
                return

        page.on("framenavigated", on_framenavigated)
    except Exception:
        pass

    try:

        def on_pageerror(err):
            try:
                task_logger.event(
                    step="browser",
                    action="pageerror",
                    message=str(err),
                    url=getattr(page, "url", ""),
                    level="error",
                )
            except Exception:
                return

        page.on("pageerror", on_pageerror)
    except Exception:
        pass

    try:

        def on_console(msg):
            try:
                msg_type = msg.type
                if msg_type not in ("warning", "error"):
                    return
                task_logger.event(
                    step="browser",
                    action=f"console_{msg_type}",
                    message=msg.text,
                    url=getattr(page, "url", ""),
                    level="warning" if msg_type == "warning" else "error",
                )
            except Exception:
                return

        page.on("console", on_console)
    except Exception:
        pass


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

    def __init__(
        self,
        task=None,
        *,
        celery_task_id: Optional[str] = None,
        account_id: Optional[int] = None,
        email: Optional[str] = None,
        kind: Optional[str] = None,
    ):
        """初始化日志记录器。

        Args:
            task: GoogleTask 实例（批量任务有；安全设置类任务通常没有）
            celery_task_id: Celery task id，用于把日志与前端轮询的 task_id 对齐
            account_id: 当前处理账号 id（可选）
            email: 当前处理账号 email（可选）
            kind: 任务类型/场景标识（可选，如 security_change_2fa）
        """

        self.task = task
        self.celery_task_id = celery_task_id
        self.account_id = account_id
        self.email = email
        self.kind = kind

        # 文件日志：默认落到 backend/logs/trace（在 docker volume 映射下可直接在宿主机查看）
        self.trace_file: Optional[Path] = None
        self.trace_rel_path: str = ""
        try:
            base_dir = Path(getattr(settings, "BASE_DIR", "."))
            trace_dir = base_dir / "logs" / "trace"
            trace_dir.mkdir(parents=True, exist_ok=True)

            safe_email = (email or "").replace("@", "_").replace(".", "_")
            if celery_task_id and safe_email:
                filename = f"trace_{celery_task_id}_{safe_email}.log"
            elif celery_task_id:
                filename = f"trace_{celery_task_id}.log"
            elif safe_email:
                filename = f"trace_{safe_email}.log"
            else:
                filename = "trace_unknown.log"

            self.trace_file = trace_dir / filename
            self.trace_rel_path = str(Path("logs") / "trace" / filename)
        except Exception:
            self.trace_file = None
            self.trace_rel_path = ""

        self.logger = logging.getLogger(__name__)

    @staticmethod
    def _mask_secret(value: str, prefix: int = 4, suffix: int = 4) -> str:
        v = (value or "").replace(" ", "").strip()
        if not v:
            return ""
        if len(v) <= prefix + suffix:
            return "***"
        return f"{v[:prefix]}***{v[-suffix:]}"

    def _context_prefix(self) -> str:
        parts = []
        if self.kind:
            parts.append(self.kind)
        if self.celery_task_id:
            parts.append(f"celery={self.celery_task_id}")
        if self.account_id is not None:
            parts.append(f"acc={self.account_id}")
        if self.email:
            parts.append(self.email)
        if not parts:
            return ""
        return "[" + "][".join(parts) + "] "

    def _append_trace_file(self, line: str) -> None:
        if not self.trace_file:
            return
        try:
            # 直接 append；即使在 async 场景也允许轻量阻塞（每条日志很短）
            self.trace_file.parent.mkdir(parents=True, exist_ok=True)
            with self.trace_file.open("a", encoding="utf-8", errors="ignore") as f:
                f.write(line)
        except Exception:
            # 兜底：不要因为写文件失败影响主流程
            pass

    def event(
        self,
        *,
        step: str,
        action: str,
        message: str,
        level: str = "info",
        url: Optional[str] = None,
        selector: Optional[str] = None,
        result: Optional[Any] = None,
        screenshot: Optional[str] = None,
        extra: Optional[dict] = None,
        mask_secret: bool = False,
    ):
        """结构化事件日志（推荐）。

        - DB：若绑定了 GoogleTask，则写入 task.log（文本）
        - 文件：始终尝试写入 trace 文件（按 celery_task_id/email 归档）

        注意：如果 message/result 可能包含 secret，请通过 mask_secret=True 或调用 _mask_secret。
        """

        ts = timezone.now().isoformat()
        msg = message or ""
        if mask_secret:
            msg = self._mask_secret(msg)

        payload = {
            "ts": ts,
            "level": level,
            "step": step,
            "action": action,
            "message": msg,
            "celery_task_id": self.celery_task_id,
            "account_id": self.account_id,
            "email": self.email,
            "kind": self.kind,
        }
        if url:
            payload["url"] = url
        if selector:
            payload["selector"] = selector
        if screenshot:
            payload["screenshot"] = screenshot
        if result is not None:
            payload["result"] = result
        if extra:
            payload["extra"] = extra

        json_line = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
        human = (
            f"[{ts}] {self._context_prefix()}{step}/{action}: {msg}"
            + (f" url={url}" if url else "")
            + (f" screenshot={screenshot}" if screenshot else "")
            + "\n"
        )

        # 写 trace 文件（json line + human line，便于 grep & 人读）
        self._append_trace_file(json_line + "\n")
        self._append_trace_file(human)

        # 写 DB（如果有 task）。这里禁止再次写 trace 文件，避免 event 重复两份。
        self.log(human.strip(), level=level, write_trace=False)

    def log(self, message: str, level: str = "info", *, write_trace: bool = True):
        """
        记录日志

        Args:
            message: 日志消息
            level: 日志级别（info, warning, error）
        """
        # 基础脱敏（避免密码/2FA/卡号直接落盘）
        message = SensitiveDataFilter.filter(message or "")

        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {self._context_prefix()}{message}\n"

        if write_trace:
            self._append_trace_file(formatted_message)

        def _append_log_db() -> None:
            if not self.task:
                return

            # 避免并发/跨线程时 self.task 过旧导致覆盖
            task = self.task.__class__.objects.get(pk=self.task.pk)
            task.log = (task.log or "") + formatted_message
            task.save(update_fields=["log"])
            self.task = task

        # 写入数据库：在 async 上下文中用线程执行，避免触发 SynchronousOnlyOperation
        try:
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

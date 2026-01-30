"""
Cloud Mail API 客户端

基于 Cloud Mail 自建邮箱系统的 API 封装
API 文档: https://doc.skymail.ink/api/api-doc.html
"""

import re
import time
import secrets
import string
import logging
from urllib.parse import urlparse
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class Email:
    """邮件数据"""

    email_id: int
    sender_email: str
    sender_name: str
    subject: str
    to_email: str
    to_name: str
    create_time: str
    email_type: int  # 0=收件, 1=发件
    content: str  # HTML 内容
    text: str  # 纯文本


class CloudMailClient:
    """
    Cloud Mail API 客户端

    使用方法:
        client = CloudMailClient(
            api_base="https://mail.180711.xyz/api/public",
            api_token="your-token",
            domains=["pigll.site", "example.com"]
        )

        # 创建随机邮箱
        email, password = client.create_random_user()

        # 等待验证码邮件
        code = client.wait_for_verification_code(email, timeout=120)
    """

    def __init__(
        self,
        api_base: str,
        api_token: str,
        domains: List[str],
        default_role: str = "user",
        timeout: float = 30.0,
    ):
        """
        初始化客户端

        Args:
            api_base: API 基础地址，如 https://mail.180711.xyz/api/public
            api_token: API Token (通过 genToken 接口获取)
            domains: 可用域名列表
            default_role: 默认用户角色
            timeout: 请求超时时间
        """
        self.api_base = api_base.rstrip("/")
        self.api_token = api_token
        self.domains = [d for d in (self._normalize_domain(x) for x in (domains or [])) if d]
        if not self.domains:
            raise ValueError("CloudMail domains is empty or invalid")
        self.default_role = default_role
        self._client = httpx.Client(
            base_url=self.api_base,
            headers={"Authorization": api_token},
            timeout=timeout,
        )

    @staticmethod
    def _normalize_domain(value: Any) -> str:
        """Normalize domain input to plain host (example.com).

        Admin UI may accidentally store items like:
        - 'http://example.com/api/public'
        - 'user@example.com'
        - ' example.com '
        """

        raw = str(value or "").strip().lower()
        if not raw:
            return ""

        # accept accidental email string
        if "@" in raw:
            raw = raw.split("@", 1)[1].strip()

        # accept URL
        if "://" in raw:
            parsed = urlparse(raw)
            raw = (parsed.netloc or parsed.path).strip()

        # strip path/query fragments
        raw = raw.split("/", 1)[0].strip()
        raw = raw.split("?", 1)[0].strip()
        raw = raw.split("#", 1)[0].strip()

        # strip port
        if ":" in raw:
            raw = raw.split(":", 1)[0].strip()

        # very small validation (ASCII only)
        if not re.fullmatch(r"[a-z0-9.-]+", raw):
            return ""
        if "." not in raw:
            return ""
        return raw

    def _request(self, endpoint: str, data: dict[str, Any] | None = None) -> Any:
        """发送 POST 请求"""
        try:
            payload: dict[str, Any] = data if isinstance(data, dict) else {}
            resp = self._client.post(endpoint, json=payload)
            resp.raise_for_status()
            result = resp.json()

            if result.get("code") != 200:
                error_msg = result.get("message", "Unknown error")
                extra = ""
                if endpoint == "/addUser" and isinstance(data, dict):
                    users = data.get("list")
                    if isinstance(users, list) and users:
                        first = users[0] if isinstance(users[0], dict) else None
                        if isinstance(first, dict) and first.get("email"):
                            extra = f" (email={first.get('email')})"
                logger.error(f"Cloud Mail API error: {error_msg}")
                raise Exception(f"Cloud Mail API Error: {error_msg}{extra}")

            return result.get("data")
        except httpx.HTTPError as e:
            logger.error(f"Cloud Mail HTTP error: {e}")
            raise

    # ==================== 用户管理 ====================

    def create_user(
        self,
        email: str,
        password: Optional[str] = None,
        role_name: Optional[str] = None,
    ) -> None:
        """
        创建邮箱用户

        Args:
            email: 完整邮箱地址 (如 test@example.com)
            password: 密码，不填则自动生成
            role_name: 权限角色名，不填使用默认权限
        """
        user_data = {"email": email}
        if password:
            user_data["password"] = password
        if role_name:
            user_data["roleName"] = role_name

        self._request("/addUser", {"list": [user_data]})
        logger.info(f"Created email user: {email}")

    def generate_random_email(
        self, domain: Optional[str] = None, prefix_length: int = 10
    ) -> str:
        """
        生成随机邮箱地址

        Args:
            domain: 使用的域名，不填则随机选择
            prefix_length: 邮箱前缀长度
        """
        import random

        domain = self._normalize_domain(domain) if domain else random.choice(self.domains)
        if not domain:
            raise ValueError("Invalid domain")
        chars = string.ascii_lowercase + string.digits
        prefix = "".join(secrets.choice(chars) for _ in range(prefix_length))
        return f"{prefix}@{domain}"

    def _generate_password(self, length: int = 16) -> str:
        """生成随机密码"""
        chars = string.ascii_letters + string.digits + "!@#$%"
        return "".join(secrets.choice(chars) for _ in range(length))

    def create_random_user(
        self,
        domain: Optional[str] = None,
        password: Optional[str] = None,
        role_name: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        创建随机邮箱用户

        Returns:
            (email, password) 元组
        """
        email = self.generate_random_email(domain)
        password = password or self._generate_password()
        self.create_user(email, password, role_name or self.default_role)
        return email, password

    # ==================== 邮件查询 ====================

    def list_emails(
        self,
        to_email: Optional[str] = None,
        send_email: Optional[str] = None,
        subject: Optional[str] = None,
        time_sort: str = "desc",
        page: int = 1,
        size: int = 20,
    ) -> List[Email]:
        """
        查询邮件列表

        模糊匹配说明:
        - 'admin' 精确匹配
        - 'admin%' 开头匹配
        - '%@example.com' 结尾匹配
        - '%admin%' 包含匹配
        """
        params = {"num": page, "size": size, "timeSort": time_sort}
        if to_email:
            params["toEmail"] = to_email
        if send_email:
            params["sendEmail"] = send_email
        if subject:
            params["subject"] = subject

        data = self._request("/emailList", params)

        if not data:
            return []

        return [
            Email(
                email_id=item["emailId"],
                sender_email=item["sendEmail"],
                sender_name=item.get("sendName", ""),
                subject=item["subject"],
                to_email=item["toEmail"],
                to_name=item.get("toName", ""),
                create_time=item["createTime"],
                email_type=item["type"],
                content=item.get("content", ""),
                text=item.get("text", ""),
            )
            for item in data
        ]

    def get_latest_email(self, to_email: str) -> Optional[Email]:
        """获取指定邮箱的最新邮件"""
        emails = self.list_emails(to_email=to_email, size=1, time_sort="desc")
        return emails[0] if emails else None

    # ==================== 验证码相关 ====================

    def wait_for_email(
        self,
        to_email: str,
        timeout: int = 120,
        poll_interval: int = 5,
        subject_contains: Optional[str] = None,
        sender_contains: Optional[str] = None,
    ) -> Optional[Email]:
        """
        等待邮件到达

        Args:
            to_email: 收件邮箱
            timeout: 超时时间（秒）
            poll_interval: 轮询间隔（秒）
            subject_contains: 主题包含的关键词（可选）
            sender_contains: 发件人包含的关键词（可选）

        Returns:
            收到的邮件，超时返回 None
        """
        start = time.time()

        # 记录初始邮件 ID
        initial_emails = self.list_emails(to_email=to_email, size=100)
        initial_ids = {e.email_id for e in initial_emails}

        logger.info(
            f"Waiting for email to {to_email}, initial count: {len(initial_ids)}"
        )

        while time.time() - start < timeout:
            emails = self.list_emails(to_email=to_email, size=10, time_sort="desc")

            for email in emails:
                if email.email_id not in initial_ids:
                    # 检查过滤条件
                    if (
                        subject_contains
                        and subject_contains.lower() not in email.subject.lower()
                    ):
                        continue
                    if (
                        sender_contains
                        and sender_contains.lower() not in email.sender_email.lower()
                    ):
                        continue

                    logger.info(f"New email received: {email.subject}")
                    return email

            time.sleep(poll_interval)

        logger.warning(f"Timeout waiting for email to {to_email}")
        return None

    def extract_verification_code(self, email: Email) -> Optional[str]:
        """从邮件中提取验证码（支持 6 位数字）"""
        text = f"{email.subject or ''}\n{email.text or ''}\n{email.content or ''}"
        
        if not text.strip():
            return None

        patterns = [
            r"代码为\s*(\d{6})",
            r"code is\s*(\d{6})",
            r"verification code[:\s]*(\d{6})",
            r"验证码[：:\s]*(\d{6})",
            r"(\d{6})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                code = match.group(1)
                if len(code) == 6 and code.isdigit():
                    return code

        return None

    def wait_for_verification_code(
        self,
        to_email: str,
        timeout: int = 120,
        poll_interval: int = 5,
        sender_contains: Optional[str] = None,
    ) -> Optional[str]:
        """
        等待并提取验证码

        Args:
            to_email: 收件邮箱
            timeout: 超时时间（秒）
            poll_interval: 轮询间隔（秒）
            sender_contains: 发件人过滤（如 'google'）

        Returns:
            验证码字符串，失败返回 None
        """
        start = time.time()
        checked_ids: set[int] = set()
        
        logger.info(f"Waiting for verification code to {to_email}")
        
        while time.time() - start < timeout:
            emails = self.list_emails(to_email=to_email, size=10, time_sort="desc")
            
            for email in emails:
                if email.email_id in checked_ids:
                    continue
                checked_ids.add(email.email_id)
                
                # 检查发件人过滤
                if sender_contains and sender_contains.lower() not in email.sender_email.lower():
                    continue
                
                # 尝试提取验证码
                code = self.extract_verification_code(email)
                if code:
                    logger.info(f"Found verification code {code} in email: {email.subject}")
                    return code
            
            time.sleep(poll_interval)
        
        logger.warning(f"Timeout waiting for verification code to {to_email}")
        return None

    def close(self):
        """关闭客户端"""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ==================== 从数据库配置创建 ====================

    @classmethod
    def from_config(cls, config=None) -> "CloudMailClient":
        """
        从数据库配置创建客户端

        Args:
            config: CloudMailConfig 实例，不填则使用默认配置
        """
        if config is None:
            from apps.integrations.email.models import CloudMailConfig

            config = CloudMailConfig.get_default()
            if not config:
                raise ValueError("No Cloud Mail config found. Please add one in admin.")

        return cls(
            api_base=config.api_base,
            api_token=config.api_token,
            domains=config.domains,
            default_role=config.default_role,
        )

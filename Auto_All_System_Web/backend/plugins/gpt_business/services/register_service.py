"""
OpenAI 注册服务 - 自动注册 ChatGPT/OpenAI 账号
"""
import logging
import random
import string
import time
from dataclasses import dataclass
from typing import Any

from .browser_service import BrowserService

logger = logging.getLogger(__name__)


@dataclass
class RegisterResult:
    """注册结果"""
    success: bool
    email: str
    error: str = ""
    session_data: dict[str, Any] | None = None


class OpenAIRegisterService:
    """OpenAI 注册服务"""

    CHATGPT_URL = "https://chatgpt.com"
    AUTH_URL_PREFIX = "https://auth.openai.com"

    def __init__(
        self,
        browser: BrowserService,
        email_code_getter: Any = None,
    ):
        self.browser = browser
        self.email_code_getter = email_code_getter

    def register(self, email: str, password: str) -> RegisterResult:
        """
        注册 OpenAI 账号
        
        流程:
        1. 打开 chatgpt.com
        2. 点击注册按钮
        3. 输入邮箱
        4. 输入密码
        5. 获取并输入邮箱验证码
        6. 填写个人信息
        """
        try:
            logger.info(f"开始注册: {email}")
            
            if not self._step_open_signup():
                return RegisterResult(False, email, "打开注册页面失败")

            if not self._step_enter_email(email):
                return RegisterResult(False, email, "输入邮箱失败")

            if not self._step_enter_password(password):
                return RegisterResult(False, email, "输入密码失败")

            if not self._step_verify_email(email):
                return RegisterResult(False, email, "邮箱验证失败")

            if not self._step_fill_profile():
                return RegisterResult(False, email, "填写个人信息失败")

            if not self._wait_for_login_success():
                return RegisterResult(False, email, "等待登录成功超时")

            logger.info(f"注册成功: {email}")
            return RegisterResult(True, email)

        except Exception as e:
            logger.exception(f"注册异常: {email}")
            return RegisterResult(False, email, str(e))

    def _step_open_signup(self) -> bool:
        """步骤1: 打开注册页面"""
        logger.info("步骤1: 打开 ChatGPT 注册页面")
        self.browser.goto(self.CHATGPT_URL)
        self.browser.human_delay(1, 2)

        signup_selectors = [
            '[data-testid="signup-button"]',
            'button:contains("Sign up")',
            'a:contains("Sign up")',
            '@@text():Sign up',
            '@@text():免费注册',
        ]

        for selector in signup_selectors:
            if self.browser.click(selector, timeout=3):
                logger.info("点击注册按钮成功")
                self.browser.human_delay(1, 2)
                return True

        logger.warning("未找到注册按钮")
        return False

    def _step_enter_email(self, email: str) -> bool:
        """步骤2: 输入邮箱"""
        logger.info("步骤2: 输入邮箱")
        
        if not self.browser.wait_for_url_contains("auth.openai.com", timeout=10):
            if not self.browser.wait_for_url_contains("login", timeout=5):
                logger.warning("未跳转到认证页面")

        self.browser.human_delay(0.5, 1)

        email_selectors = [
            'input[type="email"]',
            'input[name="email"]',
            'input[id="email"]',
            '#email-input',
        ]

        for selector in email_selectors:
            if self.browser.type_text(selector, email):
                logger.info("输入邮箱成功")
                self.browser.human_delay(0.3, 0.6)
                
                if self.browser.click('button[type="submit"]', timeout=5):
                    self.browser.human_delay(1, 2)
                    return True
                if self.browser.click('@@text():Continue', timeout=3):
                    self.browser.human_delay(1, 2)
                    return True

        logger.warning("输入邮箱失败")
        return False

    def _step_enter_password(self, password: str) -> bool:
        """步骤3: 输入密码"""
        logger.info("步骤3: 输入密码")
        
        self.browser.wait_for_url_contains("password", timeout=10)
        self.browser.human_delay(0.5, 1)

        password_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            '#password',
        ]

        for selector in password_selectors:
            if self.browser.type_text(selector, password):
                logger.info("输入密码成功")
                self.browser.human_delay(0.3, 0.6)
                
                if self.browser.click('button[type="submit"]', timeout=5):
                    self.browser.human_delay(1, 2)
                    return True

        logger.warning("输入密码失败")
        return False

    def _step_verify_email(self, email: str) -> bool:
        """步骤4: 邮箱验证"""
        logger.info("步骤4: 等待邮箱验证码")
        
        if not self.browser.wait_for_url_contains("verification", timeout=15):
            if "about-you" in self.browser.current_url():
                logger.info("跳过验证步骤，直接到填写信息")
                return True
            logger.warning("未跳转到验证页面")

        if not self.email_code_getter:
            logger.error("未配置邮箱验证码获取器")
            return False

        max_attempts = 24
        for attempt in range(max_attempts):
            logger.info(f"尝试获取验证码 ({attempt + 1}/{max_attempts})")
            try:
                code = self.email_code_getter(email)
                if code and len(code) == 6:
                    logger.info(f"获取到验证码: {code}")
                    
                    code_input = self.browser.find_element('input[type="text"]', timeout=5)
                    if code_input:
                        code_input.clear()
                        for digit in code:
                            code_input.input(digit)
                            time.sleep(0.1)
                        
                        self.browser.human_delay(0.5, 1)
                        self.browser.click('button[type="submit"]', timeout=3)
                        self.browser.human_delay(1, 2)
                        return True
            except Exception as e:
                logger.warning(f"获取验证码失败: {e}")
            
            time.sleep(5)

        logger.error("获取验证码超时")
        return False

    def _step_fill_profile(self) -> bool:
        """步骤5: 填写个人信息"""
        logger.info("步骤5: 填写个人信息")
        
        if not self.browser.wait_for_url_contains("about-you", timeout=15):
            if self._is_logged_in():
                return True
            logger.warning("未跳转到个人信息页面")

        self.browser.human_delay(0.5, 1)

        first_name = self._random_name()
        last_name = self._random_name()
        
        name_filled = False
        if self.browser.type_text('input[name="firstName"]', first_name):
            self.browser.type_text('input[name="lastName"]', last_name)
            name_filled = True
        elif self.browser.type_text('input[name="name"]', f"{first_name} {last_name}"):
            name_filled = True

        if not name_filled:
            logger.warning("填写姓名失败")

        birth_month = str(random.randint(1, 12))
        birth_day = str(random.randint(1, 28))
        birth_year = str(random.randint(1980, 2000))

        self.browser.type_text('input[name="month"]', birth_month)
        self.browser.type_text('input[name="day"]', birth_day)
        self.browser.type_text('input[name="year"]', birth_year)

        self.browser.human_delay(0.5, 1)
        
        if self.browser.click('button[type="submit"]', timeout=5):
            self.browser.human_delay(1, 2)
            return True

        if self.browser.click('@@text():Continue', timeout=3):
            self.browser.human_delay(1, 2)
            return True

        return True

    def _wait_for_login_success(self, timeout: float = 30) -> bool:
        """等待登录成功"""
        logger.info("等待登录成功...")
        start = time.time()
        while time.time() - start < timeout:
            if self._is_logged_in():
                return True
            time.sleep(1)
        return False

    def _is_logged_in(self) -> bool:
        """检查是否已登录"""
        url = self.browser.current_url()
        if "chatgpt.com" in url and "auth" not in url:
            if self.browser.exists('[data-testid="profile-button"]', timeout=2):
                return True
            if self.browser.exists('nav', timeout=2):
                return True
        return False

    @staticmethod
    def _random_name(length: int = 6) -> str:
        """生成随机英文名"""
        first = random.choice(string.ascii_uppercase)
        rest = ''.join(random.choices(string.ascii_lowercase, k=length - 1))
        return first + rest

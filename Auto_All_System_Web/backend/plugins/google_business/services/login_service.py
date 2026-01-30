"""
Google账号登录服务 (统一健壮版本)

整合 PyQt 和 Web 版本的优点：
- PyQt 的循环检测机制和头像验证
- Web 的机器人验证等待
- 统一的错误处理

@author Auto System
@date 2026-01-24
"""

import asyncio
import logging
import re
from typing import Dict, Any, Optional, Tuple
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

try:
    import pyotp
except ImportError:
    pyotp = None

try:
    from django.utils import timezone
except ImportError:
    timezone = None

from .base import BaseBrowserService
from ..utils import TaskLogger
from .robust_google_auth import (
    robust_google_login,
    check_google_login_by_avatar,
    detect_captcha,
    detect_error_message,
    wait_for_password_input,
)

logger = logging.getLogger(__name__)


class GoogleLoginService(BaseBrowserService):
    """
    Google登录服务 (统一健壮版本)

    整合 PyQt 和 Web 版本的优点：
    - 循环检测各种验证步骤
    - 头像检测确认登录成功
    - 机器人验证等待
    - 完整的错误处理
    """

    LOGIN_URL = "https://accounts.google.com/signin"
    MAX_VERIFICATION_ROUNDS = 10  # 最大验证轮次
    CAPTCHA_WAIT_TIMEOUT = 120  # 机器人验证等待超时(秒)

    def __init__(self):
        """初始化服务"""
        super().__init__()
        self.logger = logging.getLogger("plugin.google_business.login")

    # ==================== 核心登录函数 ====================

    async def login(
        self,
        page: Page,
        account_info: Dict[str, Any],
        task_logger: Optional[TaskLogger] = None,
    ) -> Dict[str, Any]:
        """
        执行Google账号登录 (健壮版本)

        Args:
            page: Playwright页面对象
            account_info: 账号信息 {email, password, secret, backup_email}
            task_logger: 任务日志记录器

        Returns:
            Dict: 登录结果 {success, message, error}
        """
        email = account_info.get("email", "")
        password = account_info.get("password", "")
        secret = (
            account_info.get("secret")
            or account_info.get("2fa_secret")
            or account_info.get("secret_key", "")
        )
        backup_email = (
            account_info.get("backup")
            or account_info.get("backup_email")
            or account_info.get("recovery_email", "")
        )

        def log(msg: str):
            self.logger.info(msg)
            if task_logger:
                task_logger.info(msg)

        log(f"开始登录: {email}")

        try:
            ok, msg = await robust_google_login(
                page,
                account_info,
                log_callback=(task_logger.info if task_logger else None),
                max_captcha_wait=self.CAPTCHA_WAIT_TIMEOUT,
            )
            if ok:
                return {"success": True, "message": msg}
            return {"success": False, "error": msg}

            # ========== 1. 导航到登录页 ==========
            try:
                current_url = page.url
                if (
                    "accounts.google.com" not in current_url
                    and "myaccount.google.com" not in current_url
                ):
                    await page.goto(
                        self.LOGIN_URL, wait_until="domcontentloaded", timeout=30000
                    )
                    await asyncio.sleep(2)
            except Exception as e:
                log(f"导航异常(可能已在页面): {e}")

            # ========== 2. 输入邮箱 ==========
            try:
                email_input = page.locator('input[type="email"]')
                if (
                    await email_input.count() > 0
                    and await email_input.first.is_visible()
                ):
                    log("输入邮箱...")
                    await email_input.first.fill(email)
                    await asyncio.sleep(0.5)

                    # 点击下一步
                    next_button = page.locator("#identifierNext >> button")
                    if await next_button.count() > 0:
                        await next_button.click()
                    else:
                        await email_input.first.press("Enter")

                    await asyncio.sleep(2)
                else:
                    # 检查是否在账号选择页面
                    if await page.locator('text="Choose an account"').count() > 0:
                        log("检测到账号选择页面")
                        account_link = page.locator(f'div:has-text("{email}")').first
                        if await account_link.count() > 0:
                            await account_link.click()
                            await asyncio.sleep(2)
            except Exception as e:
                log(f"邮箱输入异常: {e}")

            # ========== 3. 等待密码框（支持人工过验证）==========
            log("等待密码输入框...")
            password_ready, wait_msg = await self._wait_for_password_input(
                page, task_logger
            )

            if not password_ready:
                return {"success": False, "error": wait_msg}

            # ========== 4. 输入密码 ==========
            try:
                log("输入密码...")
                password_input = page.locator('input[type="password"]')
                await password_input.first.fill(password)
                await asyncio.sleep(0.5)

                # 点击下一步
                next_button = page.locator("#passwordNext >> button")
                if await next_button.count() > 0:
                    await next_button.click()
                else:
                    await password_input.first.press("Enter")

                await asyncio.sleep(3)
            except Exception as e:
                return {"success": False, "error": f"密码输入失败: {e}"}

            # ========== 5. 循环处理各种验证步骤 (PyQt 风格) ==========
            for i in range(self.MAX_VERIFICATION_ROUNDS):
                log(f"检查验证步骤 ({i + 1}/{self.MAX_VERIFICATION_ROUNDS})...")

                # 等待页面稳定
                try:
                    await page.wait_for_load_state("networkidle", timeout=3000)
                except:
                    pass

                # A. 检测是否已登录成功 (头像检测)
                if await self._check_login_by_avatar(page):
                    log("✅ 登录成功（检测到头像）")
                    return {"success": True, "message": "登录成功"}

                # B. 检测错误消息
                error_msg = await self._detect_error_message(page)
                if error_msg:
                    return {"success": False, "error": f"登录失败: {error_msg}"}

                # C. 检测机器人验证
                if await self._detect_captcha(page):
                    log("⚠️ 检测到验证码，等待人工处理...")
                    await asyncio.sleep(5)
                    continue

                # D. 检测 2FA (TOTP)
                totp_handled = await self._handle_2fa(page, secret, task_logger)
                if totp_handled == "handled":
                    continue
                elif totp_handled == "error":
                    return {"success": False, "error": "2FA 验证失败或未提供密钥"}

                # E. 检测辅助邮箱验证
                recovery_handled = await self._handle_recovery_email(
                    page, backup_email, task_logger
                )
                if recovery_handled == "handled":
                    continue
                elif recovery_handled == "error":
                    return {"success": False, "error": "需要辅助邮箱验证但未提供"}

                # F. 处理安全弹窗 ("Not now" 等)
                await self._handle_security_prompts(page)

                # G. 检查 URL 是否表明登录成功
                current_url = page.url
                if (
                    "myaccount.google.com" in current_url
                    or "google.com/search" in current_url
                    or "one.google.com" in current_url
                ):
                    log("✅ 登录成功（URL 检测）")
                    return {"success": True, "message": "登录成功"}

                await asyncio.sleep(2)

            # ========== 6. 最终检查 ==========
            if await self._check_login_by_avatar(page, timeout=5):
                log("✅ 登录成功")
                return {"success": True, "message": "登录成功"}

            current_url = page.url
            if "myaccount.google.com" in current_url:
                log("✅ 登录成功（URL）")
                return {"success": True, "message": "登录成功"}

            return {"success": False, "error": "登录超时或失败"}

        except PlaywrightTimeout as e:
            error_msg = f"Login timeout: {str(e)}"
            self.logger.error(error_msg)
            if task_logger:
                task_logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Login failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            if task_logger:
                task_logger.error(error_msg)
            return {"success": False, "error": error_msg}

    # ==================== 头像检测登录状态 (PyQt 风格) ====================

    async def _check_login_by_avatar(self, page: Page, timeout: float = 3.0) -> bool:
        """
        通过检测头像按钮判断是否已登录 (PyQt 风格)

        Args:
            page: Playwright 页面对象
            timeout: 超时时间(秒)

        Returns:
            True=已登录, False=未登录
        """
        return await check_google_login_by_avatar(page, timeout=timeout)

        try:
            # 头像按钮选择器 (多个备选)
            avatar_selectors = [
                'a[aria-label*="Google Account"] img.gbii',
                'a.gb_B[role="button"] img',
                'a[href*="SignOutOptions"] img',
                "img.gb_Q.gbii",
                'a[aria-label*="Google 帐号"] img',
                'a[aria-label*="Google 账号"] img',
                'img[alt*="Profile"]',
                "[data-ogsr-up]",
            ]

            # 快速检测
            for selector in avatar_selectors:
                try:
                    locator = page.locator(selector).first
                    if await locator.count() > 0 and await locator.is_visible():
                        return True
                except:
                    continue

            return False

        except Exception as e:
            self.logger.warning(f"登录检测异常: {e}")
            return False

    # ==================== 机器人验证检测 ====================

    async def _detect_captcha(self, page: Page) -> bool:
        """检测是否有机器人验证"""
        return await detect_captcha(page)

        captcha_indicators = [
            'iframe[src*="recaptcha"]',
            'iframe[title*="reCAPTCHA"]',
            'text="Verify it\'s you"',
            'text="验证您不是机器人"',
            'text="Confirm you\'re not a robot"',
            "#captchaimg",
            'text="Before you continue"',
            'text="Unusual traffic"',
            "[data-recaptcha]",
        ]

        try:
            for indicator in captcha_indicators:
                if await page.locator(indicator).count() > 0:
                    return True
            return False
        except:
            return False

    # ==================== 错误消息检测 ====================

    async def _detect_error_message(self, page: Page) -> Optional[str]:
        """检测登录错误消息"""
        return await detect_error_message(page)

        error_selectors = [
            '[role="alert"]',
            ".error-msg",
            ".Ekjuhf",
            'text="Wrong password"',
            'text="密码错误"',
            'text="Couldn\'t find your Google Account"',
            'text="找不到您的 Google 帐号"',
        ]

        try:
            for selector in error_selectors:
                locator = page.locator(selector)
                if await locator.count() > 0 and await locator.first.is_visible():
                    return await locator.first.inner_text()
            return None
        except:
            return None

    # ==================== 等待密码输入框 ====================

    async def _wait_for_password_input(
        self, page: Page, task_logger: Optional[TaskLogger] = None
    ) -> Tuple[bool, str]:
        """等待密码输入框出现（支持人工过验证）"""
        return await wait_for_password_input(
            page,
            max_wait_seconds=self.CAPTCHA_WAIT_TIMEOUT,
            log_callback=(task_logger.info if task_logger else None),
        )

        password_input = page.locator('input[type="password"]')
        max_wait_seconds = self.CAPTCHA_WAIT_TIMEOUT
        wait_interval = 2
        waited = 0
        captcha_warned = False

        while waited < max_wait_seconds:
            # 检查密码框是否出现
            if (
                await password_input.count() > 0
                and await password_input.first.is_visible()
            ):
                return True, "密码框已出现"

            # 检测错误消息
            error_msg = await self._detect_error_message(page)
            if error_msg:
                return False, f"登录错误: {error_msg}"

            # 检测机器人验证
            if await self._detect_captcha(page):
                if not captcha_warned:
                    if task_logger:
                        task_logger.warning("⚠️ 检测到机器人验证，请手动完成验证...")
                    captcha_warned = True
                self.logger.info(f"等待人工验证... ({waited}s/{max_wait_seconds}s)")
            else:
                if waited > 0 and waited % 10 == 0:
                    if task_logger:
                        task_logger.info(f"等待页面加载... ({waited}s)")

            await asyncio.sleep(wait_interval)
            waited += wait_interval

        # 超时
        if await self._detect_captcha(page):
            return False, f"需要人工验证但超时未完成（等待了{max_wait_seconds}秒）"
        else:
            return False, "等待密码输入框超时"

    # ==================== 2FA 处理 ====================

    async def _handle_2fa(
        self,
        page: Page,
        secret: str,
        task_logger: Optional[TaskLogger] = None,
    ) -> str:
        """
        处理 2FA 验证（带重试机制）

        Returns:
            "handled" - 已处理
            "not_needed" - 不需要
            "error" - 处理失败
        """
        import re
        import time

        totp_selectors = [
            'input[name="totpPin"]',
            'input[id="totpPin"]',
            'input[type="tel"][name="Pin"]',
            'input[type="tel"]',
        ]

        totp_input = None
        for selector in totp_selectors:
            loc = page.locator(selector)
            if await loc.count() > 0 and await loc.first.is_visible():
                totp_input = loc.first
                break

        if not totp_input:
            return "not_needed"

        if task_logger:
            task_logger.info("检测到 2FA 输入框")

        if not secret or not pyotp:
            self.logger.warning("需要 2FA 验证但未提供密钥")
            return "error"

        secret = secret.replace(" ", "").strip().upper()

        def _wrong_code_visible() -> bool:
            try:
                wrong = page.get_by_text(
                    re.compile(r"Wrong code|Try again|incorrect|Invalid", re.IGNORECASE),
                    exact=False,
                ).first
                return wrong.is_visible(timeout=500)
            except Exception:
                return False

        async def _submit_code(code: str) -> bool:
            await totp_input.fill(code)
            await asyncio.sleep(0.5)

            next_btn = page.locator("#totpNext >> button")
            if await next_btn.count() > 0:
                await next_btn.click()
            else:
                await totp_input.press("Enter")

            await asyncio.sleep(1.5)

            try:
                if not await totp_input.is_visible(timeout=500):
                    return True
            except Exception:
                pass

            try:
                url_now = page.url or ""
                if "/challenge/totp" not in url_now and "signin/challenge" not in url_now:
                    return True
            except Exception:
                pass

            if await _wrong_code_visible():
                return False

            return False

        try:
            totp = pyotp.TOTP(secret)

            base_ts = int(time.time())
            codes = []
            for delta in (0, -30, 30):
                try:
                    codes.append(totp.at(base_ts + delta))
                except Exception:
                    continue
            uniq_codes = list(dict.fromkeys(codes))

            for idx, code in enumerate(uniq_codes[:3]):
                if task_logger:
                    task_logger.info(f"尝试 2FA 验证码 ({idx + 1}/{len(uniq_codes)}): {code[:3]}***")

                if await _submit_code(code):
                    if task_logger:
                        task_logger.info("2FA 验证成功")
                    return "handled"

                if task_logger:
                    task_logger.warning(f"2FA 验证码 {code[:3]}*** 失败，尝试下一个")

            wait_s = 30 - (int(time.time()) % 30)
            wait_s = max(2, min(wait_s + 1, 31))
            if task_logger:
                task_logger.info(f"等待 {wait_s}s 进入下一个 TOTP 时间窗口")
            await asyncio.sleep(wait_s)

            code = totp.now()
            if task_logger:
                task_logger.info(f"最后尝试 2FA 验证码: {code[:3]}***")

            if await _submit_code(code):
                if task_logger:
                    task_logger.info("2FA 验证成功")
                return "handled"

            self.logger.error("2FA 验证失败：所有尝试均未成功")
            return "error"

        except Exception as e:
            self.logger.error(f"2FA 验证失败: {e}")
            return "error"

    # ==================== 辅助邮箱验证处理 ====================

    async def _handle_recovery_email(
        self,
        page: Page,
        backup_email: str,
        task_logger: Optional[TaskLogger] = None,
    ) -> str:
        """
        处理辅助邮箱验证

        Returns:
            "handled" - 已处理
            "not_needed" - 不需要
            "error" - 处理失败
        """
        recovery_indicators = [
            'text="Confirm your recovery email"',
            'text="确认您的辅助邮箱"',
            'text="Enter recovery email"',
            'input[id="knowledge-preregistered-email-response"]',
        ]

        for indicator in recovery_indicators:
            if await page.locator(indicator).count() > 0:
                if task_logger:
                    task_logger.info("检测到辅助邮箱验证")

                if backup_email:
                    try:
                        # 先尝试点击选项
                        option = page.locator(
                            'div[role="link"]:has-text("Confirm your recovery email")'
                        )
                        if await option.count() > 0 and await option.first.is_visible():
                            await option.first.click()
                            await asyncio.sleep(2)

                        # 输入辅助邮箱
                        recovery_input = page.locator(
                            'input[id="knowledge-preregistered-email-response"], '
                            'input[name="knowledgePreregisteredEmailResponse"]'
                        )
                        if await recovery_input.count() > 0:
                            if task_logger:
                                task_logger.info(f"输入辅助邮箱: {backup_email}")
                            await recovery_input.first.fill(backup_email)
                            await asyncio.sleep(0.5)

                            # 点击下一步
                            next_btn = page.locator(
                                'button:has-text("Next"), button:has-text("下一步")'
                            )
                            if await next_btn.count() > 0:
                                await next_btn.first.click()
                            else:
                                await recovery_input.first.press("Enter")

                            await asyncio.sleep(3)
                            return "handled"
                    except Exception as e:
                        self.logger.error(f"辅助邮箱验证异常: {e}")
                else:
                    return "error"

        return "not_needed"

    # ==================== 安全弹窗处理 ====================

    async def _handle_security_prompts(self, page: Page):
        """处理安全弹窗 (Not now 等)"""
        skip_buttons = [
            'button:has-text("Not now")',
            'button:has-text("Cancel")',
            'button:has-text("No thanks")',
            'button:has-text("暂不")',
            'button:has-text("取消")',
            'button:has-text("以后再说")',
        ]

        for btn_selector in skip_buttons:
            btn = page.locator(btn_selector).first
            try:
                if await btn.count() > 0 and await btn.is_visible():
                    self.logger.info("跳过安全提示弹窗...")
                    await btn.click()
                    await asyncio.sleep(1)
                    break
            except:
                pass

    # ==================== 登录状态检查 ====================

    async def check_login_status(self, page: Page) -> bool:
        """
        检查是否已登录

        Args:
            page: Playwright页面对象

        Returns:
            bool: 是否已登录
        """
        try:
            # 先用头像检测
            if await self._check_login_by_avatar(page):
                return True

            # 访问Google账号页面
            await page.goto("https://myaccount.google.com/", timeout=15000)
            await asyncio.sleep(2)

            # 检查是否需要登录
            current_url = page.url
            if (
                "accounts.google.com/servicelogin" in current_url
                or "accounts.google.com/signin" in current_url
            ):
                return False

            # 再次用头像检测
            return await self._check_login_by_avatar(page)

        except Exception as e:
            self.logger.error(f"Error checking login status: {e}")
            return False

    async def logout(self, page: Page) -> bool:
        """
        退出登录

        Args:
            page: Playwright页面对象

        Returns:
            bool: 是否成功
        """
        try:
            await page.goto("https://accounts.google.com/Logout", timeout=15000)
            await asyncio.sleep(2)
            self.logger.info("Logged out successfully")
            return True
        except Exception as e:
            self.logger.error(f"Logout failed: {e}")
            return False

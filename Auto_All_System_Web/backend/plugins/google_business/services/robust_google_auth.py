"""
Google账号认证和登录模块 (统一健壮版本)

整合 PyQt 和 Web 版本的优点：
- PyQt 的循环检测机制和头像检测
- Web 的机器人验证等待
- 统一的错误处理

@author Auto System
@date 2026-01-24
"""

import asyncio
import re
import logging
import time
from typing import Tuple, Optional, Dict, Any
from playwright.async_api import Page

try:
    import pyotp
except ImportError:
    pyotp = None

logger = logging.getLogger("plugin.google_business.login")


# ==================== 登录状态枚举 ====================


class GoogleLoginStatus:
    """Google登录状态枚举"""

    LOGGED_IN = "logged_in"
    NOT_LOGGED_IN = "not_logged_in"
    NEED_PASSWORD = "need_password"
    NEED_2FA = "need_2fa"
    NEED_RECOVERY = "need_recovery"
    NEED_CAPTCHA = "need_captcha"  # 新增：需要人工验证
    SESSION_EXPIRED = "session_expired"
    SECURITY_CHECK = "security_check"
    UNKNOWN = "unknown"


# ==================== 核心检测函数 ====================


async def check_google_login_by_avatar(page: Page, timeout: float = 10.0) -> bool:
    """
    核心登录检测：通过检测头像按钮判断是否已登录

    Args:
        page: Playwright 页面对象
        timeout: 超时时间(秒)

    Returns:
        True=已登录, False=未登录
    """
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
            except Exception:
                continue

        # 通过 URL 判断
        current_url = page.url
        if "myaccount.google.com" in current_url and "signin" not in current_url:
            return True

        return False

    except Exception as e:
        logger.warning(f"登录检测异常: {e}")
        return False


async def detect_captcha(page: Page) -> bool:
    """
    检测是否有机器人验证/CAPTCHA

    Returns:
        True=检测到验证码, False=未检测到
    """
    captcha_indicators = [
        'iframe[src*="recaptcha"]',
        'iframe[title*="reCAPTCHA"]',
        'text="验证您不是机器人"',
        'text="Confirm you\'re not a robot"',
        "#captchaimg",
        'text="Unusual traffic"',
        "[data-recaptcha]",
    ]

    try:
        for indicator in captcha_indicators:
            locator = page.locator(indicator)
            if await locator.count() > 0 and await locator.first.is_visible():
                logger.info(f"检测到验证码指标: {indicator}")
                return True
        return False
    except Exception:
        return False


async def detect_error_message(page: Page) -> Optional[str]:
    """
    检测登录错误消息

    Returns:
        错误消息文本，如果没有则返回 None
    """
    error_selectors = [
        '[role="alert"]',
        ".error-msg",
        ".Ekjuhf",
        'text="Wrong password"',
        'text="密码错误"',
        'text=/Your password was changed/i',
        'text=/password was changed/i',
        'text="您的密码已更改"',
        'text="Couldn\'t find your Google Account"',
        'text="找不到您的 Google 帐号"',
    ]

    try:
        for selector in error_selectors:
            locator = page.locator(selector)
            if await locator.count() > 0 and await locator.first.is_visible():
                return await locator.first.inner_text()
        return None
    except Exception:
        return None


async def detect_phone_verification(page: Page) -> bool:
    """
    检测是否需要手机号验证

    Returns:
        True=检测到手机号验证, False=未检测到
    """
    indicators = [
        'text="Enter a phone number to get a text message with a verification code"',
        'text="Enter a phone number"',
        'text="phone number"',
        'text="请输入手机号"',
        'text="输入手机号"',
        'text="短信验证码"',
        'text="发送验证码"',
    ]

    try:
        for indicator in indicators:
            locator = page.locator(indicator)
            if await locator.count() > 0 and await locator.first.is_visible():
                return True
        return False
    except Exception:
        return False


async def wait_for_password_input(
    page: Page,
    max_wait_seconds: int = 120,
    log_callback=None,
    exit_on_captcha: bool = False,
) -> Tuple[bool, str]:
    """
    等待密码输入框出现（支持人工过验证）

    Args:
        page: Playwright 页面对象
        max_wait_seconds: 最大等待时间
        log_callback: 日志回调函数

    Returns:
        (成功, 消息)
    """

    def log(msg):
        if log_callback:
            log_callback(msg)
        logger.info(msg)

    password_input = page.locator('input[type="password"]')
    wait_interval = 2
    waited = 0
    captcha_warned = False

    while waited < max_wait_seconds:
        # 检查密码框是否出现
        if await password_input.count() > 0 and await password_input.first.is_visible():
            return True, "密码框已出现"

        # 检测错误消息
        error_msg = await detect_error_message(page)
        if error_msg:
            return False, f"登录错误: {error_msg}"

        # 检测手机号验证
        if await detect_phone_verification(page):
            if log_callback:
                log_callback("⚠️ 检测到手机号验证，退出等待")
            return False, "需要手机号验证"

        # 检测机器人验证
        if await detect_captcha(page):
            if exit_on_captcha:
                log("⚠️ 检测到机器人验证，退出等待")
                return False, "检测到机器人验证"
            if not captcha_warned:
                log("⚠️ 检测到机器人验证，请手动完成验证...")
                captcha_warned = True
            logger.info(f"等待人工验证... ({waited}s/{max_wait_seconds}s)")
        else:
            if waited > 0 and waited % 10 == 0:
                log(f"等待页面加载... ({waited}s)")

        await asyncio.sleep(wait_interval)
        waited += wait_interval

    # 超时
    if await detect_captcha(page):
        return False, f"需要人工验证但超时未完成（等待了{max_wait_seconds}秒）"
    else:
        return False, "等待密码输入框超时"


# ==================== 核心登录函数 ====================


async def robust_google_login(
    page: Page,
    account_info: Dict[str, Any],
    log_callback=None,
    max_captcha_wait: int = 120,
    exit_on_captcha: bool = False,
) -> Tuple[bool, str]:
    """
    健壮的 Google 登录函数

    整合 PyQt 和 Web 版本的优点：
    - 循环检测各种验证步骤
    - 支持机器人验证等待
    - 头像检测确认登录成功

    Args:
        page: Playwright 页面对象
        account_info: 账号信息 {email, password, secret/2fa_secret, backup/backup_email}
        log_callback: 日志回调函数
        max_captcha_wait: 机器人验证最大等待时间(秒)

    Returns:
        (success, message)
    """

    def log(msg):
        if log_callback:
            log_callback(msg)
        logger.info(msg)

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

    log(f"开始登录: {email}")

    try:
        # ========== 1. 导航到登录页 ==========
        try:
            current_url = page.url
            if (
                "accounts.google.com" not in current_url
                and "myaccount.google.com" not in current_url
            ):
                await page.goto(
                    "https://accounts.google.com/signin",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                await asyncio.sleep(2)
        except Exception as e:
            log(f"导航异常(可能已在页面): {e}")

        # ========== 2. 输入邮箱 ==========
        try:
            email_input = page.locator('input[type="email"]')
            if await email_input.count() > 0 and await email_input.first.is_visible():
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
        except Exception as e:
            log(f"邮箱输入异常: {e}")

        # ========== 3. 等待密码框（支持人工过验证）==========
        log("等待密码输入框...")
        password_ready, wait_msg = await wait_for_password_input(
            page,
            max_wait_seconds=max_captcha_wait,
            log_callback=log_callback,
            exit_on_captcha=exit_on_captcha,
        )

        if not password_ready:
            return False, wait_msg

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
            return False, f"密码输入失败: {e}"

        # ========== 5. 循环处理各种验证步骤 ==========
        max_checks = 10

        async def _click_first_visible(selectors: list[str], timeout_ms: int = 600) -> bool:
            for selector in selectors:
                try:
                    locator = page.locator(selector).first
                    if await locator.count() > 0 and await locator.is_visible(timeout=timeout_ms):
                        await locator.click(timeout=2500)
                        return True
                except Exception:
                    continue
            return False

        async def _handle_challenge_method_selection() -> bool:
            """处理 challenge 认证方式选择页（先选方式，再进入输入框）。"""
            current_url = (page.url or "").lower()
            if "signin/challenge" not in current_url:
                return False

            # 已经进入具体输入步骤时不重复选择方式
            direct_inputs = page.locator(
                'input[name="totpPin"], '
                'input[id="totpPin"], '
                'input[id="knowledge-preregistered-email-response"], '
                'input[name="knowledgePreregisteredEmailResponse"], '
                'input[type="password"]'
            )
            try:
                if await direct_inputs.count() > 0 and await direct_inputs.first.is_visible(timeout=300):
                    return False
            except Exception:
                pass

            # 优先走 2FA（有 secret 时）
            if secret and pyotp:
                auth_selectors = [
                    'div[role="button"]:has-text("Google Authenticator")',
                    'div[role="link"]:has-text("Google Authenticator")',
                    'button:has-text("Google Authenticator")',
                    'div.l5PPKe:has-text("Google Authenticator")',
                    'text=/Get a verification code from.*Google Authenticator/i',
                    'text=/Google Authenticator app/i',
                ]
                if await _click_first_visible(auth_selectors):
                    log("检测到认证方式选择页，已选择 Google Authenticator")
                    await asyncio.sleep(2)
                    return True

            # 无 2FA 或 2FA 选择不可用时，尝试辅助邮箱方式
            if backup_email:
                recovery_selectors = [
                    'div[role="button"]:has-text("Confirm your recovery email")',
                    'div[role="link"]:has-text("Confirm your recovery email")',
                    'button:has-text("Confirm your recovery email")',
                    'text=/Confirm your recovery email/i',
                    'text=/Enter recovery email/i',
                ]
                if await _click_first_visible(recovery_selectors):
                    log("检测到认证方式选择页，已选择辅助邮箱验证")
                    await asyncio.sleep(2)
                    return True

            return False

        for i in range(max_checks):
            log(f"检查验证步骤 ({i + 1}/{max_checks})...")

            # 等待页面稳定
            try:
                await page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
                pass

            # A. 检测是否已登录成功
            if await check_google_login_by_avatar(page, timeout=3):
                log("✅ 登录成功（检测到头像）")
                return True, "登录成功"

            # B. 检测错误消息
            error_msg = await detect_error_message(page)
            if error_msg:
                return False, f"登录失败: {error_msg}"

            # B2. 检测手机号验证
            if await detect_phone_verification(page):
                return False, "需要手机号验证"

            # C. 检测机器人验证
            if await detect_captcha(page):
                if exit_on_captcha:
                    return False, "检测到机器人验证"
                log("⚠️ 检测到验证码，等待人工处理...")
                await asyncio.sleep(5)
                continue

            # C2. challenge 方式选择页（先选方式，再进入 TOTP/辅助邮箱输入）
            if await _handle_challenge_method_selection():
                continue

            # D. 检测 2FA (TOTP)
            totp_selectors = [
                'input[name="totpPin"]',
                'input[id="totpPin"]',
                'input[type="tel"][name="Pin"]',
            ]

            totp_found = False
            wrong_code_patterns = re.compile(
                r"Wrong code|Try again|incorrect|Invalid|代码错误|验证码错误",
                re.IGNORECASE,
            )

            async def _seems_logged_in_now() -> bool:
                try:
                    if await check_google_login_by_avatar(page, timeout=2):
                        return True
                except Exception:
                    pass

                try:
                    current = (page.url or "").lower()
                    if "myaccount.google.com" in current and "signin/challenge" not in current:
                        return True
                except Exception:
                    pass
                return False

            async def _totp_still_challenge(input_locator) -> bool:
                """判断是否仍停留在 TOTP challenge 页面。"""
                try:
                    current = (page.url or "").lower()
                    if "myaccount.google.com" in current and "signin/challenge" not in current:
                        return False
                except Exception:
                    pass

                try:
                    wrong_hint = page.get_by_text(wrong_code_patterns, exact=False).first
                    if await wrong_hint.is_visible(timeout=500):
                        return True
                except Exception:
                    pass

                try:
                    current = (page.url or "").lower()
                    if "challenge/totp" in current or "signin/challenge" in current:
                        return True
                except Exception:
                    pass

                try:
                    if await input_locator.is_visible(timeout=300):
                        return True
                except Exception:
                    pass

                return False
            for selector in totp_selectors:
                totp_input = page.locator(selector)
                if await totp_input.count() > 0 and await totp_input.first.is_visible():
                    totp_found = True
                    log("检测到 2FA 输入框")

                    if secret and pyotp:
                        try:
                            s = secret.replace(" ", "").strip()
                            totp = pyotp.TOTP(s)
                            code = totp.now()
                            log(f"输入 2FA 验证码: {code[:3]}***")
                            await totp_input.first.fill(code)
                            await asyncio.sleep(0.5)

                            # 点击下一步
                            next_btn = page.locator("#totpNext >> button")
                            if await next_btn.count() > 0 and await next_btn.first.is_visible(timeout=500):
                                await next_btn.first.click(timeout=3500)
                            else:
                                await totp_input.first.press("Enter")

                            await asyncio.sleep(2)

                            if await _seems_logged_in_now():
                                log("检测到已登录，跳过 2FA 重试")
                                break

                            # 首次登录常见场景：验证码在提交时过期。
                            # 若仍在 challenge 页面，等待下一个窗口后再重试一次（单次兜底，避免死循环）。
                            if await _totp_still_challenge(totp_input.first):
                                wait_s = 30 - (int(time.time()) % 30)
                                wait_s = max(2, min(wait_s + 1, 31))
                                log(f"2FA 可能过期/错误，等待 {wait_s}s 后重试一次")
                                await asyncio.sleep(wait_s)

                                if await _seems_logged_in_now():
                                    log("等待后检测到已登录，跳过 2FA 重试")
                                    break

                                if not await _totp_still_challenge(totp_input.first):
                                    log("检测到已离开 challenge，跳过 2FA 重试")
                                    break

                                retry_code = totp.now()
                                log(f"重试 2FA 验证码: {retry_code[:3]}***")
                                retry_input = totp_input
                                if not (
                                    await retry_input.count() > 0
                                    and await retry_input.first.is_visible(timeout=500)
                                ):
                                    retry_input = page.locator('input[name="totpPin"], input[id="totpPin"], input[type="tel"][name="Pin"]')
                                if not (
                                    await retry_input.count() > 0
                                    and await retry_input.first.is_visible(timeout=500)
                                ):
                                    if await _seems_logged_in_now():
                                        log("重试阶段检测到已登录，跳过补提交流程")
                                        break
                                    raise RuntimeError("2FA 重试输入框不可用")

                                await retry_input.first.fill(retry_code)
                                await asyncio.sleep(0.5)

                                if await next_btn.count() > 0 and await next_btn.first.is_visible(timeout=500):
                                    await next_btn.first.click(timeout=3500)
                                else:
                                    await retry_input.first.press("Enter")

                                await asyncio.sleep(2)

                                if await _seems_logged_in_now():
                                    log("2FA 重试后检测到已登录")
                                    break
                        except Exception as e:
                            if (
                                await check_google_login_by_avatar(page, timeout=2)
                                or "myaccount.google.com" in (page.url or "")
                            ):
                                log("2FA 提交后页面已登录，忽略重试点击异常")
                            else:
                                return False, f"2FA 验证失败: {e}"
                    else:
                        return False, "需要 2FA 验证但未提供密钥"
                    break

            if totp_found:
                continue

            # E. 检测辅助邮箱验证
            recovery_indicators = [
                'text="Confirm your recovery email"',
                'text="确认您的辅助邮箱"',
                'text="Enter recovery email"',
                'input[id="knowledge-preregistered-email-response"]',
            ]

            recovery_found = False
            for indicator in recovery_indicators:
                if await page.locator(indicator).count() > 0:
                    recovery_found = True
                    log("检测到辅助邮箱验证")

                    if backup_email:
                        try:
                            # 先尝试点击选项
                            option = page.locator(
                                'div[role="link"]:has-text("Confirm your recovery email")'
                            )
                            if (
                                await option.count() > 0
                                and await option.first.is_visible()
                            ):
                                await option.first.click()
                                await asyncio.sleep(2)

                            # 输入辅助邮箱
                            recovery_input = page.locator(
                                'input[id="knowledge-preregistered-email-response"], '
                                'input[name="knowledgePreregisteredEmailResponse"]'
                            )
                            if await recovery_input.count() > 0:
                                log(f"输入辅助邮箱: {backup_email}")
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
                        except Exception as e:
                            log(f"辅助邮箱验证异常: {e}")
                    else:
                        return False, "需要辅助邮箱验证但未提供"
                    break

            if recovery_found:
                continue

            # F. 处理 "Not now" / "暂不" 等安全弹窗
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
                if await btn.count() > 0 and await btn.is_visible():
                    log(f"跳过安全提示弹窗...")
                    try:
                        await btn.click()
                        await asyncio.sleep(1)
                    except Exception:
                        pass
                    break

            # G. 检查 URL 是否表明登录成功
            current_url = page.url
            if (
                "myaccount.google.com" in current_url
                or "google.com/search" in current_url
            ):
                log("✅ 登录成功（URL 检测）")
                return True, "登录成功"

            await asyncio.sleep(2)

        # ========== 6. 最终检查 ==========
        if await check_google_login_by_avatar(page, timeout=5):
            log("✅ 登录成功")
            return True, "登录成功"

        # 检查 URL
        current_url = page.url
        if "myaccount.google.com" in current_url:
            log("✅ 登录成功（URL）")
            return True, "登录成功"

        return False, "登录超时或失败"

    except Exception as e:
        logger.error(f"登录异常: {e}", exc_info=True)
        return False, f"登录异常: {e}"


# ==================== 便捷函数 ====================


async def check_google_login_status(
    page: Page, timeout: float = 5.0
) -> Tuple[str, Dict[str, Any]]:
    """
    检测登录状态（兼容旧接口）

    Returns:
        (status, extra_info)
    """
    is_logged = await check_google_login_by_avatar(page, timeout)
    if is_logged:
        email = await _extract_logged_in_email(page)
        return GoogleLoginStatus.LOGGED_IN, {"email": email} if email else {}
    else:
        return GoogleLoginStatus.NOT_LOGGED_IN, {}


async def is_logged_in(page: Page) -> bool:
    """检查是否已登录"""
    return await check_google_login_by_avatar(page)


async def _extract_logged_in_email(page: Page) -> Optional[str]:
    """提取已登录邮箱"""
    try:
        label_locator = page.locator('a[aria-label*="Google"]').first
        if await label_locator.count() > 0:
            label = await label_locator.get_attribute("aria-label") or ""
            match = re.search(r"[\w\.-]+@[\w\.-]+", label)
            if match:
                return match.group(0)
    except Exception:
        pass
    return None

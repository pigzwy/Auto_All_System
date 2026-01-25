"""
@file google_auth.py
@brief Google账号认证和登录状态检测模块 (V2)
@details 包含Google账号登录状态检测(头像检测)、自动登录、资格检测(API拦截)等功能
@author Auto System
@date 2026-01-22
"""

import asyncio
import re
import pyotp
from typing import Tuple, Optional, Dict, Any
from playwright.async_api import Page, expect


# ==================== 登录状态枚举 ====================
class GoogleLoginStatus:
    """Google登录状态枚举"""

    LOGGED_IN = "logged_in"  # 已登录
    NOT_LOGGED_IN = "not_logged_in"  # 未登录（在登录页面）
    # 以下状态在V2检测中可能归类为NOT_LOGGED_IN，但保留枚举兼容
    NEED_PASSWORD = "need_password"
    NEED_2FA = "need_2fa"
    NEED_RECOVERY = "need_recovery"
    SESSION_EXPIRED = "session_expired"
    SECURITY_CHECK = "security_check"
    UNKNOWN = "unknown"


# ==================== V2 检测逻辑 (核心) ====================


async def check_google_login_by_avatar(page: Page, timeout: float = 10.0) -> bool:
    """
    @brief 核心登录检测：通过检测头像按钮判断是否已登录
    @param page Playwright 页面对象
    @param timeout 超时时间(秒)
    @return True=已登录, False=未登录
    """
    try:
        # 如果不在Google域下，可能需要导航（取决于调用者，这里假设已在Google页面）
        # 如果页面是空白或 about:blank，导航到 accounts.google.com
        if "about:blank" in page.url:
            await page.goto(
                "https://accounts.google.com/", wait_until="domcontentloaded"
            )

        # 头像按钮选择器 (多个备选)
        avatar_selectors = [
            'a[aria-label*="Google Account"] img.gbii',
            'a.gb_B[role="button"] img',
            'a[href*="SignOutOptions"] img',
            "img.gb_Q.gbii",
            'a[aria-label*="Google 帐号"] img',
            'a[aria-label*="Google 账号"] img',
        ]

        # 尝试检测头像元素
        # 使用first匹配，any即可
        for selector in avatar_selectors:
            try:
                # 使用 expect 自动等待，设置较短超时避免所有都check一遍花太久，
                # 但首个check需要足够时间等待页面加载
                # 这里逻辑优化：并行的逻辑比较难写，顺序检查
                locator = page.locator(selector).first
                if await locator.count() > 0 and await locator.is_visible():
                    return True
            except:
                continue

        # 如果上面快速检查没过，使用 expect 等待其中一个通用选择器（等待页面加载延迟）
        try:
            primary_selector = 'a[aria-label*="Google"] img'
            await expect(page.locator(primary_selector).first).to_be_visible(
                timeout=timeout * 1000
            )
            return True
        except:
            pass

        return False

    except Exception as e:
        print(f"[GoogleAuth] 登录检测异常: {e}")
        return False


async def check_google_login_status(
    page: Page, timeout: float = 5.0
) -> Tuple[str, Dict[str, Any]]:
    """
    @brief 兼容旧接口：检测登录状态
    @return (status, extra_info)
    """
    is_logged = await check_google_login_by_avatar(page, timeout)
    if is_logged:
        # 尝试获取邮箱（可选）
        email = await _extract_logged_in_email(page)
        return GoogleLoginStatus.LOGGED_IN, {"email": email} if email else {}
    else:
        return GoogleLoginStatus.NOT_LOGGED_IN, {}


async def check_google_one_status(
    page: Page, timeout: float = 20.0
) -> Tuple[str, Optional[str]]:
    """
    @brief V2资格检测：通过 API 拦截 + jsname 属性检测资格状态
    @param page Playwright 页面对象
    @param timeout 超时时间(秒)
    @return (status, sheerid_link)
            status: 'subscribed_antigravity' | 'subscribed' | 'verified' | 'link_ready' | 'ineligible' | 'error'
    """
    api_response_data = None
    response_received = asyncio.Event()

    async def handle_response(response):
        """响应拦截处理"""
        nonlocal api_response_data
        try:
            # 关键特征 rpcids=GI6Jdd
            if "rpcids=GI6Jdd" in response.url:
                text = await response.text()
                api_response_data = text
                response_received.set()
                # print(f"[GoogleAuth] 🔍 拦截到 GI6Jdd API 响应")
        except Exception:
            pass

    # 注册响应监听器
    page.on("response", handle_response)

    try:
        # 导航到目标页面（如果不在的话）
        target_url = "https://one.google.com/ai-student?g1_landing_page=75"
        if target_url not in page.url:
            await page.goto(
                target_url, wait_until="domcontentloaded", timeout=timeout * 1000
            )

        # 等待 API 响应 (最多 timeout 秒)
        try:
            await asyncio.wait_for(response_received.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass  # 超时没收到API，继续检查元素

        # 等待页面网络空闲（确保元素加载）
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except:
            pass

        # ============ 分析 API 响应 ============
        if api_response_data:
            status = _parse_api_response(api_response_data)
            if status:
                return status, None

        # ============ 检测页面元素 (API没拦截到或API显示未订阅时) ============
        return await _detect_page_elements(page)

    except Exception as e:
        print(f"[GoogleAuth] 资格检测异常: {e}")
        return "error", str(e)

    finally:
        # 移除监听器
        page.remove_listener("response", handle_response)


# ==================== 辅助函数 ====================


def _parse_api_response(response_text: str) -> Optional[str]:
    """解析 GI6Jdd API 响应"""
    try:
        # 检查订阅状态
        # 响应通常包含 JSON 数组，这里简化做字符串匹配
        has_2tb = (
            "2 TB" in response_text
            or "2TB" in response_text
            or '"2 TB"' in response_text
        )
        has_antigravity = (
            "Antigravity" in response_text or '"Antigravity"' in response_text
        )

        if has_2tb:
            if has_antigravity:
                return "subscribed_antigravity"
            else:
                return "subscribed"
        return None
    except Exception:
        return None


async def _detect_page_elements(page: Page) -> Tuple[str, Optional[str]]:
    """通过页面元素检测资格状态"""
    try:
        # 1. 检查 hSRGPd (有资格待验证 - 含有 SheerID 验证链接)
        link_ready_locator = page.locator('[jsname="hSRGPd"]')
        if (
            await link_ready_locator.count() > 0
            and await link_ready_locator.first.is_visible()
        ):
            sheerid_link = await _extract_sheerid_link(page)
            return "link_ready", sheerid_link

        # 2. 检查 V67aGc (已验证未绑卡 - Get student offer 按钮)
        verified_locator = page.locator('[jsname="V67aGc"]')
        if (
            await verified_locator.count() > 0
            and await verified_locator.first.is_visible()
        ):
            return "verified", None

        # 3. 再次检查是否有 SheerID 链接 (备选方案 - 有时候jsname可能变)
        sheerid_link = await _extract_sheerid_link(page)
        if sheerid_link:
            return "link_ready", sheerid_link

        # 4. 检查是否有 "Get student offer" 相关按钮
        offer_selectors = [
            'button:has-text("Get student offer")',
            'button:has-text("Get offer")',
            '[data-action="offerDetails"]',
        ]
        for selector in offer_selectors:
            if await page.locator(selector).count() > 0:
                return "verified", None

        # 5. 再次检查已订阅文本（防止API漏掉）
        if (
            await page.locator('text="Subscribed"').count() > 0
            or await page.locator('text="已订阅"').count() > 0
        ):
            return "subscribed", None

        return "ineligible", None

    except Exception:
        return "ineligible", None


async def _extract_sheerid_link(page: Page) -> Optional[str]:
    """提取 SheerID 验证链接"""
    try:
        # 方法1: 查找 sheerid.com 链接
        sheerid_locator = page.locator('a[href*="sheerid.com"]')
        if await sheerid_locator.count() > 0:
            href = await sheerid_locator.first.get_attribute("href")
            if href:
                return href

        # 方法2: 从页面内容中查找
        content = await page.content()
        match = re.search(r'https://[^"\']*sheerid\.com[^"\']*', content)
        if match:
            return match.group(0)
        return None
    except Exception:
        return None


async def _extract_logged_in_email(page: Page) -> Optional[str]:
    """提取已登录邮箱"""
    try:
        # 尝试从aria-label提取: "Google Account: Name  (email@gmail.com)"
        label_locator = page.locator('a[aria-label*="Google"]').first
        if await label_locator.count() > 0:
            label = await label_locator.get_attribute("aria-label") or ""
            match = re.search(r"[\w\.-]+@[\w\.-]+", label)
            if match:
                return match.group(0)
    except:
        pass
    return None


# ==================== 登录操作逻辑 (保持) ====================


async def is_logged_in(page: Page) -> bool:
    """检查是否已登录"""
    return await check_google_login_by_avatar(page)


async def ensure_google_login(page: Page, account_info: dict) -> Tuple[bool, str]:
    """确保Google已登录"""
    email = account_info.get("email", "")

    # 1. 检查当前状态
    is_logged = await check_google_login_by_avatar(page)
    if is_logged:
        # 可选：检查是否是正确账号
        current_email = await _extract_logged_in_email(page)
        if current_email and email and current_email.lower() != email.lower():
            print(f"[GoogleAuth] 账号不匹配: 当前 {current_email}, 目标 {email}")
            # 这里如果不匹配，可能需要退出登录? 或者直接报错
            # 为简单起见，暂不强制退出，仅提示
        return True, "已登录"

    # 2. 未登录，执行登录
    return await google_login(page, account_info)


async def google_login(page: Page, account_info: dict) -> Tuple[bool, str]:
    """
    执行登录流程 (统一健壮版本)

    整合机器人验证等待功能
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

    print(f"[GoogleAuth] 开始登录: {email}")

    # 机器人验证等待配置
    CAPTCHA_WAIT_TIMEOUT = 120  # 秒
    MAX_VERIFICATION_ROUNDS = 10

    try:
        # 1. 导航
        if "accounts.google.com" not in page.url:
            await page.goto(
                "https://accounts.google.com/signin", wait_until="domcontentloaded"
            )
            await asyncio.sleep(2)

        # 2. 邮箱
        try:
            email_input = page.locator('input[type="email"]')
            if await email_input.count() > 0 and await email_input.first.is_visible():
                await email_input.first.fill(email)
                await asyncio.sleep(0.5)
                await page.click("#identifierNext >> button")
                await asyncio.sleep(2)
        except Exception as e:
            # 可能已经在密码页
            print(f"[GoogleAuth] 邮箱输入异常(可能已在密码页): {e}")

        # 3. 等待密码框（支持人工过机器人验证）
        print("[GoogleAuth] 等待密码输入框...")
        password_input = page.locator('input[type="password"]')
        waited = 0
        captcha_warned = False

        while waited < CAPTCHA_WAIT_TIMEOUT:
            if (
                await password_input.count() > 0
                and await password_input.first.is_visible()
            ):
                break

            # 检测错误消息
            if (
                await page.locator('text="Couldn\'t find your Google Account"').count()
                > 0
            ):
                return False, "账号不存在"

            # 检测机器人验证
            captcha_detected = False
            captcha_indicators = [
                'iframe[src*="recaptcha"]',
                'iframe[title*="reCAPTCHA"]',
                'text="Verify it\'s you"',
                'text="验证您不是机器人"',
                'text="Confirm you\'re not a robot"',
                "#captchaimg",
            ]
            for indicator in captcha_indicators:
                if await page.locator(indicator).count() > 0:
                    captcha_detected = True
                    break

            if captcha_detected:
                if not captcha_warned:
                    print(f"[GoogleAuth] ⚠️ 检测到机器人验证，请手动完成验证...")
                    captcha_warned = True
                else:
                    print(
                        f"[GoogleAuth] 等待人工验证... ({waited}s/{CAPTCHA_WAIT_TIMEOUT}s)"
                    )
            else:
                if waited > 0 and waited % 10 == 0:
                    print(f"[GoogleAuth] 等待页面加载... ({waited}s)")

            await asyncio.sleep(2)
            waited += 2

        # 检查密码框是否出现
        if await password_input.count() > 0 and await password_input.first.is_visible():
            print("[GoogleAuth] 输入密码...")
            await password_input.first.fill(password)
            await asyncio.sleep(0.5)
            await page.click("#passwordNext >> button")
            await asyncio.sleep(3)
        else:
            # 超时
            if captcha_warned:
                return (
                    False,
                    f"需要人工验证但超时未完成（等待了{CAPTCHA_WAIT_TIMEOUT}秒）",
                )
            else:
                return False, "密码输入框未出现"

        # 4. 循环检测验证步骤 (增强版)
        for i in range(MAX_VERIFICATION_ROUNDS):
            print(f"[GoogleAuth] 检查验证步骤 ({i + 1}/{MAX_VERIFICATION_ROUNDS})...")

            try:
                await page.wait_for_load_state("networkidle", timeout=3000)
            except:
                pass

            # A. 检测是否登录成功
            if await check_google_login_by_avatar(page, timeout=3):
                print("[GoogleAuth] ✅ 登录成功（检测到头像）")
                return True, "登录成功"

            # B. 检测错误消息
            error_selectors = [
                '[role="alert"]',
                'text="Wrong password"',
                'text="密码错误"',
            ]
            for selector in error_selectors:
                if await page.locator(selector).count() > 0:
                    try:
                        error_text = await page.locator(selector).first.inner_text()
                        return False, f"登录失败: {error_text}"
                    except:
                        return False, "登录失败: 密码错误"

            # C. 检测机器人验证
            captcha_detected = False
            for indicator in captcha_indicators:
                if await page.locator(indicator).count() > 0:
                    captcha_detected = True
                    break
            if captcha_detected:
                print("[GoogleAuth] ⚠️ 检测到验证码，等待人工处理...")
                await asyncio.sleep(5)
                continue

            # D. 检测2FA
            totp_selectors = [
                'input[id="totpPin"]',
                'input[name="totpPin"]',
                'input[type="tel"]',
            ]
            totp_found = False
            for selector in totp_selectors:
                totp_input = page.locator(selector)
                if await totp_input.count() > 0 and await totp_input.first.is_visible():
                    totp_found = True
                    print("[GoogleAuth] 检测到 2FA 输入框")
                    if secret:
                        try:
                            code = pyotp.TOTP(secret.replace(" ", "")).now()
                            print(f"[GoogleAuth] 输入 2FA 验证码: {code[:3]}***")
                            await totp_input.first.fill(code)
                            await asyncio.sleep(0.5)
                            await page.click("#totpNext >> button")
                            await asyncio.sleep(3)
                        except Exception as e:
                            return False, f"2FA密钥无效: {e}"
                    else:
                        return False, "缺少2FA密钥"
                    break
            if totp_found:
                continue

            # E. 检测辅助邮箱验证
            recovery_indicators = [
                'text="Confirm your recovery email"',
                'text="确认您的辅助邮箱"',
                'input[id="knowledge-preregistered-email-response"]',
            ]
            recovery_found = False
            for indicator in recovery_indicators:
                if await page.locator(indicator).count() > 0:
                    recovery_found = True
                    print("[GoogleAuth] 检测到辅助邮箱验证")
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
                                'input[id="knowledge-preregistered-email-response"]'
                            )
                            if await recovery_input.count() > 0:
                                print(f"[GoogleAuth] 输入辅助邮箱: {backup_email}")
                                await recovery_input.first.fill(backup_email)
                                await asyncio.sleep(0.5)
                                next_btn = page.locator(
                                    'button:has-text("Next"), button:has-text("下一步")'
                                )
                                if await next_btn.count() > 0:
                                    await next_btn.first.click()
                                else:
                                    await recovery_input.first.press("Enter")
                                await asyncio.sleep(3)
                        except Exception as e:
                            print(f"[GoogleAuth] 辅助邮箱验证异常: {e}")
                    else:
                        return False, "需要辅助邮箱验证但未提供"
                    break
            if recovery_found:
                continue

            # F. 处理安全弹窗
            skip_buttons = [
                'button:has-text("Not now")',
                'button:has-text("暂不")',
                'button:has-text("Cancel")',
                'button:has-text("以后再说")',
            ]
            for btn_selector in skip_buttons:
                btn = page.locator(btn_selector).first
                try:
                    if await btn.count() > 0 and await btn.is_visible():
                        print("[GoogleAuth] 跳过安全提示弹窗...")
                        await btn.click()
                        await asyncio.sleep(1)
                        break
                except:
                    pass

            # G. 检查 URL
            current_url = page.url
            if "myaccount.google.com" in current_url or "one.google.com" in current_url:
                print("[GoogleAuth] ✅ 登录成功（URL 检测）")
                return True, "登录成功"

            await asyncio.sleep(2)

        # 最终检查
        if await check_google_login_by_avatar(page):
            print("[GoogleAuth] ✅ 登录成功")
            return True, "登录成功"

        return False, "登录超时或失败"

    except Exception as e:
        import traceback

        traceback.print_exc()
        return False, f"登录异常: {e}"


# ==================== 综合检测流程 ====================


async def full_google_detection(
    page: Page, account_info: dict = None, timeout: float = 20.0
) -> Tuple[bool, str, Optional[str]]:
    """
    @brief 完整的 Google 检测流程 (登录 + 资格)
    @return (is_logged_in, status, sheerid_link)
    """
    # 1. 检测登录状态
    is_logged_in = await check_google_login_by_avatar(page, timeout=timeout)

    if not is_logged_in:
        return False, "not_logged_in", None

    # 2. 检测资格状态
    status, sheerid_link = await check_google_one_status(page, timeout=timeout)

    return True, status, sheerid_link


# ==================== 状态常量 ====================

# 账号状态定义
STATUS_NOT_LOGGED_IN = "not_logged_in"
STATUS_SUBSCRIBED_ANTIGRAVITY = "subscribed_antigravity"
STATUS_SUBSCRIBED = "subscribed"
STATUS_VERIFIED = "verified"
STATUS_LINK_READY = "link_ready"
STATUS_INELIGIBLE = "ineligible"
STATUS_ERROR = "error"
STATUS_PENDING = "pending_check"

# 状态显示映射
STATUS_DISPLAY = {
    STATUS_PENDING: "❔待检测",
    STATUS_NOT_LOGGED_IN: "🔒未登录",
    STATUS_INELIGIBLE: "❌无资格",
    STATUS_LINK_READY: "🔗待验证",
    STATUS_VERIFIED: "✅已验证",
    STATUS_SUBSCRIBED: "👑已订阅",
    STATUS_SUBSCRIBED_ANTIGRAVITY: "🌟已解锁",
    STATUS_ERROR: "⚠️错误",
}

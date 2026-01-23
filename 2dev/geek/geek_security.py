#!/usr/bin/env python3
"""
GeekezBrowser 版 Google 安全设置自动化
适配 geek_process.py 的 API，功能与 google_security_automation.py 相同

功能：
- 修改 2FA 密钥
- 修改辅助邮箱
- 获取备份验证码
- 一键修改全部
"""

from __future__ import annotations

import asyncio
import pyotp
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# 添加仓库根目录到 sys.path
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from geek_process import GeekProcess, load_accounts
from geek_browser_api import LaunchInfo


def _log(msg: str, log_callback: Optional[Callable[[str], None]] = None) -> None:
    if log_callback:
        try:
            log_callback(msg)
            return
        except Exception:
            pass
    print(msg)


class GeekSecurityAutomation:
    """GeekezBrowser 版安全设置自动化"""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 19527,
    ) -> None:
        self.proc = GeekProcess(host=host, port=port)

    # -------------------------------------------
    # 辅助方法：2FA 验证码生成
    # -------------------------------------------
    @staticmethod
    def generate_2fa_code(secret: str) -> str:
        """生成 TOTP 验证码"""
        try:
            secret_clean = secret.replace(" ", "").upper()
            totp = pyotp.TOTP(secret_clean)
            return totp.now()
        except Exception:
            return ""

    # -------------------------------------------
    # 核心自动化方法
    # -------------------------------------------
    async def _ensure_logged_in(
        self,
        page,
        account_info: Dict[str, str],
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """确保已登录 Google 账号"""
        email = account_info.get("email", "")
        password = account_info.get("password", "")
        secret = account_info.get("secret", "") or account_info.get("2fa_secret", "")

        _log(f"[Security] 检查登录状态: {email}", log_callback)

        # 访问 Google 账号安全页面
        try:
            await page.goto(
                "https://myaccount.google.com/signinoptions/two-step-verification",
                wait_until="networkidle",
                timeout=30000,
            )
        except Exception as e:
            _log(f"[Security] 页面加载超时，继续尝试: {e}", log_callback)

        await page.wait_for_timeout(2000)

        # 检查是否需要登录
        current_url = page.url
        if "accounts.google.com" in current_url and (
            "identifier" in current_url or "signin" in current_url
        ):
            _log(f"[Security] 需要登录", log_callback)

            # 输入邮箱
            try:
                email_input = page.locator('input[type="email"]')
                if await email_input.count() > 0:
                    await email_input.fill(email)
                    await page.click(
                        'button:has-text("Next"), button:has-text("下一步")'
                    )
                    await page.wait_for_timeout(2000)
            except Exception as e:
                _log(f"[Security] 输入邮箱失败: {e}", log_callback)

            # 输入密码
            try:
                pwd_input = page.locator('input[type="password"]')
                if await pwd_input.count() > 0:
                    await pwd_input.fill(password)
                    await page.click(
                        'button:has-text("Next"), button:has-text("下一步")'
                    )
                    await page.wait_for_timeout(3000)
            except Exception as e:
                _log(f"[Security] 输入密码失败: {e}", log_callback)

            # 处理 2FA
            await self._handle_2fa_if_needed(page, secret, log_callback)

        # 验证登录成功
        await page.wait_for_timeout(2000)
        current_url = page.url
        if "myaccount.google.com" in current_url:
            _log(f"[Security] 登录成功", log_callback)
            return True

        _log(f"[Security] 登录状态未知: {current_url}", log_callback)
        return False

    async def _handle_2fa_if_needed(
        self,
        page,
        secret: str,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """处理 2FA 验证"""
        if not secret:
            return True

        try:
            # 查找 2FA 输入框
            totp_input = page.locator(
                'input[type="tel"], input[name="totpPin"], input[aria-label*="验证码"]'
            )
            if await totp_input.count() > 0:
                code = self.generate_2fa_code(secret)
                if code:
                    _log(f"[Security] 输入 2FA 验证码", log_callback)
                    await totp_input.fill(code)
                    await page.click(
                        'button:has-text("Next"), button:has-text("下一步")'
                    )
                    await page.wait_for_timeout(2000)
                    return True
        except Exception as e:
            _log(f"[Security] 2FA 处理失败: {e}", log_callback)

        return False

    async def _change_2fa_secret_async(
        self,
        page,
        account_info: Dict[str, str],
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, str, str]:
        """
        修改 2FA 密钥
        返回: (成功, 新密钥, 消息)
        """
        email = account_info.get("email", "")
        password = account_info.get("password", "")
        old_secret = account_info.get("secret", "") or account_info.get(
            "2fa_secret", ""
        )

        _log(f"[Security] 开始修改 2FA: {email}", log_callback)

        try:
            # 确保登录
            if not await self._ensure_logged_in(page, account_info, log_callback):
                return False, "", "登录失败"

            # 导航到 2FA 设置页面
            await page.goto(
                "https://myaccount.google.com/signinoptions/two-step-verification",
                wait_until="networkidle",
                timeout=30000,
            )
            await page.wait_for_timeout(2000)

            # 可能需要再次验证身份
            pwd_input = page.locator('input[type="password"]')
            if await pwd_input.count() > 0:
                await pwd_input.fill(password)
                await page.click('button:has-text("Next"), button:has-text("下一步")')
                await page.wait_for_timeout(2000)
                await self._handle_2fa_if_needed(page, old_secret, log_callback)

            # 查找 Authenticator app 选项
            _log(f"[Security] 查找 Authenticator 选项", log_callback)

            # 点击 Authenticator app
            auth_selectors = [
                'text="Authenticator app"',
                'text="身份验证器应用"',
                'text="Google Authenticator"',
                '[data-identifier="authenticator"]',
            ]

            clicked = False
            for selector in auth_selectors:
                try:
                    elem = page.locator(selector)
                    if await elem.count() > 0:
                        await elem.first.click()
                        clicked = True
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

            if not clicked:
                _log(f"[Security] 未找到 Authenticator 选项", log_callback)
                return False, "", "未找到 Authenticator 选项"

            # 点击更改/设置按钮
            change_selectors = [
                'text="Change"',
                'text="更改"',
                'text="Set up"',
                'text="设置"',
                'button:has-text("Change")',
                'button:has-text("更改")',
            ]

            for selector in change_selectors:
                try:
                    elem = page.locator(selector)
                    if await elem.count() > 0:
                        await elem.first.click()
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

            # 点击 "Can't scan it?" 或类似链接获取密钥
            cant_scan_selectors = [
                'text="Can\'t scan it"',
                'text="无法扫描"',
                'text="Enter a setup key"',
                'text="输入设置密钥"',
            ]

            for selector in cant_scan_selectors:
                try:
                    elem = page.locator(selector)
                    if await elem.count() > 0:
                        await elem.first.click()
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

            # 提取新密钥
            page_text = await page.content()

            # 查找 secret key 模式
            secret_patterns = [
                r"[A-Z2-7]{16,32}",  # Base32 编码的密钥
            ]

            new_secret = ""
            for pattern in secret_patterns:
                matches = re.findall(pattern, page_text)
                for match in matches:
                    # 验证是否是有效的 TOTP secret
                    if len(match) >= 16 and match.isalnum():
                        try:
                            # 尝试生成验证码来验证密钥有效性
                            test_totp = pyotp.TOTP(match)
                            test_totp.now()
                            new_secret = match
                            break
                        except Exception:
                            continue
                if new_secret:
                    break

            if not new_secret:
                _log(f"[Security] 未能提取新密钥", log_callback)
                return False, "", "未能提取新密钥"

            _log(f"[Security] 获取到新密钥: {new_secret[:8]}...", log_callback)

            # 输入验证码确认
            new_code = self.generate_2fa_code(new_secret)
            if new_code:
                code_input = page.locator(
                    'input[type="tel"], input[type="text"][maxlength="6"]'
                )
                if await code_input.count() > 0:
                    await code_input.fill(new_code)
                    await page.wait_for_timeout(500)

                    # 点击验证/下一步按钮
                    verify_selectors = [
                        'button:has-text("Verify")',
                        'button:has-text("验证")',
                        'button:has-text("Next")',
                        'button:has-text("下一步")',
                        'button:has-text("Done")',
                        'button:has-text("完成")',
                    ]

                    for selector in verify_selectors:
                        try:
                            elem = page.locator(selector)
                            if await elem.count() > 0:
                                await elem.first.click()
                                await page.wait_for_timeout(2000)
                                break
                        except Exception:
                            continue

            _log(f"[Security] 2FA 修改完成", log_callback)
            return True, new_secret, "成功"

        except Exception as e:
            _log(f"[Security] 修改 2FA 失败: {e}", log_callback)
            return False, "", str(e)

    async def _change_recovery_email_async(
        self,
        page,
        account_info: Dict[str, str],
        new_recovery_email: str,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, str]:
        """
        修改辅助邮箱
        返回: (成功, 消息)
        """
        email = account_info.get("email", "")
        password = account_info.get("password", "")

        _log(
            f"[Security] 开始修改辅助邮箱: {email} -> {new_recovery_email}",
            log_callback,
        )

        try:
            # 确保登录
            if not await self._ensure_logged_in(page, account_info, log_callback):
                return False, "登录失败"

            # 导航到辅助邮箱设置页面
            await page.goto(
                "https://myaccount.google.com/recovery/email",
                wait_until="networkidle",
                timeout=30000,
            )
            await page.wait_for_timeout(2000)

            # 可能需要验证身份
            pwd_input = page.locator('input[type="password"]')
            if await pwd_input.count() > 0:
                await pwd_input.fill(password)
                await page.click('button:has-text("Next"), button:has-text("下一步")')
                await page.wait_for_timeout(2000)

            # 点击更新/添加辅助邮箱
            update_selectors = [
                'text="Add recovery email"',
                'text="添加辅助邮箱"',
                'text="Update"',
                'text="更新"',
                '[aria-label*="recovery email"]',
            ]

            for selector in update_selectors:
                try:
                    elem = page.locator(selector)
                    if await elem.count() > 0:
                        await elem.first.click()
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

            # 输入新辅助邮箱
            email_input = page.locator(
                'input[type="email"], input[name="recovery-email"]'
            )
            if await email_input.count() > 0:
                await email_input.fill(new_recovery_email)
                await page.wait_for_timeout(500)

                # 确认
                confirm_selectors = [
                    'button:has-text("Next")',
                    'button:has-text("下一步")',
                    'button:has-text("Save")',
                    'button:has-text("保存")',
                    'button:has-text("Done")',
                    'button:has-text("完成")',
                ]

                for selector in confirm_selectors:
                    try:
                        elem = page.locator(selector)
                        if await elem.count() > 0:
                            await elem.first.click()
                            await page.wait_for_timeout(2000)
                            break
                    except Exception:
                        continue

                _log(f"[Security] 辅助邮箱修改完成", log_callback)
                return True, "成功"

            return False, "未找到邮箱输入框"

        except Exception as e:
            _log(f"[Security] 修改辅助邮箱失败: {e}", log_callback)
            return False, str(e)

    async def _get_backup_codes_async(
        self,
        page,
        account_info: Dict[str, str],
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, List[str], str]:
        """
        获取备份验证码
        返回: (成功, 验证码列表, 消息)
        """
        email = account_info.get("email", "")
        password = account_info.get("password", "")
        old_secret = account_info.get("secret", "") or account_info.get(
            "2fa_secret", ""
        )

        _log(f"[Security] 开始获取备份验证码: {email}", log_callback)

        try:
            # 确保登录
            if not await self._ensure_logged_in(page, account_info, log_callback):
                return False, [], "登录失败"

            # 导航到备份验证码页面
            await page.goto(
                "https://myaccount.google.com/signinoptions/two-step-verification",
                wait_until="networkidle",
                timeout=30000,
            )
            await page.wait_for_timeout(2000)

            # 可能需要验证身份
            pwd_input = page.locator('input[type="password"]')
            if await pwd_input.count() > 0:
                await pwd_input.fill(password)
                await page.click('button:has-text("Next"), button:has-text("下一步")')
                await page.wait_for_timeout(2000)
                await self._handle_2fa_if_needed(page, old_secret, log_callback)

            # 点击 Backup codes
            backup_selectors = [
                'text="Backup codes"',
                'text="备份验证码"',
                'text="备用验证码"',
                '[data-identifier="backup-codes"]',
            ]

            for selector in backup_selectors:
                try:
                    elem = page.locator(selector)
                    if await elem.count() > 0:
                        await elem.first.click()
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

            # 点击获取新验证码
            get_codes_selectors = [
                'text="Get backup codes"',
                'text="获取备份验证码"',
                'text="Get new codes"',
                'text="获取新验证码"',
                'button:has-text("Get")',
            ]

            for selector in get_codes_selectors:
                try:
                    elem = page.locator(selector)
                    if await elem.count() > 0:
                        await elem.first.click()
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

            # 提取验证码
            page_text = await page.inner_text("body")

            # 备份验证码通常是 8 位数字
            code_pattern = r"\b\d{4}\s?\d{4}\b|\b\d{8}\b"
            matches = re.findall(code_pattern, page_text)

            codes = []
            for match in matches:
                code = match.replace(" ", "")
                if len(code) == 8 and code.isdigit():
                    codes.append(code)

            # 去重
            codes = list(dict.fromkeys(codes))

            if codes:
                _log(f"[Security] 获取到 {len(codes)} 个备份验证码", log_callback)
                return True, codes, "成功"

            return False, [], "未能提取备份验证码"

        except Exception as e:
            _log(f"[Security] 获取备份验证码失败: {e}", log_callback)
            return False, [], str(e)

    # -------------------------------------------
    # 同步包装方法（供 GUI 调用）
    # -------------------------------------------
    def change_2fa_secret(
        self,
        email: str,
        account_info: Dict[str, str],
        log_callback: Optional[Callable[[str], None]] = None,
        close_browser: bool = True,
    ) -> Tuple[bool, str, str]:
        """
        修改 2FA 密钥（同步方法）
        返回: (成功, 新密钥, 消息)
        """
        launch_info: Optional[LaunchInfo] = None
        playwright = None

        try:
            # 启动浏览器
            _log(f"[Security] 启动浏览器: {email}", log_callback)
            launch_info = self.proc.launch_by_email(email)

            async def _runner():
                nonlocal playwright
                pw, browser, page = await self.proc._connect_page(
                    launch_info.cdp_endpoint
                )
                playwright = pw
                return await self._change_2fa_secret_async(
                    page, account_info, log_callback
                )

            result = asyncio.run(_runner())
            return result

        except Exception as e:
            _log(f"[Security] 错误: {e}", log_callback)
            return False, "", str(e)
        finally:
            if playwright:
                try:
                    asyncio.run(playwright.stop())
                except Exception:
                    pass
            if close_browser and launch_info:
                try:
                    self.proc.close_by_email(email)
                except Exception:
                    pass

    def change_recovery_email(
        self,
        email: str,
        account_info: Dict[str, str],
        new_recovery_email: str,
        log_callback: Optional[Callable[[str], None]] = None,
        close_browser: bool = True,
    ) -> Tuple[bool, str]:
        """
        修改辅助邮箱（同步方法）
        返回: (成功, 消息)
        """
        launch_info: Optional[LaunchInfo] = None
        playwright = None

        try:
            _log(f"[Security] 启动浏览器: {email}", log_callback)
            launch_info = self.proc.launch_by_email(email)

            async def _runner():
                nonlocal playwright
                pw, browser, page = await self.proc._connect_page(
                    launch_info.cdp_endpoint
                )
                playwright = pw
                return await self._change_recovery_email_async(
                    page, account_info, new_recovery_email, log_callback
                )

            result = asyncio.run(_runner())
            return result

        except Exception as e:
            _log(f"[Security] 错误: {e}", log_callback)
            return False, str(e)
        finally:
            if playwright:
                try:
                    asyncio.run(playwright.stop())
                except Exception:
                    pass
            if close_browser and launch_info:
                try:
                    self.proc.close_by_email(email)
                except Exception:
                    pass

    def get_backup_codes(
        self,
        email: str,
        account_info: Dict[str, str],
        log_callback: Optional[Callable[[str], None]] = None,
        close_browser: bool = True,
    ) -> Tuple[bool, List[str], str]:
        """
        获取备份验证码（同步方法）
        返回: (成功, 验证码列表, 消息)
        """
        launch_info: Optional[LaunchInfo] = None
        playwright = None

        try:
            _log(f"[Security] 启动浏览器: {email}", log_callback)
            launch_info = self.proc.launch_by_email(email)

            async def _runner():
                nonlocal playwright
                pw, browser, page = await self.proc._connect_page(
                    launch_info.cdp_endpoint
                )
                playwright = pw
                return await self._get_backup_codes_async(
                    page, account_info, log_callback
                )

            result = asyncio.run(_runner())
            return result

        except Exception as e:
            _log(f"[Security] 错误: {e}", log_callback)
            return False, [], str(e)
        finally:
            if playwright:
                try:
                    asyncio.run(playwright.stop())
                except Exception:
                    pass
            if close_browser and launch_info:
                try:
                    self.proc.close_by_email(email)
                except Exception:
                    pass

    def one_click_security_update(
        self,
        email: str,
        account_info: Dict[str, str],
        new_recovery_email: Optional[str] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        一键修改全部安全设置
        返回: {"2fa": (ok, new_secret, msg), "recovery": (ok, msg), "backup": (ok, codes, msg)}
        """
        launch_info: Optional[LaunchInfo] = None
        playwright = None

        result = {
            "2fa": (False, "", "未执行"),
            "recovery": (False, "未执行"),
            "backup": (False, [], "未执行"),
        }

        try:
            _log(f"[Security] 一键修改: {email}", log_callback)
            launch_info = self.proc.launch_by_email(email)

            async def _runner():
                nonlocal playwright
                pw, browser, page = await self.proc._connect_page(
                    launch_info.cdp_endpoint
                )
                playwright = pw

                # 1. 修改 2FA
                _log(f"[Security] 步骤 1/3: 修改 2FA", log_callback)
                result["2fa"] = await self._change_2fa_secret_async(
                    page, account_info, log_callback
                )

                # 如果 2FA 修改成功，更新 account_info 中的密钥
                if result["2fa"][0] and result["2fa"][1]:
                    account_info["secret"] = result["2fa"][1]
                    account_info["2fa_secret"] = result["2fa"][1]

                # 2. 修改辅助邮箱
                if new_recovery_email:
                    _log(f"[Security] 步骤 2/3: 修改辅助邮箱", log_callback)
                    result["recovery"] = await self._change_recovery_email_async(
                        page, account_info, new_recovery_email, log_callback
                    )
                else:
                    result["recovery"] = (True, "跳过")

                # 3. 获取备份验证码
                _log(f"[Security] 步骤 3/3: 获取备份验证码", log_callback)
                result["backup"] = await self._get_backup_codes_async(
                    page, account_info, log_callback
                )

                return result

            asyncio.run(_runner())
            return result

        except Exception as e:
            _log(f"[Security] 一键修改错误: {e}", log_callback)
            return result
        finally:
            if playwright:
                try:
                    asyncio.run(playwright.stop())
                except Exception:
                    pass
            if launch_info:
                try:
                    self.proc.close_by_email(email)
                except Exception:
                    pass

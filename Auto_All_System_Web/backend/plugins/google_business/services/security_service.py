"""
Google 账号安全设置服务

迁移自: 2dev/geek/geek_security.py
功能: 修改 2FA 密钥、修改辅助邮箱、获取备份验证码
"""

import asyncio
import logging
import pyotp
from typing import Dict, Any, Optional, Tuple, List
from playwright.async_api import Page

from apps.integrations.browser_base import get_browser_manager, BrowserType

logger = logging.getLogger(__name__)


class GoogleSecurityService:
    """
    Google 账号安全设置服务

    功能:
    - 修改 2FA 密钥
    - 修改辅助邮箱
    - 获取备份验证码
    - 一键修改全部安全设置
    """

    SECURITY_URL = "https://myaccount.google.com/security"
    TWO_STEP_URL = "https://myaccount.google.com/signinoptions/two-step-verification"
    RECOVERY_EMAIL_URL = "https://myaccount.google.com/recovery/email"

    def __init__(self, browser_type: Optional[BrowserType] = None):
        self.browser_manager = get_browser_manager()
        self.browser_type = browser_type

    async def change_2fa_secret(
        self,
        page: Page,
        account: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[str]]:
        """
        修改 2FA 密钥

        Args:
            page: Playwright 页面对象
            account: 账号信息

        Returns:
            (success, message, new_secret)
        """
        email = account.get("email", "")
        current_secret = account.get("totp_secret", "")

        try:
            # 1. 导航到两步验证页面
            await page.goto(self.TWO_STEP_URL, wait_until="networkidle")
            await asyncio.sleep(2)

            # 2. 可能需要重新验证密码
            password_input = page.locator('input[type="password"]')
            if await password_input.is_visible():
                await password_input.fill(account.get("password", ""))
                await page.keyboard.press("Enter")
                await asyncio.sleep(3)

            # 3. 点击 Authenticator app 选项
            auth_app_link = page.locator("text=Authenticator app").first
            if await auth_app_link.is_visible():
                await auth_app_link.click()
                await asyncio.sleep(2)

            # 4. 点击更改手机/Change phone 或 设置
            change_btn = page.locator(
                'button:has-text("Change phone"), button:has-text("更改手机")'
            ).first
            if await change_btn.is_visible():
                await change_btn.click()
                await asyncio.sleep(2)

            # 5. 选择 "Can't scan it?" 获取密钥
            cant_scan = page.locator("text=Can't scan it, text=无法扫描").first
            if await cant_scan.is_visible():
                await cant_scan.click()
                await asyncio.sleep(2)

            # 6. 提取新的密钥
            secret_element = page.locator("[data-secret], .secret-key, code").first
            if await secret_element.is_visible():
                new_secret = await secret_element.text_content()
                new_secret = new_secret.replace(" ", "").strip()

                # 7. 使用新密钥生成验证码并验证
                totp = pyotp.TOTP(new_secret)
                code = totp.now()

                code_input = page.locator(
                    'input[type="tel"], input[name="totpPin"]'
                ).first
                if await code_input.is_visible():
                    await code_input.fill(code)
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(3)

                # 8. 检查是否成功
                success_indicator = page.locator(
                    "text=Done, text=完成, text=Verified"
                ).first
                if await success_indicator.is_visible():
                    logger.info(f"2FA secret changed for {email}")
                    return True, "2FA 密钥修改成功", new_secret

            return False, "未能获取新的 2FA 密钥", None

        except Exception as e:
            logger.exception(f"Failed to change 2FA for {email}")
            return False, str(e), None

    async def change_recovery_email(
        self,
        page: Page,
        account: Dict[str, Any],
        new_email: str,
    ) -> Tuple[bool, str]:
        """
        修改辅助邮箱

        Args:
            page: Playwright 页面对象
            account: 账号信息
            new_email: 新的辅助邮箱

        Returns:
            (success, message)
        """
        email = account.get("email", "")

        try:
            # 1. 导航到辅助邮箱设置页面
            await page.goto(self.RECOVERY_EMAIL_URL, wait_until="networkidle")
            await asyncio.sleep(2)

            # 2. 可能需要重新验证密码
            password_input = page.locator('input[type="password"]')
            if await password_input.is_visible():
                await password_input.fill(account.get("password", ""))
                await page.keyboard.press("Enter")
                await asyncio.sleep(3)

            # 3. 可能需要 2FA 验证
            totp_secret = account.get("totp_secret", "")
            if totp_secret:
                totp_input = page.locator(
                    'input[type="tel"], input[name="totpPin"]'
                ).first
                if await totp_input.is_visible():
                    totp = pyotp.TOTP(totp_secret)
                    await totp_input.fill(totp.now())
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(3)

            # 4. 点击编辑/添加辅助邮箱
            edit_btn = page.locator(
                'button:has-text("Add"), button:has-text("Edit"), button:has-text("添加"), button:has-text("编辑")'
            ).first
            if await edit_btn.is_visible():
                await edit_btn.click()
                await asyncio.sleep(2)

            # 5. 输入新邮箱
            email_input = page.locator('input[type="email"]').first
            if await email_input.is_visible():
                await email_input.clear()
                await email_input.fill(new_email)
                await page.keyboard.press("Enter")
                await asyncio.sleep(3)

            # 6. 检查是否需要验证新邮箱
            # (可能需要到新邮箱收验证码)

            logger.info(f"Recovery email change initiated for {email}")
            return True, f"辅助邮箱已更改为 {new_email}"

        except Exception as e:
            logger.exception(f"Failed to change recovery email for {email}")
            return False, str(e)

    async def get_backup_codes(
        self,
        page: Page,
        account: Dict[str, Any],
    ) -> Tuple[bool, str, List[str]]:
        """
        获取备份验证码

        Args:
            page: Playwright 页面对象
            account: 账号信息

        Returns:
            (success, message, codes)
        """
        email = account.get("email", "")

        try:
            # 1. 导航到两步验证页面
            await page.goto(self.TWO_STEP_URL, wait_until="networkidle")
            await asyncio.sleep(2)

            # 2. 可能需要重新验证
            password_input = page.locator('input[type="password"]')
            if await password_input.is_visible():
                await password_input.fill(account.get("password", ""))
                await page.keyboard.press("Enter")
                await asyncio.sleep(3)

            # 3. 点击 Backup codes
            backup_link = page.locator("text=Backup codes, text=备用验证码").first
            if await backup_link.is_visible():
                await backup_link.click()
                await asyncio.sleep(2)

            # 4. 点击 "Get new codes" 或 "Show codes"
            get_codes_btn = page.locator(
                'button:has-text("Get new codes"), button:has-text("Show codes"), button:has-text("获取新验证码")'
            ).first
            if await get_codes_btn.is_visible():
                await get_codes_btn.click()
                await asyncio.sleep(2)

            # 5. 提取备份验证码
            codes = []
            code_elements = page.locator(
                '.backup-code, [data-backup-code], li:has-text(" ")'
            ).all()
            for elem in await code_elements:
                code = await elem.text_content()
                code = code.strip().replace(" ", "")
                if code and len(code) == 8 and code.isdigit():
                    codes.append(code)

            if codes:
                logger.info(f"Got {len(codes)} backup codes for {email}")
                return True, f"获取到 {len(codes)} 个备份验证码", codes

            return False, "未能获取备份验证码", []

        except Exception as e:
            logger.exception(f"Failed to get backup codes for {email}")
            return False, str(e), []

    async def one_click_security_update(
        self,
        page: Page,
        account: Dict[str, Any],
        new_recovery_email: Optional[str] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        一键修改全部安全设置

        Args:
            page: Playwright 页面对象
            account: 账号信息
            new_recovery_email: 新的辅助邮箱 (可选)

        Returns:
            (success, message, data)
            data 包含: new_2fa_secret, backup_codes, new_recovery_email
        """
        email = account.get("email", "")
        result_data = {}
        errors = []

        # 1. 修改 2FA 密钥
        ok, msg, new_secret = await self.change_2fa_secret(page, account)
        if ok:
            result_data["new_2fa_secret"] = new_secret
            # 更新 account 中的密钥以便后续操作使用
            account["totp_secret"] = new_secret
        else:
            errors.append(f"2FA: {msg}")

        # 2. 获取备份验证码
        ok, msg, codes = await self.get_backup_codes(page, account)
        if ok:
            result_data["backup_codes"] = codes
        else:
            errors.append(f"Backup codes: {msg}")

        # 3. 修改辅助邮箱 (如果提供)
        if new_recovery_email:
            ok, msg = await self.change_recovery_email(
                page, account, new_recovery_email
            )
            if ok:
                result_data["new_recovery_email"] = new_recovery_email
            else:
                errors.append(f"Recovery email: {msg}")

        # 汇总结果
        if not errors:
            return True, "所有安全设置已更新", result_data
        elif result_data:
            return True, f"部分成功，错误: {'; '.join(errors)}", result_data
        else:
            return False, "; ".join(errors), result_data

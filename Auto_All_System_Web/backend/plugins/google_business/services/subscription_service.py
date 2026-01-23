"""
订阅状态验证服务

迁移自: 2dev/geek/geek_process.py 中的 verify_subscription_status
功能: 检测账号订阅状态并截图
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from playwright.async_api import Page

logger = logging.getLogger(__name__)


class SubscriptionStatus:
    """订阅状态枚举"""

    SUBSCRIBED = "subscribed"  # 已订阅
    VERIFIED = "verified"  # 已验证学生身份，待绑卡
    LINK_READY = "link_ready"  # SheerLink 已准备好
    INELIGIBLE = "ineligible"  # 无资格
    PENDING_CHECK = "pending_check"  # 待检测
    UNKNOWN = "unknown"  # 未知状态


class SubscriptionVerifyService:
    """
    订阅状态验证服务

    功能:
    - 检测账号订阅状态
    - 截图保存
    - 点击订阅按钮
    """

    GOOGLE_ONE_URL = "https://one.google.com/about/plans"
    STUDENT_PLAN_URL = "https://one.google.com/about/plans/ai-premium/student"

    SCREENSHOT_DIR = "screenshots"

    def __init__(self):
        # 确保截图目录存在
        os.makedirs(self.SCREENSHOT_DIR, exist_ok=True)

    async def verify_subscription_status(
        self,
        page: Page,
        account: Dict[str, Any],
        take_screenshot: bool = True,
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        验证订阅状态

        Args:
            page: Playwright 页面对象
            account: 账号信息
            take_screenshot: 是否截图

        Returns:
            (success, status_info, screenshot_path)
        """
        email = account.get("email", "")

        try:
            # 1. 导航到 Google One 页面
            await page.goto(self.STUDENT_PLAN_URL, wait_until="networkidle")
            await asyncio.sleep(3)

            # 2. 检测订阅状态
            status = await self._detect_status(page)

            # 3. 截图
            screenshot_path = None
            if take_screenshot:
                screenshot_path = await self._take_screenshot(page, email, status)

            status_info = {
                "status": status,
                "email": email,
                "url": page.url,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(f"Subscription status for {email}: {status}")
            return True, status_info, screenshot_path

        except Exception as e:
            logger.exception(f"Failed to verify subscription for {email}")
            return False, {"error": str(e)}, None

    async def _detect_status(self, page: Page) -> str:
        """检测当前页面的订阅状态"""

        # 检测已订阅
        subscribed_indicators = [
            "text=You're subscribed",
            "text=已订阅",
            "text=Current plan",
            "text=当前方案",
        ]
        for indicator in subscribed_indicators:
            if await page.locator(indicator).first.is_visible():
                return SubscriptionStatus.SUBSCRIBED

        # 检测无资格 (通过 CSS 类)
        ineligible_indicators = [
            ".ineligible",
            "text=not eligible",
            "text=不符合资格",
            "text=Verification failed",
        ]
        for indicator in ineligible_indicators:
            if await page.locator(indicator).first.is_visible():
                return SubscriptionStatus.INELIGIBLE

        # 检测 SheerLink 准备好
        link_ready_indicators = [
            "text=Verify your student status",
            "text=验证学生身份",
            'a[href*="sheerid"]',
        ]
        for indicator in link_ready_indicators:
            if await page.locator(indicator).first.is_visible():
                return SubscriptionStatus.LINK_READY

        # 检测已验证待绑卡
        verified_indicators = [
            "text=Student verified",
            "text=已验证学生身份",
            'button:has-text("Subscribe")',
            'button:has-text("订阅")',
        ]
        for indicator in verified_indicators:
            if await page.locator(indicator).first.is_visible():
                return SubscriptionStatus.VERIFIED

        return SubscriptionStatus.UNKNOWN

    async def _take_screenshot(self, page: Page, email: str, status: str) -> str:
        """截图保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 清理邮箱中的特殊字符
        safe_email = email.replace("@", "_at_").replace(".", "_")
        filename = f"{safe_email}_{status}_{timestamp}.png"
        filepath = os.path.join(self.SCREENSHOT_DIR, filename)

        await page.screenshot(path=filepath, full_page=True)
        logger.info(f"Screenshot saved: {filepath}")

        return filepath

    async def click_subscribe_button(
        self,
        page: Page,
        account: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """
        点击订阅按钮

        Args:
            page: Playwright 页面对象
            account: 账号信息

        Returns:
            (success, message)
        """
        email = account.get("email", "")

        try:
            # 查找订阅按钮
            subscribe_btn = page.locator(
                'button:has-text("Subscribe"), button:has-text("订阅"), button:has-text("Get started")'
            ).first

            if not await subscribe_btn.is_visible():
                return False, "未找到订阅按钮"

            await subscribe_btn.click()
            await asyncio.sleep(3)

            # 检查是否出现确认对话框
            confirm_btn = page.locator(
                'button:has-text("Confirm"), button:has-text("确认")'
            ).first
            if await confirm_btn.is_visible():
                await confirm_btn.click()
                await asyncio.sleep(3)

            logger.info(f"Subscribe button clicked for {email}")
            return True, "已点击订阅按钮"

        except Exception as e:
            logger.exception(f"Failed to click subscribe for {email}")
            return False, str(e)

    async def verify_result(
        self,
        page: Page,
        account: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[str]]:
        """
        验证订阅结果并截图

        Args:
            page: Playwright 页面对象
            account: 账号信息

        Returns:
            (success, status, screenshot_path)
        """
        email = account.get("email", "")

        try:
            await asyncio.sleep(3)

            # 检测最终状态
            status = await self._detect_status(page)

            # 截图
            screenshot_path = await self._take_screenshot(
                page, email, f"result_{status}"
            )

            success = status == SubscriptionStatus.SUBSCRIBED
            return success, status, screenshot_path

        except Exception as e:
            logger.exception(f"Failed to verify result for {email}")
            return False, SubscriptionStatus.UNKNOWN, None

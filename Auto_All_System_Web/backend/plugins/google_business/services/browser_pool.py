"""
浏览器资源池管理
提供浏览器实例的分配、管理和回收
支持多种浏览器类型 (比特浏览器 / GeekezBrowser)
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from apps.integrations.browser_base import (
    get_browser_manager,
    BrowserType,
    LaunchInfo,
)

logger = logging.getLogger(__name__)


class BrowserInstance:
    """浏览器实例包装类"""

    def __init__(
        self,
        browser_id: str,
        ws_endpoint: str,
        browser_type: BrowserType = BrowserType.BITBROWSER,
    ):
        self.browser_id = browser_id
        self.ws_endpoint = ws_endpoint
        self.browser_type = browser_type
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.created_at = timezone.now()
        self.last_used_at = timezone.now()
        self.is_busy = False
        self.task_id = None

    async def connect(self):
        """连接到浏览器"""
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.connect_over_cdp(self.ws_endpoint)
            self.context = self.browser.contexts[0]
            self.page = (
                self.context.pages[0]
                if self.context.pages
                else await self.context.new_page()
            )
            logger.info(f"Browser {self.browser_id} connected")

    async def disconnect(self):
        """断开浏览器连接"""
        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                logger.error(f"Error closing browser {self.browser_id}: {e}")
            finally:
                self.browser = None
                self.context = None
                self.page = None
                logger.info(f"Browser {self.browser_id} disconnected")

    def mark_busy(self, task_id: str):
        """标记为忙碌状态"""
        self.is_busy = True
        self.task_id = task_id
        self.last_used_at = timezone.now()

    def mark_idle(self):
        """标记为空闲状态"""
        self.is_busy = False
        self.task_id = None
        self.last_used_at = timezone.now()

    def is_expired(self, max_age_minutes: int = 60) -> bool:
        """检查是否超时（超过指定时间未使用）"""
        age = timezone.now() - self.last_used_at
        return age > timedelta(minutes=max_age_minutes)


class BrowserPool:
    """
    浏览器资源池

    管理多个浏览器实例，提供分配、回收和清理功能
    支持并发任务的浏览器资源管理
    支持多种浏览器类型 (比特浏览器 / GeekezBrowser)
    """

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化资源池"""
        if self._initialized:
            return

        self.pool: Dict[str, BrowserInstance] = {}
        self.logger = logging.getLogger("plugin.google_business.browser_pool")
        self.max_pool_size = 10  # 最大浏览器实例数
        self.max_browser_age = 60  # 浏览器最大闲置时间（分钟）
        self.browser_manager = get_browser_manager()  # 统一浏览器管理器
        self._initialized = True

        self.logger.info("Browser pool initialized")

    def get_available_browsers(self) -> List[Dict[str, Any]]:
        """
        获取可用的浏览器类型列表

        Returns:
            List[Dict]: 浏览器类型及其在线状态
        """
        return self.browser_manager.list_available()

    async def acquire(
        self,
        browser_id: str,
        ws_endpoint: str,
        task_id: str,
        browser_type: BrowserType = BrowserType.BITBROWSER,
        force_new: bool = False,
    ) -> Optional[BrowserInstance]:
        """
        获取浏览器实例

        Args:
            browser_id: BitBrowser的浏览器ID
            ws_endpoint: WebSocket连接端点
            task_id: 任务ID
            force_new: 是否强制创建新实例

        Returns:
            BrowserInstance: 浏览器实例，失败返回None
        """
        async with self._lock:
            try:
                # 检查是否已有该浏览器的实例
                if browser_id in self.pool and not force_new:
                    instance = self.pool[browser_id]

                    # 如果实例正忙，返回None
                    if instance.is_busy:
                        self.logger.warning(
                            f"Browser {browser_id} is busy with task {instance.task_id}"
                        )
                        return None

                    # 检查实例是否过期
                    if instance.is_expired(self.max_browser_age):
                        self.logger.info(f"Browser {browser_id} expired, recreating...")
                        await self.release(browser_id)
                    else:
                        # 复用现有实例
                        instance.mark_busy(task_id)
                        self.logger.info(
                            f"Reusing browser {browser_id} for task {task_id}"
                        )
                        return instance

                # 检查资源池是否已满
                if len(self.pool) >= self.max_pool_size:
                    self.logger.warning(
                        f"Browser pool is full ({len(self.pool)}/{self.max_pool_size})"
                    )
                    # 尝试清理过期实例
                    await self._cleanup_expired()

                    # 如果仍然满，返回None
                    if len(self.pool) >= self.max_pool_size:
                        self.logger.error(
                            "Browser pool is full and no expired instances to clean"
                        )
                        return None

                # 创建新实例
                instance = BrowserInstance(browser_id, ws_endpoint, browser_type)
                await instance.connect()
                instance.mark_busy(task_id)

                self.pool[browser_id] = instance
                self.logger.info(
                    f"Created new browser instance {browser_id} for task {task_id} (pool size: {len(self.pool)})"
                )

                return instance

            except Exception as e:
                self.logger.error(
                    f"Error acquiring browser {browser_id}: {e}", exc_info=True
                )
                return None

    async def release(self, browser_id: str, close: bool = False) -> bool:
        """
        释放浏览器实例

        Args:
            browser_id: 浏览器ID
            close: 是否关闭并移除实例（默认只标记为空闲）

        Returns:
            bool: 是否成功
        """
        async with self._lock:
            try:
                if browser_id not in self.pool:
                    self.logger.warning(f"Browser {browser_id} not in pool")
                    return False

                instance = self.pool[browser_id]

                if close:
                    # 关闭并移除
                    await instance.disconnect()
                    del self.pool[browser_id]
                    self.logger.info(
                        f"Closed and removed browser {browser_id} from pool (pool size: {len(self.pool)})"
                    )
                else:
                    # 只标记为空闲
                    instance.mark_idle()
                    self.logger.info(f"Released browser {browser_id} (marked as idle)")

                return True

            except Exception as e:
                self.logger.error(
                    f"Error releasing browser {browser_id}: {e}", exc_info=True
                )
                return False

    async def get_instance(self, browser_id: str) -> Optional[BrowserInstance]:
        """
        获取浏览器实例（不改变状态）

        Args:
            browser_id: 浏览器ID

        Returns:
            BrowserInstance: 浏览器实例
        """
        return self.pool.get(browser_id)

    async def _cleanup_expired(self):
        """清理过期的浏览器实例"""
        expired_ids = []

        for browser_id, instance in self.pool.items():
            if not instance.is_busy and instance.is_expired(self.max_browser_age):
                expired_ids.append(browser_id)

        for browser_id in expired_ids:
            await self.release(browser_id, close=True)
            self.logger.info(f"Cleaned up expired browser {browser_id}")

    async def cleanup_all(self):
        """清理所有浏览器实例"""
        async with self._lock:
            browser_ids = list(self.pool.keys())

            for browser_id in browser_ids:
                await self.release(browser_id, close=True)

            self.logger.info("Cleaned up all browsers from pool")

    def get_pool_stats(self) -> Dict[str, Any]:
        """
        获取资源池统计信息

        Returns:
            Dict: 统计数据
        """
        total = len(self.pool)
        busy = sum(1 for instance in self.pool.values() if instance.is_busy)
        idle = total - busy

        return {
            "total": total,
            "busy": busy,
            "idle": idle,
            "max_size": self.max_pool_size,
            "utilization": (busy / self.max_pool_size * 100)
            if self.max_pool_size > 0
            else 0,
            "available_browsers": self.get_available_browsers(),
            "browsers": [
                {
                    "browser_id": browser_id,
                    "browser_type": instance.browser_type.value,
                    "is_busy": instance.is_busy,
                    "task_id": instance.task_id,
                    "created_at": instance.created_at.isoformat(),
                    "last_used_at": instance.last_used_at.isoformat(),
                }
                for browser_id, instance in self.pool.items()
            ],
        }

    async def acquire_by_email(
        self,
        email: str,
        task_id: str,
        account_info: Optional[Dict[str, Any]] = None,
        proxy: Optional[str] = None,
        browser_type: Optional[BrowserType] = None,
    ) -> Optional[BrowserInstance]:
        """
        通过邮箱获取浏览器实例 (便捷方法)

        自动处理:
        1. 创建/更新 Profile
        2. 启动浏览器
        3. 获取 BrowserInstance

        Args:
            email: 账号邮箱 (用作 Profile 名称)
            task_id: 任务ID
            account_info: 账号信息 (可选)
            proxy: 代理地址 (可选)
            browser_type: 浏览器类型 (可选, 默认使用系统默认)

        Returns:
            BrowserInstance: 浏览器实例
        """
        try:
            # 使用指定类型或默认类型
            bt = browser_type or self.browser_manager._default_type
            api = self.browser_manager.get_api(bt)

            # 1. 创建/更新 Profile
            profile = api.create_or_update_profile(
                name=email, proxy=proxy, metadata={"account": account_info or {}}
            )

            # 2. 启动浏览器
            launch_info = api.launch_profile(profile.id)
            if not launch_info:
                self.logger.error(f"Failed to launch browser for {email}")
                return None

            # 3. 获取 BrowserInstance
            ws_endpoint = launch_info.ws_endpoint or launch_info.cdp_endpoint
            return await self.acquire(
                browser_id=profile.id,
                ws_endpoint=ws_endpoint,
                task_id=task_id,
                browser_type=bt,
            )

        except Exception as e:
            self.logger.error(
                f"Error acquiring browser for {email}: {e}", exc_info=True
            )
            return None

    async def release_by_email(
        self,
        email: str,
        browser_type: Optional[BrowserType] = None,
        close: bool = False,
    ) -> bool:
        """
        通过邮箱释放浏览器实例

        Args:
            email: 账号邮箱
            browser_type: 浏览器类型
            close: 是否关闭浏览器

        Returns:
            bool: 是否成功
        """
        try:
            bt = browser_type or self.browser_manager._default_type
            api = self.browser_manager.get_api(bt)

            # 获取 Profile ID
            profile = api.get_profile_by_name(email)
            if not profile:
                self.logger.warning(f"Profile not found for {email}")
                return False

            # 释放 BrowserInstance
            result = await self.release(profile.id, close=close)

            # 如果需要关闭，也关闭浏览器
            if close:
                api.close_profile(profile.id)

            return result

        except Exception as e:
            self.logger.error(
                f"Error releasing browser for {email}: {e}", exc_info=True
            )
            return False


# 全局浏览器资源池实例
browser_pool = BrowserPool()

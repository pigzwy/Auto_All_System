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
        self._playwright = None
        self.created_at = timezone.now()
        self.last_used_at = timezone.now()
        self.is_busy = False
        self.task_id = None

    async def connect(self):
        """连接到浏览器"""
        if not self.browser:
            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.connect_over_cdp(
                self.ws_endpoint
            )
            browser = self.browser
            assert browser is not None
            # connect_over_cdp 可能返回 0 个 contexts；做兼容兜底
            self.context = (
                browser.contexts[0] if browser.contexts else await browser.new_context()
            )
            context = self.context
            assert context is not None
            self.page = (
                context.pages[0] if context.pages else await context.new_page()
            )
            logger.info(f"Browser {self.browser_id} connected")

    async def disconnect(self):
        """断开浏览器连接"""
        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                logger.error(f"Error closing browser {self.browser_id}: {e}")
            try:
                if self._playwright is not None:
                    await self._playwright.stop()
            except Exception:
                pass
            finally:
                self.browser = None
                self.context = None
                self.page = None
                self._playwright = None
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

    async def release(
        self,
        browser_id: str,
        close: bool = False,
        browser_type: Optional[BrowserType] = None,
    ) -> bool:
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
                    if close:
                        # 即使实例不在池中，也尝试关闭外部 profile，避免环境残留。
                        try:
                            bt = browser_type or self.browser_manager._default_type
                            api = self.browser_manager.get_api(bt)
                            closed = bool(api.close_profile(str(browser_id)))
                            if closed:
                                self.logger.info(
                                    f"Browser {browser_id} not in pool, but profile closed directly"
                                )
                            else:
                                self.logger.warning(
                                    f"Browser {browser_id} not in pool and direct close_profile failed"
                                )
                            return closed
                        except Exception as e:
                            self.logger.warning(
                                f"Browser {browser_id} not in pool and direct close_profile raised error: {e}",
                                exc_info=True,
                            )
                            return False

                    self.logger.warning(f"Browser {browser_id} not in pool")
                    return False

                instance = self.pool[browser_id]
                profile_closed = True

                if close:
                    # 关闭并移除
                    await instance.disconnect()
                    del self.pool[browser_id]

                    # 释放 Playwright 连接后，额外关闭外部浏览器环境（BitBrowser/Geekez Profile）
                    # 否则会出现“任务结束但环境仍在运行”的现象。
                    try:
                        api = self.browser_manager.get_api(
                            instance.browser_type
                            if instance.browser_type
                            else (browser_type or self.browser_manager._default_type)
                        )
                        profile_closed = bool(api.close_profile(str(browser_id)))
                        if not profile_closed:
                            self.logger.warning(
                                f"Failed to close browser profile {browser_id} after disconnect"
                            )
                    except Exception as e:
                        profile_closed = False
                        self.logger.warning(
                            f"Error closing browser profile {browser_id}: {e}",
                            exc_info=True,
                        )

                    self.logger.info(
                        f"Closed and removed browser {browser_id} from pool (pool size: {len(self.pool)})"
                    )
                    if not profile_closed:
                        return False
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
        wait_seconds: int = 15,
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
            # 注意：不要把明文账号密码/2FA 写入浏览器 Profile 文件（host 上的 profiles.json）。
            # 这里只保留必要的非敏感信息用于备注/排查。
            meta_account: Dict[str, Any] = {"email": email}
            profile = api.create_or_update_profile(
                name=email, proxy=proxy, metadata={"account": meta_account}
            )

            # 2. 启动浏览器
            launch_info = api.launch_profile(profile.id)
            if not launch_info:
                self.logger.error(f"Failed to launch browser for {email}")
                return None

            # 3. 获取 BrowserInstance
            ws_endpoint = launch_info.ws_endpoint or launch_info.cdp_endpoint
            # 某些情况下（实例刚释放/连接抖动/资源池满）会短暂返回 None，这里做等待重试
            for i in range(max(1, int(wait_seconds))):
                inst = await self.acquire(
                    browser_id=profile.id,
                    ws_endpoint=ws_endpoint,
                    task_id=task_id,
                    browser_type=bt,
                )
                if inst and inst.page:
                    return inst
                await asyncio.sleep(1)

            self.logger.warning(
                f"Failed to acquire browser instance for {email} after {wait_seconds}s. pool_stats={self.get_pool_stats()}"
            )
            return None

        except Exception as e:
            self.logger.error(
                f"Error acquiring browser for {email}: {e}", exc_info=True
            )
            return None

    async def acquire_by_profile_id(
        self,
        profile_id: str,
        task_id: str,
        browser_type: Optional[BrowserType] = None,
        wait_seconds: int = 15,
    ) -> Optional[BrowserInstance]:
        """
        通过 Profile ID 获取浏览器实例

        Args:
            profile_id: Geekez/BitBrowser 的 Profile ID
            task_id: 任务ID
            browser_type: 浏览器类型 (可选, 默认使用系统默认)
            wait_seconds: 等待获取实例的秒数

        Returns:
            BrowserInstance: 浏览器实例
        """
        if not profile_id:
            return None

        try:
            bt = browser_type or self.browser_manager._default_type
            api = self.browser_manager.get_api(bt)

            launch_info = api.launch_profile(str(profile_id))
            if not launch_info:
                self.logger.error(f"Failed to launch browser for profile {profile_id}")
                return None

            ws_endpoint = launch_info.ws_endpoint or launch_info.cdp_endpoint
            for _ in range(max(1, int(wait_seconds))):
                inst = await self.acquire(
                    browser_id=str(profile_id),
                    ws_endpoint=ws_endpoint,
                    task_id=task_id,
                    browser_type=bt,
                )
                if inst and inst.page:
                    return inst
                await asyncio.sleep(1)

            self.logger.warning(
                f"Failed to acquire browser instance for profile {profile_id} after {wait_seconds}s. pool_stats={self.get_pool_stats()}"
            )
            return None

        except Exception as e:
            self.logger.error(
                f"Error acquiring browser for profile {profile_id}: {e}",
                exc_info=True,
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
            result = await self.release(profile.id, close=close, browser_type=bt)

            # 当实例不在池中时，release() 会返回 False；这里做兜底关闭。
            if close and not result:
                closed = api.close_profile(profile.id)
                if not closed:
                    self.logger.warning(f"Failed to close browser profile for {email}")
                return closed

            return result

        except Exception as e:
            self.logger.error(
                f"Error releasing browser for {email}: {e}", exc_info=True
            )
            return False


# 全局浏览器资源池实例
browser_pool = BrowserPool()

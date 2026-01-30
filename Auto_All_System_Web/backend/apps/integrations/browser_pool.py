"""Browser resource pool.

Centralizes:
- create/update Geekez/BitBrowser profiles
- launch profiles and get ws_endpoint/cdp_endpoint
- connect via Playwright CDP

This is shared infra (not plugin-specific).
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Optional, List

from django.utils import timezone
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from apps.integrations.browser_base import get_browser_manager, BrowserType

logger = logging.getLogger(__name__)


@dataclass
class BrowserSession:
    browser_id: str
    ws_endpoint: str
    browser_type: BrowserType
    browser: Optional[Browser] = None
    context: Optional[BrowserContext] = None
    page: Optional[Page] = None
    _pw: Any = None
    created_at: Any = None
    last_used_at: Any = None
    is_busy: bool = False
    task_id: Optional[str] = None

    async def connect(self) -> None:
        if self.browser:
            return
        self._pw = await async_playwright().start()
        self.browser = await self._pw.chromium.connect_over_cdp(self.ws_endpoint)
        browser = self.browser
        assert browser is not None

        self.context = (
            browser.contexts[0] if browser.contexts else await browser.new_context()
        )
        context = self.context
        assert context is not None

        self.page = context.pages[0] if context.pages else await context.new_page()
        logger.info(f"BrowserSession connected: {self.browser_id}")

    async def disconnect(self) -> None:
        if not self.browser:
            return
        try:
            await self.browser.close()
        except Exception as e:
            logger.warning(f"Error closing browser session {self.browser_id}: {e}")
        try:
            if self._pw is not None:
                await self._pw.stop()
        except Exception:
            pass
        self.browser = None
        self.context = None
        self.page = None
        self._pw = None
        logger.info(f"BrowserSession disconnected: {self.browser_id}")

    def mark_busy(self, task_id: str) -> None:
        self.is_busy = True
        self.task_id = task_id
        self.last_used_at = timezone.now()

    def mark_idle(self) -> None:
        self.is_busy = False
        self.task_id = None
        self.last_used_at = timezone.now()

    def is_expired(self, max_age_minutes: int = 60) -> bool:
        if not self.last_used_at:
            return False
        return (timezone.now() - self.last_used_at) > timedelta(minutes=max_age_minutes)


class BrowserPool:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.pool: Dict[str, BrowserSession] = {}
        self.max_pool_size = 10
        self.max_browser_age = 60
        self.browser_manager = get_browser_manager()
        self._initialized = True

    async def acquire_by_profile_name(
        self,
        *,
        name: str,
        task_id: str,
        proxy: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        browser_type: BrowserType = BrowserType.GEEKEZ,
        force_new: bool = False,
    ) -> Optional[BrowserSession]:
        """Create/update profile, launch it, and acquire a pooled CDP session."""

        api = self.browser_manager.get_api(browser_type)
        logger.info(f"[{task_id}] Creating/updating profile: {name}")
        profile = api.create_or_update_profile(name=name, proxy=proxy, metadata=metadata)
        logger.info(f"[{task_id}] Profile ready: id={profile.id}, name={profile.name}")
        
        logger.info(f"[{task_id}] Launching profile: {profile.id}")
        launch = api.launch_profile(profile.id)
        if not launch:
            logger.error(f"[{task_id}] launch_profile failed: {profile.id}")
            return None
        logger.info(f"[{task_id}] Profile launched, ws_endpoint={launch.ws_endpoint}, cdp_endpoint={launch.cdp_endpoint}")
        
        ws_endpoint = launch.ws_endpoint or launch.cdp_endpoint
        return await self.acquire(
            browser_id=profile.id,
            ws_endpoint=ws_endpoint,
            task_id=task_id,
            browser_type=browser_type,
            force_new=force_new,
        )

    async def acquire(
        self,
        *,
        browser_id: str,
        ws_endpoint: str,
        task_id: str,
        browser_type: BrowserType,
        force_new: bool = False,
    ) -> Optional[BrowserSession]:
        async with self._lock:
            # reuse
            if browser_id in self.pool and not force_new:
                sess = self.pool[browser_id]
                if sess.is_busy:
                    return None
                if sess.is_expired(self.max_browser_age):
                    await self.release(browser_id, close=True)
                else:
                    # Ensure connection is alive
                    try:
                        await sess.connect()
                    except Exception:
                        # Reconnect by dropping old connection
                        try:
                            await sess.disconnect()
                        except Exception:
                            pass
                        await sess.connect()
                    sess.mark_busy(task_id)
                    return sess

            if len(self.pool) >= self.max_pool_size:
                await self._cleanup_expired()
                if len(self.pool) >= self.max_pool_size:
                    return None

            sess = BrowserSession(
                browser_id=browser_id,
                ws_endpoint=ws_endpoint,
                browser_type=browser_type,
                created_at=timezone.now(),
                last_used_at=timezone.now(),
            )
            await sess.connect()
            sess.mark_busy(task_id)
            self.pool[browser_id] = sess
            return sess

    async def release(self, browser_id: str, close: bool = False) -> bool:
        async with self._lock:
            if browser_id not in self.pool:
                # Still try to close the browser in Geekez if requested
                if close:
                    try:
                        api = self.browser_manager.get_api(BrowserType.GEEKEZ)
                        api.close_profile(browser_id)
                        logger.info(f"Closed Geekez profile (not in pool): {browser_id}")
                    except Exception as e:
                        logger.warning(f"Failed to close Geekez profile: {browser_id}, error: {e}")
                return False
            sess = self.pool[browser_id]
            if close:
                await sess.disconnect()
                del self.pool[browser_id]
                # Also close the browser in Geekez
                try:
                    api = self.browser_manager.get_api(sess.browser_type)
                    api.close_profile(browser_id)
                    logger.info(f"Closed Geekez profile: {browser_id}")
                except Exception as e:
                    logger.warning(f"Failed to close Geekez profile: {browser_id}, error: {e}")
            else:
                sess.mark_idle()
            return True

    async def _cleanup_expired(self) -> None:
        expired = [bid for bid, s in self.pool.items() if not s.is_busy and s.is_expired(self.max_browser_age)]
        for bid in expired:
            await self.release(bid, close=True)


browser_pool = BrowserPool()

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional, Tuple

from playwright.async_api import Page

from apps.integrations.browser_base import BrowserType
from apps.integrations.browser_pool import browser_pool, BrowserSession

logger = logging.getLogger(__name__)


@asynccontextmanager
async def acquire_geekez_page(
    *,
    profile_name: str,
    task_id: str,
    proxy: Optional[str],
    metadata: Optional[Dict[str, Any]],
    browser_type: BrowserType = BrowserType.GEEKEZ,
    timeout_ms: int = 60_000,
    wait_seconds: int = 20,
    close_on_exit: bool = True,
) -> AsyncIterator[Tuple[Page, str]]:
    """Acquire a pooled Geekez browser session and create a fresh Page.

    Args:
        close_on_exit: If True, close browser when context exits. Default True for task isolation.

    Returns (page, profile_id).
    """

    sess: BrowserSession | None = None
    for attempt in range(max(1, wait_seconds)):
        logger.info(f"[{task_id}] Acquiring browser session for {profile_name}, attempt {attempt + 1}/{wait_seconds}")
        sess = await browser_pool.acquire_by_profile_name(
            name=profile_name,
            task_id=task_id,
            proxy=proxy,
            metadata=metadata,
            browser_type=browser_type,
        )
        if sess is not None:
            logger.info(f"[{task_id}] Browser session acquired: {sess.browser_id}")
            break
        await asyncio.sleep(1)

    if sess is None or sess.context is None:
        logger.error(f"[{task_id}] Failed to acquire browser session for {profile_name} after {wait_seconds}s")
        raise RuntimeError("No available Geekez browser session (pool busy or connect failed)")

    page = await sess.context.new_page()
    page.set_default_timeout(timeout_ms)

    try:
        yield page, sess.browser_id
    finally:
        try:
            await page.close()
        except Exception:
            pass
        try:
            await browser_pool.release(sess.browser_id, close=close_on_exit)
            logger.info(f"[{task_id}] Browser session released (close={close_on_exit}): {sess.browser_id}")
        except Exception as e:
            logger.warning(f"[{task_id}] Failed to release browser session: {e}")

"""
Google 账号安全设置服务

迁移自: 2dev/geek/geek_security.py
功能: 修改 2FA 密钥、修改辅助邮箱、获取备份验证码
"""

import asyncio
import base64
import binascii
import logging
import re
import time
from pathlib import Path
import pyotp
from typing import Dict, Any, Optional, Tuple, List, Callable, Awaitable
from playwright.async_api import Page, Locator

from apps.integrations.browser_base import get_browser_manager, BrowserType
from django.conf import settings
from ..utils import TaskLogger

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

    # 备注：Geekez profile 的语言/地区可能导致 Google 页面显示为非中英文（例如波兰语）。
    # 为了让 selector 更稳定，这里强制 hl=en。
    SECURITY_URL = "https://myaccount.google.com/security?hl=en"
    TWO_STEP_URL = (
        "https://myaccount.google.com/signinoptions/two-step-verification?hl=en"
    )
    RECOVERY_EMAIL_URL = "https://myaccount.google.com/recovery/email?hl=en"

    def __init__(self, browser_type: Optional[BrowserType] = None):
        self.browser_manager = get_browser_manager()
        self.browser_type = browser_type

    # Google 展示的 setup key 通常是不带 '=' padding 的 Base32（A-Z2-7），并且长度一般是 32。
    # 为避免误把页面上的普通英文（例如 "GOOGLEAUTHENTICATOR"）当成 key，这里额外要求长度为 8 的倍数。
    _BASE32_RE = re.compile(r"^[A-Z2-7]{16,64}$")

    # 性能相关参数（在稳定性和速度之间取平衡）
    SHORT_WAIT_SECONDS = 0.35
    MEDIUM_WAIT_SECONDS = 0.5
    REAUTH_PROBE_TIMEOUT_MS = 300
    CLICK_PROBE_TIMEOUT_MS = 350
    VISIBLE_PROBE_TIMEOUT_MS = 220
    LOCATOR_POLL_INTERVAL_SECONDS = 0.15
    CLICK_TOTAL_BUDGET_MS = 4500
    MAX_SECRET_EXTRACT_ATTEMPTS = 10

    # TOTP 窗口保护：剩余时间太短时，先等到下一窗口，避免刚提交就过期。
    TOTP_SAFE_REMAINING_SECONDS = 6

    @staticmethod
    def _normalize_base32_secret(raw: str) -> str:
        # Google 展示 key 时常带空格/短横线分组；统一清洗后再验证。
        cleaned = re.sub(r"[\s\-_]", "", raw or "")
        return cleaned.strip().upper()

    def _is_plausible_base32_secret(self, cand: str) -> bool:
        c = self._normalize_base32_secret(cand)
        if not c:
            return False
        if not self._BASE32_RE.match(c):
            return False
        if len(c) < 16:
            return False
        # Base32 长度并非必须是 8 的倍数，但 mod 1/3/6 无法通过标准 padding 补齐。
        if len(c) % 8 in {1, 3, 6}:
            return False
        # 最终以可解码性为准，避免后续 pyotp 抛 Incorrect padding。
        try:
            base64.b32decode(self._to_pyotp_secret(c), casefold=True)
        except (binascii.Error, ValueError):
            return False
        return True

    def _to_pyotp_secret(self, cand: str) -> str:
        """将无 padding 的 Base32 secret 规范化为 pyotp 可用格式。"""
        c = self._normalize_base32_secret(cand)
        if not c:
            return ""
        remainder = len(c) % 8
        if remainder:
            c = c + ("=" * (8 - remainder))
        return c

    async def _maybe_fill_password(self, page: Page, password: str) -> bool:
        password = (password or "").strip()
        if not password:
            return False

        url = (getattr(page, "url", "") or "").lower()
        probe_timeout_ms = self.REAUTH_PROBE_TIMEOUT_MS
        if "challenge/pwd" in url:
            probe_timeout_ms = max(probe_timeout_ms, 1500)

        password_input: Optional[Locator] = None
        for selector in ['input[name="Passwd"]', 'input[type="password"]']:
            candidates = page.locator(selector)
            try:
                count = await candidates.count()
            except Exception:
                count = 0
            for idx in range(min(count, 3)):
                candidate = candidates.nth(idx)
                try:
                    if await candidate.is_visible(timeout=probe_timeout_ms):
                        password_input = candidate
                        break
                except Exception:
                    continue
            if password_input is not None:
                break

        if password_input is None:
            return False

        try:
            await password_input.fill(password)
            await page.keyboard.press("Enter")
            # 等待页面反应，不用固定 sleep 太久
            await asyncio.sleep(self.SHORT_WAIT_SECONDS)
            return True
        except Exception:
            return False
        return False

    async def _maybe_fill_totp(self, page: Page, totp_secret: str) -> bool:
        totp_secret = self._normalize_base32_secret(totp_secret)
        if not totp_secret:
            return False

        # Google challenge 页面经常先渲染隐藏输入，再替换为可见输入；
        # 不能只拿 .first，否则容易漏填“第二次 reauth”的 TOTP。
        url = (getattr(page, "url", "") or "").lower()
        probe_timeout_ms = self.REAUTH_PROBE_TIMEOUT_MS
        if "challenge/totp" in url:
            probe_timeout_ms = max(probe_timeout_ms, 1500)

        totp_input: Optional[Locator] = None
        for selector in [
            'input[name="totpPin"]',
            'input[autocomplete="one-time-code"]',
            'input[type="tel"]',
        ]:
            candidates = page.locator(selector)
            try:
                count = await candidates.count()
            except Exception:
                count = 0
            for idx in range(min(count, 4)):
                candidate = candidates.nth(idx)
                try:
                    if await candidate.is_visible(timeout=probe_timeout_ms):
                        totp_input = candidate
                        break
                except Exception:
                    continue
            if totp_input is not None:
                break

        if totp_input is None:
            return False

        async def _still_on_totp_challenge() -> bool:
            cur_url = (getattr(page, "url", "") or "").lower()
            if "challenge/totp" in cur_url:
                return True
            # URL 未及时更新时，仍可通过输入框可见性判断
            try:
                return await page.locator(
                    'input[name="totpPin"], input[autocomplete="one-time-code"], input[type="tel"]'
                ).first.is_visible(timeout=220)
            except Exception:
                return False

        try:
            # 这里的 secret 可能来自 DB（加密/明文兼容），必须确保格式正确
            if not self._is_plausible_base32_secret(totp_secret):
                return False

            totp = pyotp.TOTP(self._to_pyotp_secret(totp_secret))

            # attempt 1
            now_ts = int(time.time())
            remaining = 30 - (now_ts % 30)
            if remaining < self.TOTP_SAFE_REMAINING_SECONDS:
                await asyncio.sleep(remaining + 1)

            code = totp.now()
            await totp_input.fill(code)
            await page.keyboard.press("Enter")
            await asyncio.sleep(self.SHORT_WAIT_SECONDS)

            # challenge/totp 仍在时，等待到下一个窗口再重试一次，避免无限重试。
            if await _still_on_totp_challenge():
                now_ts = int(time.time())
                wait_s = 30 - (now_ts % 30) + 1
                await asyncio.sleep(wait_s)
                code_retry = totp.now()
                await totp_input.fill(code_retry)
                await page.keyboard.press("Enter")
                await asyncio.sleep(self.SHORT_WAIT_SECONDS)

            return True
        except Exception:
            return False

    async def _dismiss_common_prompts(self, page: Page) -> None:
        # 一些常见的“跳过/稍后”弹窗（不保证覆盖全部）
        candidates = [
            page.get_by_role("button", name="Not now"),
            page.get_by_role("button", name="Skip"),
            page.get_by_role("button", name="以后再说"),
            page.get_by_role("button", name="稍后"),
            page.get_by_role("button", name="跳过"),
        ]
        for loc in candidates:
            try:
                if await loc.first.is_visible(timeout=self.REAUTH_PROBE_TIMEOUT_MS):
                    await loc.first.click(timeout=1200)
                    await asyncio.sleep(0.2)
            except Exception:
                continue

    async def _needs_reauth(self, page: Page) -> bool:
        """快速判断是否在 re-auth 场景，避免无意义的重复填充导致变慢。"""
        url = (getattr(page, "url", "") or "").lower()
        if any(
            token in url
            for token in [
                "challenge",
                "identifier",
                "accounts.google.com/signin/v2",
            ]
        ):
            return True

        checks = [
            page.locator('input[type="password"]').first,
            page.locator('input[name="totpPin"], input[type="tel"]').first,
            page.get_by_role("button", name="Not now").first,
            page.get_by_role("button", name="Skip").first,
        ]
        for loc in checks:
            try:
                if await loc.count() > 0 and await loc.is_visible(
                    timeout=self.REAUTH_PROBE_TIMEOUT_MS
                ):
                    return True
            except Exception:
                continue

        return False

    async def _handle_reauth(self, page: Page, account: Dict[str, Any]) -> None:
        # 重新验证身份：可能出现 password + 2FA
        if not await self._needs_reauth(page):
            return

        # challenge 页面常见 pwd -> totp 串联跳转，这里做有限次数的处理，
        # 避免单轮探测错过可见输入框后直接放弃。
        for _ in range(3):
            if not await self._needs_reauth(page):
                return

            await self._dismiss_common_prompts(page)
            filled_password = await self._maybe_fill_password(
                page, account.get("password", "")
            )
            filled_totp = await self._maybe_fill_totp(page, account.get("totp_secret", ""))
            await self._dismiss_common_prompts(page)

            if not (filled_password or filled_totp):
                await asyncio.sleep(0.35)
            else:
                await asyncio.sleep(self.SHORT_WAIT_SECONDS)

    async def _click_first_visible(
        self,
        locators: List[Locator],
        debug_label: str = "",
        max_total_ms: Optional[int] = None,
    ) -> bool:
        """
        尝试点击第一个可见的元素

        Args:
            locators: Locator 列表
            debug_label: 调试标签，用于日志

        Returns:
            是否成功点击
        """

        # Playwright 的 locator.is_visible()/is_enabled() 默认会用全局 timeout（常见 30s）。
        # 这里是"试探性"点击：不应为单个 selector 卡太久，否则多 selector 串起来会非常慢。
        probe_timeout_ms = self.CLICK_PROBE_TIMEOUT_MS
        total_budget_ms = max_total_ms or self.CLICK_TOTAL_BUDGET_MS

        # 关键优化：按 selector 置信度分层超时。
        # 列表越靠前通常越精准，给稍长点击预算；兜底 selector 用更短预算，避免总耗时爆炸。
        def _pick_click_timeout_ms(locator_index: int) -> int:
            if locator_index <= 1:
                return 2500
            if locator_index <= 4:
                return 1500
            return 900

        async def _try_click(
            target: Locator,
            label: str,
            click_timeout_ms: int,
            force_click_timeout_ms: int,
        ) -> bool:
            """Google 页面经常把文本放在 span 内，真正可点的是祖先 button/role=button。

            这里优先常规 click，失败后再点祖先元素，最后才 force click。
            """

            # 1) 先快速检查元素是否存在，避免不必要的超时等待
            try:
                if await target.count() == 0:
                    return False
            except Exception:
                return False

            try:
                await target.scroll_into_view_if_needed()
            except Exception:
                pass

            # 2) 直接点目标
            try:
                if await target.is_visible(timeout=probe_timeout_ms):
                    try:
                        if not await target.is_enabled(timeout=probe_timeout_ms):
                            return False
                    except Exception:
                        # 某些元素不支持 enabled 检查，忽略
                        pass
                    await target.click(timeout=click_timeout_ms)
                    return True
            except Exception as e:
                if label:
                    logger.debug(f"[{label}] direct click failed: {e}")

            # 3) 点祖先 button / role=button / link
            for ancestor_selector in [
                "xpath=ancestor-or-self::button[1]",
                'xpath=ancestor-or-self::*[@role="button"][1]',
                "xpath=ancestor-or-self::a[1]",
            ]:
                try:
                    anc = target.locator(ancestor_selector).first
                    if await anc.count() > 0 and await anc.is_visible(
                        timeout=probe_timeout_ms
                    ):
                        try:
                            await anc.scroll_into_view_if_needed()
                        except Exception:
                            pass
                        await anc.click(timeout=click_timeout_ms)
                        return True
                except Exception as e:
                    if label:
                        logger.debug(
                            f"[{label}] ancestor click failed ({ancestor_selector}): {e}"
                        )
                    continue

            # 4) 兜底：force click（避免被内部 span 指针事件影响）
            try:
                if await target.is_visible(timeout=probe_timeout_ms):
                    await target.click(timeout=force_click_timeout_ms, force=True)
                    return True
            except Exception as e:
                if label:
                    logger.debug(f"[{label}] force click failed: {e}")
            return False

        loop = asyncio.get_running_loop()
        all_started_at = loop.time()

        for i, loc in enumerate(locators):
            try:
                if (loop.time() - all_started_at) * 1000 >= total_budget_ms:
                    if debug_label:
                        logger.warning(
                            f"[{debug_label}] click budget exceeded: {total_budget_ms}ms"
                        )
                    break

                candidate = loc.first
                click_timeout_ms = _pick_click_timeout_ms(i)
                force_click_timeout_ms = min(click_timeout_ms, 900)
                started_at = loop.time()

                # 先 count 再 is_visible：避免 is_visible 的默认超时导致串行等待过久
                if await candidate.count() <= 0:
                    continue

                is_visible = await candidate.is_visible(timeout=probe_timeout_ms)
                if debug_label:
                    logger.debug(f"[{debug_label}] Locator {i}: visible={is_visible}")
                if not is_visible:
                    continue

                clicked = await _try_click(
                    candidate,
                    debug_label,
                    click_timeout_ms,
                    force_click_timeout_ms,
                )
                elapsed_ms = int((loop.time() - started_at) * 1000)

                if debug_label and (clicked or elapsed_ms >= 1500):
                    logger.info(
                        f"[{debug_label}] Locator {i}: clicked={clicked} "
                        f"elapsed_ms={elapsed_ms} click_timeout_ms={click_timeout_ms}"
                    )

                if clicked:
                    await asyncio.sleep(self.SHORT_WAIT_SECONDS)
                    if debug_label:
                        logger.info(f"[{debug_label}] Clicked locator {i} successfully")
                    return True
            except Exception as e:
                if debug_label:
                    logger.warning(f"[{debug_label}] Locator {i} failed: {e}")
                continue
        if debug_label:
            logger.warning(f"[{debug_label}] No locator was clickable")
        return False

    async def _save_debug_screenshot(self, page: Page, prefix: str, email: str) -> str:
        try:
            base_dir = Path(getattr(settings, "BASE_DIR", "."))
            shots_dir = base_dir / "screenshots"
            shots_dir.mkdir(parents=True, exist_ok=True)

            safe_email = (email or "").replace("@", "_").replace(".", "_")
            ts = asyncio.get_running_loop().time()
            filename = f"{prefix}_{safe_email}_{int(ts)}.png"
            path = shots_dir / filename
            await page.screenshot(path=str(path), full_page=True)
            return filename
        except Exception:
            return ""

    async def _extract_base32_secret(self, page: Page) -> Optional[str]:
        """
        提取 2FA 密钥

        真实页面元素示例:
        <li class="mzEcT">Enter your email address and this key (spaces don't matter):
            <div><strong>ddve xsur 6eqm 2prg 4byt mefr susm eaj3</strong></div>
        </li>
        """
        # 只在 Google 的 “this key (spaces don't matter)” 区域尝试提取。
        # 避免在 re-auth/totp challenge 页面误匹配到无关 strong 文本。
        try:
            if await page.locator("li.mzEcT").count() <= 0:
                return None
        except Exception:
            return None

        # 方式1: 优先从 <li class="mzEcT"> 中的 <strong> 提取 (Google 真实页面结构)
        try:
            strong_in_li = page.locator("li.mzEcT strong").first
            if await strong_in_li.is_visible():
                txt = await strong_in_li.text_content()
                if txt:
                    cand = self._normalize_base32_secret(txt)
                    if self._is_plausible_base32_secret(cand):
                        logger.info(f"从 li.mzEcT strong 提取到密钥: {cand[:8]}...")
                        return cand
        except Exception:
            pass

        # 方式2: 兼容结构变化：仍限制在 li.mzEcT 内，不扫描全站 strong
        try:
            strongs = await page.locator("li.mzEcT strong").all()
            for s in strongs[:5]:
                try:
                    txt = await s.text_content()
                    if txt:
                        cand = self._normalize_base32_secret(txt)
                        if self._is_plausible_base32_secret(cand):
                            logger.info(
                                f"从 li.mzEcT strong(alt) 提取到密钥: {cand[:8]}..."
                            )
                            return cand
                except Exception:
                    continue
        except Exception:
            pass

        # 方式3: 从 "this key" 文本附近提取
        try:
            key_label = page.get_by_text("this key", exact=False).first
            if await key_label.is_visible():
                # 获取父容器的文本
                parent = key_label.locator("xpath=..")
                txt = await parent.text_content()
                if txt:
                    m = re.search(r"([a-zA-Z2-7]{16,64})", txt.replace(" ", ""))
                    if m:
                        cand = self._normalize_base32_secret(m.group(1))
                        if self._is_plausible_base32_secret(cand):
                            logger.info(f"从 'this key' 附近提取到密钥: {cand[:8]}...")
                            return cand
        except Exception:
            pass

        # 方式4: 从 Setup key 区域提取
        try:
            setup_label = page.get_by_text("Setup key", exact=False).first
            if await setup_label.is_visible():
                try:
                    container = setup_label.locator(
                        "xpath=ancestor-or-self::*[self::section or self::div][1]"
                    )
                except Exception:
                    container = setup_label
                txt = await container.text_content()
                if txt:
                    m = re.search(r"([A-Z2-7]{16,64})", txt.replace(" ", "").upper())
                    if m:
                        cand = self._normalize_base32_secret(m.group(1))
                        if self._is_plausible_base32_secret(cand):
                            return cand
        except Exception:
            pass

        # 方式5: 从 data-secret 属性尝试
        try:
            el = page.locator("[data-secret]").first
            if await el.is_visible():
                val = await el.get_attribute("data-secret")
                if isinstance(val, str):
                    cand = self._normalize_base32_secret(val)
                    if self._is_plausible_base32_secret(cand):
                        return cand
        except Exception:
            pass

        # 方式6: 从可见文本提取（code / .secret-key 等）
        candidates: List[str] = []
        for sel in [".secret-key", "code", "[data-secret]", "li.mzEcT"]:
            try:
                locs = await page.locator(sel).all()
                for loc in locs[:20]:
                    try:
                        txt = await loc.text_content()
                        if not txt:
                            continue
                        candidates.append(txt)
                    except Exception:
                        continue
            except Exception:
                continue

        for raw in candidates:
            cand = self._normalize_base32_secret(raw)
            m = re.search(r"([A-Z2-7]{16,64})", cand)
            if m:
                v = m.group(1)
                if self._is_plausible_base32_secret(v):
                    return v

        # 方式7: 兜底从完整 HTML 中提取
        try:
            html = await page.content()
            if html and (
                "this key" in html.lower()
                or "setup key" in html.lower()
                or "enter a setup key" in html.lower()
            ):
                for v in re.findall(r"[A-Z2-7]{16,64}", html.upper()):
                    cand = self._normalize_base32_secret(v)
                    if not self._is_plausible_base32_secret(cand):
                        continue
                    try:
                        pyotp.TOTP(self._to_pyotp_secret(cand)).now()
                        return cand
                    except Exception:
                        continue
        except Exception:
            pass

        return None

    async def _find_first_visible_locator(
        self, page: Page, selectors: List[str], timeout_s: float = 8.0
    ) -> Optional[Locator]:
        """在 page + 所有 frames 里查找第一个可见的元素。

        Google 的验证/弹窗有时会挂在 frame 里（或 portal 结构变化），这里做统一兜底。
        """

        end_time = asyncio.get_running_loop().time() + max(timeout_s, 0.1)

        # 先把 selectors 编译成 Locator，避免循环里重复创建
        page_locs: List[Locator] = [page.locator(sel).first for sel in selectors]

        # frames 可能很多，控制一下遍历成本
        frames = getattr(page, "frames", []) or []
        frame_locs: List[Locator] = []
        try:
            for fr in frames[:10]:
                for sel in selectors:
                    try:
                        frame_locs.append(fr.locator(sel).first)
                    except Exception:
                        continue
        except Exception:
            frame_locs = []

        all_locs = page_locs + frame_locs

        # 统一显式可见性探测超时，避免某些运行时回落到全局 timeout 造成意外长等待。
        visible_probe_timeout_ms = self.VISIBLE_PROBE_TIMEOUT_MS

        while asyncio.get_running_loop().time() < end_time:
            for loc in all_locs:
                try:
                    if await loc.count() > 0 and await loc.is_visible(
                        timeout=visible_probe_timeout_ms
                    ):
                        return loc
                except Exception:
                    continue
            await asyncio.sleep(self.LOCATOR_POLL_INTERVAL_SECONDS)

        return None

    async def change_2fa_secret(
        self,
        page: Page,
        account: Dict[str, Any],
        task_logger: Optional[TaskLogger] = None,
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
        # 旧密钥用于 re-auth（可能出现再次输入当前 2FA）
        current_secret = account.get("totp_secret", "")
        loop = asyncio.get_running_loop()

        if task_logger:
            task_logger.event(
                step="2fa",
                action="start",
                message="start change_2fa_secret",
                url=getattr(page, "url", ""),
            )

        try:
            # 1) 导航到两步验证页面
            if task_logger:
                task_logger.event(
                    step="2fa",
                    action="goto",
                    message="goto TWO_STEP_URL",
                    url=self.TWO_STEP_URL,
                )
            await page.goto(self.TWO_STEP_URL, wait_until="domcontentloaded")
            await asyncio.sleep(self.SHORT_WAIT_SECONDS)
            await self._handle_reauth(page, {**account, "totp_secret": current_secret})
            if await self._needs_reauth(page):
                await self._handle_reauth(page, {**account, "totp_secret": current_secret})

            # 2) 进入 Authenticator app 设置
            # 真实元素: <div class="mMsbvc ">Authenticator</div>
            auth_click_started_at = loop.time()
            clicked_auth = await self._click_first_visible(
                [
                    # 精确匹配 Google 页面的 div.mMsbvc
                    page.locator('div.mMsbvc:has-text("Authenticator")'),
                    page.locator('.mMsbvc:has-text("Authenticator")'),
                    # 文本匹配兜底
                    page.get_by_text("Authenticator", exact=True),
                    page.get_by_text("Authenticator app", exact=False),
                    page.get_by_text("Authenticator", exact=False),
                    # 中文
                    page.get_by_text("身份验证器", exact=False),
                ],
                debug_label="click_authenticator",
            )
            auth_click_elapsed_ms = int((loop.time() - auth_click_started_at) * 1000)
            if task_logger:
                task_logger.event(
                    step="2fa",
                    action="click",
                    message=(
                        "clicked Authenticator entry"
                        if clicked_auth
                        else "Authenticator entry not clicked"
                    ),
                    url=getattr(page, "url", ""),
                    result={
                        "clicked_authenticator": clicked_auth,
                        "elapsed_ms": auth_click_elapsed_ms,
                    },
                )
            if clicked_auth:
                await self._handle_reauth(
                    page, {**account, "totp_secret": current_secret}
                )

            # 3) 点击 "Change authenticator app" 进入更换流程
            # 真实元素: <span jsname="V67aGc" class="mUIrbf-vQzf8d">Change authenticator app</span>
            # 先等待一次目标面板就绪，避免太早触发宽泛 fallback 导致串行长超时。
            # 该步骤是成败关键：若 Change 没点到，后续提取 setup key 基本会空转。
            change_surface_wait_started_at = loop.time()
            change_surface = await self._find_first_visible_locator(
                page,
                selectors=[
                    'span.mUIrbf-vQzf8d:has-text("Change authenticator app")',
                    '.mUIrbf-vQzf8d:has-text("Change authenticator")',
                    '[jsname="V67aGc"]:has-text("Change")',
                    'button:has-text("Change phone")',
                    'button:has-text("Change")',
                    "text=Change authenticator app",
                    "text=更改身份验证器",
                    "text=Zmień aplikację uwierzytelniającą",
                ],
                timeout_s=5.0,
            )
            if task_logger:
                task_logger.event(
                    step="2fa",
                    action="wait",
                    message="waited change authenticator surface",
                    url=getattr(page, "url", ""),
                    result={
                        "surface_ready": bool(change_surface),
                        "elapsed_ms": int(
                            (loop.time() - change_surface_wait_started_at) * 1000
                        ),
                    },
                )

            change_click_started_at = loop.time()
            clicked_change_authenticator = await self._click_first_visible(
                [
                    # 精确匹配 Google 页面的 span.mUIrbf-vQzf8d
                    page.locator(
                        'span.mUIrbf-vQzf8d:has-text("Change authenticator app")'
                    ),
                    page.locator('.mUIrbf-vQzf8d:has-text("Change authenticator")'),
                    page.locator('[jsname="V67aGc"]:has-text("Change")'),
                    # 文本匹配
                    page.get_by_text("Change authenticator app", exact=False),
                    page.get_by_text("Change authenticator", exact=False),
                    # 按钮兜底
                    page.locator('button:has-text("Change phone")'),
                    page.locator('button:has-text("Change")'),
                    page.locator('button:has-text("Set up")'),
                    # 中文
                    page.get_by_text("更改身份验证器", exact=False),
                    page.locator('button:has-text("更改")'),
                    # 波兰语
                    page.locator('span.mUIrbf-vQzf8d:has-text("Zmień aplikację")'),
                    page.get_by_text("Zmień aplikację", exact=False),
                    page.get_by_text("Zmień", exact=False),
                ],
                debug_label="click_change_authenticator",
                max_total_ms=6200,
            )

            if task_logger:
                task_logger.event(
                    step="2fa",
                    action="click",
                    message=(
                        "clicked Change authenticator app"
                        if clicked_change_authenticator
                        else "Change authenticator app not clicked"
                    ),
                    url=getattr(page, "url", ""),
                    result={
                        "clicked_change_authenticator": clicked_change_authenticator,
                        "elapsed_ms": int((loop.time() - change_click_started_at) * 1000),
                    },
                )

            if not clicked_change_authenticator:
                # 兜底：再走一次 twosv 页面重进 + 更宽预算点击，避免因阶段性渲染延迟漏点。
                if task_logger:
                    task_logger.event(
                        step="2fa",
                        action="retry",
                        level="warning",
                        message="retry entering change authenticator flow",
                        url=getattr(page, "url", ""),
                    )

                try:
                    await page.goto(self.TWO_STEP_URL, wait_until="domcontentloaded")
                    await asyncio.sleep(self.SHORT_WAIT_SECONDS)
                except Exception:
                    pass

                await self._handle_reauth(page, {**account, "totp_secret": current_secret})
                if await self._needs_reauth(page):
                    await self._handle_reauth(
                        page, {**account, "totp_secret": current_secret}
                    )

                await self._click_first_visible(
                    [
                        page.locator('div.mMsbvc:has-text("Authenticator")'),
                        page.locator('.mMsbvc:has-text("Authenticator")'),
                        page.get_by_text("Authenticator", exact=True),
                        page.get_by_text("Authenticator app", exact=False),
                        page.get_by_text("身份验证器", exact=False),
                    ],
                    debug_label="click_authenticator_retry",
                    max_total_ms=6200,
                )

                retry_started_at = loop.time()
                clicked_change_authenticator = await self._click_first_visible(
                    [
                        page.locator(
                            'span.mUIrbf-vQzf8d:has-text("Change authenticator app")'
                        ),
                        page.locator('.mUIrbf-vQzf8d:has-text("Change authenticator")'),
                        page.locator('[jsname="V67aGc"]:has-text("Change")'),
                        page.get_by_text("Change authenticator app", exact=False),
                        page.get_by_text("Change authenticator", exact=False),
                        page.locator('button:has-text("Change phone")'),
                        page.locator('button:has-text("Change")'),
                        page.locator('button:has-text("Set up")'),
                        page.get_by_text("更改身份验证器", exact=False),
                        page.locator('button:has-text("更改")'),
                        page.locator('span.mUIrbf-vQzf8d:has-text("Zmień aplikację")'),
                        page.get_by_text("Zmień aplikację", exact=False),
                        page.get_by_text("Zmień", exact=False),
                    ],
                    debug_label="click_change_authenticator_retry",
                    max_total_ms=8000,
                )

                if task_logger:
                    task_logger.event(
                        step="2fa",
                        action="click",
                        level="warning" if not clicked_change_authenticator else "info",
                        message=(
                            "clicked Change authenticator app (retry)"
                            if clicked_change_authenticator
                            else "Change authenticator app not clicked after retry"
                        ),
                        url=getattr(page, "url", ""),
                        result={
                            "clicked_change_authenticator": clicked_change_authenticator,
                            "elapsed_ms": int((loop.time() - retry_started_at) * 1000),
                        },
                    )

            if not clicked_change_authenticator:
                # 仍在 challenge 页时先尝试一次 reauth，再做最后一次 Change 点击。
                # 目的：避免“二次 TOTP 还没填/还未生效”就直接 fail-fast。
                if await self._needs_reauth(page):
                    await self._handle_reauth(
                        page, {**account, "totp_secret": current_secret}
                    )
                    reauth_retry_started_at = loop.time()
                    clicked_change_authenticator = await self._click_first_visible(
                        [
                            page.locator(
                                'span.mUIrbf-vQzf8d:has-text("Change authenticator app")'
                            ),
                            page.locator(
                                '.mUIrbf-vQzf8d:has-text("Change authenticator")'
                            ),
                            page.locator('[jsname="V67aGc"]:has-text("Change")'),
                            page.get_by_text("Change authenticator app", exact=False),
                            page.get_by_text("Change authenticator", exact=False),
                            page.locator('button:has-text("Change")'),
                            page.locator('button:has-text("Set up")'),
                        ],
                        debug_label="click_change_authenticator_after_reauth",
                        max_total_ms=6200,
                    )
                    if task_logger:
                        task_logger.event(
                            step="2fa",
                            action="click",
                            level="warning" if not clicked_change_authenticator else "info",
                            message=(
                                "clicked Change authenticator app after reauth"
                                if clicked_change_authenticator
                                else "Change authenticator app still not clicked after reauth"
                            ),
                            url=getattr(page, "url", ""),
                            result={
                                "clicked_change_authenticator": clicked_change_authenticator,
                                "elapsed_ms": int(
                                    (loop.time() - reauth_retry_started_at) * 1000
                                ),
                            },
                        )

            if not clicked_change_authenticator:
                shot = await self._save_debug_screenshot(page, "security_change_2fa", email)
                url = getattr(page, "url", "")
                msg = "未进入 Change authenticator 流程，无法提取新的 2FA 密钥"
                if url:
                    msg += f" (url={url})"
                if shot:
                    msg += f" (screenshot={shot})"
                if task_logger:
                    task_logger.event(
                        step="2fa",
                        action="fail",
                        level="error",
                        message=msg,
                        url=url,
                        screenshot=shot,
                        result={"reason": "change_authenticator_not_clicked"},
                    )
                return False, msg, None

            await self._handle_reauth(page, {**account, "totp_secret": current_secret})

            # 4) 等待页面加载完成，尝试获取 secret
            # 减少循环次数避免长时间等待
            new_secret: Optional[str] = None
            for attempt in range(self.MAX_SECRET_EXTRACT_ATTEMPTS):
                if task_logger:
                    task_logger.event(
                        step="2fa",
                        action="attempt",
                        message=(
                            f"extract setup key attempt {attempt + 1}/"
                            f"{self.MAX_SECRET_EXTRACT_ATTEMPTS}"
                        ),
                        url=getattr(page, "url", ""),
                    )
                await self._handle_reauth(
                    page, {**account, "totp_secret": current_secret}
                )

                # 如果已经进入“输入 6 位验证码”的步骤（Step 2），说明走到了扫码验证环节。
                # 需要明文密钥来生成验证码，所以优先回退到上一步寻找 "Can't scan it?"。
                try:
                    enter_code = page.get_by_text(
                        "Enter the 6-digit code", exact=False
                    ).first
                    if await enter_code.is_visible(timeout=self.REAUTH_PROBE_TIMEOUT_MS):
                        back_btn = page.get_by_role("button", name="Back").first
                        if await back_btn.is_visible(
                            timeout=self.REAUTH_PROBE_TIMEOUT_MS
                        ):
                            await back_btn.click()
                            await asyncio.sleep(self.SHORT_WAIT_SECONDS)
                except Exception:
                    pass

                # 优先尝试点击 "Can't scan it?" 以显示文本 secret
                # 真实元素: <span jsname="V67aGc" class="mUIrbf-vQzf8d">Can't scan it?</span>
                cant_scan_click_started_at = loop.time()
                clicked_cant_scan = await self._click_first_visible(
                    [
                        # 方式1: 精确匹配 Google 页面的 span.mUIrbf-vQzf8d
                        page.locator('span.mUIrbf-vQzf8d:has-text("Can\'t scan it")'),
                        page.locator(
                            'span.mUIrbf-vQzf8d:has-text("Can\u2019t scan it")'
                        ),
                        page.locator('.mUIrbf-vQzf8d:has-text("Can\'t scan")'),
                        page.locator('.mUIrbf-vQzf8d:has-text("Can\u2019t scan")'),
                        page.locator('[jsname="V67aGc"]:has-text("Can\'t scan")'),
                        page.locator('[jsname="V67aGc"]:has-text("Can\u2019t scan")'),
                        # 方式2: 文本匹配
                        page.get_by_text("Can't scan it?", exact=True),
                        page.get_by_text("Can\u2019t scan it?", exact=True),
                        page.get_by_text("Can't scan it?", exact=False),
                        page.get_by_text("Can\u2019t scan it?", exact=False),
                        page.get_by_text("Can't scan it", exact=False),
                        page.get_by_text("Can\u2019t scan it", exact=False),
                        # 方式3: role 定位
                        page.get_by_role("link", name="Can't scan it"),
                        page.get_by_role("button", name="Can't scan it"),
                        # name=regex 兜底（兼容 ' / ’）
                        page.get_by_role(
                            "button",
                            name=re.compile(r"Can['\u2019]t scan it\??", re.IGNORECASE),
                        ),
                        page.get_by_role(
                            "link",
                            name=re.compile(r"Can['\u2019]t scan it\??", re.IGNORECASE),
                        ),
                        # 方式4: 其他文本
                        page.get_by_text("Cannot scan", exact=False),
                        page.get_by_text("Enter a setup key", exact=False),
                        # 中文
                        page.get_by_text("无法扫描", exact=False),
                    ],
                    debug_label="cant_scan_click",
                    max_total_ms=2800,
                )
                cant_scan_click_elapsed_ms = int(
                    (loop.time() - cant_scan_click_started_at) * 1000
                )
                if task_logger and (
                    clicked_cant_scan or cant_scan_click_elapsed_ms >= 1500
                ):
                    task_logger.event(
                        step="2fa",
                        action="click_probe",
                        message=(
                            "clicked Can't scan it?"
                            if clicked_cant_scan
                            else "Can't scan it? not clicked"
                        ),
                        url=getattr(page, "url", ""),
                        result={
                            "attempt": attempt + 1,
                            "clicked_cant_scan": clicked_cant_scan,
                            "elapsed_ms": cant_scan_click_elapsed_ms,
                        },
                    )
                if clicked_cant_scan:
                    # 等待明文密钥区域渲染
                    try:
                        await page.locator("li.mzEcT strong").first.wait_for(
                            state="visible", timeout=3000
                        )
                    except Exception:
                        await asyncio.sleep(self.SHORT_WAIT_SECONDS)

                new_secret = await self._extract_base32_secret(page)
                if new_secret:
                    normalized_secret = self._normalize_base32_secret(new_secret)
                    if not self._is_plausible_base32_secret(normalized_secret):
                        if task_logger:
                            task_logger.event(
                                step="2fa",
                                action="extract_secret_invalid",
                                level="warning",
                                message="extracted setup key candidate failed validation, continue probing",
                                url=getattr(page, "url", ""),
                                result={
                                    "attempt": attempt + 1,
                                    "candidate_masked": TaskLogger._mask_secret(
                                        normalized_secret
                                    ),
                                },
                            )
                        await asyncio.sleep(self.SHORT_WAIT_SECONDS)
                        continue

                    new_secret = normalized_secret
                    if task_logger:
                        task_logger.event(
                            step="2fa",
                            action="extract_secret",
                            message=f"got setup key {TaskLogger._mask_secret(new_secret)}",
                            url=getattr(page, "url", ""),
                        )
                    break

                await asyncio.sleep(self.SHORT_WAIT_SECONDS)

            if not new_secret:
                shot = await self._save_debug_screenshot(
                    page, "security_change_2fa", email
                )
                url = getattr(page, "url", "")
                msg = "未能获取新的 2FA 密钥"
                if url:
                    msg += f" (url={url})"
                if shot:
                    msg += f" (screenshot={shot})"
                if task_logger:
                    task_logger.event(
                        step="2fa",
                        action="fail",
                        level="error",
                        message=msg,
                        url=url,
                        screenshot=shot,
                    )
                return False, msg, None

            # 6) 使用新密钥生成验证码并验证
            try:
                new_secret = self._normalize_base32_secret(new_secret)
                if not self._is_plausible_base32_secret(new_secret):
                    shot = await self._save_debug_screenshot(
                        page, "security_change_2fa", email
                    )
                    url = getattr(page, "url", "")
                    msg = "提取到的 2FA key 无法通过校验（可能页面内容混入非密钥文本）"
                    if url:
                        msg += f" (url={url})"
                    if shot:
                        msg += f" (screenshot={shot})"
                    if task_logger:
                        task_logger.event(
                            step="2fa",
                            action="fail",
                            level="error",
                            message=msg,
                            url=url,
                            screenshot=shot,
                            result={
                                "candidate_masked": TaskLogger._mask_secret(new_secret)
                            },
                        )
                    return False, msg, None

                code = pyotp.TOTP(self._to_pyotp_secret(new_secret)).now()
            except Exception as e:
                shot = await self._save_debug_screenshot(
                    page, "security_change_2fa", email
                )
                msg = f"生成 TOTP 失败: {e}"
                if shot:
                    msg += f" (screenshot={shot})"
                return False, msg, None

            # 拿到密钥后，进入验证码输入步骤
            # 真实元素: <span jsname="V67aGc" class="VfPpkd-vQzf8d">Next</span>
            next_click_started_at = loop.time()
            clicked_next = await self._click_first_visible(
                [
                    # role 定位（优先，避免点到内部 span）
                    page.get_by_role("button", name="Next"),
                    page.get_by_role("button", name="下一步"),
                    page.get_by_role("button", name="Continue"),
                    page.get_by_role(
                        "button",
                        name=re.compile(r"^(Next|Continue)$", re.IGNORECASE),
                    ),
                    # 精确匹配 Google 页面的 span.VfPpkd-vQzf8d
                    page.locator('span.VfPpkd-vQzf8d:has-text("Next")'),
                    page.locator('.VfPpkd-vQzf8d:has-text("Next")'),
                    page.locator('[jsname="V67aGc"]:has-text("Next")'),
                    # 文本匹配兜底
                    page.get_by_text("Next", exact=True),
                ],
                debug_label="click_next",
            )
            next_click_elapsed_ms = int((loop.time() - next_click_started_at) * 1000)
            await asyncio.sleep(self.MEDIUM_WAIT_SECONDS)

            if task_logger:
                task_logger.event(
                    step="2fa",
                    action="click",
                    message="clicked Next to open code dialog",
                    url=getattr(page, "url", ""),
                    result={
                        "clicked_next": clicked_next,
                        "elapsed_ms": next_click_elapsed_ms,
                    },
                )

            # Google 这一步的输入框有时是 type=text + placeholder=Enter Code，
            # 之前仅用 name=totpPin/type=tel 会误判“未进入输入步骤”。
            # 优先尝试在 dialog 内找 textbox；失败再全局 + frames 兜底。
            code_input: Optional[Locator] = None
            try:
                dialog = page.get_by_role("dialog").first
                if await dialog.count() > 0 and await dialog.is_visible():
                    # dialog 内优先找 textbox
                    dialog_tb = dialog.get_by_role("textbox").first
                    if await dialog_tb.count() > 0 and await dialog_tb.is_visible():
                        code_input = dialog_tb
                    else:
                        dialog_inp = dialog.locator("input").first
                        if (
                            await dialog_inp.count() > 0
                            and await dialog_inp.is_visible()
                        ):
                            code_input = dialog_inp
            except Exception:
                code_input = None

            if not code_input:
                code_input = await self._find_first_visible_locator(
                    page,
                    selectors=[
                        'input[name="totpPin"]',
                        'input[autocomplete="one-time-code"]',
                        'input[inputmode="numeric"]',
                        # placeholder / aria-label 往往是 Enter Code / Enter code / Code
                        'input[placeholder*="code" i]',
                        'input[placeholder*="enter" i]',
                        'input[aria-label*="code" i]',
                        'input[aria-label*="enter" i]',
                        'input[type="tel"]',
                        # 有些实现是 text + maxlength=6
                        'input[type="text"][maxlength="6"]',
                    ],
                    timeout_s=8.0,
                )

            if not code_input:
                shot = await self._save_debug_screenshot(
                    page, "security_change_2fa", email
                )
                url = getattr(page, "url", "")
                msg = "未能定位验证码输入框（页面已进入 Step 2，但 selector 未覆盖该结构）"
                if not clicked_next:
                    msg += "（未找到可点击的 Next 按钮）"
                if url:
                    msg += f" (url={url})"
                if shot:
                    msg += f" (screenshot={shot})"
                return False, msg, None

            await code_input.fill(code)
            if task_logger:
                task_logger.event(
                    step="2fa",
                    action="fill",
                    message="filled TOTP code",
                    url=getattr(page, "url", ""),
                    result={"code_masked": code[:2] + "****"},
                )
            # 优先点 Verify（通常在 dialog 右下角）
            try:
                verify_btn = page.get_by_role("button", name="Verify").first
                if await verify_btn.is_visible() and await verify_btn.is_enabled():
                    await verify_btn.click()
                else:
                    await page.keyboard.press("Enter")
            except Exception:
                await page.keyboard.press("Enter")
            await asyncio.sleep(self.MEDIUM_WAIT_SECONDS)

            if task_logger:
                task_logger.event(
                    step="2fa",
                    action="submit",
                    message="submitted Verify",
                    url=getattr(page, "url", ""),
                )

            # 如果出现错误提示，直接返回可读错误 + 截图
            for err_loc in [
                page.get_by_text("Wrong code", exact=False),
                page.get_by_text("Try again", exact=False),
                page.get_by_text("Invalid", exact=False),
                page.get_by_text("incorrect", exact=False),
            ]:
                try:
                    if await err_loc.first.is_visible():
                        shot = await self._save_debug_screenshot(
                            page, "security_change_2fa", email
                        )
                        url = getattr(page, "url", "")
                        msg = "验证码验证失败（可能未获取到正确的 setup key）"
                        if url:
                            msg += f" (url={url})"
                        if shot:
                            msg += f" (screenshot={shot})"
                        return False, msg, None
                except Exception:
                    continue

            # 7) 成功判断
            # 目前强制 hl=en，Google 在成功后通常会回到 twosv 页面，并在 Authenticator 项旁显示
            # “Added just now / Added X minutes ago”等状态。
            success = False

            # A. 优先判断 “Added just now / Added ... ago” 这类明确成功标识
            try:
                added_marker = page.get_by_text(
                    re.compile(
                        r"Added\s+(just\s+now|\d+\s+(second|minute|hour|day)s?\s+ago)",
                        re.IGNORECASE,
                    ),
                    exact=False,
                ).first
                if await added_marker.is_visible():
                    success = True
            except Exception:
                pass

            # B. 兼容一些页面会出现的 Done/Verified 文案
            for loc in [
                page.get_by_text("Done", exact=False),
                page.get_by_text("完成", exact=False),
                page.get_by_text("Verified", exact=False),
                page.get_by_text("已验证", exact=False),
                page.get_by_text("已开启", exact=False),
            ]:
                try:
                    if await loc.first.is_visible():
                        success = True
                        break
                except Exception:
                    continue

            # C. 最后兜底：回到了 twosv 页面，且验证码输入框/弹窗已消失 + 未看到错误提示
            if not success:
                try:
                    url_now = getattr(page, "url", "") or ""
                    is_twosv_page = "/signinoptions/twosv" in url_now
                    dialog_visible = False
                    try:
                        dlg = page.get_by_role("dialog").first
                        dialog_visible = await dlg.is_visible(timeout=800)
                    except Exception:
                        dialog_visible = False

                    if is_twosv_page and not dialog_visible:
                        success = True
                except Exception:
                    pass

            if success:
                logger.info(f"2FA secret changed for {email}")
                if task_logger:
                    task_logger.event(
                        step="2fa",
                        action="success",
                        message="2FA change confirmed",
                        url=getattr(page, "url", ""),
                    )
                return True, "2FA 密钥修改成功", new_secret

            # 再兜底：回到 2FA 页面看看是否仍然需要设置
            try:
                await page.goto(self.TWO_STEP_URL, wait_until="domcontentloaded")
                await asyncio.sleep(self.SHORT_WAIT_SECONDS)
            except Exception:
                pass

            shot = await self._save_debug_screenshot(page, "security_change_2fa", email)
            url = getattr(page, "url", "")
            msg = "未能确认 2FA 修改是否成功"
            if url:
                msg += f" (url={url})"
            if shot:
                msg += f" (screenshot={shot})"

            if task_logger:
                task_logger.event(
                    step="2fa",
                    action="fail",
                    level="error",
                    message=msg,
                    url=url,
                    screenshot=shot,
                )
            return False, msg, None

        except Exception as e:
            logger.exception(f"Failed to change 2FA for {email}")
            shot = ""
            try:
                shot = await self._save_debug_screenshot(
                    page, "security_change_2fa", email
                )
            except Exception:
                shot = ""
            msg = str(e)
            url = getattr(page, "url", "")
            if url:
                msg += f" (url={url})"
            if shot:
                msg += f" (screenshot={shot})"

            if task_logger:
                task_logger.event(
                    step="2fa",
                    action="exception",
                    level="error",
                    message=msg,
                    url=url,
                    screenshot=shot,
                )
            return False, msg, None

    async def change_recovery_email(
        self,
        page: Page,
        account: Dict[str, Any],
        new_email: str,
        task_logger: Optional[TaskLogger] = None,
        verification_code_callback: Optional[
            Callable[[str], Awaitable[Optional[str]]]
        ] = None,
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
            if task_logger:
                task_logger.event(
                    step="recovery_email",
                    action="goto",
                    message="goto RECOVERY_EMAIL_URL",
                    url=self.RECOVERY_EMAIL_URL,
                )
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
                    totp = pyotp.TOTP(self._to_pyotp_secret(totp_secret))
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
            await asyncio.sleep(2.5)
            verification_input = None
            verification_input_selectors = [
                'input[type="text"]',
                'input[type="tel"]',
                'input[name="code"]',
                'input[aria-label*="code" i]',
                'input[aria-label*="验证"]',
            ]
            for selector in verification_input_selectors:
                candidate = page.locator(selector).first
                try:
                    if await candidate.is_visible(timeout=1200):
                        verification_input = candidate
                        break
                except Exception:
                    continue

            if verification_input and verification_code_callback:
                try:
                    verification_code = await verification_code_callback(new_email)
                except Exception as callback_error:
                    logger.warning(
                        "Failed to fetch recovery verification code for %s: %s",
                        new_email,
                        callback_error,
                    )
                    verification_code = ""

                if isinstance(verification_code, str) and verification_code.strip():
                    code = verification_code.strip()
                    try:
                        await verification_input.fill(code)
                    except Exception:
                        await verification_input.click()
                        await page.keyboard.type(code)

                    submit_btn = page.locator(
                        'button:has-text("Next"), button:has-text("Verify"), button:has-text("下一步"), button:has-text("验证")'
                    ).first
                    submitted = False
                    try:
                        if await submit_btn.is_visible(timeout=1200):
                            await submit_btn.click()
                            submitted = True
                    except Exception:
                        submitted = False

                    if not submitted:
                        await page.keyboard.press("Enter")

                    await asyncio.sleep(2)
                else:
                    logger.warning(
                        "Verification code required but not obtained for %s, proceeding without",
                        new_email,
                    )
            elif verification_input and not verification_code_callback:
                logger.warning(
                    "Verification input found but no callback provided for %s",
                    new_email,
                )

            logger.info(f"Recovery email change initiated for {email}")
            if task_logger:
                task_logger.event(
                    step="recovery_email",
                    action="success",
                    message=f"recovery email updated to {new_email}",
                    url=getattr(page, "url", ""),
                )
            return True, f"辅助邮箱已更改为 {new_email}"

        except Exception as e:
            logger.exception(f"Failed to change recovery email for {email}")
            if task_logger:
                task_logger.event(
                    step="recovery_email",
                    action="exception",
                    level="error",
                    message=str(e),
                    url=getattr(page, "url", ""),
                )
            return False, str(e)

    async def get_backup_codes(
        self,
        page: Page,
        account: Dict[str, Any],
        task_logger: Optional[TaskLogger] = None,
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
            if task_logger:
                task_logger.event(
                    step="backup_codes",
                    action="goto",
                    message="goto TWO_STEP_URL",
                    url=self.TWO_STEP_URL,
                )
            await page.goto(self.TWO_STEP_URL, wait_until="domcontentloaded")
            await asyncio.sleep(1)
            await self._handle_reauth(page, account)

            # 2. 点击 Backup codes（多语言兜底）
            clicked = await self._click_first_visible(
                [
                    page.get_by_text("Backup codes", exact=False),
                    page.get_by_text("备用验证码", exact=False),
                ]
            )
            if clicked:
                await asyncio.sleep(1)

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
                code = (code or "").strip().replace(" ", "")
                if code and len(code) == 8 and code.isdigit():
                    codes.append(code)

            if codes:
                logger.info(f"Got {len(codes)} backup codes for {email}")
                if task_logger:
                    task_logger.event(
                        step="backup_codes",
                        action="success",
                        message=f"got {len(codes)} backup codes",
                        url=getattr(page, "url", ""),
                    )
                return True, f"获取到 {len(codes)} 个备份验证码", codes

            if task_logger:
                task_logger.event(
                    step="backup_codes",
                    action="fail",
                    level="error",
                    message="no backup codes found",
                    url=getattr(page, "url", ""),
                )
            return False, "未能获取备份验证码", []

        except Exception as e:
            logger.exception(f"Failed to get backup codes for {email}")
            if task_logger:
                task_logger.event(
                    step="backup_codes",
                    action="exception",
                    level="error",
                    message=str(e),
                    url=getattr(page, "url", ""),
                )
            return False, str(e), []

    async def one_click_security_update(
        self,
        page: Page,
        account: Dict[str, Any],
        new_recovery_email: Optional[str] = None,
        task_logger: Optional[TaskLogger] = None,
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
        ok, msg, new_secret = await self.change_2fa_secret(
            page, account, task_logger=task_logger
        )
        if ok:
            result_data["new_2fa_secret"] = new_secret
            # 更新 account 中的密钥以便后续操作使用
            account["totp_secret"] = new_secret
        else:
            errors.append(f"2FA: {msg}")

        # 2. 获取备份验证码
        ok, msg, codes = await self.get_backup_codes(
            page, account, task_logger=task_logger
        )
        if ok:
            result_data["backup_codes"] = codes
        else:
            errors.append(f"Backup codes: {msg}")

        # 3. 修改辅助邮箱 (如果提供)
        if new_recovery_email:
            ok, msg = await self.change_recovery_email(
                page, account, new_recovery_email, task_logger=task_logger
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

#!/usr/bin/env python3
"""GeekezBrowser orchestration for this repo.

Responsibilities:
- Load `accounts.txt` as "environment" list
- Create/Update Geek profiles (name = email)
- Launch/Close profiles via Geek control API
- Run SheerLink / verify / bind-card / auto flows using Playwright

Keep BitBrowser flow intact: this module is standalone and only reuses shared
automation helpers (auto_bind_card / account_manager / sheerid_verifier).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import asyncio
import os
import re
import sys
import time
import threading
from urllib.parse import urlparse

from geek_browser_api import GeekezBrowserAPI, LaunchInfo


# Ensure repo root is importable (create_window.py, auto_bind_card.py, etc.)
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _base_dir() -> Path:
    # Follow existing scripts: when frozen, use executable dir.
    if getattr(sys, "frozen", False):
        return Path(os.path.dirname(sys.executable))
    return REPO_ROOT


def _log(msg: str, log_callback: Optional[Callable[[str], None]] = None) -> None:
    if log_callback:
        try:
            log_callback(msg)
            return
        except Exception:
            pass
    print(msg)


def load_accounts(accounts_file: Optional[Path] = None) -> List[Dict[str, Any]]:
    accounts_path = accounts_file or (_base_dir() / "accounts.txt")
    if not accounts_path.exists():
        return []

    separator = "----"
    lines = accounts_path.read_text(encoding="utf-8").splitlines()
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("分隔符=") or line.lower().startswith("separator="):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                separator = value
        break

    accounts: List[Dict[str, Any]] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("分隔符=") or line.lower().startswith("separator="):
            continue

        parts = [p.strip() for p in line.split(separator) if p.strip()]
        if not parts:
            continue

        email = parts[0]
        password = parts[1] if len(parts) > 1 else ""
        backup_email = parts[2] if len(parts) > 2 else ""
        twofa_secret = parts[3] if len(parts) > 3 else ""
        accounts.append(
            {
                "email": email,
                "password": password,
                "backup_email": backup_email,
                "2fa_secret": twofa_secret,
                "full_line": line,
            }
        )
    return accounts


def load_proxies(proxies_file: Optional[Path] = None) -> List[Dict[str, Any]]:
    proxies_path = proxies_file or (_base_dir() / "proxies.txt")
    if not proxies_path.exists():
        return []

    proxies: List[Dict[str, Any]] = []
    for raw in proxies_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("分隔符=") or line.lower().startswith("separator="):
            continue

        # Allow "host:port" as shorthand
        value = line if "://" in line else f"http://{line}"
        try:
            parsed = urlparse(value)
        except Exception:
            continue

        host = parsed.hostname
        port = parsed.port
        if not host or not port:
            continue

        scheme = (parsed.scheme or "").lower()
        ptype = "socks5" if scheme in {"socks5", "socks5h"} else "http"
        proxies.append(
            {
                "type": ptype,
                "host": host,
                "port": int(port),
                "username": parsed.username or "",
                "password": parsed.password or "",
            }
        )
    return proxies


def load_cards(cards_file: Optional[Path] = None) -> List[Dict[str, str]]:
    cards_path = cards_file or (_base_dir() / "cards.txt")
    if not cards_path.exists():
        return []

    cards: List[Dict[str, str]] = []
    for raw in cards_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("分隔符=") or line.lower().startswith("separator="):
            continue

        parts = line.split()
        if len(parts) < 4:
            continue
        cards.append(
            {
                "number": parts[0],
                "exp_month": parts[1],
                "exp_year": parts[2],
                "cvv": parts[3],
            }
        )
    return cards


def proxy_to_url(proxy: Dict[str, Any]) -> str:
    if not isinstance(proxy, dict):
        return ""
    ptype = (proxy.get("type") or "").lower()
    host = proxy.get("host") or ""
    port = proxy.get("port") or ""
    username = proxy.get("username") or ""
    password = proxy.get("password") or ""
    if not host or not port:
        return ""

    scheme = "socks5" if ptype == "socks5" else "http"
    if username and password:
        return f"{scheme}://{username}:{password}@{host}:{port}"
    return f"{scheme}://{host}:{port}"


def build_account_line(account: Dict[str, Any], link: Optional[str] = None) -> str:
    # Match other modules' expectations: `email----pwd----backup----secret`.
    email = (account.get("email") or "").strip()
    pwd = (account.get("password") or "").strip()
    backup = (account.get("backup_email") or "").strip()
    secret = (account.get("2fa_secret") or "").strip()
    parts = [email, pwd, backup, secret]
    joined = "----".join(parts)
    return f"{link}----{joined}" if link else joined


def to_auto_account_info(account: Dict[str, Any]) -> Dict[str, str]:
    # auto_bind_card.check_and_login expects keys: email/password/secret
    return {
        "email": (account.get("email") or "").strip(),
        "password": (account.get("password") or "").strip(),
        "secret": (account.get("2fa_secret") or "").strip(),
    }


@dataclass(frozen=True)
class EnvInfo:
    email: str
    profile_id: Optional[str]
    has_profile: bool


class GeekProcess:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 19527,
        data_dir: Optional[Path] = None,
        timeout_seconds: float = 8.0,
    ) -> None:
        self.api = GeekezBrowserAPI(
            host=host, port=port, data_dir=data_dir, timeout_seconds=timeout_seconds
        )
        self._profiles_lock = threading.Lock()

    # ------------------------------
    # Environments (accounts -> profiles)
    # ------------------------------
    def list_envs(
        self, accounts: Optional[List[Dict[str, Any]]] = None
    ) -> List[EnvInfo]:
        accounts = accounts or load_accounts()
        envs: List[EnvInfo] = []

        with self._profiles_lock:
            profiles = self.api.load_profiles()
        profile_by_name = {p.get("name"): p for p in profiles if isinstance(p, dict)}

        for acc in accounts:
            email = (acc.get("email") or "").strip()
            if not email:
                continue
            profile = profile_by_name.get(email)
            envs.append(
                EnvInfo(
                    email=email,
                    profile_id=profile.get("id") if profile else None,
                    has_profile=bool(profile),
                )
            )
        return envs

    def ensure_profile(
        self, account: Dict[str, Any], proxy_str: Optional[str] = None
    ) -> Dict[str, Any]:
        email = (account.get("email") or "").strip()
        if not email:
            raise ValueError("account.email is required")

        # Store account line as metadata for debugging / later lookup.
        metadata = {"remark": build_account_line(account)}
        with self._profiles_lock:
            return self.api.upsert_profile(
                name=email, proxy_str=proxy_str, metadata=metadata
            )

    def ensure_profiles(
        self,
        accounts: Optional[List[Dict[str, Any]]] = None,
        proxies: Optional[List[Dict[str, Any]]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> List[EnvInfo]:
        accounts = accounts or load_accounts()
        proxies = proxies or []

        _log(f"[Geek] accounts: {len(accounts)}", log_callback)
        _log(f"[Geek] proxies: {len(proxies)}", log_callback)

        for idx, acc in enumerate(accounts):
            email = (acc.get("email") or "").strip()
            if not email:
                continue

            proxy_str: Optional[str] = None
            if proxies:
                proxy_candidate = proxy_to_url(proxies[idx % len(proxies)])
                if proxy_candidate:
                    proxy_str = proxy_candidate

            profile = self.ensure_profile(acc, proxy_str=proxy_str)
            _log(f"[Geek] upsert profile: {email} ({profile.get('id')})", log_callback)

        return self.list_envs(accounts)

    # ------------------------------
    # Launch / Close
    # ------------------------------
    def launch_by_email(self, email: str) -> LaunchInfo:
        with self._profiles_lock:
            profile = self.api.find_profile_by_name(email)
        if not profile:
            raise RuntimeError(f"profile not found for email: {email}")

        if not self.api.is_running():
            raise RuntimeError(
                "GeekezBrowser control server not running (GET /health failed)"
            )

        return self.api.launch_profile(
            profile["id"], debug_port=0, enable_remote_debugging=True
        )

    def close_by_email(self, email: str) -> bool:
        with self._profiles_lock:
            profile = self.api.find_profile_by_name(email)
        if not profile:
            return False
        return self.api.close_profile(profile["id"])

    def close_by_profile_id(self, profile_id: str) -> bool:
        return self.api.close_profile(profile_id)

    # ------------------------------
    # Playwright automation (SheerLink / Auto)
    # ------------------------------
    async def _connect_page(self, cdp_endpoint: str):
        # Import lazily so this module can be imported without Playwright.
        try:
            import importlib

            async_api = importlib.import_module("playwright.async_api")
            async_playwright = getattr(async_api, "async_playwright")
        except Exception as e:
            raise RuntimeError(
                "Playwright 未安装或不可用，请先安装 playwright 并完成 `playwright install`"
            ) from e

        playwright = await async_playwright().start()
        browser = await playwright.chromium.connect_over_cdp(cdp_endpoint)
        context = (
            browser.contexts[0] if browser.contexts else await browser.new_context()
        )
        page = context.pages[0] if context.pages else await context.new_page()
        return playwright, browser, page

    @staticmethod
    async def _detect_status(page) -> str:
        text = ""
        try:
            text = await page.evaluate(
                "() => document.body ? document.body.innerText : ''"
            )
        except Exception:
            pass

        # Fallback to HTML
        try:
            text = f"{text}\n{await page.content()}"
        except Exception:
            pass

        lower = (text or "").lower()
        if "subscribed" in lower or "已订阅" in text:
            return "subscribed"
        if "get student offer" in lower or "获取学生优惠" in text:
            return "verified"
        if "verify your eligibility" in lower or "验证您的资格" in text:
            return "link_ready"
        if (
            "not available" in lower
            or "ineligible" in lower
            or "不可用" in text
            or "无资格" in text
        ):
            return "ineligible"
        return "error"

    @staticmethod
    async def _extract_sheerid_link(
        page, log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        # Try to click the eligibility button (best-effort; UI copies differ).
        for selector in [
            "text=verify your eligibility",
            "text=Verify your eligibility",
            "text=验证您的资格",
            "text=验证你的资格",
        ]:
            try:
                await page.click(selector, timeout=2000)
                await page.wait_for_timeout(1500)
                break
            except Exception:
                continue

        url = getattr(page, "url", "") or ""
        if "sheerid" in url:
            return url

        for frame in getattr(page, "frames", []):
            try:
                u = frame.url or ""
                if "sheerid" in u:
                    return u
            except Exception:
                continue

        try:
            html = await page.content()
        except Exception:
            html = ""

        match = re.search(r"https?://[^\s\"']*sheerid[^\s\"']*", html, re.IGNORECASE)
        if match:
            return match.group(0)

        _log("[Geek] SheerID link not found", log_callback)
        return None

    def run_sheerlink(
        self,
        account: Dict[str, Any],
        proxy_str: Optional[str] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, str]:
        """Extract SheerID link and persist to DB/files via AccountManager."""
        from account_manager import AccountManager
        from auto_bind_card import check_and_login

        email = (account.get("email") or "").strip()
        if not email:
            return False, "missing email"

        self.ensure_profile(account, proxy_str=proxy_str)
        launch = self.launch_by_email(email)

        async def _runner() -> Tuple[bool, str]:
            playwright = browser = None
            try:
                playwright, browser, page = await self._connect_page(
                    launch.cdp_endpoint
                )
                await page.goto(
                    "https://one.google.com/ai-student",
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )
                await page.wait_for_timeout(2000)

                await check_and_login(page, to_auto_account_info(account))
                await page.wait_for_timeout(1500)

                link = await self._extract_sheerid_link(page, log_callback=log_callback)
                if not link:
                    AccountManager.move_to_error(build_account_line(account))
                    return False, "link not found"

                AccountManager.save_link(build_account_line(account, link=link))
                return True, link
            finally:
                try:
                    if playwright:
                        await playwright.stop()
                except Exception:
                    pass

        try:
            ok, msg = asyncio.run(_runner())
            return ok, msg
        finally:
            self.close_by_profile_id(launch.profile_id)

    def run_auto(
        self,
        account: Dict[str, Any],
        card: Optional[Dict[str, str]] = None,
        api_key: str = "",
        proxy_str: Optional[str] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, str]:
        """Full flow: detect status -> (link extract + verify) -> bind card."""
        from account_manager import AccountManager
        from database import DBManager
        from auto_bind_card import check_and_login, auto_bind_card
        from sheerid_verifier import SheerIDVerifier

        email = (account.get("email") or "").strip()
        if not email:
            return False, "missing email"

        if not card:
            return False, "missing card"

        self.ensure_profile(account, proxy_str=proxy_str)
        launch = self.launch_by_email(email)

        async def _runner() -> Tuple[bool, str]:
            playwright = browser = None
            try:
                playwright, browser, page = await self._connect_page(
                    launch.cdp_endpoint
                )
                await page.goto(
                    "https://one.google.com/ai-student",
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )
                await page.wait_for_timeout(2000)

                await check_and_login(page, to_auto_account_info(account))
                await page.wait_for_timeout(1500)

                status = await self._detect_status(page)
                _log(f"[Geek] status: {email} -> {status}", log_callback)

                if status == "subscribed":
                    AccountManager.move_to_subscribed(build_account_line(account))
                    return True, "subscribed"

                if status == "ineligible":
                    AccountManager.move_to_ineligible(build_account_line(account))
                    return True, "ineligible"

                if status == "link_ready":
                    link = await self._extract_sheerid_link(
                        page, log_callback=log_callback
                    )
                    if not link:
                        AccountManager.move_to_error(build_account_line(account))
                        DBManager.update_status(
                            email, "error", message="link not found"
                        )
                        return False, "link not found"

                    AccountManager.save_link(build_account_line(account, link=link))

                    if not api_key:
                        # Without API key, we can only persist the link.
                        return True, "link saved (no api key)"

                    verifier = SheerIDVerifier(api_key=api_key)
                    success, vid, msg = await asyncio.to_thread(
                        verifier.verify_single, link
                    )
                    if not success:
                        AccountManager.move_to_error(
                            build_account_line(account, link=link)
                        )
                        DBManager.update_status(
                            email, "error", message=f"sheerid verify failed: {msg}"
                        )
                        return False, f"sheerid verify failed: {msg}"

                    AccountManager.move_to_verified(
                        build_account_line(account, link=link)
                    )
                    await page.reload(wait_until="domcontentloaded")
                    await page.wait_for_timeout(1500)
                    # Continue to bind card after verified.
                    status = "verified"

                if status == "verified":
                    ok, message = await auto_bind_card(
                        page, card, to_auto_account_info(account)
                    )
                    if ok:
                        AccountManager.move_to_subscribed(build_account_line(account))
                        DBManager.update_status(email, "subscribed", message=message)
                        return True, message

                    AccountManager.move_to_error(build_account_line(account))
                    DBManager.update_status(email, "error", message=message)
                    return False, message

                # Unknown state
                AccountManager.move_to_error(build_account_line(account))
                DBManager.update_status(
                    email, "error", message=f"unknown status: {status}"
                )
                return False, f"unknown status: {status}"
            finally:
                try:
                    if playwright:
                        await playwright.stop()
                except Exception:
                    pass

        try:
            ok, msg = asyncio.run(_runner())
            return ok, msg
        finally:
            self.close_by_profile_id(launch.profile_id)

    # -------------------------------------------
    # 订阅验证相关方法
    # -------------------------------------------

    def verify_subscription_status(
        self,
        account: Dict[str, Any],
        proxy_str: Optional[str] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        take_screenshot: bool = True,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        验证订阅状态并可选截图。

        返回: (is_subscribed, status_message, screenshot_path)

        状态说明:
        - subscribed: 已订阅
        - verified: 已验证学生身份，待订阅
        - link_ready: 需要验证学生身份
        - ineligible: 无资格
        - error: 未知状态
        """
        from account_manager import AccountManager
        from auto_bind_card import check_and_login

        email = (account.get("email") or "").strip()
        if not email:
            return False, "missing email", None

        self.ensure_profile(account, proxy_str=proxy_str)
        launch = self.launch_by_email(email)

        async def _runner() -> Tuple[bool, str, Optional[str]]:
            playwright = browser = None
            screenshot_path = None
            try:
                playwright, browser, page = await self._connect_page(
                    launch.cdp_endpoint
                )
                await page.goto(
                    "https://one.google.com/ai-student",
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )
                await page.wait_for_timeout(2000)

                await check_and_login(page, to_auto_account_info(account))
                await page.wait_for_timeout(1500)

                status = await self._detect_status(page)
                _log(f"[Geek] 订阅状态: {email} -> {status}", log_callback)

                is_subscribed = status == "subscribed"

                # 截图
                if take_screenshot:
                    try:
                        import os
                        from datetime import datetime

                        screenshots_dir = _base_dir() / "screenshots"
                        screenshots_dir.mkdir(parents=True, exist_ok=True)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        safe_email = email.replace("@", "_at_").replace(".", "_")
                        screenshot_path = str(
                            screenshots_dir / f"{safe_email}_{status}_{timestamp}.png"
                        )
                        await page.screenshot(path=screenshot_path, full_page=True)
                        _log(f"[Geek] 截图已保存: {screenshot_path}", log_callback)
                    except Exception as e:
                        _log(f"[Geek] 截图失败: {e}", log_callback)

                # 更新状态
                if status == "subscribed":
                    AccountManager.move_to_subscribed(build_account_line(account))
                elif status == "ineligible":
                    AccountManager.move_to_ineligible(build_account_line(account))

                return is_subscribed, status, screenshot_path
            finally:
                try:
                    if playwright:
                        await playwright.stop()
                except Exception:
                    pass

        try:
            result = asyncio.run(_runner())
            return result
        finally:
            self.close_by_profile_id(launch.profile_id)

    def click_subscribe_button(
        self,
        account: Dict[str, Any],
        proxy_str: Optional[str] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, str]:
        """
        点击 Subscribe 按钮进行订阅。

        返回: (success, message)

        前提: 账号已验证学生身份(verified状态)
        """
        from auto_bind_card import check_and_login

        email = (account.get("email") or "").strip()
        if not email:
            return False, "missing email"

        self.ensure_profile(account, proxy_str=proxy_str)
        launch = self.launch_by_email(email)

        async def _runner() -> Tuple[bool, str]:
            playwright = browser = None
            try:
                playwright, browser, page = await self._connect_page(
                    launch.cdp_endpoint
                )
                await page.goto(
                    "https://one.google.com/ai-student",
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )
                await page.wait_for_timeout(2000)

                await check_and_login(page, to_auto_account_info(account))
                await page.wait_for_timeout(1500)

                # 查找并点击 Subscribe 按钮
                subscribe_selectors = [
                    'button:has-text("Subscribe")',
                    'button:has-text("订阅")',
                    'button:has-text("Get student offer")',
                    'button:has-text("获取学生优惠")',
                    'text="Subscribe"',
                    'text="订阅"',
                    '[data-action="subscribe"]',
                ]

                clicked = False
                for selector in subscribe_selectors:
                    try:
                        elem = page.locator(selector)
                        if await elem.count() > 0:
                            await elem.first.click()
                            clicked = True
                            _log(f"[Geek] 点击订阅按钮成功: {selector}", log_callback)
                            await page.wait_for_timeout(2000)
                            break
                    except Exception:
                        continue

                if not clicked:
                    _log(f"[Geek] 未找到订阅按钮", log_callback)
                    return False, "Subscribe button not found"

                # 检查是否有确认对话框
                confirm_result = await self._handle_confirmation_dialog(
                    page, log_callback
                )

                return confirm_result

            finally:
                try:
                    if playwright:
                        await playwright.stop()
                except Exception:
                    pass

        try:
            ok, msg = asyncio.run(_runner())
            return ok, msg
        finally:
            self.close_by_profile_id(launch.profile_id)

    def check_confirmation_dialog(
        self,
        account: Dict[str, Any],
        proxy_str: Optional[str] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, str]:
        """
        检查并处理确认对话框。

        返回: (has_dialog, message)

        用途: 处理订阅流程中可能出现的确认弹窗
        """
        from auto_bind_card import check_and_login

        email = (account.get("email") or "").strip()
        if not email:
            return False, "missing email"

        self.ensure_profile(account, proxy_str=proxy_str)
        launch = self.launch_by_email(email)

        async def _runner() -> Tuple[bool, str]:
            playwright = browser = None
            try:
                playwright, browser, page = await self._connect_page(
                    launch.cdp_endpoint
                )
                await page.goto(
                    "https://one.google.com/ai-student",
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )
                await page.wait_for_timeout(2000)

                await check_and_login(page, to_auto_account_info(account))
                await page.wait_for_timeout(1500)

                return await self._handle_confirmation_dialog(page, log_callback)

            finally:
                try:
                    if playwright:
                        await playwright.stop()
                except Exception:
                    pass

        try:
            ok, msg = asyncio.run(_runner())
            return ok, msg
        finally:
            self.close_by_profile_id(launch.profile_id)

    @staticmethod
    async def _handle_confirmation_dialog(
        page,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, str]:
        """
        处理确认对话框的内部方法。

        查找并点击 Confirm/Continue/OK 等确认按钮。
        """
        # 检查是否有对话框
        dialog_selectors = [
            '[role="dialog"]',
            '[role="alertdialog"]',
            ".modal",
            '[class*="dialog"]',
            '[class*="modal"]',
        ]

        has_dialog = False
        for selector in dialog_selectors:
            try:
                elem = page.locator(selector)
                if await elem.count() > 0:
                    has_dialog = True
                    _log(f"[Geek] 检测到对话框: {selector}", log_callback)
                    break
            except Exception:
                continue

        # 查找确认按钮
        confirm_selectors = [
            'button:has-text("Confirm")',
            'button:has-text("确认")',
            'button:has-text("Continue")',
            'button:has-text("继续")',
            'button:has-text("OK")',
            'button:has-text("确定")',
            'button:has-text("Yes")',
            'button:has-text("是")',
            'button:has-text("Accept")',
            'button:has-text("接受")',
            'button:has-text("Agree")',
            'button:has-text("同意")',
        ]

        for selector in confirm_selectors:
            try:
                elem = page.locator(selector)
                if await elem.count() > 0:
                    await elem.first.click()
                    _log(f"[Geek] 点击确认按钮: {selector}", log_callback)
                    await page.wait_for_timeout(1500)
                    return True, "confirmed"
            except Exception:
                continue

        if has_dialog:
            return True, "dialog found but no confirm button"

        return False, "no dialog"

    def verify_result(
        self,
        account: Dict[str, Any],
        proxy_str: Optional[str] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        验证操作结果（成功/失败）并截图。

        返回: (is_success, result_type, screenshot_path)

        result_type: "success", "error", "pending", "unknown"
        """
        from auto_bind_card import check_and_login

        email = (account.get("email") or "").strip()
        if not email:
            return False, "missing email", None

        self.ensure_profile(account, proxy_str=proxy_str)
        launch = self.launch_by_email(email)

        async def _runner() -> Tuple[bool, str, Optional[str]]:
            playwright = browser = None
            screenshot_path = None
            try:
                playwright, browser, page = await self._connect_page(
                    launch.cdp_endpoint
                )
                await page.goto(
                    "https://one.google.com/ai-student",
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )
                await page.wait_for_timeout(2000)

                await check_and_login(page, to_auto_account_info(account))
                await page.wait_for_timeout(1500)

                # 获取页面文本
                page_text = ""
                try:
                    page_text = await page.evaluate(
                        "() => document.body ? document.body.innerText : ''"
                    )
                except Exception:
                    pass

                lower_text = page_text.lower()

                # 检测结果类型
                result_type = "unknown"
                is_success = False

                # 成功关键词
                success_keywords = [
                    "success",
                    "successful",
                    "complete",
                    "completed",
                    "subscribed",
                    "thank you",
                    "welcome",
                    "成功",
                    "完成",
                    "已订阅",
                    "谢谢",
                    "欢迎",
                ]

                # 错误关键词
                error_keywords = [
                    "error",
                    "failed",
                    "declined",
                    "rejected",
                    "invalid",
                    "expired",
                    "problem",
                    "issue",
                    "错误",
                    "失败",
                    "拒绝",
                    "无效",
                    "过期",
                    "问题",
                ]

                for kw in success_keywords:
                    if kw in lower_text:
                        result_type = "success"
                        is_success = True
                        break

                if result_type == "unknown":
                    for kw in error_keywords:
                        if kw in lower_text:
                            result_type = "error"
                            break

                _log(f"[Geek] 结果检测: {email} -> {result_type}", log_callback)

                # 截图
                try:
                    from datetime import datetime

                    screenshots_dir = _base_dir() / "screenshots"
                    screenshots_dir.mkdir(parents=True, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_email = email.replace("@", "_at_").replace(".", "_")
                    screenshot_path = str(
                        screenshots_dir
                        / f"{safe_email}_result_{result_type}_{timestamp}.png"
                    )
                    await page.screenshot(path=screenshot_path, full_page=True)
                    _log(f"[Geek] 结果截图: {screenshot_path}", log_callback)
                except Exception as e:
                    _log(f"[Geek] 截图失败: {e}", log_callback)

                return is_success, result_type, screenshot_path

            finally:
                try:
                    if playwright:
                        await playwright.stop()
                except Exception:
                    pass

        try:
            result = asyncio.run(_runner())
            return result
        finally:
            self.close_by_profile_id(launch.profile_id)


__all__ = [
    "GeekProcess",
    "EnvInfo",
    "load_accounts",
    "load_proxies",
    "load_cards",
]

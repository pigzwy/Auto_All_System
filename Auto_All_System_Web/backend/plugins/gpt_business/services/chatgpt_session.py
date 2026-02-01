from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable


logger = logging.getLogger(__name__)


class NeedsRegistrationError(RuntimeError):
    """Raised when the flow reaches account creation / email verification screens."""



def fetch_auth_session(page, *, timeout: int = 7) -> dict[str, Any]:
    """从 https://chatgpt.com/api/auth/session 获取 session JSON。

    这里用 fetch('/api/auth/session')，避免受页面渲染影响。
    """
    js = f"""
        return Promise.race([
          fetch('/api/auth/session', {{ method: 'GET', credentials: 'include' }})
            .then(r => r.json())
            .then(d => JSON.stringify(d))
            .catch(() => '{{}}'),
          new Promise((_, reject) => setTimeout(() => reject('timeout'), {timeout * 1000}))
        ]).catch(() => '{{}}');
    """.strip()

    try:
        raw = page.run_js(js, timeout=timeout + 2)
    except Exception:
        return {}

    if not raw or raw == "{}":
        return {}
    try:
        data = json.loads(raw)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _get_access_token_and_email(session_data: dict[str, Any]) -> tuple[str, str]:
    token = str(session_data.get("accessToken") or "").strip()
    user = session_data.get("user")
    email = str(user.get("email") or "").strip() if isinstance(user, dict) else ""
    return token, email


def ensure_access_token(
    page,
    *,
    email: str,
    password: str,
    timeout: int = 120,
    log_callback: Callable[[str], None] | None = None,
    screenshot_callback: Callable[[str], None] | None = None,
) -> tuple[str, dict[str, Any]]:
    """确保已登录指定账号并返回 accessToken。

    - 如果已登录且邮箱匹配：直接返回
    - 如果已登录但邮箱不匹配：尝试登出再登录
    - 否则：走登录流程
    """
    target_email = (email or "").strip()
    if not target_email:
        raise ValueError("missing email")
    if not (password or "").strip():
        raise ValueError("missing password")

    def _log(msg: str):
        try:
            if log_callback:
                log_callback(msg)
        except Exception:
            pass
        logger.info(msg)

    def _shot(name: str):
        try:
            if screenshot_callback:
                screenshot_callback(name)
        except Exception:
            pass

    def _probe(tag: str):
        """输出当前页面的轻量状态，便于排查 selector/跳转问题。"""
        try:
            js = """
                try {
                  const q = (sel) => document.querySelectorAll(sel).length;
                  const href = location.href;
                  const title = document.title || '';
                  const inputs = q('input');
                  const emailInputs = q('input[type="email"],input[name="email"],input[id="email"],input[name="username"],input[id="username"],input[autocomplete="username"],input[autocomplete="email"],input[inputmode="email"]');
                  const passwordInputs = q('input[type="password"],input[name="password"],input[id="password"],input[autocomplete="current-password"],input[autocomplete="new-password"]');
                  const submitButtons = q('button[type="submit"]');
                  return JSON.stringify({href, title, inputs, emailInputs, passwordInputs, submitButtons});
                } catch (e) {
                  return JSON.stringify({error: String(e)});
                }
            """.strip()
            raw = page.run_js(js, timeout=2)
            if raw:
                _log(f"[{tag}] probe={raw}")
        except Exception:
            return

    email_selector = (
        'css:input[type="email"], input[name="email"], input[id="email"], '
        'input[name="username"], input[id="username"], '
        'input[autocomplete="username"], input[autocomplete="email"], input[inputmode="email"]'
    )
    password_selector = (
        'css:input[type="password"], input[name="password"], input[id="password"], '
        'input[autocomplete="current-password"], input[autocomplete="new-password"]'
    )

    _log(f"ensure_access_token start email={target_email}")
    try:
        _probe("start")
        _shot("invite_login_00_start.png")
    except Exception:
        pass

    def _poll_session(deadline: float) -> tuple[str, dict[str, Any]]:
        last: dict[str, Any] = {}
        while time.time() < deadline:
            last = fetch_auth_session(page, timeout=7)
            token, current_email = _get_access_token_and_email(last)
            if token and current_email and current_email.lower() == target_email.lower():
                return token, last
            time.sleep(1.0)
        return "", last

    deadline = time.time() + max(10, int(timeout))

    # 1) 先看当前 session
    session = fetch_auth_session(page, timeout=7)
    token, current_email = _get_access_token_and_email(session)
    if current_email:
        _log(f"session found user={current_email}")
    if token:
        _log(f"session accessToken len={len(token)}")
    if token and current_email and current_email.lower() == target_email.lower():
        _log("session already matches target user")
        return token, session

    # 2) 如果登录了别的账号，尝试登出
    if token and current_email and current_email.lower() != target_email.lower():
        _log(f"session user mismatch (current={current_email}, target={target_email}), trying logout")
        try:
            from .openai_register import logout_current_account

            logout_current_account(page)
        except Exception as e:
            logger.warning(f"logout failed: {e}")
        _probe("after_logout")
        _shot("invite_login_00b_after_logout.png")

    # 2.5) 先去首页看下是否已登录（有些 profile 会自动带 cookie）
    try:
        _log("open chatgpt.com homepage")
        page.get("https://chatgpt.com/")
        time.sleep(2)
        _probe("home")
        _shot("invite_login_00c_home.png")
        token2, sess2 = _poll_session(time.time() + 8)
        if token2:
            _log("got accessToken from existing cookies")
            return token2, sess2
    except Exception:
        pass

    # 3) 登录流程
    try:
        from .openai_register import human_delay, wait_for_element, wait_for_page_stable, wait_for_url_change, type_slowly

        page.get("https://chatgpt.com/auth/login")
        time.sleep(2)
        wait_for_page_stable(page, timeout=8)
        _probe("login_page")
        _shot("invite_login_01_login_page.png")

        # 新版 chatgpt.com/auth/login 可能先展示一个 "Log in" 按钮（点击后才进入 auth.openai.com）
        try:
            login_btn = wait_for_element(page, 'css:button[data-testid="login-button"]', timeout=3)
            if login_btn:
                _log("click chatgpt.com login-button")
                login_btn.click()
                human_delay(0.8, 1.6)
                _probe("after_login_button")
                _shot("invite_login_01c_after_login_button.png")
        except Exception:
            pass

        # 登录页可能会跳转到 auth.openai.com
        max_steps = 10
        forced_auth0 = False
        for step in range(max_steps):
            current_url = page.url or ""
            _log(f"login step {step + 1}: {current_url}")
            _probe(f"step_{step + 1}")

            # a) 已回到 chatgpt 且拿到 session
            sess_data = fetch_auth_session(page, timeout=7)
            token3, email3 = _get_access_token_and_email(sess_data)
            if token3 and email3 and email3.lower() == target_email.lower():
                return token3, sess_data

            # b) chatgpt.com 弹窗模式：直接输入 email
            if "chatgpt.com" in current_url and "auth.openai.com" not in current_url:
                # 某些版本在 /auth/login 会先出现 login-button，点击后才进入真正的登录流程
                if "/auth/login" in current_url:
                    if not forced_auth0 and step >= 2:
                        _log("still stuck on /auth/login, open auth.openai.com directly")
                        try:
                            page.get("https://auth.openai.com/log-in-or-create-account")
                            human_delay(0.8, 1.6)
                            _probe("force_auth0")
                            _shot("invite_login_force_auth0.png")
                        except Exception:
                            pass
                        forced_auth0 = True
                        time.sleep(1)
                        continue

                    try:
                        login_btn = wait_for_element(page, 'css:button[data-testid="login-button"]', timeout=2)
                        if login_btn:
                            _log("click chatgpt.com login-button (loop)")
                            login_btn.click()
                            human_delay(0.8, 1.6)
                            _probe("after_login_button_loop")
                            _shot("invite_login_01d_after_login_button_loop.png")
                            time.sleep(1)
                            continue
                    except Exception:
                        pass

                email_input = wait_for_element(
                    page,
                    email_selector,
                    timeout=5,
                )

                # 有些版本会先出现“Continue with email/使用邮箱继续”按钮
                if not email_input:
                    btn = wait_for_element(page, "text:Continue with email", timeout=2)
                    if not btn:
                        btn = wait_for_element(page, "text:使用邮箱继续", timeout=2)
                    if not btn:
                        btn = wait_for_element(page, "text:使用电子邮件继续", timeout=2)
                    if btn:
                        _log("click 'Continue with email'")
                        btn.click()
                        human_delay(0.6, 1.2)
                        _probe("after_continue_with_email")
                        _shot("invite_login_01b_after_continue_with_email.png")
                        email_input = wait_for_element(
                            page,
                            email_selector,
                            timeout=6,
                        )

                if email_input:
                    _log("fill email on chatgpt.com login")
                    human_delay()
                    type_slowly(page, email_selector, target_email)
                    _shot("invite_login_02_email_filled.png")
                    human_delay(0.5, 1.0)
                    submit_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=5)
                    if submit_btn:
                        _log("click submit after email")
                        old_url = current_url
                        submit_btn.click()
                        wait_for_url_change(page, old_url, timeout=12)
                        human_delay(0.8, 1.2)
                        _probe("after_email_submit")
                        _shot("invite_login_02b_after_email_submit.png")
                    time.sleep(1)
                    continue

            # c) auth.openai.com：邮箱页
            if "auth.openai.com/log-in-or-create-account" in current_url:
                _log("auth.openai.com email/identifier page")
                email_input = wait_for_element(page, email_selector, timeout=10)
                if not email_input:
                    _shot("invite_login_err_email_input_missing.png")
                    raise RuntimeError(f"login email input not found (url={current_url})")
                human_delay()
                type_slowly(page, email_selector, target_email)
                _shot("invite_login_03_auth0_email_filled.png")
                human_delay(0.5, 1.2)
                submit_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=5)
                if submit_btn:
                    _log("click submit on auth0 email page")
                    old_url = current_url
                    submit_btn.click()
                    wait_for_url_change(page, old_url, timeout=15)
                    _probe("after_auth0_email_submit")
                    _shot("invite_login_03b_after_auth0_email_submit.png")
                time.sleep(1)
                continue

            # d) auth.openai.com：密码页
            if "auth.openai.com/create-account/password" in current_url:
                _log("auth.openai.com create-account password page detected; require registration + email verification")
                _shot("invite_login_need_register.png")
                raise NeedsRegistrationError("account needs registration (create-account/password)")

            if "auth.openai.com/email-verification" in current_url:
                _log("auth.openai.com email verification page detected; require registration flow")
                _shot("invite_login_need_email_verification.png")
                raise NeedsRegistrationError("account needs email verification")

            if "auth.openai.com/log-in/password" in current_url:
                _log("auth.openai.com password page")
                password_input = wait_for_element(page, password_selector, timeout=10)
                if not password_input:
                    _shot("invite_login_err_password_input_missing.png")
                    raise RuntimeError(f"login password input not found (url={current_url})")
                human_delay()
                type_slowly(page, password_selector, str(password))
                _shot("invite_login_04_auth0_password_filled.png")
                human_delay(0.5, 1.2)
                submit_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=5)
                if submit_btn:
                    _log("click submit on auth0 password page")
                    old_url = current_url
                    submit_btn.click()
                    wait_for_url_change(page, old_url, timeout=20)
                    _probe("after_auth0_password_submit")
                    _shot("invite_login_04b_after_auth0_password_submit.png")
                time.sleep(2)
                continue

            # e) auth.openai.com 新版路径兼容（例如 /u/login/identifier /u/login/password）
            if "auth.openai.com" in current_url or "auth0.openai.com" in current_url:
                email_input = wait_for_element(page, email_selector, timeout=2)
                if email_input:
                    _log("auth0 generic page: found email input")
                    human_delay()
                    type_slowly(page, email_selector, target_email)
                    _shot("invite_login_03b_auth0_email_filled.png")
                    human_delay(0.5, 1.2)
                    submit_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=5)
                    if submit_btn:
                        _log("auth0 generic page: click submit after email")
                        old_url = current_url
                        submit_btn.click()
                        wait_for_url_change(page, old_url, timeout=20)
                    time.sleep(1)
                    continue

                password_input = wait_for_element(page, password_selector, timeout=2)
                if password_input:
                    _log("auth0 generic page: found password input")
                    human_delay()
                    type_slowly(page, password_selector, str(password))
                    _shot("invite_login_04b_auth0_password_filled.png")
                    human_delay(0.5, 1.2)
                    submit_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=5)
                    if submit_btn:
                        _log("auth0 generic page: click submit after password")
                        old_url = current_url
                        submit_btn.click()
                        wait_for_url_change(page, old_url, timeout=25)
                    time.sleep(2)
                    continue

            time.sleep(1)
    except Exception as e:
        if isinstance(e, NeedsRegistrationError):
            # 让调用方走 register_openai_account（会拉邮件验证码）
            raise
        _log(f"login flow exception: {e}")
        _shot("invite_login_err_exception.png")

    # 登录动作完成后，回到 chatgpt.com 再拿一次 session
    try:
        _log("navigate back to chatgpt.com to fetch session")
        page.get("https://chatgpt.com/")
        time.sleep(2)
        _probe("back_home")
        _shot("invite_login_99_back_to_chatgpt.png")
    except Exception:
        pass

    token, session = _poll_session(min(deadline, time.time() + 30))
    if not token:
        raise RuntimeError(f"failed to obtain accessToken from /api/auth/session (url={page.url or ''})")
    _log(f"got accessToken len={len(token)}")
    return token, session

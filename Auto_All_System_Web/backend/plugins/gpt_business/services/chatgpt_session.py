from __future__ import annotations

import json
import logging
import random
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
    get_verification_code: Callable[[str], str | None] | None = None,
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

    def _handle_workspace_chooser() -> bool:
        """处理 workspace 选择页/弹窗，优先选择团队工作区并避免 Personal account。"""
        js_detect_chooser = """
        (function() {
            try {
                var lower = function(v) { return String(v || '').toLowerCase(); };
                var compact = function(v) { return String(v || '').replace(/\\s+/g, ' ').trim(); };
                var currentUrl = lower(location.href || '');
                var dialog = document.querySelector('[role="dialog"]');
                var dialogText = lower(compact(dialog ? dialog.innerText : ''));
                var hasChooserText =
                    dialogText.indexOf('select a workspace') !== -1 ||
                    dialogText.indexOf('choose a workspace') !== -1 ||
                    dialogText.indexOf('选择工作区') !== -1 ||
                    dialogText.indexOf('工作区') !== -1;
                var hasChooser = currentUrl.indexOf('/workspace') !== -1 || hasChooserText;
                return hasChooser ? 'yes' : 'no';
            } catch (e) {
                return 'error:' + String(e);
            }
        })();
        """

        try:
            detected = str(page.run_js(js_detect_chooser, timeout=3) or "")
        except Exception:
            detected = ""
        if detected != "yes":
            return False

        _log("detected workspace chooser, selecting non-personal workspace")
        _shot("workspace_chooser.png")

        js_pick_workspace = """
        (function() {
            try {
                var lower = function(v) { return String(v || '').toLowerCase(); };
                var compact = function(v) { return String(v || '').replace(/\\s+/g, ' ').trim(); };
                var isVisible = function(el) {
                    if (!el) return false;
                    var style = window.getComputedStyle(el);
                    if (!style) return false;
                    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
                    var rect = el.getBoundingClientRect();
                    return !!rect && rect.width > 0 && rect.height > 0;
                };

                var currentUrl = lower(location.href || '');
                var dialog = document.querySelector('[role="dialog"]');
                var dialogText = lower(compact(dialog ? dialog.innerText : ''));
                var hasChooserText =
                    dialogText.indexOf('select a workspace') !== -1 ||
                    dialogText.indexOf('choose a workspace') !== -1 ||
                    dialogText.indexOf('选择工作区') !== -1 ||
                    dialogText.indexOf('工作区') !== -1;
                var hasChooser = currentUrl.indexOf('/workspace') !== -1 || hasChooserText;
                if (!hasChooser) return 'no_chooser';

                var root = dialog || document;
                var selectors = [
                    'button[name="workspace_id"]',
                    '[role="group"] button[role="radio"]',
                    'button[role="radio"]',
                    '[data-radix-collection-item][role="radio"]'
                ];
                var all = [];
                var seen = new Set();
                for (var si = 0; si < selectors.length; si++) {
                    var items = root.querySelectorAll(selectors[si]);
                    for (var i = 0; i < items.length; i++) {
                        var el = items[i];
                        if (!el || seen.has(el) || !isVisible(el)) continue;
                        seen.add(el);
                        all.push(el);
                    }
                }
                if (!all.length) return 'no_buttons';

                var personalPhrases = ['personal account', '个人账号', '个人账户'];
                var teamBtn = null;
                var texts = [];

                for (var bi = 0; bi < all.length; bi++) {
                    var btn = all[bi];
                    var txt = compact(btn.innerText || btn.textContent || '');
                    if (!txt) continue;
                    texts.push(txt.slice(0, 80));
                    var lo = lower(txt);
                    var isPersonal = false;
                    for (var pi = 0; pi < personalPhrases.length; pi++) {
                        if (lo.indexOf(personalPhrases[pi]) !== -1) {
                            isPersonal = true;
                            break;
                        }
                    }
                    if (!isPersonal && !teamBtn) {
                        teamBtn = btn;
                    }
                }

                if (!teamBtn) {
                    return 'team_not_found:' + texts.join(' | ').slice(0, 240);
                }

                var chosen = compact(teamBtn.innerText || teamBtn.textContent || '');
                teamBtn.click();
                return 'clicked:' + chosen.slice(0, 120);
            } catch (e) {
                return 'error:' + String(e);
            }
        })();
        """

        try:
            from .openai_register import human_delay

            click_result = "not_run"
            for _attempt in range(2):
                click_result = str(page.run_js(js_pick_workspace, timeout=6) or "")
                _log(f"workspace chooser click result: {click_result}")
                if click_result.startswith("clicked:"):
                    break
                time.sleep(1.0)

            if not click_result.startswith("clicked:"):
                return False

            human_delay(0.3, 0.8)
            time.sleep(1.5)
            _probe("after_workspace_select")
            _shot("workspace_after_select.png")
            return True
        except Exception as e:
            _log(f"workspace chooser handling failed: {e}")
            return False

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
        _handle_workspace_chooser()
        _probe("home")
        _shot("invite_login_00c_home.png")
        token2, sess2 = _poll_session(time.time() + 8)
        if token2:
            _log("got accessToken from existing cookies")
            return token2, sess2
    except Exception:
        pass

    # 2.6) 检查 "Welcome back / Choose an account" 页面
    # 某些情况下 chatgpt.com 首页会展示账号选择卡片，点击即可登录（无需重走 auth 流程）
    try:
        from .openai_register import human_delay

        _log("check for 'Welcome back / Choose an account' page")

        # 用 JS 精确查找账号卡片：
        # - 必须是可点击元素 (button, a, li, [role=button])
        # - 包含目标邮箱文本
        # - 排除含有 "verification" / "验证码" / "code" 等验证相关文本
        # - 元素文本长度合理（账号卡片文本不会太长）
        js_find_and_click = """
        (function() {
            var email = '__EMAIL__'.toLowerCase();
            var excludeWords = ['verification', 'verify', 'code', '验证', '验证码', 'sent to', '发送'];
            var selectors = 'button, a, li, [role="button"], [role="listitem"], [data-testid*="account"]';
            var elements = document.querySelectorAll(selectors);
            for (var i = 0; i < elements.length; i++) {
                var el = elements[i];
                var text = (el.textContent || '').trim();
                var textLower = text.toLowerCase();
                // 必须包含邮箱
                if (textLower.indexOf(email) === -1) continue;
                // 文本不能太长（账号卡片通常不超过 120 字符，排除大段文本）
                if (text.length > 150) continue;
                // 排除验证码相关元素
                var excluded = false;
                for (var j = 0; j < excludeWords.length; j++) {
                    if (textLower.indexOf(excludeWords[j]) !== -1) { excluded = true; break; }
                }
                if (excluded) continue;
                // 确保元素可见
                var rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) continue;
                el.click();
                return 'clicked: ' + text.substring(0, 80);
            }
            return 'not_found';
        })();
        """.replace("__EMAIL__", target_email.lower().replace("'", "\\'"))

        click_result = page.run_js(js_find_and_click, timeout=5)
        _log(f"account card JS result: {click_result}")

        if click_result and click_result != "not_found":
            time.sleep(3)
            _probe("after_account_card_click")
            _shot("invite_login_00d_after_account_click.png")

            # 等待登录完成并获取 session
            token_ac, sess_ac = _poll_session(time.time() + 20)
            if token_ac:
                _log("got accessToken from account card click")
                return token_ac, sess_ac
            _log("account card click did not yield session, continuing to login flow")
    except Exception as e:
        _log(f"account card detection failed: {e}")

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

            # a2) 工作区选择页面 — 自动选择后重新检查 session
            if _handle_workspace_chooser():
                sess_data = fetch_auth_session(page, timeout=7)
                token3, email3 = _get_access_token_and_email(sess_data)
                if token3 and email3 and email3.lower() == target_email.lower():
                    return token3, sess_data
                continue

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
                    # Use the element we just located; selector may match hidden inputs.
                    type_slowly(page, email_input, target_email)
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
                # Use the element we just located; selector may match hidden inputs.
                type_slowly(page, email_input, target_email)
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

            # d) auth.openai.com：创建账号密码页（账号不存在，需要注册）
            if "auth.openai.com/create-account/password" in current_url:
                _log("auth.openai.com create-account/password page (new account)")
                _shot("invite_login_create_account_password.png")

                # 有密码就直接填写继续注册流程，后续会走验证码页面
                password_input = wait_for_element(page, password_selector, timeout=10)
                if not password_input:
                    _shot("invite_login_err_create_password_input_missing.png")
                    raise NeedsRegistrationError("account needs registration (create-account/password input not found)")
                human_delay()
                type_slowly(page, password_input, str(password))
                _log("filled password on create-account page")
                _shot("invite_login_create_account_password_filled.png")
                human_delay(0.5, 1.2)
                submit_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=5)
                if submit_btn:
                    _log("click submit on create-account password page")
                    old_url = current_url
                    submit_btn.click()
                    wait_for_url_change(page, old_url, timeout=20)
                    _probe("after_create_account_password_submit")
                    _shot("invite_login_create_account_password_submitted.png")
                time.sleep(2)
                continue

            if "auth.openai.com/email-verification" in current_url:
                # 检查页面标题：如果已经是 "Email verified" 说明验证码已提交成功，等待跳转即可
                try:
                    page_title = page.title or ""
                except Exception:
                    page_title = ""

                if "verified" in page_title.lower() or "已验证" in page_title:
                    _log(f"email already verified (title={page_title}), waiting for redirect...")
                    # 等待页面自动跳转离开 email-verification
                    for _wait_i in range(15):
                        time.sleep(2)
                        try:
                            new_url = page.url or ""
                            if "email-verification" not in new_url:
                                _log(f"redirected to: {new_url}")
                                break
                        except Exception:
                            break
                    time.sleep(1)
                    continue

                _log("auth.openai.com email verification page (passwordless login)")
                _shot("invite_login_email_verification.png")

                if not get_verification_code:
                    _log("no get_verification_code callback, cannot handle email verification")
                    raise NeedsRegistrationError("account needs email verification (no callback)")

                _log(f"waiting for verification code for {target_email}...")
                code = get_verification_code(target_email)
                if not code:
                    _log("failed to get verification code")
                    raise RuntimeError("verification code not received")

                _log(f"got verification code, len={len(code)}")

                # 填写验证码（复用 register_openai_account 中的逻辑）
                code_inputs = page.eles(
                    'css:input[name="code"], input[autocomplete="one-time-code"], '
                    'input[inputmode="numeric"], input[type="tel"], '
                    'input[placeholder*="代码"], input[placeholder*="code"]'
                )
                code_inputs = [x for x in (code_inputs or []) if x]

                if not code_inputs:
                    _log("verification code input not found on page")
                    raise RuntimeError("verification code input not found")

                digits = [c for c in code if c.isdigit()]
                if len(code_inputs) >= 6 and len(digits) >= 6:
                    # 多输入框：逐个填入
                    for ci in range(6):
                        try:
                            code_inputs[ci].click()
                            time.sleep(0.08)
                            code_inputs[ci].input(digits[ci], clear=True)
                            time.sleep(0.08)
                        except Exception:
                            pass
                else:
                    # 单输入框
                    try:
                        code_inputs[0].clear()
                    except Exception:
                        pass
                    try:
                        type_slowly(page, code_inputs[0], code, base_delay=0.08)
                    except Exception:
                        pass

                time.sleep(0.6)
                submit_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=10)
                if submit_btn:
                    _log("submit verification code")
                    submit_btn.click()
                    # 验证码提交后等待页面变化（标题变化或 URL 变化）
                    for _wait_i in range(15):
                        time.sleep(2)
                        try:
                            new_title = page.title or ""
                            new_url = page.url or ""
                            if "verified" in new_title.lower() or "已验证" in new_title:
                                _log(f"verification successful (title={new_title})")
                                break
                            if "email-verification" not in new_url:
                                _log(f"redirected after verification to: {new_url}")
                                break
                        except Exception:
                            break
                    _probe("after_verification_submit")
                    _shot("invite_login_after_verification.png")

                time.sleep(2)
                continue

            # d2) auth.openai.com about-you 页面（注册新账号后需要填写姓名+生日）
            if "auth.openai.com/onboarding/about-you" in current_url or "about-you" in current_url:
                _log("auth.openai.com about-you page (name + birthday)")
                _shot("invite_login_about_you.png")

                random_name = f"{random.choice(['Tom', 'John', 'Mike', 'David', 'James'])} {random.choice(['Smith', 'Lee', 'Wang', 'Brown', 'Wilson'])}"
                year = str(random.randint(1990, 2000))
                month = f"{random.randint(1, 12):02d}"
                day = f"{random.randint(1, 28):02d}"
                birthday_mmddyyyy = f"{month}/{day}/{year}"

                # Full name
                name_input = wait_for_element(page, 'css:input[name="name"]', timeout=5)
                if not name_input:
                    name_input = wait_for_element(page, 'css:input[autocomplete="name"]', timeout=3)
                if not name_input:
                    name_input = wait_for_element(page, 'css:input[aria-label*="name"], input[aria-label*="Name"]', timeout=3)
                if not name_input:
                    name_input = wait_for_element(page, 'css:input[placeholder*="name"], input[placeholder*="Name"], input[placeholder*="James"]', timeout=3)

                if name_input:
                    _log(f"fill name: {random_name}")
                    human_delay()
                    type_slowly(page, name_input, random_name)
                else:
                    _log("about-you: name input not found, skip")

                # Birthday — 优先单输入框，兜底分段输入
                bday_input = wait_for_element(
                    page,
                    'css:input[aria-label="Birthday"], input[name*="birth"], input[autocomplete*="bday"], input[aria-label*="Birth"], input[aria-label*="birth"], input[placeholder*="/"]',
                    timeout=6,
                )
                if bday_input:
                    _log(f"fill birthday (single): {birthday_mmddyyyy}")
                    try:
                        bday_input.click()
                        time.sleep(0.12)
                        bday_input.input(birthday_mmddyyyy, clear=True)
                    except Exception:
                        try:
                            type_slowly(page, bday_input, birthday_mmddyyyy)
                        except Exception:
                            _log("about-you: birthday fill failed")
                else:
                    year_input = wait_for_element(page, 'css:[data-type="year"]', timeout=3)
                    month_input = wait_for_element(page, 'css:[data-type="month"]', timeout=3) if year_input else None
                    day_input = wait_for_element(page, 'css:[data-type="day"]', timeout=3) if year_input else None
                    if year_input and month_input and day_input:
                        _log(f"fill birthday (segments): {year}/{month}/{day}")
                        try:
                            year_input.click()
                            time.sleep(0.15)
                            year_input.input(year, clear=True)
                            time.sleep(0.2)
                            month_input.click()
                            time.sleep(0.15)
                            month_input.input(month, clear=True)
                            time.sleep(0.2)
                            day_input.click()
                            time.sleep(0.15)
                            day_input.input(day, clear=True)
                        except Exception:
                            _log("about-you: birthday segment fill failed")
                    else:
                        _log("about-you: birthday input not found")

                time.sleep(0.6)
                submit_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=8)
                if not submit_btn:
                    submit_btn = wait_for_element(page, 'text:Continue', timeout=3)
                if submit_btn:
                    _log("click submit on about-you page")
                    old_url = current_url
                    submit_btn.click()
                    wait_for_url_change(page, old_url, timeout=20)
                    _probe("after_about_you_submit")
                    _shot("invite_login_about_you_after_submit.png")
                time.sleep(2)
                continue

            if "auth.openai.com/log-in/password" in current_url:
                _log("auth.openai.com password page")
                password_input = wait_for_element(page, password_selector, timeout=10)
                if not password_input:
                    _shot("invite_login_err_password_input_missing.png")
                    raise RuntimeError(f"login password input not found (url={current_url})")
                human_delay()
                # Use the element we just located; selector may match hidden inputs.
                type_slowly(page, password_input, str(password))
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
                    # Use the element we just located; selector may match hidden inputs.
                    type_slowly(page, email_input, target_email)
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
                    # Use the element we just located; selector may match hidden inputs.
                    type_slowly(page, password_input, str(password))
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
        _handle_workspace_chooser()
        _probe("back_home")
        _shot("invite_login_99_back_to_chatgpt.png")
    except Exception:
        pass

    token, session = _poll_session(min(deadline, time.time() + 30))
    if not token:
        raise RuntimeError(f"failed to obtain accessToken from /api/auth/session (url={page.url or ''})")
    _log(f"got accessToken len={len(token)}")
    return token, session

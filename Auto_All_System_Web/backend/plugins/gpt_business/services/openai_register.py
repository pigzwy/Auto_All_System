# ==================== OpenAI 注册服务 ====================
# 直接从 oai-team-auto-provisioner/browser_automation.py 移植
# 使用 DrissionPage 进行浏览器自动化

import time
import random
import logging
from typing import Optional, Callable

from DrissionPage import ChromiumPage, ChromiumOptions

logger = logging.getLogger(__name__)


# ==================== 常量配置 ====================
TYPING_DELAY = 0.08  # 打字延迟
ACTION_DELAY = (0.3, 0.8)  # 操作间隔


def connect_to_browser(debug_port: int) -> ChromiumPage:
    """连接到已运行的 Geekez 浏览器
    
    Args:
        debug_port: Geekez 启动浏览器后返回的调试端口
        
    Returns:
        ChromiumPage: DrissionPage 浏览器实例
    """
    co = ChromiumOptions()
    co.set_local_port(debug_port)
    page = ChromiumPage(co)
    logger.info(f"已连接到浏览器端口 {debug_port}")
    return page


def wait_for_page_stable(page, timeout: int = 10, check_interval: float = 0.5) -> bool:
    """等待页面稳定"""
    start_time = time.time()
    last_html_len = 0
    stable_count = 0
    
    while time.time() - start_time < timeout:
        try:
            ready_state = page.run_js('return document.readyState', timeout=2)
            if ready_state != 'complete':
                stable_count = 0
                time.sleep(check_interval)
                continue
            
            current_len = len(page.html)
            if current_len == last_html_len:
                stable_count += 1
                if stable_count >= 3:
                    return True
            else:
                stable_count = 0
                last_html_len = current_len
            time.sleep(check_interval)
        except Exception:
            time.sleep(check_interval)
    
    return False


def wait_for_element(page, selector: str, timeout: int = 10, visible: bool = True):
    """等待元素出现"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            element = page.ele(selector, timeout=1)
            if element:
                if not visible or (element.states.is_displayed if hasattr(element, 'states') else True):
                    return element
        except Exception:
            pass
        time.sleep(0.3)
    
    return None


def wait_for_url_change(page, old_url: str, timeout: int = 15, contains: str | None = None) -> bool:
    """等待 URL 变化"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            current_url = page.url
            if current_url != old_url:
                if contains is None or contains in current_url:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    
    return False


def type_slowly(page, selector_or_element, text, base_delay=None):
    """缓慢输入文本"""
    if base_delay is None:
        base_delay = TYPING_DELAY
    
    if isinstance(selector_or_element, str):
        element = page.ele(selector_or_element, timeout=10)
    else:
        element = selector_or_element

    if not text:
        return

    # 短文本直接输入
    if len(text) <= 8:
        element.input(text, clear=True)
        return

    # 长文本逐字符输入
    element.input(text[0], clear=True)
    time.sleep(random.uniform(0.1, 0.2))

    for char in text[1:]:
        element.input(char, clear=False)
        actual_delay = base_delay * random.uniform(0.5, 1.2)
        if char in ' @._-':
            actual_delay *= 1.3
        time.sleep(actual_delay)


def human_delay(min_sec: float | None = None, max_sec: float | None = None):
    """模拟人类操作间隔"""
    if min_sec is None:
        min_sec = ACTION_DELAY[0]
    if max_sec is None:
        max_sec = ACTION_DELAY[1]
    time.sleep(random.uniform(min_sec, max_sec))


def is_logged_in(page, timeout: int = 5) -> tuple[bool, str]:
    """检测是否已登录 ChatGPT
    
    Returns:
        tuple: (是否登录, 登录邮箱)
    """
    try:
        result = page.run_js(f'''
            return Promise.race([
                fetch('/api/auth/session', {{
                    method: 'GET',
                    credentials: 'include'
                }})
                .then(r => r.json())
                .then(data => JSON.stringify(data))
                .catch(e => '{{}}'),
                new Promise((_, reject) => setTimeout(() => reject('timeout'), {timeout * 1000}))
            ]).catch(() => '{{}}');
        ''', timeout=timeout + 2)

        if result and result != '{}':
            import json
            data = json.loads(result)
            if data.get('user') and data.get('accessToken'):
                user_email = data['user'].get('email', '')
                logger.info(f"已登录: {user_email}")
                return True, user_email
        return False, ""
    except Exception as e:
        logger.warning(f"登录检测异常: {e}")
        return False, ""


def logout_current_account(page) -> bool:
    """登出当前账号"""
    try:
        logger.info("登出当前账号...")
        
        profile_btn = page.ele('[data-testid="profile-button"], [aria-label*="profile"]', timeout=5)
        if profile_btn:
            profile_btn.click()
            time.sleep(1)
            
            logout_btn = page.ele('text:Log out', timeout=3)
            if not logout_btn:
                logout_btn = page.ele('text:退出登录', timeout=2)
            
            if logout_btn:
                logout_btn.click()
                time.sleep(2)
                logger.info("已登出")
                return True
        
        page.get("https://chatgpt.com/auth/logout")
        time.sleep(2)
        return True
    except Exception as e:
        logger.warning(f"登出失败: {e}")
        return False


def register_openai_account(
    page,
    email: str,
    password: str,
    get_verification_code: Callable[[str], Optional[str]] | None = None,
    log_callback: Callable[[str], None] | None = None,
    screenshot_callback: Callable[[str], None] | None = None,
) -> bool:
    """使用浏览器注册 OpenAI 账号
    
    Args:
        page: DrissionPage 浏览器实例
        email: 邮箱地址
        password: 密码
        get_verification_code: 获取验证码的回调函数
        log_callback: 日志回调
        screenshot_callback: 截图回调
        
    Returns:
        bool: 是否成功
    """
    def _log(msg):
        logger.info(msg)
        if log_callback:
            log_callback(msg)
    
    def _shot(name):
        if screenshot_callback:
            screenshot_callback(name)

    def _complete_about_you_page() -> bool:
        """填写 about-you / 年龄确认页面。

        页面可能是三段生日输入(year/month/day)，也可能是单个 Birthday 输入框。
        """
        _log("个人信息页面")
        _shot("05_about_you.png")

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

        if not name_input:
            _log("无法找到姓名输入框")
            _shot("about_you_name_missing.png")
            return False

        _log(f"输入姓名: {random_name}")
        try:
            type_slowly(page, name_input, random_name)
        except Exception:
            _shot("about_you_name_fill_failed.png")
            return False

        # Birthday
        # 优先按页面真实可见的单输入框（截图显示 aria-label="Birthday"）填写；分段输入仅作为兜底。
        bday_input = wait_for_element(
            page,
            'css:input[aria-label="Birthday"], input[name*="birth"], input[autocomplete*="bday"], input[aria-label*="Birth"], input[aria-label*="birth"], input[placeholder*="/"]',
            timeout=6,
        )
        if bday_input:
            _log(f"输入生日(单框): {birthday_mmddyyyy}")
            try:
                bday_input.click()
                time.sleep(0.12)
                bday_input.input(birthday_mmddyyyy, clear=True)
            except Exception:
                try:
                    type_slowly(page, bday_input, birthday_mmddyyyy)
                except Exception:
                    _shot("about_you_birthday_fill_failed.png")
                    return False
        else:
            # 分段输入
            year_input = wait_for_element(page, 'css:[data-type="year"]', timeout=3)
            month_input = wait_for_element(page, 'css:[data-type="month"]', timeout=3) if year_input else None
            day_input = wait_for_element(page, 'css:[data-type="day"]', timeout=3) if year_input else None
            if year_input and month_input and day_input:
                _log(f"输入生日(分段): {year}/{month}/{day}")
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
                    _shot("about_you_birthday_fill_failed.png")
                    return False
            else:
                _log("无法找到生日输入框")
                _shot("about_you_birthday_missing.png")
                return False

        _log("生日已输入")

        time.sleep(0.6)
        submit_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=8)
        if not submit_btn:
            submit_btn = wait_for_element(page, 'text:Continue', timeout=3)
        if not submit_btn:
            _log("无法找到 Continue 按钮")
            _shot("about_you_continue_missing.png")
            return False

        # 按钮可能处于 disabled（未真正填入/未触发校验），这种情况下不要误点并跳走。
        try:
            disabled = page.run_js(
                """
                const btn = document.querySelector('button[type="submit"]');
                return btn ? !!btn.disabled : null;
                """.strip(),
                timeout=2,
            )
            if disabled is True:
                _log("Continue 按钮为 disabled，说明表单未生效")
                _shot("about_you_continue_disabled.png")
                return False
        except Exception:
            pass

        old_url = page.url
        try:
            submit_btn.click()
        except Exception:
            _shot("about_you_continue_click_failed.png")
            return False

        # 等待跳转离开 about-you（成功时一般会重定向回 chatgpt.com 或进入后续 step）
        for _ in range(20):
            time.sleep(0.5)
            if page.url != old_url and "about-you" not in (page.url or ""):
                break
        _shot("about_you_after_submit.png")

        # 如果仍停留在 about-you，说明提交未生效
        if "about-you" in (page.url or ""):
            _log("提交后仍停留在 about-you，可能未通过校验")
            return False

        return True

    def _wait_target_session(target_email: str, timeout_sec: int = 60) -> tuple[bool, str]:
        """在 chatgpt.com 上轮询 /api/auth/session，确认是否已登录目标账号。"""
        start = time.time()
        last_email = ""
        while time.time() - start < timeout_sec:
            ok, current_email = is_logged_in(page, timeout=7)
            if current_email:
                last_email = current_email
            if ok and current_email and current_email.lower() == target_email.lower():
                return True, current_email
            time.sleep(2)
        return False, last_email

    _log(f"开始注册 OpenAI 账号: {email}")

    try:
        # 打开注册页面
        url = "https://chatgpt.com"
        _log(f"打开 {url}")
        page.get(url)

        # 等待页面加载
        wait_for_page_stable(page, timeout=8)
        _shot("01_homepage.png")
        _log(f"页面加载完成: {page.url}")

        # 检查是否已登录
        try:
            logged_in, current_email = is_logged_in(page)
            if logged_in:
                if current_email.lower() == email.lower():
                    _log(f"已登录目标账号: {email}")
                    return True
                else:
                    _log(f"已登录其他账号 ({current_email})，需要登出...")
                    logout_current_account(page)
                    page.get(url)
                    wait_for_page_stable(page, timeout=8)
                    _log("已登出其他账号，继续注册流程")
        except Exception:
            pass

        # 点击注册按钮
        _log("点击注册按钮...")
        signup_btn = wait_for_element(page, 'css:[data-testid="signup-button"]', timeout=5)
        if not signup_btn:
            signup_btn = wait_for_element(page, 'text:免费注册', timeout=3)
        if not signup_btn:
            signup_btn = wait_for_element(page, 'text:Sign up', timeout=3)

        # 新版可能需要先进入 /auth/login 才能看到注册入口
        if not signup_btn:
            try:
                page.get("https://chatgpt.com/auth/login")
                wait_for_page_stable(page, timeout=8)
            except Exception:
                pass
            signup_btn = wait_for_element(page, 'css:button[data-testid="signup-button"]', timeout=5)
            if not signup_btn:
                signup_btn = wait_for_element(page, 'text:Sign up', timeout=3)
            if not signup_btn:
                signup_btn = wait_for_element(page, 'text:Create account', timeout=3)
            if not signup_btn:
                signup_btn = wait_for_element(page, 'text:注册', timeout=2)
        
        if not signup_btn:
            _log("无法找到注册按钮")
            _shot("02_signup_button_not_found.png")
            return False

        if signup_btn:
            old_url = page.url
            _log("点击注册按钮 (signup-button)")
            signup_btn.click()
            # 等待 URL 变化或弹窗出现
            for _ in range(6):
                time.sleep(0.5)
                if page.url != old_url:
                    break
                try:
                    email_input = page.ele(
                        'css:input[type="email"], input[name="email"], input[id="email"], input[name="username"], input[id="username"]',
                        timeout=1,
                    )
                    if email_input and email_input.states.is_displayed:
                        break
                except Exception:
                    pass

        _shot("02_after_signup_click.png")
        current_url = page.url
        _log(f"注册按钮点击后: {current_url}")

        # 如果还在 chatgpt.com（弹窗模式）
        if "auth.openai.com" not in current_url and "chatgpt.com" in current_url:
            _log("弹窗模式，输入邮箱...")
            
            email_input = wait_for_element(page, 'css:input[type="email"], input[name="email"], input[id="email"]', timeout=5)
            if email_input:
                human_delay()
                type_slowly(page, 'css:input[type="email"], input[name="email"], input[id="email"]', email)
                _log("邮箱已输入")

                # 点击继续 (使用 button[type="submit"])
                human_delay(0.5, 1.0)
                _log("点击继续...")
                continue_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=5)
                if continue_btn:
                    old_url = page.url
                    continue_btn.click()
                    wait_for_url_change(page, old_url, timeout=10, contains="/password")

        _shot("03_after_email.png")

        def _is_auth0_email_page(url_text: str) -> bool:
            return (
                "auth.openai.com/log-in-or-create-account" in url_text
                or "auth.openai.com/u/login/identifier" in url_text
            )

        def _is_auth0_password_page(url_text: str) -> bool:
            return (
                "auth.openai.com/log-in/password" in url_text
                or "auth.openai.com/create-account/password" in url_text
                or "auth.openai.com/u/login/password" in url_text
                or "auth.openai.com/u/signup/password" in url_text
            )

        # 状态机循环处理注册流程
        max_steps = 15
        fallback_auth_login_done = False
        force_auth0_count = 0
        max_force_auth0_count = 3
        for step in range(max_steps):
            current_url = page.url
            _log(f"注册流程步骤 {step + 1}: {current_url}")

            # 如果在 chatgpt.com 且已登录，注册成功
            if "chatgpt.com" in current_url and "auth.openai.com" not in current_url:
                try:
                    logged_in, current_email = is_logged_in(page)
                    if logged_in and current_email and current_email.lower() == email.lower():
                        _log(f"检测到已登录({current_email})，账号已注册成功")
                        return True
                    if logged_in and current_email and current_email.lower() != email.lower():
                        _log(f"检测到已登录其他账号({current_email})，登出后继续注册")
                        logout_current_account(page)
                        page.get(url)
                        wait_for_page_stable(page, timeout=8)
                        continue
                except Exception:
                    pass

                # 卡在 chatgpt.com（弹窗没弹出来/没跳转 auth0）时，兜底走 /auth/login 点击 signup-button
                if not fallback_auth_login_done and step >= 2:
                    fallback_auth_login_done = True
                    try:
                        _log("仍未进入 auth0，尝试打开 /auth/login 并点击 signup-button")
                        page.get("https://chatgpt.com/auth/login")
                        wait_for_page_stable(page, timeout=8)
                        _shot("fallback_auth_login.png")
                        old_url = page.url
                        signup_btn = wait_for_element(page, 'css:button[data-testid="signup-button"]', timeout=6)
                        if signup_btn:
                            try:
                                signup_btn.click()
                            except Exception:
                                try:
                                    page.run_js(
                                        'var b=document.querySelector(\'button[data-testid="signup-button"]\'); if (b) { b.click(); }',
                                        timeout=2,
                                    )
                                except Exception:
                                    pass
                            wait_for_url_change(page, old_url, timeout=15)
                            _shot("fallback_after_signup_click.png")
                            continue
                    except Exception:
                        pass

            # 明确处理：卡在 chatgpt.com/auth/login 时，直接跳转 auth0（避免按钮点击无反应）
            if "chatgpt.com/auth/login" in current_url:
                if force_auth0_count >= max_force_auth0_count:
                    _log("多次强制跳转 auth0 仍失败，终止注册流程")
                    _shot("force_auth0_exceeded.png")
                    return False
                try:
                    _log("卡在 /auth/login，尝试直接打开 auth.openai.com/log-in-or-create-account")
                    page.get("https://auth.openai.com/log-in-or-create-account")
                    wait_for_page_stable(page, timeout=8)
                    _shot("force_auth0_from_auth_login.png")
                    force_auth0_count += 1
                    continue
                except Exception:
                    pass

            # 步骤1: 输入邮箱
            if _is_auth0_email_page(current_url):
                _log("邮箱输入页面")
                email_input = wait_for_element(
                    page,
                    'css:input[type="email"], input[name="email"], input[name="username"], input[id="username"], input[autocomplete="username"], input[autocomplete="email"]',
                    timeout=15,
                )
                if not email_input:
                    _log("无法找到邮箱输入框")
                    return False

                human_delay()
                type_slowly(page, email_input, email)
                _log("邮箱已输入")

                human_delay(0.5, 1.2)
                continue_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=5)
                if continue_btn:
                    old_url = page.url
                    continue_btn.click()
                    wait_for_url_change(page, old_url, timeout=10)
                continue

            # 步骤2: 输入密码
            if _is_auth0_password_page(current_url):
                _log("密码输入页面")
                _shot(f"step{step}_password.png")
                
                password_input = wait_for_element(page, 'css:input[type="password"]', timeout=5)
                if not password_input:
                    _log("无法找到密码输入框")
                    return False

                human_delay()
                type_slowly(page, password_input, password)
                _log("密码已输入")

                human_delay(0.5, 1.2)
                continue_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=5)
                if continue_btn:
                    old_url = page.url
                    continue_btn.click()
                    time.sleep(2)
                    wait_for_url_change(page, old_url, timeout=10)
                continue

            # 步骤3: 验证码页面（URL 可能是 /email-verification 或 /u/email-verification 等）
            if "email-verification" in current_url and "auth.openai.com" in current_url:
                break

            # 步骤4: 个人信息页面
            if "about-you" in current_url and "auth.openai.com" in current_url:
                break

            time.sleep(0.5)

        # 检查当前页面状态
        current_url = page.url
        _shot("04_after_loop.png")

        # 如果已在 chatgpt.com 且已登录
        if "chatgpt.com" in current_url and "auth.openai.com" not in current_url:
            try:
                logged_in, current_email = is_logged_in(page)
                if logged_in and current_email and current_email.lower() == email.lower():
                    _log(f"账号已注册成功({current_email})")
                    return True
                if logged_in and current_email and current_email.lower() != email.lower():
                    _log(f"检测到已登录其他账号({current_email})，登出后继续注册")
                    logout_current_account(page)
                    page.get(url)
                    wait_for_page_stable(page, timeout=8)
            except Exception:
                pass

        # 个人信息页面
        if "about-you" in current_url and "auth.openai.com" in current_url:
            ok = _complete_about_you_page()
            if not ok:
                _log("个人信息页面处理失败")
                return False

            try:
                page.get(url)
                wait_for_page_stable(page, timeout=8)
                ok, current_email = _wait_target_session(email, timeout_sec=60)
                if ok:
                    _log(f"注册完成: {current_email}")
                    return True
            except Exception:
                pass

            _log("个人信息提交后仍未登录")
            _shot("about_you_login_not_ready.png")
            return False

        # 验证码页面
        if "email-verification" in current_url and "auth.openai.com" in current_url:
            _log("邮箱验证码页面")
            _shot("05_verification.png")

            if not get_verification_code:
                _log("没有提供验证码获取函数")
                return False

            verification_code = get_verification_code(email)
            if not verification_code:
                _log("无法获取验证码")
                return False

            _log(f"输入验证码: ****** (len={len(verification_code)})")

            # 兼容多种验证码输入形态：单输入框 / 多个分隔输入框 / one-time-code
            code_inputs = page.eles(
                'css:input[name="code"], input[autocomplete="one-time-code"], input[inputmode="numeric"], input[type="tel"], input[placeholder*="代码"], input[placeholder*="code"]'
            )
            code_inputs = [x for x in (code_inputs or []) if x]

            if not code_inputs:
                _log("无法找到验证码输入框")
                return False

            digits = [c for c in verification_code if c.isdigit()]
            if len(code_inputs) >= 6 and len(digits) >= 6:
                # 多输入框：逐个填入
                for i in range(6):
                    try:
                        code_inputs[i].click()
                        time.sleep(0.08)
                        code_inputs[i].input(digits[i], clear=True)
                        time.sleep(0.08)
                    except Exception:
                        pass
            else:
                # 单输入框：直接填入
                try:
                    try:
                        code_inputs[0].clear()
                    except Exception:
                        pass
                    type_slowly(
                        page,
                        'css:input[name="code"], input[autocomplete="one-time-code"], input[inputmode="numeric"], input[type="tel"], input[placeholder*="代码"], input[placeholder*="code"]',
                        verification_code,
                        base_delay=0.08,
                    )
                except Exception:
                    pass

            time.sleep(0.6)

            continue_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=10)
            if continue_btn:
                continue_btn.click()

            time.sleep(2)
            _shot("06_after_verification.png")

            # 等待个人信息页面
            current_url = page.url
            if "about-you" in current_url and "auth.openai.com" in current_url:
                ok = _complete_about_you_page()
                if not ok:
                    _log("个人信息页面处理失败")
                    return False

            # 最终回到 chatgpt.com 校验是否真的登录成功
            try:
                page.get(url)
                wait_for_page_stable(page, timeout=8)
                ok, current_email = _wait_target_session(email, timeout_sec=60)
                if ok:
                    _shot("07_registered.png")
                    _log(f"注册完成: {current_email}")
                    return True
            except Exception:
                pass

            _log("验证码提交后仍未登录/注册未完成")
            _shot("registration_incomplete.png")
            return False

        _log(f"注册流程异常，当前页面: {current_url}")
        return False

    except Exception as e:
        _log(f"注册失败: {e}")
        _shot("error.png")
        return False

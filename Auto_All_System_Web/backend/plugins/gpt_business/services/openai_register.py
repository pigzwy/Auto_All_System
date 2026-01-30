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


def wait_for_url_change(page, old_url: str, timeout: int = 15, contains: str = None) -> bool:
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


def human_delay(min_sec: float = None, max_sec: float = None):
    """模拟人类操作间隔"""
    if min_sec is None:
        min_sec = ACTION_DELAY[0]
    if max_sec is None:
        max_sec = ACTION_DELAY[1]
    time.sleep(random.uniform(min_sec, max_sec))


def is_logged_in(page, timeout: int = 5) -> bool:
    """检测是否已登录 ChatGPT"""
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
                logger.info(f"已登录: {data['user'].get('email', 'unknown')}")
                return True
        return False
    except Exception as e:
        logger.warning(f"登录检测异常: {e}")
        return False


def register_openai_account(
    page,
    email: str,
    password: str,
    get_verification_code: Callable[[str], Optional[str]] = None,
    log_callback: Callable[[str], None] = None,
    screenshot_callback: Callable[[str], None] = None,
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
            if is_logged_in(page):
                _log("检测到已登录，跳过注册步骤")
                return True
        except Exception:
            pass

        # 点击注册按钮
        _log("点击注册按钮...")
        signup_btn = wait_for_element(page, 'css:[data-testid="signup-button"]', timeout=5)
        if not signup_btn:
            signup_btn = wait_for_element(page, 'text:免费注册', timeout=3)
        if not signup_btn:
            signup_btn = wait_for_element(page, 'text:Sign up', timeout=3)
        
        if signup_btn:
            old_url = page.url
            signup_btn.click()
            # 等待 URL 变化或弹窗出现
            for _ in range(6):
                time.sleep(0.5)
                if page.url != old_url:
                    break
                try:
                    email_input = page.ele('css:input[type="email"], input[name="email"]', timeout=1)
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

        # 状态机循环处理注册流程
        max_steps = 10
        for step in range(max_steps):
            current_url = page.url
            _log(f"注册流程步骤 {step + 1}: {current_url}")

            # 如果在 chatgpt.com 且已登录，注册成功
            if "chatgpt.com" in current_url and "auth.openai.com" not in current_url:
                try:
                    if is_logged_in(page):
                        _log("检测到已登录，账号已注册成功")
                        return True
                except Exception:
                    pass

            # 步骤1: 输入邮箱
            if "auth.openai.com/log-in-or-create-account" in current_url:
                _log("邮箱输入页面")
                email_input = wait_for_element(page, 'css:input[type="email"]', timeout=15)
                if not email_input:
                    _log("无法找到邮箱输入框")
                    return False

                human_delay()
                type_slowly(page, 'css:input[type="email"]', email)
                _log("邮箱已输入")

                human_delay(0.5, 1.2)
                continue_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=5)
                if continue_btn:
                    old_url = page.url
                    continue_btn.click()
                    wait_for_url_change(page, old_url, timeout=10)
                continue

            # 步骤2: 输入密码
            if "auth.openai.com/log-in/password" in current_url or "auth.openai.com/create-account/password" in current_url:
                _log("密码输入页面")
                _shot(f"step{step}_password.png")
                
                password_input = wait_for_element(page, 'css:input[type="password"]', timeout=5)
                if not password_input:
                    _log("无法找到密码输入框")
                    return False

                human_delay()
                type_slowly(page, 'css:input[type="password"]', password)
                _log("密码已输入")

                human_delay(0.5, 1.2)
                continue_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=5)
                if continue_btn:
                    old_url = page.url
                    continue_btn.click()
                    time.sleep(2)
                    wait_for_url_change(page, old_url, timeout=10)
                continue

            # 步骤3: 验证码页面
            if "auth.openai.com/email-verification" in current_url:
                break

            # 步骤4: 个人信息页面
            if "auth.openai.com/about-you" in current_url:
                break

            time.sleep(0.5)

        # 检查当前页面状态
        current_url = page.url
        _shot("04_after_loop.png")

        # 如果已在 chatgpt.com 且已登录
        if "chatgpt.com" in current_url and "auth.openai.com" not in current_url:
            try:
                if is_logged_in(page):
                    _log("账号已注册成功")
                    return True
            except Exception:
                pass

        # 个人信息页面
        if "auth.openai.com/about-you" in current_url:
            _log("个人信息页面")
            _shot("05_about_you.png")
            
            # 输入姓名
            name_input = wait_for_element(page, 'css:input[name="name"]', timeout=5)
            if not name_input:
                name_input = wait_for_element(page, 'css:input[autocomplete="name"]', timeout=3)
            
            random_name = f"{random.choice(['Tom', 'John', 'Mike', 'David', 'James'])} {random.choice(['Smith', 'Lee', 'Wang', 'Brown', 'Wilson'])}"
            _log(f"输入姓名: {random_name}")
            type_slowly(page, 'css:input[name="name"], input[autocomplete="name"]', random_name)

            # 输入生日
            year = str(random.randint(1990, 2000))
            month = f"{random.randint(1, 12):02d}"
            day = f"{random.randint(1, 28):02d}"
            _log(f"输入生日: {year}/{month}/{day}")

            year_input = wait_for_element(page, 'css:[data-type="year"]', timeout=10)
            if year_input:
                year_input.click()
                time.sleep(0.15)
                year_input.input(year, clear=True)
                time.sleep(0.2)

            month_input = wait_for_element(page, 'css:[data-type="month"]', timeout=5)
            if month_input:
                month_input.click()
                time.sleep(0.15)
                month_input.input(month, clear=True)
                time.sleep(0.2)

            day_input = wait_for_element(page, 'css:[data-type="day"]', timeout=5)
            if day_input:
                day_input.click()
                time.sleep(0.15)
                day_input.input(day, clear=True)

            _log("生日已输入")

            time.sleep(0.5)
            submit_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=5)
            if submit_btn:
                submit_btn.click()

            time.sleep(2)
            _shot("06_after_about_you.png")
            _log(f"注册完成: {email}")
            return True

        # 验证码页面
        if "auth.openai.com/email-verification" in current_url:
            _log("邮箱验证码页面")
            _shot("05_verification.png")

            if not get_verification_code:
                _log("没有提供验证码获取函数")
                return False

            verification_code = get_verification_code(email)
            if not verification_code:
                _log("无法获取验证码")
                return False

            _log(f"输入验证码: {verification_code}")
            code_input = wait_for_element(page, 'css:input[name="code"]', timeout=10)
            if not code_input:
                code_input = wait_for_element(page, 'css:input[placeholder*="代码"]', timeout=5)

            if not code_input:
                _log("无法找到验证码输入框")
                return False

            try:
                code_input.clear()
            except Exception:
                pass
            type_slowly(page, 'css:input[name="code"], input[placeholder*="代码"]', verification_code, base_delay=0.08)
            time.sleep(0.5)

            continue_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=10)
            if continue_btn:
                continue_btn.click()

            time.sleep(2)
            _shot("06_after_verification.png")

            # 等待个人信息页面
            current_url = page.url
            if "auth.openai.com/about-you" in current_url:
                _log("个人信息页面")
                
                # 输入姓名
                random_name = f"{random.choice(['Tom', 'John', 'Mike', 'David', 'James'])} {random.choice(['Smith', 'Lee', 'Wang', 'Brown', 'Wilson'])}"
                _log(f"输入姓名: {random_name}")
                name_input = wait_for_element(page, 'css:input[name="name"]', timeout=15)
                if not name_input:
                    name_input = wait_for_element(page, 'css:input[autocomplete="name"]', timeout=5)
                type_slowly(page, 'css:input[name="name"], input[autocomplete="name"]', random_name)

                # 输入生日
                year = str(random.randint(1990, 2000))
                month = f"{random.randint(1, 12):02d}"
                day = f"{random.randint(1, 28):02d}"
                _log(f"输入生日: {year}/{month}/{day}")

                year_input = wait_for_element(page, 'css:[data-type="year"]', timeout=10)
                if year_input:
                    year_input.click()
                    time.sleep(0.15)
                    year_input.input(year, clear=True)
                    time.sleep(0.2)

                month_input = wait_for_element(page, 'css:[data-type="month"]', timeout=5)
                if month_input:
                    month_input.click()
                    time.sleep(0.15)
                    month_input.input(month, clear=True)
                    time.sleep(0.2)

                day_input = wait_for_element(page, 'css:[data-type="day"]', timeout=5)
                if day_input:
                    day_input.click()
                    time.sleep(0.15)
                    day_input.input(day, clear=True)

                _log("生日已输入")

                continue_btn = wait_for_element(page, 'css:button[type="submit"]', timeout=10)
                if continue_btn:
                    continue_btn.click()

                time.sleep(2)
                _shot("07_registered.png")

            _log(f"注册完成: {email}")
            return True

        _log(f"注册流程异常，当前页面: {current_url}")
        return False

    except Exception as e:
        _log(f"注册失败: {e}")
        _shot("error.png")
        return False

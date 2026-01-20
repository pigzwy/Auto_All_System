"""
GPT 自动化核心模块
- 自动登录 ChatGPT
- 检测订阅状态
- 处理 2FA 验证
"""
import asyncio
import time
import pyotp
import re
import os
import sys
from playwright.async_api import async_playwright, Page

# 添加父目录到路径以便导入共用模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bit_api import openBrowser, closeBrowser
from create_window import get_browser_list, get_browser_info


def get_base_path():
    """获取基础路径"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


async def gpt_handle_2fa(page: Page, secret_key: str, log_callback=None):
    """
    处理 GPT 2FA 验证
    
    Args:
        page: Playwright Page 对象
        secret_key: 2FA 密钥
        log_callback: 日志回调函数
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)
    
    try:
        # 检查是否出现 2FA 输入框
        totp_selectors = [
            'input[name="code"]',
            'input[type="text"][autocomplete="one-time-code"]',
            'input[placeholder*="code"]',
            'input[placeholder*="验证"]',
        ]
        
        for selector in totp_selectors:
            try:
                totp_input = await page.wait_for_selector(selector, timeout=5000)
                if totp_input and await totp_input.is_visible():
                    log("🔐 检测到 2FA 验证...")
                    
                    if not secret_key:
                        log("❌ 缺少 2FA 密钥")
                        return False
                    
                    # 生成验证码
                    clean_secret = secret_key.replace(" ", "").strip()
                    totp = pyotp.TOTP(clean_secret)
                    code = totp.now()
                    log(f"📱 生成验证码: {code}")
                    
                    await totp_input.fill(code)
                    await asyncio.sleep(0.5)
                    
                    # 点击确认按钮
                    confirm_selectors = [
                        'button[type="submit"]',
                        'button:has-text("Continue")',
                        'button:has-text("继续")',
                        'button:has-text("Verify")',
                    ]
                    
                    for btn_sel in confirm_selectors:
                        try:
                            btn = page.locator(btn_sel).first
                            if await btn.count() > 0 and await btn.is_visible():
                                await btn.click()
                                log("✅ 2FA 验证提交")
                                return True
                        except:
                            continue
                    
                    return True
            except:
                continue
        
        return True  # 没有 2FA，直接返回成功
        
    except Exception as e:
        log(f"⚠️ 2FA 处理出错: {e}")
        return False


async def gpt_login(page: Page, account_info: dict, log_callback=None):
    """
    自动登录 ChatGPT
    
    Args:
        page: Playwright Page 对象
        account_info: 账号信息 {'email', 'password', 'secret'}
        log_callback: 日志回调函数
    
    Returns:
        (success: bool, message: str)
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)
    
    email = account_info.get('email', '')
    password = account_info.get('password', '')
    secret = account_info.get('secret', '')
    
    log(f"🔐 开始登录: {email}")
    
    try:
        # 1. 导航到 ChatGPT
        log("📍 导航到 ChatGPT...")
        await page.goto("https://chatgpt.com", wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(3)
        
        # 2. 检查是否已登录
        try:
            # 如果能看到用户菜单或聊天界面，说明已登录
            logged_in_indicators = [
                'button[aria-label*="User"]',
                'button[data-testid="profile-button"]',
                '[data-testid="conversation-turn"]',
                'nav[aria-label="Chat history"]',
            ]
            
            for indicator in logged_in_indicators:
                elem = page.locator(indicator).first
                if await elem.count() > 0 and await elem.is_visible():
                    log("✅ 已经登录")
                    return True, "已登录"
        except:
            pass
        
        # 3. 点击登录按钮
        log("🔍 查找登录按钮...")
        login_selectors = [
            'button:has-text("Log in")',
            'button:has-text("登录")',
            'a:has-text("Log in")',
            '[data-testid="login-button"]',
        ]
        
        for selector in login_selectors:
            try:
                btn = page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    log("✅ 点击登录按钮")
                    break
            except:
                continue
        
        await asyncio.sleep(3)
        
        # 4. 输入邮箱
        log("📧 输入邮箱...")
        email_input = await page.wait_for_selector('input[name="email"], input[type="email"], input[id="email-input"]', timeout=10000)
        if email_input:
            await email_input.fill(email)
            await asyncio.sleep(0.5)
            
            # 点击继续
            continue_btn = page.locator('button[type="submit"], button:has-text("Continue"), button:has-text("继续")').first
            if await continue_btn.count() > 0:
                await continue_btn.click()
                log("✅ 邮箱输入完成")
        
        await asyncio.sleep(2)
        
        # 5. 输入密码
        log("🔑 输入密码...")
        password_input = await page.wait_for_selector('input[type="password"], input[name="password"]', timeout=10000)
        if password_input:
            await password_input.fill(password)
            await asyncio.sleep(0.5)
            
            # 点击登录
            login_btn = page.locator('button[type="submit"], button:has-text("Continue"), button:has-text("Log in")').first
            if await login_btn.count() > 0:
                await login_btn.click()
                log("✅ 密码输入完成")
        
        await asyncio.sleep(3)
        
        # 6. 处理 2FA
        if secret:
            await gpt_handle_2fa(page, secret, log_callback)
        
        await asyncio.sleep(3)
        
        # 7. 检查登录结果
        try:
            for indicator in logged_in_indicators:
                elem = page.locator(indicator).first
                if await elem.count() > 0:
                    log("✅ 登录成功！")
                    return True, "登录成功"
        except:
            pass
        
        log("⚠️ 无法确认登录状态")
        return True, "可能成功，请手动验证"
        
    except Exception as e:
        log(f"❌ 登录失败: {e}")
        return False, str(e)


async def gpt_check_subscription(page: Page, log_callback=None):
    """
    检测 GPT 订阅状态
    
    Returns:
        (status: str, message: str)
        status: 'free', 'plus', 'business', 'unknown'
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)
    
    try:
        log("🔍 检测订阅状态...")
        
        # 导航到设置页面
        await page.goto("https://chatgpt.com/#settings", wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)
        
        page_text = await page.content()
        page_text_lower = page_text.lower()
        
        # 检测 Plus
        if 'chatgpt plus' in page_text_lower or 'plus subscriber' in page_text_lower:
            log("✅ 检测到 Plus 订阅")
            return 'plus', "ChatGPT Plus"
        
        # 检测 Business/Team
        if 'chatgpt team' in page_text_lower or 'business' in page_text_lower:
            log("✅ 检测到 Business/Team 订阅")
            return 'business', "ChatGPT Business/Team"
        
        # 检测免费用户
        if 'upgrade' in page_text_lower or 'free' in page_text_lower:
            log("📊 免费账号")
            return 'free', "Free"
        
        log("⚠️ 无法确定订阅状态")
        return 'unknown', "未知"
        
    except Exception as e:
        log(f"❌ 检测失败: {e}")
        return 'unknown', str(e)


async def process_gpt_browser(browser_id: str, action: str = 'login', log_callback=None, **kwargs):
    """
    处理单个 GPT 浏览器窗口
    
    Args:
        browser_id: BitBrowser 窗口 ID
        action: 操作类型 'login', 'check', 'subscribe'
        log_callback: 日志回调函数
        **kwargs: 额外参数
    
    Returns:
        (success: bool, message: str)
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)
    
    # 获取浏览器信息
    browser_info = get_browser_info(browser_id)
    if not browser_info:
        return False, "找不到浏览器窗口"
    
    # 解析账号信息
    remark = browser_info.get('remark', '')
    parts = re.split(r'-{3,}', remark)
    
    account_info = {
        'email': parts[0].strip() if len(parts) > 0 else '',
        'password': parts[1].strip() if len(parts) > 1 else '',
        'backup': parts[2].strip() if len(parts) > 2 else '',
        'secret': parts[3].strip() if len(parts) > 3 else '',
    }
    
    log(f"🌐 打开浏览器: {browser_id[:12]}...")
    
    # 打开浏览器
    result = openBrowser(browser_id)
    if not result.get('success'):
        return False, "打开浏览器失败"
    
    ws_endpoint = result['data']['ws']
    
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            
            if action == 'login':
                return await gpt_login(page, account_info, log_callback)
            elif action == 'check':
                status, msg = await gpt_check_subscription(page, log_callback)
                return True, f"{status}: {msg}"
            elif action == 'subscribe':
                # 先登录
                success, msg = await gpt_login(page, account_info, log_callback)
                if not success:
                    return False, f"登录失败: {msg}"
                
                # 然后绑卡订阅
                from .gpt_bind_card import gpt_subscribe
                card_info = kwargs.get('card_info')
                sub_type = kwargs.get('sub_type', 'plus')
                return await gpt_subscribe(page, card_info, sub_type, log_callback)
            else:
                return False, f"未知操作: {action}"
                
    except Exception as e:
        log(f"❌ 处理失败: {e}")
        return False, str(e)
    
    finally:
        try:
            closeBrowser(browser_id)
        except:
            pass


# 同步入口点
def run_gpt_task(browser_id: str, action: str = 'login', log_callback=None, **kwargs):
    """同步执行 GPT 任务"""
    return asyncio.run(process_gpt_browser(browser_id, action, log_callback, **kwargs))


if __name__ == "__main__":
    # 测试
    test_id = "test_browser_id"
    success, msg = run_gpt_task(test_id, 'login')
    print(f"Result: {success} - {msg}")

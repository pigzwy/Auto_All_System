"""
GPT 自动登录模块
- 邮箱/密码登录
- 2FA 验证处理
- 代理支持
"""
import asyncio
import time
import pyotp
import os
import sys
from playwright.async_api import async_playwright, Page

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bit_api import openBrowser, closeBrowser


def get_base_path():
    """获取基础路径"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_proxies():
    """加载代理列表"""
    proxies = []
    base_path = get_base_path()
    proxy_file = os.path.join(base_path, "proxies.txt")
    
    if os.path.exists(proxy_file):
        try:
            with open(proxy_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        proxies.append(line)
        except Exception:
            pass
    
    return proxies


async def gpt_check_logged_in(page: Page, log_callback=None):
    """
    检测是否已登录 ChatGPT
    
    Returns:
        bool: 是否已登录
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)
    
    try:
        # 已登录标识
        logged_in_indicators = [
            'button[aria-label*="User"]',
            'button[data-testid="profile-button"]',
            '[data-testid="conversation-turn"]',
            'nav[aria-label="Chat history"]',
            'button[aria-haspopup="menu"]',
            'div[data-testid="composer"]',
        ]
        
        for indicator in logged_in_indicators:
            try:
                elem = page.locator(indicator).first
                if await elem.count() > 0 and await elem.is_visible():
                    log("✅ 检测到已登录状态")
                    return True
            except:
                continue
        
        return False
        
    except Exception as e:
        log(f"⚠️ 检测登录状态出错: {e}")
        return False


async def gpt_handle_2fa(page: Page, secret_key: str, log_callback=None):
    """
    处理 GPT 2FA 验证
    
    Args:
        page: Playwright Page 对象
        secret_key: 2FA 密钥
        log_callback: 日志回调函数
    
    Returns:
        bool: 是否成功处理
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)
    
    try:
        # 2FA 输入框选择器
        totp_selectors = [
            'input[name="code"]',
            'input[type="text"][autocomplete="one-time-code"]',
            'input[placeholder*="code"]',
            'input[placeholder*="验证"]',
            'input[inputmode="numeric"]',
        ]
        
        for selector in totp_selectors:
            try:
                totp_input = await page.wait_for_selector(selector, timeout=5000)
                if totp_input and await totp_input.is_visible():
                    log("🔐 检测到 2FA 验证...")
                    
                    if not secret_key:
                        log("❌ 缺少 2FA 密钥，需要手动输入")
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
                        'button:has-text("验证")',
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
        if await gpt_check_logged_in(page, log_callback):
            return True, "已登录"
        
        # 3. 点击登录按钮
        log("🔍 查找登录按钮...")
        login_selectors = [
            'button:has-text("Log in")',
            'button:has-text("登录")',
            'a:has-text("Log in")',
            '[data-testid="login-button"]',
        ]
        
        clicked = False
        for selector in login_selectors:
            try:
                btn = page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    log("✅ 点击登录按钮")
                    clicked = True
                    break
            except:
                continue
        
        if not clicked:
            log("⚠️ 未找到登录按钮")
        
        await asyncio.sleep(3)
        
        # 4. 输入邮箱
        log("📧 输入邮箱...")
        try:
            email_input = await page.wait_for_selector(
                'input[name="email"], input[type="email"], input[id="email-input"], input[name="username"]', 
                timeout=10000
            )
            if email_input:
                await email_input.fill(email)
                await asyncio.sleep(0.5)
                
                # 点击继续
                continue_btn = page.locator('button[type="submit"], button:has-text("Continue"), button:has-text("继续")').first
                if await continue_btn.count() > 0:
                    await continue_btn.click()
                    log("✅ 邮箱输入完成")
        except Exception as e:
            log(f"⚠️ 邮箱输入失败: {e}")
        
        await asyncio.sleep(2)
        
        # 5. 输入密码
        log("🔑 输入密码...")
        try:
            password_input = await page.wait_for_selector(
                'input[type="password"], input[name="password"]', 
                timeout=10000
            )
            if password_input:
                await password_input.fill(password)
                await asyncio.sleep(0.5)
                
                # 点击登录
                login_btn = page.locator('button[type="submit"], button:has-text("Continue"), button:has-text("Log in")').first
                if await login_btn.count() > 0:
                    await login_btn.click()
                    log("✅ 密码输入完成")
        except Exception as e:
            log(f"⚠️ 密码输入失败: {e}")
        
        await asyncio.sleep(3)
        
        # 6. 处理 2FA
        if secret:
            await gpt_handle_2fa(page, secret, log_callback)
        
        await asyncio.sleep(3)
        
        # 7. 检查登录结果
        if await gpt_check_logged_in(page, log_callback):
            log("✅ 登录成功！")
            return True, "登录成功"
        
        log("⚠️ 无法确认登录状态")
        return True, "可能成功，请手动验证"
        
    except Exception as e:
        log(f"❌ 登录失败: {e}")
        return False, str(e)


async def gpt_login_with_browser(browser_id: str, account_info: dict, log_callback=None):
    """
    使用 BitBrowser 窗口登录 GPT
    
    Args:
        browser_id: BitBrowser 窗口 ID
        account_info: 账号信息
        log_callback: 日志回调函数
    
    Returns:
        (success: bool, message: str)
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)
    
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
            
            return await gpt_login(page, account_info, log_callback)
            
    except Exception as e:
        log(f"❌ 处理失败: {e}")
        return False, str(e)
    
    finally:
        try:
            closeBrowser(browser_id)
        except:
            pass


# 同步入口
def run_gpt_login(browser_id: str, account_info: dict, log_callback=None):
    """同步执行 GPT 登录"""
    return asyncio.run(gpt_login_with_browser(browser_id, account_info, log_callback))


if __name__ == "__main__":
    print("GPT Login Module")
    print("=" * 40)
    print("使用方式: run_gpt_login(browser_id, account_info)")

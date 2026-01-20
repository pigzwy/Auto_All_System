"""
Google账号安全信息自动化修改模块
- 批量修改2FA密钥（全自动）
- 批量修改辅助邮箱（全自动 - 支持IMAP自动读取验证码）
"""
import asyncio
import time
import random
import pyotp
import re
import os
import sys
from playwright.async_api import async_playwright, Page
from bit_api import openBrowser, closeBrowser
import io

# 导入邮件验证码读取模块
try:
    from email_verifier import get_google_verification_code_from_163
    EMAIL_VERIFIER_AVAILABLE = True
except ImportError:
    EMAIL_VERIFIER_AVAILABLE = False
    print("⚠️ 邮件验证码自动读取功能不可用（email_verifier模块未找到）")

# 尝试修复Windows下的控制台输出编码问题
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_recovery_emails():
    """加载备用邮箱列表"""
    base_path = get_base_path()
    file_path = os.path.join(base_path, "recovery_emails.txt")
    
    emails = []
    if os.path.exists(file_path):
        # 尝试多种编码
        encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin-1']
        content = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        if content:
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '@' in line:
                    emails.append(line)
    return emails


def load_imap_config():
    """加载IMAP邮箱配置"""
    try:
        import configparser
        
        base_path = get_base_path()
        config_path = os.path.join(base_path, "email_config.ini")
        
        if not os.path.exists(config_path):
            return None
        
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        
        if 'imap_163' in config:
            return {
                'email': config['imap_163'].get('email', ''),
                'password': config['imap_163'].get('password', ''),
            }
        
        return None
    except Exception as e:
        print(f"⚠️ 加载IMAP配置失败: {e}")
        return None


def save_new_2fa_secret(email: str, new_secret: str, log_callback=None):
    """将新的2FA密钥保存到文件"""
    def log(msg):
        if log_callback:
            log_callback(msg)
        try:
            print(msg)
        except:
            pass
    
    try:
        base_path = get_base_path()
        file_path = os.path.join(base_path, "new_2fa_secrets.txt")
        
        # 获取当前时间
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 追加写入文件
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp} | {email} | {new_secret}\n")
        
        log(f"📁 新密钥已保存到: {file_path}")
        return True
    except Exception as e:
        log(f"⚠️ 保存新密钥到文件时出错: {e}")
        return False


def get_random_recovery_email(emails_list):
    """从列表中随机选择一个邮箱"""
    if not emails_list:
        return None
    return random.choice(emails_list)


async def ensure_logged_in(page: Page, account_info: dict, log_callback=None, max_login_attempts: int = 3):
    """
    确保Google账号已登录，如果未登录则自动执行登录流程
    
    Args:
        page: Playwright页面对象
        account_info: 账号信息 {'email', 'password', 'secret'}
        log_callback: 日志回调函数
        max_login_attempts: 最大登录尝试次数
    
    Returns:
        (success: bool, message: str)
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        try:
            print(msg)
        except:
            pass
    
    email = account_info.get('email', '')
    password = account_info.get('password', '')
    secret = account_info.get('secret', '')
    
    log("🔍 检查登录状态...")
    
    for attempt in range(max_login_attempts):
        try:
            await asyncio.sleep(2)
            
            # 获取当前URL和页面内容
            current_url = page.url
            page_content = await page.content()
            
            # 简化判断：检查是否已登录到 myaccount
            # 已登录的标志：在 myaccount.google.com 且页面有账号相关内容
            is_logged_in = (
                'myaccount.google.com' in current_url and 
                'accounts.google.com' not in current_url and
                ('Security' in page_content or '安全' in page_content or 
                 'Personal info' in page_content or '个人信息' in page_content or
                 'Data & privacy' in page_content or '数据和隐私' in page_content)
            )
            
            if is_logged_in:
                log("✅ 已检测到登录状态")
                return True, "已登录"
            
            # 检查是否在登录页面（有邮箱或密码输入框）
            has_email_input = 'input[type="email"]' in page_content or 'name="identifier"' in page_content
            has_password_input = 'input[type="password"]' in page_content
            is_login_page = has_email_input or has_password_input
            
            # 如果不在登录页面，直接导航到 Google 登录页面
            if not is_login_page:
                log("📍 导航到 Google 登录页面...")
                await page.goto("https://accounts.google.com/signin/v2/identifier?service=accountsettings&flowName=GlifWebSignIn", 
                               wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)
                # 重新获取页面内容
                current_url = page.url
                page_content = await page.content()
            
            # 需要登录
            log(f"📍 开始登录流程... (尝试 {attempt + 1}/{max_login_attempts})")
            
            # 步骤1: 输入邮箱
            email_input = page.locator('input[type="email"]').first
            if await email_input.count() > 0 and await email_input.is_visible():
                log(f"📧 输入邮箱: {email}")
                await email_input.fill(email)
                await asyncio.sleep(1)
                
                # 点击下一步
                next_selectors = [
                    '#identifierNext >> button',
                    '#identifierNext',
                    'button:has-text("Next")',
                    'button:has-text("下一步")',
                    'div[role="button"]:has-text("Next")'
                ]
                
                for selector in next_selectors:
                    try:
                        btn = page.locator(selector).first
                        if await btn.count() > 0 and await btn.is_visible():
                            await btn.click()
                            log("✅ 邮箱已提交")
                            break
                    except:
                        continue
                
                await asyncio.sleep(3)
            
            # 步骤2: 输入密码
            password_input = page.locator('input[type="password"]').first
            if await password_input.count() > 0 and await password_input.is_visible():
                log(f"🔑 输入密码...")
                await password_input.fill(password)
                await asyncio.sleep(1)
                
                # 点击下一步
                pass_next_selectors = [
                    '#passwordNext >> button',
                    '#passwordNext',
                    'button:has-text("Next")',
                    'button:has-text("下一步")'
                ]
                
                for selector in pass_next_selectors:
                    try:
                        btn = page.locator(selector).first
                        if await btn.count() > 0 and await btn.is_visible():
                            await btn.click()
                            log("✅ 密码已提交")
                            break
                    except:
                        continue
                
                await asyncio.sleep(3)
            
            # 步骤3: 处理2FA验证码（可能多次）
            for _ in range(5):  # 最多处理5次2FA
                await asyncio.sleep(2)
                
                # 检查是否需要2FA
                totp_selectors = [
                    'input[name="totpPin"]',
                    'input[id="totpPin"]',
                    'input[type="tel"]',
                    'input[aria-label*="code"]',
                    'input[aria-label*="验证"]'
                ]
                
                totp_input = None
                for selector in totp_selectors:
                    try:
                        locator = page.locator(selector).first
                        if await locator.count() > 0 and await locator.is_visible():
                            totp_input = locator
                            break
                    except:
                        continue
                
                if totp_input:
                    log("📱 检测到2FA验证，生成验证码...")
                    
                    if not secret:
                        log("❌ 缺少2FA密钥，无法生成验证码")
                        return False, "缺少2FA密钥"
                    
                    try:
                        totp = pyotp.TOTP(secret.replace(' ', ''))
                        code = totp.now()
                        log(f"📱 生成验证码: {code}")
                        
                        await totp_input.fill(code)
                        await asyncio.sleep(1)
                        
                        # 点击验证
                        verify_selectors = [
                            'button:has-text("Next")',
                            'button:has-text("下一步")',
                            'button:has-text("Verify")',
                            'button:has-text("验证")',
                            '#totpNext >> button',
                            '#totpNext'
                        ]
                        
                        for selector in verify_selectors:
                            try:
                                btn = page.locator(selector).first
                                if await btn.count() > 0 and await btn.is_visible():
                                    await btn.click()
                                    log("✅ 2FA验证码已提交")
                                    break
                            except:
                                continue
                        
                        await asyncio.sleep(3)
                    except Exception as e:
                        log(f"⚠️ 生成2FA验证码时出错: {e}")
                else:
                    # 没有2FA输入框，检查是否登录成功
                    break
            
            # 检查最终状态
            await asyncio.sleep(2)
            current_url = page.url
            
            if 'myaccount.google.com' in current_url:
                log("✅ 登录成功!")
                return True, "登录成功"
            
            # 检查是否有错误消息
            error_texts = ['Wrong password', '密码错误', 'couldn\'t sign you in', '无法登录']
            page_text = await page.inner_text('body')
            
            for error in error_texts:
                if error.lower() in page_text.lower():
                    log(f"❌ 登录失败: {error}")
                    return False, f"登录失败: {error}"
                    
        except Exception as e:
            log(f"⚠️ 登录过程出错: {e}")
            import traceback
            traceback.print_exc()
    
    return False, "登录尝试次数已用完"

async def verify_2fa_if_needed(page: Page, secret_key: str, log_callback=None, password: str = None, email: str = None, max_attempts: int = 5):
    """
    循环检测并处理2FA验证和密码输入（如果需要）
    会持续检测直到不再出现2FA或密码输入框
    
    Args:
        page: Playwright页面对象
        secret_key: 2FA密钥
        log_callback: 日志回调函数
        password: 账号密码（用于重新输入密码的情况）
        email: 账号邮箱（用于重新输入邮箱的情况）
        max_attempts: 最大尝试次数，防止无限循环
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        try:
            print(msg)
        except:
            pass

    
    attempts = 0
    total_2fa_count = 0
    total_password_count = 0
    
    log("🔍 开始检测是否需要验证...")
    
    try:
        while attempts < max_attempts:
            attempts += 1
            
            # 等待页面加载
            await asyncio.sleep(2)
            
            found_input = False
            
            # 检查是否需要输入邮箱
            try:
                email_locator = page.locator('input[type="email"]')
                if await email_locator.count() > 0:
                    first_email = email_locator.first
                    if await first_email.is_visible():
                        log(f"📧 检测到需要输入邮箱...")
                        found_input = True
                        
                        if not email:
                            log("❌ 缺少邮箱地址，无法自动填写")
                            # 尝试继续，也许已经填好了？
                        else:
                            # 检查是否已经填入
                            current_val = await first_email.input_value()
                            if current_val != email:
                                await first_email.fill(email)
                                await asyncio.sleep(0.5)
                            
                            # 点击下一步
                            next_btn_selectors = [
                                '#identifierNext >> button',
                                '#identifierNext',
                                'button:has-text("Next")',
                                'button:has-text("下一步")',
                                'div[role="button"]:has-text("Next")',
                                'div[role="button"]:has-text("下一步")'
                            ]
                            
                            for selector in next_btn_selectors:
                                try:
                                    btn = page.locator(selector).first
                                    if await btn.count() > 0 and await btn.is_visible():
                                        await btn.click()
                                        log("✅ 邮箱输入完成，点击下一步")
                                        break
                                except:
                                    continue
                            
                            await asyncio.sleep(3)
                            continue

            except Exception as e:
                log(f"⚠️ 检查邮箱输入时出错: {e}")

            # 检查是否需要输入密码 - 使用 locator 和 is_visible
            try:
                password_locator = page.locator('input[type="password"]')
                if await password_locator.count() > 0:
                    # 检查第一个是否可见
                    first_password = password_locator.first
                    is_visible = await first_password.is_visible()
                    
                    if is_visible:
                        log(f"🔑 检测到需要输入密码（第{total_password_count + 1}次）...")
                        found_input = True
                        total_password_count += 1
                        
                        if not password:
                            log("❌ 缺少密码，无法自动验证")
                            return False, "缺少密码"
                        
                        # 输入密码
                        await first_password.fill(password)
                        await asyncio.sleep(0.5)
                        
                        # 点击下一步按钮
                        next_btn_selectors = [
                            '#passwordNext >> button',
                            '#passwordNext',
                            'button[type="submit"]',
                            'button:has-text("Next")',
                            'button:has-text("下一步")',
                            'div[role="button"]:has-text("Next")',
                            'div[role="button"]:has-text("下一步")'
                        ]
                        
                        for selector in next_btn_selectors:
                            try:
                                btn = page.locator(selector).first
                                if await btn.count() > 0 and await btn.is_visible():
                                    await btn.click()
                                    log("✅ 密码输入完成，点击下一步")
                                    break
                            except:
                                continue
                        
                        await asyncio.sleep(3)
                        continue  # 继续检查是否还有其他验证
            except Exception as e:
                log(f"⚠️ 检查密码输入时出错: {e}")
            
            # 检查是否需要2FA验证 - 使用多种选择器
            try:
                totp_selectors = [
                    'input[name="totpPin"]',
                    'input[id="totpPin"]',
                    'input[type="tel"][autocomplete="one-time-code"]',
                    'input[type="tel"]',
                    'input[aria-label*="code"]',
                    'input[aria-label*="验证码"]',
                    'input[aria-label*="verification"]',
                    'input[placeholder*="code"]',
                    'input[placeholder*="验证"]'
                ]
                
                totp_input = None
                for selector in totp_selectors:
                    try:
                        locator = page.locator(selector)
                        if await locator.count() > 0:
                            first_elem = locator.first
                            if await first_elem.is_visible():
                                totp_input = first_elem
                                log(f"📍 通过选择器 {selector} 找到2FA输入框")
                                break
                    except:
                        continue
                
                if totp_input:
                    log(f"🔐 检测到需要2FA验证（第{total_2fa_count + 1}次）...")
                    found_input = True
                    total_2fa_count += 1
                    
                    if not secret_key:
                        log("❌ 缺少2FA密钥，无法自动验证")
                        return False, "缺少2FA密钥"
                    
                    # 生成验证码
                    try:
                        clean_secret = secret_key.replace(" ", "").strip()
                        totp = pyotp.TOTP(clean_secret)
                        code = totp.now()
                        log(f"📱 生成2FA验证码: {code}")
                    except Exception as e:
                        log(f"❌ 生成2FA验证码失败: {e}")
                        return False, f"生成验证码失败: {e}"
                    
                    # 清空并输入验证码
                    await totp_input.fill('')
                    await asyncio.sleep(0.2)
                    await totp_input.fill(code)
                    await asyncio.sleep(0.5)
                    
                    # 点击下一步/验证按钮
                    next_selectors = [
                        '#totpNext >> button',
                        '#totpNext',
                        'button[type="submit"]',
                        'button:has-text("Next")',
                        'button:has-text("Verify")',
                        'button:has-text("下一步")',
                        'button:has-text("验证")',
                        'button:has-text("确认")',
                        'div[role="button"]:has-text("Next")',
                        'div[role="button"]:has-text("下一步")'
                    ]
                    
                    for selector in next_selectors:
                        try:
                            btn = page.locator(selector).first
                            if await btn.count() > 0 and await btn.is_visible():
                                await btn.click()
                                log("✅ 2FA验证完成，点击下一步")
                                break
                        except:
                            continue
                    
                    await asyncio.sleep(3)
                    continue  # 继续检查是否还有其他验证
            except Exception as e:
                log(f"⚠️ 检查2FA输入时出错: {e}")
            
            # 如果没有找到任何输入框，说明验证已完成
            if not found_input:
                if total_2fa_count > 0 or total_password_count > 0:
                    log(f"✅ 所有验证完成（密码: {total_password_count}次, 2FA: {total_2fa_count}次）")
                    return True, "验证成功"
                else:
                    log("ℹ️ 未检测到验证需求，继续...")
                    return True, "无需验证"
        
        # 超过最大尝试次数
        log(f"⚠️ 达到最大尝试次数 ({max_attempts})，停止验证")
        return True, f"验证可能完成（尝试次数: {attempts}）"
        
    except Exception as e:
        log(f"❌ 验证过程出错: {e}")
        return False, str(e)


async def change_2fa_secret(browser_id: str, account_info: dict, log_callback=None, close_browser=True, page=None):
    """
    修改Google账号的2FA密钥（全自动）
    
    Args:
        browser_id: BitBrowser窗口ID
        account_info: 账号信息字典 {'email', 'password', 'secret'}
        log_callback: 日志回调函数
        close_browser: 是否在完成后关闭浏览器（默认True）
        page: 现有的Playwright页面对象（可选，如果提供则不重新打开浏览器）
    
    Returns:
        (success: bool, new_secret: str, message: str)
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        try:
            print(msg)
        except:
            pass

    
    old_secret = account_info.get('secret', '')
    email = account_info.get('email', '')
    
    log(f"🔐 开始修改2FA: {email}")
    
    playwright = None
    browser = None
    page_obj = page
    is_self_managed = False

    try:
        if not page_obj:
            is_self_managed = True
            # 打开浏览器
            result = openBrowser(browser_id)
            if not result.get('success'):
                return False, None, "打开浏览器失败"
            
            ws_endpoint = result['data']['ws']
            
            playwright = await async_playwright().start()
            browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
            context = browser.contexts[0]
            page_obj = context.pages[0] if context.pages else await context.new_page()
            
            # 只有在新打开时才检查登录
            log("📍 检查登录状态...")
            await page_obj.goto("https://myaccount.google.com/", wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)
            
            login_success, login_msg = await ensure_logged_in(page_obj, account_info, log_callback)
            if not login_success:
                log(f"❌ 登录失败: {login_msg}")
                return False, None, f"登录失败: {login_msg}"

        # 导航到2FA设置页面
        log("📍 导航到2FA设置页面...")
        await page_obj.goto("https://myaccount.google.com/signinoptions/two-step-verification", 
                      wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)
        
        # 处理可能的2FA验证和密码验证
        password = account_info.get('password', '')
        success, msg = await verify_2fa_if_needed(page_obj, old_secret, log_callback, password=password, email=email)
        if not success:
            return False, None, msg
        
        await asyncio.sleep(2)
        
        # 确保 'page' 变量引用正确的页面对象（与 change_recovery_email 和 get_backup_codes 保持一致）
        page = page_obj
        
        if True:
            if True:
                
                # 查找 Authenticator app 选项
                log("🔍 查找 Authenticator 应用选项...")
                
                # 尝试多种选择器
                auth_selectors = [
                    'text="Authenticator"',
                    'text="身份验证器"',
                    'text="Authenticator app"',
                    '[data-identifier="authenticator"]',
                    'h2:has-text("Authenticator")',
                    'div:has-text("Authenticator")'
                ]
                
                auth_option = None
                for selector in auth_selectors:
                    try:
                        # 查找包含Authenticator的列表项，点击它进入详情页
                        elements = await page.locator(selector).all()
                        for elem in elements:
                            if await elem.is_visible():
                                auth_option = elem
                                break
                        if auth_option:
                            break
                    except:
                        continue
                
                if not auth_option:
                    log("❌ 未找到 Authenticator 选项")
                    return False, None, "未找到Authenticator选项"
                
                # 滚动到该元素并点击
                try:
                    await auth_option.scroll_into_view_if_needed()
                    await auth_option.click()
                except Exception as e:
                    log(f"⚠️ 点击 Authenticator 选项失败: {e}")
                    # 尝试强制点击
                    await page.mouse.click(100, 100) # Dummy click
                    await auth_option.click(force=True)
                
                await asyncio.sleep(3)
                
                # 查找并点击 "Change authenticator app", "Set up authenticator" 或 "Add authenticator"
                log("🔄 查找 设置/添加/更换 验证器按钮...")
                
                change_selectors = [
                    'text="Change authenticator app"',      # Screenshot 1 (User specific)
                    'text="Add authenticator application"', 
                    'text="Set up the authenticator"',
                    'text="添加身份验证器应用"',
                    'text="Set up authenticator"',
                    'text="设置身份验证器"',
                    'text="Add authenticator"',
                    'button:has-text("Change authenticator")',
                    'div[role="button"]:has-text("Change authenticator")',
                    'button:has-text("Add")',
                    'text="更换验证器应用"',
                ]
                
                change_btn = None
                for selector in change_selectors:
                    try:
                        # 使用 strict=False 允许模糊匹配，或者 regex
                        btn = page.locator(selector).first
                        if await btn.count() > 0 and await btn.is_visible():
                            change_btn = btn
                            log(f"✅ 找到按钮: {selector}")
                            break
                    except:
                        continue
                
                if change_btn:
                    try:
                        await change_btn.click()
                        log("✅ 点击了更换/添加按钮")
                    except Exception as e:
                        log(f"⚠️ 点击按钮失败，尝试JS点击: {e}")
                        await change_btn.evaluate("element => element.click()")
                else:
                    log("⚠️ 未找到明确的添加/修改按钮，尝试查找 '+' 号按钮...")
                    # 尝试查找 + 号按钮
                    try:
                        plus_btns = await page.locator('button:has-text("+")').all()
                        for btn in plus_btns:
                            if await btn.is_visible():
                                await btn.click()
                                log("✅ 点击了 + 号按钮")
                                change_btn = True
                                break
                    except:
                        pass
                
                # 等待模态框出现
                log("⏳ 等待 '设置/更换 身份验证器' 模态框...")
                modal_selectors = [
                    'text="Change authenticator app"', # User specific
                    'text="Set up the authenticator application"',
                    'text="Set up authenticator"',
                    'text="设置身份验证器"', 
                    'text="设置身份验证器应用"',
                    'h2:has-text("Authenticator")',
                    'h2:has-text("身份验证器")'
                ]
                
                modal_found = False
                for _ in range(10): # 尝试5秒
                    for selector in modal_selectors:
                        try:
                            if await page.locator(selector).first.is_visible():
                                modal_found = True
                                log(f"✅ 模态框已打开: {selector}")
                                break
                        except:
                            pass
                    if modal_found:
                        break
                    await asyncio.sleep(0.5)
                
                if not modal_found:
                    log("⚠️ 未检测到模态框标题，但继续尝试操作...")
                
                # 等待模态框内容（QR码和链接）加载完成
                log("⏳ 等待模态框内容加载...")
                await asyncio.sleep(3)

                # 查找 "Can't scan it?" 或 "无法扫描?" 链接 (带重试)
                log("🔗 查找 'Can't scan it?' 选项...")
                
                cant_scan = None
                
                # 重试循环，最多等待10秒
                for attempt in range(20):
                    try:
                        # 方法0 (最优先): 使用用户提供的精确选择器
                        # <span jsname="V67aGc" class="mUIrbf-vQzf8d">Can't scan it?</span>
                        try:
                            specific_span = page.locator('span[jsname="V67aGc"]')
                            spans = await specific_span.all()
                            for span in spans:
                                try:
                                    text = await span.inner_text()
                                    if 'scan' in text.lower() and len(text) < 30:
                                        if await span.is_visible():
                                            cant_scan = span
                                            log(f"✅ 用精确选择器找到: '{text}'")
                                            break
                                except:
                                    continue
                        except:
                            pass
                        
                        if cant_scan:
                            break
                        
                        # 方法1: 直接用文本内容查找链接 (只匹配短文本)
                        links = await page.query_selector_all('a, button, [role="link"], [role="button"], span[jsname]')
                        for link in links:
                            try:
                                text = await link.inner_text()
                                text_lower = text.lower().strip()
                                # 检查是否包含 "scan" 关键词 AND 文本长度小于30字符 (避免匹配父元素)
                                if len(text) < 30 and 'scan' in text_lower and ('can' in text_lower or 'unable' in text_lower or '无法' in text):
                                    if await link.is_visible():
                                        cant_scan = link
                                        log(f"✅ 找到链接: '{text}'")
                                        break
                            except:
                                continue
                        
                        if cant_scan:
                            break  # 找到了，退出重试循环
                        
                        # 方法2: 如果方法1失败，尝试用选择器
                        cant_scan_selectors = [
                            'span.mUIrbf-vQzf8d:has-text("scan")',  # User's exact class
                            'a:has-text("scan")',
                            'text=/^Can.*scan.*\\?$/',  # 精确匹配短文本
                            'text="Can\'t scan it?"',
                            'text="Unable to scan?"',
                            ':text("无法扫描")',
                        ]
                        
                        for selector in cant_scan_selectors:
                            try:
                                elem = page.locator(selector).first
                                if await elem.count() > 0 and await elem.is_visible():
                                    cant_scan = elem
                                    log(f"✅ 用选择器找到: {selector}")
                                    break
                            except:
                                continue
                        
                        if cant_scan:
                            break  # 找到了，退出重试循环
                        
                        # 方法3: 在所有 frames 中查找
                        for frame in page.frames:
                            try:
                                frame_links = await frame.query_selector_all('a, button, span[jsname]')
                                for link in frame_links:
                                    try:
                                        text = await link.inner_text()
                                        if 'scan' in text.lower():
                                            if await link.is_visible():
                                                cant_scan = link
                                                log(f"✅ 在 frame 中找到: '{text}'")
                                                break
                                    except:
                                        continue
                                if cant_scan:
                                    break
                            except:
                                continue
                        
                        if cant_scan:
                            break  # 找到了，退出重试循环
                            
                    except Exception as e:
                        pass  # 忽略单次尝试的错误
                    
                    # 未找到，等待0.5秒后重试
                    if attempt < 19:
                        log(f"🔍 第{attempt + 1}次尝试未找到，等待重试...")
                        await asyncio.sleep(0.5)
                
                # 执行点击
                if cant_scan:
                    try:
                        await cant_scan.click()
                        log("✅ 点击了 'Can't scan it?' 链接")
                    except Exception as click_err:
                        log(f"⚠️ 常规点击失败: {click_err}, 尝试JS点击...")
                        try:
                            await cant_scan.evaluate("element => element.click()")
                            log("✅ JS点击成功")
                        except Exception as js_err:
                            log(f"⚠️ JS点击也失败: {js_err}")
                    await asyncio.sleep(2)
                else:
                    log("⚠️ 未找到 'Can't scan it?' 选项，尝试直接查找密钥...")
                

                # 提取新的密钥
                log("🔑 提取新的2FA密钥...")
                
                # 等待密钥文本出现
                try:
                    # User screenshot has "enter your setup key"
                    await page.wait_for_selector('text="setup key"', timeout=5000)
                except:
                    try:
                        await page.wait_for_selector('text="密钥"', timeout=2000)
                    except:
                        pass

                new_secret = None
                
                # 方法0 (最优先): 从 <strong> 元素提取密钥
                # User element: <strong>4r22 xbif i6yv jajy 2ppi u3ia lxnj xkne</strong>
                try:
                    strong_elements = await page.query_selector_all('strong')
                    for elem in strong_elements:
                        text = await elem.inner_text()
                        text_clean = text.strip().replace(' ', '').upper()
                        # 检查是否是Base32格式 (16-32个字符)
                        if re.match(r'^[A-Z2-7]{16,32}$', text_clean):
                            try:
                                test_totp = pyotp.TOTP(text_clean)
                                test_totp.now()
                                new_secret = text_clean
                                log(f"✅ 从 <strong> 元素提取到密钥")
                                break
                            except:
                                continue
                except:
                    pass
                
                # 方法1: 用正则从页面内容提取
                if not new_secret:
                    page_content = await page.content()
                    
                    # User example: bzl3 h3kz fomc lz7u fesy 4l4a vpwc efum
                    secret_pattern = r'\b([a-zA-Z2-7]{4}(?:\s+[a-zA-Z2-7]{4}){3,7})\b'
                    matches = re.findall(secret_pattern, page_content)
                    
                    if not matches:
                         matches = re.findall(r'\b([a-zA-Z2-7]{16,32})\b', page_content)
                    
                    for match in matches:
                        clean_match = match.replace(' ', '').strip().upper()
                        
                        if clean_match in ['ABCDEFGHIJKLMNOP', 'QRSTUVWXYZ234567']:
                            continue
                            
                        try:
                            test_totp = pyotp.TOTP(clean_match)
                            test_totp.now()
                            new_secret = clean_match
                            break
                        except:
                            continue
                
                if not new_secret:
                    log("❌ 无法提取新的2FA密钥")
                    return False, None, "无法提取新密钥"
                
                # 显示完整的新密钥 (用户需要记录)
                log(f"🔑 ========================================")
                log(f"🔑 新的2FA密钥: {new_secret}")
                log(f"🔑 ========================================")
                
                # 点击 "Next" 按钮
                # 使用用户提供的精确选择器: <span jsname="V67aGc" class="VfPpkd-vQzf8d">Next</span>
                log("👉 点击 'Next' 按钮...")
                
                next_clicked = False
                
                # 方法0: 使用精确的 span 选择器
                try:
                    next_spans = await page.query_selector_all('span[jsname="V67aGc"]')
                    for span in next_spans:
                        try:
                            text = await span.inner_text()
                            if text.strip().lower() == 'next' or text.strip() == '下一页':
                                if await span.is_visible():
                                    await span.click()
                                    next_clicked = True
                                    log(f"✅ 点击了 '{text}' 按钮")
                                    break
                        except:
                            continue
                except:
                    pass
                
                # 方法1: 备用选择器
                if not next_clicked:
                    next_selectors = [
                        'button:has-text("Next")',
                        'text="Next"',
                        'span:has-text("下一页")',   
                        'button:has-text("下一页")',
                    ]
                    
                    for selector in next_selectors:
                        try:
                            btn = page.locator(selector).first
                            if await btn.count() > 0 and await btn.is_visible():
                                await btn.click()
                                next_clicked = True
                                log("✅ 点击了下一步")
                                break
                        except:
                            continue
                
                if not next_clicked:
                    log("⚠️ 未点击到 'Next' 按钮，尝试直接输入验证码...")
                
                await asyncio.sleep(2)

                # 使用 **新的2FA密钥** 生成验证码 (Google要求验证新密钥是否正确配置)
                log(f"📱 使用新密钥生成验证码...")
                totp = pyotp.TOTP(new_secret)
                verification_code = totp.now()
                log(f"📱 生成验证码: {verification_code}")
                
                # 等待验证码输入框出现 (带重试)
                code_input = None
                for input_attempt in range(10):
                    code_input = await page.query_selector('input[type="text"]:not([disabled])')
                    if not code_input:
                        code_input = await page.query_selector('input[name="totpPin"], input[type="tel"]')
                    if code_input and await code_input.is_visible():
                        break
                    await asyncio.sleep(0.5)

                if not code_input:
                    log("❌ 未找到验证码输入框")
                    return False, None, "未找到验证码输入框"
                
                await code_input.fill(verification_code)
                log(f"✅ 已输入验证码: {verification_code}")
                await asyncio.sleep(1)
                
                # 点击 "Verify" 按钮
                # 使用用户提供的精确选择器: <span jsname="V67aGc" class="VfPpkd-vQzf8d">Verify</span>
                log("👊 点击 'Verify' 按钮...")
                
                verify_clicked = False
                
                # 方法0: 使用精确的 span 选择器
                try:
                    verify_spans = await page.query_selector_all('span[jsname="V67aGc"]')
                    for span in verify_spans:
                        try:
                            text = await span.inner_text()
                            if text.strip().lower() == 'verify' or text.strip() == '验证':
                                if await span.is_visible():
                                    await span.click()
                                    verify_clicked = True
                                    log(f"✅ 点击了 '{text}' 按钮")
                                    break
                        except:
                            continue
                except:
                    pass
                
                # 方法1: 备用选择器
                if not verify_clicked:
                    verify_selectors = [
                        'button:has-text("Verify")',
                        'text="Verify"',
                        'span:has-text("验证")',   
                        'button:has-text("验证")',
                    ]
                    
                    for selector in verify_selectors:
                        try:
                            verify_btn = await page.query_selector(selector)
                            if verify_btn:
                                await verify_btn.click()
                                verify_clicked = True
                                log("✅ 点击了验证按钮")
                                break
                        except:
                            continue
                
                if not verify_clicked:
                    log("⚠️ 未找到 Verify 按钮")
                
                await asyncio.sleep(3)
                
                # 检查是否成功
                success_indicators = ['Done', '完成', 'Success', '成功', 'verified', '已验证']
                # ... (rest of logic)
                page_text = await page.inner_text('body')
                
                is_success = any(indicator.lower() in page_text.lower() for indicator in success_indicators)
                
                if is_success:
                    log(f"✅ 2FA密钥修改成功！新密钥: {new_secret}")
                    
                    # 更新数据库
                    try:
                        from database import DBManager
                        DBManager.update_2fa_secret(email, new_secret, old_secret)
                    except Exception as e:
                        log(f"⚠️ 更新数据库时出错: {e}")
                    
                    # 保存新密钥到文件（防止忘记复制）
                    save_new_2fa_secret(email, new_secret, log_callback)
                    
                    return True, new_secret, "2FA密钥修改成功"
                else:
                    log("⚠️ 无法确认是否修改成功，但仍保存新密钥")
                    # 即使无法确认成功，也保存新密钥（防止丢失）
                    save_new_2fa_secret(email, new_secret, log_callback)
                    return True, new_secret, "可能成功，请手动验证"
                
    except Exception as e:
        log(f"❌ 自动化过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False, None, str(e)
    
    finally:
        if is_self_managed:
            if browser:
                try:
                     await browser.close()
                except: pass
            if playwright:
                try:
                     await playwright.stop()
                except: pass
            if close_browser:
                try:
                    closeBrowser(browser_id)
                except:
                    pass


async def change_recovery_email(browser_id: str, account_info: dict, new_email: str, 
                                 verification_code_callback=None, log_callback=None, close_browser=True, page=None,
                                 imap_config: dict = None):
    """
    修改Google账号的辅助邮箱（全自动 - 支持IMAP自动读取验证码）
    
    Args:
        browser_id: BitBrowser窗口ID
        account_info: 账号信息字典
        new_email: 新的辅助邮箱地址
        verification_code_callback: 获取验证码的回调函数（可选，如果有imap_config则优先使用IMAP）
        log_callback: 日志回调函数
        close_browser: 是否在完成后关闭浏览器（默认True）
        page: 现有的Playwright页面对象（可选）
        imap_config: IMAP配置字典，格式: {'server': 'imap.163.com', 'email': 'xxx@163.com', 'password': 'auth_code'}
    
    Returns:
        (success: bool, message: str)
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        try:
            print(msg)
        except:
            pass

    
    email = account_info.get('email', '')
    secret = account_info.get('secret', '')
    password = account_info.get('password', '')
    old_recovery = account_info.get('backup', '') or account_info.get('recovery_email', '')
    
    log(f"📧 开始修改辅助邮箱: {email}")
    log(f"   新辅助邮箱: {new_email}")
    
    playwright_obj = None
    browser = None
    page_obj = page
    is_self_managed = False

    try:
        if not page_obj:
            is_self_managed = True
            try:
                # 打开浏览器
                result = openBrowser(browser_id)
                if not result.get('success'):
                    return False, "打开浏览器失败"
                
                ws_endpoint = result['data']['ws']
                
                playwright_obj = await async_playwright().start()
                browser = await playwright_obj.chromium.connect_over_cdp(ws_endpoint)
                context = browser.contexts[0]
                page_obj = context.pages[0] if context.pages else await context.new_page()
                
                # 先导航到Google账号页面检查登录状态
                log("📍 检查登录状态...")
                await page_obj.goto("https://myaccount.google.com/", wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)
                
                # 确保已登录，如果未登录则自动登录
                login_success, login_msg = await ensure_logged_in(page_obj, account_info, log_callback)
                if not login_success:
                    log(f"❌ 登录失败: {login_msg}")
                    return False, f"登录失败: {login_msg}"
            except Exception as e:
                log(f"❌ 初始化浏览器失败: {e}")
                return False, str(e)

        page = page_obj
        
        # 导航到Personal info页面（这是访问Recovery email的正确入口）
        log("📍 导航到Personal info页面...")
        await page.goto("https://myaccount.google.com/personal-info", 
                      wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)
        
        # 处理可能的2FA验证和密码验证
        success, msg = await verify_2fa_if_needed(page, secret, log_callback, password=password, email=email)
        if not success:
            return False, msg
        
        await asyncio.sleep(2)
        
        # 步骤1: 点击 "Recovery email" - 使用用户提供的元素
        log("🔍 查找并点击 'Recovery email'...")
        
        # 增加等待时间确保页面完全加载
        await asyncio.sleep(5)
        
        recovery_email_clicked = False
        
        # 方法1: 使用用户提供的精确class
        try:
            log("   方法1: 查找 div.IlKlLe...")
            recovery_divs = await page.query_selector_all('div.IlKlLe')
            log(f"   找到 {len(recovery_divs)} 个 div.IlKlLe 元素")
            
            for div in recovery_divs:
                try:
                    text = await div.inner_text()
                    log(f"   检查文本: {text[:50]}")
                    # 支持多种文本变体：Recovery email, auxiliary email, 辅助邮箱等
                    if ('recovery' in text.lower() and 'email' in text.lower()) or \
                       ('auxiliary' in text.lower() and 'email' in text.lower()) or \
                       '辅助邮箱' in text or '恢复邮箱' in text:
                        # 点击这个div或其父元素
                        parent = await div.evaluate_handle('element => element.parentElement')
                        await parent.as_element().click()
                        log(f"✅ 点击了辅助邮箱元素: {text[:30]}")
                        recovery_email_clicked = True
                        break
                except Exception as e:
                    log(f"   检查元素时出错: {e}")
                    continue
        except Exception as e:
            log(f"⚠️ 方法1失败: {e}")
        
        # 方法2: 使用更宽泛的文本匹配
        if not recovery_email_clicked:
            log("   方法2: 使用文本选择器...")
            selectors = [
                # Recovery email variants
                'text="Recovery email"',
                'text="recovery email"',
                ':text("Recovery email")',
                ':text-is("Recovery email")',
                'div:has-text("Recovery email")',
                # Auxiliary email variants (Google有时用这个术语)
                'text="auxiliary email"',
                'text="Auxiliary email"',
                ':text("auxiliary email")',
                'div:has-text("auxiliary email")',
                # Chinese variants
                'text="辅助邮箱"',
                # Aria labels
                '[aria-label*="Recovery"]',
                '[aria-label*="recovery"]',
                '[aria-label*="auxiliary"]'
            ]
            
            for selector in selectors:
                try:
                    log(f"   尝试选择器: {selector}")
                    elem = page.locator(selector).first
                    count = await elem.count()
                    log(f"   找到 {count} 个匹配")
                    if count > 0:
                        await elem.wait_for(state='visible', timeout=5000)
                        is_visible = await elem.is_visible()
                        log(f"   元素可见: {is_visible}")
                        if is_visible:
                            await elem.click(timeout=5000)
                            log(f"✅ 点击了 Recovery email (使用选择器: {selector})")
                            recovery_email_clicked = True
                            break
                except Exception as e:
                    log(f"   选择器失败: {e}")
                    continue
        
        # 方法3: 直接查找所有包含"recovery"的元素
        if not recovery_email_clicked:
            log("   方法3: 搜索所有包含recovery的元素...")
            try:
                all_elements = await page.query_selector_all('div, span, a, button')
                log(f"   检查 {len(all_elements)} 个元素...")
                for elem in all_elements:
                    try:
                        text = await elem.inner_text()
                        if text and 'recovery' in text.lower() and 'email' in text.lower():
                            log(f"   找到可能的元素: {text[:50]}")
                            await elem.click(timeout=3000)
                            log("✅ 点击了 Recovery email (方法3)")
                            recovery_email_clicked = True
                            break
                    except:
                        continue
            except Exception as e:
                log(f"⚠️ 方法3失败: {e}")
        
        if not recovery_email_clicked:
            # 保存页面HTML用于调试
            try:
                log("💾 保存页面内容用于调试...")
                content = await page.content()
                import os
                base_path = os.path.dirname(os.path.abspath(__file__))
                debug_file = os.path.join(base_path, "debug_personal_info_page.html")
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                log(f"💾 页面已保存到: {debug_file}")
            except:
                pass
            
            log("❌ 未找到 Recovery email 选项")
            return False, "未找到 Recovery email 选项"
        
        await asyncio.sleep(3)
        
        # 步骤2: 可能需要输入密码或2FA验证码
        log("🔐 检查是否需要验证...")
        success, msg = await verify_2fa_if_needed(page, secret, log_callback, password=password, email=email, max_attempts=3)
        if not success:
            log(f"⚠️ 验证步骤遇到问题: {msg}")
        
        await asyncio.sleep(2)
        
        # 步骤3: 点击铅笔图标 - 使用用户提供的元素
        log("✏️ 查找并点击编辑按钮（铅笔图标）...")
        
        pencil_clicked = False
        
        # 方法1: 使用用户提供的精确class
        try:
            pencil_divs = await page.query_selector_all('div.pYTkkf-Bz112c-RLmnJb')
            if pencil_divs:
                # 通常只有一个，取第一个
                for pencil in pencil_divs:
                    if await pencil.is_visible():
                        await pencil.click()
                        log("✅ 点击了编辑按钮")
                        pencil_clicked = True
                        break
        except Exception as e:
            log(f"⚠️ 精确选择器失败: {e}")
        
        # 方法2: 备用选择器（查找编辑/铅笔图标的通用选择器）
        if not pencil_clicked:
            edit_selectors = [
                'button[aria-label*="Edit"]',
                'button[aria-label*="编辑"]',
                '[data-tooltip*="Edit"]',
                'button:has-text("Edit")',
                'div[role="button"]:has([d*="M3"])',  # SVG pencil icon path
            ]
            
            for selector in edit_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.count() > 0 and await elem.is_visible():
                        await elem.click()
                        log("✅ 点击了编辑按钮 (备用方法)")
                        pencil_clicked = True
                        break
                except:
                    continue
        
        if not pencil_clicked:
            log("❌ 未找到编辑按钮")
            return False, "未找到编辑按钮"
        
        await asyncio.sleep(2)
        
        # 步骤4: 输入新邮箱
        log(f"📝 输入新邮箱: {new_email}...")
        
        email_input = None
        
        # 查找邮箱输入框
        input_selectors = [
            'input[type="email"]',
            'input[autocomplete="email"]',
            'input[id*="email"]',
            'input[name*="email"]',
            'input[placeholder*="email"]',
            'input[placeholder*="邮箱"]'
        ]
        
        for selector in input_selectors:
            try:
                elem = page.locator(selector).first
                if await elem.count() > 0 and await elem.is_visible():
                    email_input = elem
                    break
            except:
                continue
        
        if not email_input:
            log("❌ 未找到邮箱输入框")
            return False, "未找到邮箱输入框"
        
        # 清空并输入新邮箱
        await email_input.fill('')
        await asyncio.sleep(0.3)
        await email_input.fill(new_email)
        await asyncio.sleep(1)
        
        log("✅ 邮箱输入完成")
        
        # 步骤5: 点击 Save 按钮 - 使用用户提供的元素
        log("💾 查找并点击 Save 按钮...")
        
        save_clicked = False
        
        # 方法1: 使用用户提供的精确选择器
        try:
            save_spans = await page.query_selector_all('span[jsname="V67aGc"].UywwFc-vQzf8d')
            for span in save_spans:
                try:
                    text = await span.inner_text()
                    if text.strip().lower() == 'save' or text.strip() == '保存':
                        if await span.is_visible():
                            await span.click()
                            log("✅ 点击了 Save 按钮")
                            save_clicked = True
                            break
                except:
                    continue
        except Exception as e:
            log(f"⚠️ 精确选择器失败: {e}")
        
        # 方法2: 备用选择器
        if not save_clicked:
            save_selectors = [
                'button:has-text("Save")',
                'button:has-text("保存")',
                'span:has-text("Save")',
                'div[role="button"]:has-text("Save")',
                '[aria-label*="Save"]'
            ]
            
            for selector in save_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.count() > 0 and await btn.is_visible():
                        await btn.click()
                        log("✅ 点击了 Save 按钮 (备用方法)")
                        save_clicked = True
                        break
                except:
                    continue
        
        if not save_clicked:
            log("❌ 未找到 Save 按钮")
            return False, "未找到 Save 按钮"
        
        await asyncio.sleep(3)
        
        # 步骤6: 获取并输入验证码
        log("📬 等待验证码...")
        log(f"   验证码将发送到: {new_email}")
        
        verification_code = None
        
        # 优先使用IMAP自动读取
        if imap_config and EMAIL_VERIFIER_AVAILABLE:
            log("🤖 使用IMAP自动读取验证码...")
            try:
                verification_code = get_google_verification_code_from_163(
                    email_address=imap_config.get('email', ''),
                    auth_code=imap_config.get('password', ''),
                    recovery_email=new_email,
                    timeout=120,
                    log_callback=log_callback
                )
            except Exception as e:
                log(f"⚠️ IMAP读取失败: {e}")
                verification_code = None
        
        # 如果IMAP失败，使用回调函数
        if not verification_code and verification_code_callback:
            log("⏸️ 等待手动输入验证码...")
            verification_code = await verification_code_callback(new_email)
        
        if not verification_code:
            log("❌ 未获取到验证码")
            return False, "未获取到验证码"
        
        log(f"✅ 获取到验证码: {verification_code}")
        
        # 输入验证码
        code_input = None
        code_selectors = [
            'input[type="tel"]',
            'input[type="text"]',
            'input[name*="code"]',
            'input[placeholder*="code"]',
            'input[placeholder*="验证码"]',
            'input[autocomplete="one-time-code"]'
        ]
        
        for selector in code_selectors:
            try:
                elem = page.locator(selector).first
                if await elem.count() > 0 and await elem.is_visible():
                    code_input = elem
                    break
            except:
                continue
        
        if not code_input:
            log("❌ 未找到验证码输入框")
            return False, "未找到验证码输入框"
        
        await code_input.fill(verification_code)
        await asyncio.sleep(1)
        log("✅ 验证码输入完成")
        
        # 点击确认/下一步按钮
        next_selectors = [
            'button:has-text("Next")',
            'button:has-text("下一步")',
            'button:has-text("Verify")',
            'button:has-text("验证")',
            'button:has-text("Confirm")',
            'button:has-text("确认")',
            'button[type="submit"]',
            'span[jsname="V67aGc"]:has-text("Next")',
            'span[jsname="V67aGc"]:has-text("Verify")'
        ]
        
        confirm_clicked = False
        for selector in next_selectors:
            try:
                btn = page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    log("✅ 点击了确认按钮")
                    confirm_clicked = True
                    break
            except:
                continue
        
        if not confirm_clicked:
            log("⚠️ 未找到确认按钮，验证码可能自动提交")
        
        await asyncio.sleep(3)
        
        # 检查是否成功
        success_indicators = ['Done', '完成', 'Success', '成功', 'saved', '已保存', 'verified', '已验证', 'updated', '已更新']
        page_text = await page.inner_text('body')
        
        is_success = any(indicator.lower() in page_text.lower() for indicator in success_indicators)
        
        if is_success or confirm_clicked:
            log(f"✅ 辅助邮箱修改成功！新邮箱: {new_email}")
            
            # 更新数据库
            try:
                from database import DBManager
                DBManager.update_recovery_email(email, new_email, old_recovery)
            except Exception as e:
                log(f"⚠️ 更新数据库时出错: {e}")
            
            return True, "辅助邮箱修改成功"
        else:
            log("⚠️ 无法确认是否修改成功")
            return True, "可能成功，请手动验证"
                
    except Exception as e:
        log(f"❌ 修改辅助邮箱失败: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)
    
    finally:
        if is_self_managed:
            if browser: 
                try: await browser.close()
                except: pass
            if playwright_obj: 
                try: await playwright_obj.stop()
                except: pass
            if close_browser:
                try:
                    closeBrowser(browser_id)
                except:
                    pass


def save_backup_codes(email: str, codes: list, log_callback=None):
    """
    将获取到的备份验证码保存到文件
    
    Args:
        email: 账号邮箱
        codes: 备份验证码列表
        log_callback: 日志回调函数
    
    Returns:
        bool: 是否保存成功
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        try:
            print(msg)
        except:
            pass
    
    try:
        base_path = get_base_path()
        file_path = os.path.join(base_path, "backup_codes.txt")
        
        # 获取当前时间
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 将codes列表转换为逗号分隔的字符串
        codes_str = ",".join(codes) if codes else ""
        
        # 追加写入文件
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp} | {email} | {codes_str}\n")
        
        log(f"📁 备份验证码已保存到: {file_path}")
        return True
    except Exception as e:
        log(f"⚠️ 保存备份验证码到文件时出错: {e}")
        return False


async def get_backup_codes(browser_id: str, account_info: dict, log_callback=None, close_browser=True, page=None):
    """
    获取Google账号的Backup codes
    
    Args:
        browser_id: BitBrowser窗口ID
        account_info: 账号信息字典 {'email', 'password', 'secret'}
        log_callback: 日志回调函数
        close_browser: 是否在完成后关闭浏览器（默认True）
        page: 现有的Playwright页面对象（可选）
    
    Returns:
        (success: bool, codes: list, message: str)
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        try:
            print(msg)
        except:
            pass
    
    email = account_info.get('email', '')
    secret = account_info.get('secret', '')
    password = account_info.get('password', '')
    
    log(f"🔐 开始获取备份验证码: {email}")
    
    playwright = None
    browser = None
    page_obj = page
    is_self_managed = False

    try:
        if not page_obj:
            is_self_managed = True
            try:
                # 打开浏览器
                result = openBrowser(browser_id)
                if not result.get('success'):
                    return False, [], "打开浏览器失败"
                
                ws_endpoint = result['data']['ws']
                
                playwright = await async_playwright().start()
                browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
                context = browser.contexts[0]
                page_obj = context.pages[0] if context.pages else await context.new_page()
                
                # 先导航到Google账号页面检查登录状态
                log("📍 检查登录状态...")
                await page_obj.goto("https://myaccount.google.com/", wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)
                
                # 确保已登录，如果未登录则自动登录
                login_success, login_msg = await ensure_logged_in(page_obj, account_info, log_callback)
                if not login_success:
                    log(f"❌ 登录失败: {login_msg}")
                    return False, [], f"登录失败: {login_msg}"
            except Exception as e:
                 log(f"❌ 初始化浏览器失败: {e}")
                 return False, [], str(e)
        
        if True:
            if True:
                # 为了兼容后续代码引用 page 变量，这里做个赋值
                page = page_obj
                
                # 导航到2FA设置页面
                log("📍 导航到2FA设置页面...")
                await page.goto("https://myaccount.google.com/signinoptions/two-step-verification", 
                              wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)
                
                # 处理可能的2FA验证和密码验证
                success, msg = await verify_2fa_if_needed(page, secret, log_callback, password=password, email=email)
                if not success:
                    return False, [], msg
                
                await asyncio.sleep(2)
                
                # 查找 Backup codes 选项
                log("🔍 查找 Backup codes 选项...")
                
                backup_selectors = [
                    'text="Backup codes"',
                    'text="备份验证码"',
                    'text="备用代码"',
                    'text="Backup verification codes"',
                    ':text("backup codes")',
                    'h2:has-text("Backup")',
                    'div:has-text("Backup codes")'
                ]
                
                backup_option = None
                for selector in backup_selectors:
                    try:
                        elements = await page.locator(selector).all()
                        for elem in elements:
                            if await elem.is_visible():
                                backup_option = elem
                                log(f"✅ 找到 Backup codes 选项")
                                break
                        if backup_option:
                            break
                    except:
                        continue
                
                if not backup_option:
                    log("❌ 未找到 Backup codes 选项")
                    return False, [], "未找到 Backup codes 选项"
                
                # 点击进入
                await backup_option.scroll_into_view_if_needed()
                await backup_option.click()
                await asyncio.sleep(3)
                
                # 查找 "Get backup codes" 或 "Show codes" 按钮
                log("🔄 查找获取备份验证码按钮...")
                
                get_codes_selectors = [
                    'text="Get backup codes"',
                    'text="获取备份验证码"',
                    'text="Show codes"',
                    'text="显示代码"',
                    'text="Get new codes"',
                    'text="获取新代码"',
                    'button:has-text("Get")',
                    'button:has-text("Show")',
                    'button:has-text("获取")',
                    'button:has-text("显示")'
                ]
                
                get_btn = None
                for selector in get_codes_selectors:
                    try:
                        btn = page.locator(selector).first
                        if await btn.count() > 0 and await btn.is_visible():
                            get_btn = btn
                            log(f"✅ 找到按钮: {selector}")
                            break
                    except:
                        continue
                
                if get_btn:
                    await get_btn.click()
                    log("✅ 点击了获取备份验证码按钮")
                    await asyncio.sleep(3)
                
                # 可能需要再次验证密码/2FA
                await verify_2fa_if_needed(page, secret, log_callback, password=password, email=email, max_attempts=2)
                await asyncio.sleep(2)
                
                # 提取备份验证码
                log("🔑 提取备份验证码...")
                
                codes = []
                codes_set = set()  # 用于去重
                
                # 方法1: 优先从页面文本内容提取（避免HTML标签干扰）
                try:
                    # 获取页面可见文本
                    page_text = await page.inner_text('body')
                    
                    # 匹配8位数字（可能带空格或连字符）
                    # Google备份码格式通常是: 1234 5678 或 12345678
                    # 使用单词边界确保不会匹配更长的数字
                    patterns = [
                        r'\b(\d{4})\s+(\d{4})\b',  # 1234 5678 格式
                        r'\b(\d{8})\b',             # 12345678 格式
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, page_text)
                        for match in matches:
                            if isinstance(match, tuple):
                                if len(match) == 2 and match[0] and match[1]:
                                    # 格式: (1234, 5678)
                                    code = f"{match[0]} {match[1]}"
                                    if code not in codes_set and len(codes_set) < 10:
                                        codes_set.add(code)
                                        codes.append(code)
                                elif len(match) == 1 or (len(match) == 2 and not match[1]):
                                    # 格式: 12345678
                                    num = match[0] if match[0] else match
                                    if len(num) == 8 and num.isdigit():
                                        code = f"{num[:4]} {num[4:]}"
                                        if code not in codes_set and len(codes_set) < 10:
                                            codes_set.add(code)
                                            codes.append(code)
                            else:
                                # 单个匹配（12345678格式）
                                if len(match) == 8 and match.isdigit():
                                    code = f"{match[:4]} {match[4:]}"
                                    if code not in codes_set and len(codes_set) < 10:
                                        codes_set.add(code)
                                        codes.append(code)
                    
                    log(f"   方法1提取到 {len(codes)} 个备份码")
                except Exception as e:
                    log(f"⚠️ 方法1提取失败: {e}")
                
                # 方法2: 如果方法1提取不够，从DOM元素提取
                if len(codes) < 10:
                    try:
                        log("   使用方法2从DOM元素提取...")
                        # 查找可能包含备份码的元素
                        selectors = [
                            'li',           # 列表项
                            'div[role="listitem"]',
                            'span',
                            'td',           # 表格单元格
                            're',           # 可能的代码容器
                        ]
                        
                        for selector in selectors:
                            if len(codes) >= 10:
                                break
                            
                            elements = await page.query_selector_all(selector)
                            for elem in elements:
                                try:
                                    text = await elem.inner_text()
                                    text = text.strip()
                                    
                                    # 检查是否是8位数字（可能带空格）
                                    clean = text.replace(' ', '').replace('-', '').replace('\n', '')
                                    if len(clean) == 8 and clean.isdigit():
                                        code = f"{clean[:4]} {clean[4:]}"
                                        if code not in codes_set and len(codes_set) < 10:
                                            codes_set.add(code)
                                            codes.append(code)
                                except:
                                    continue
                        
                        log(f"   方法2额外提取到 {len(codes) - len(codes_set)} 个备份码")
                    except Exception as e:
                        log(f"⚠️ 方法2提取失败: {e}")
                
                # 最终只保留前10个（Google只生成10个备份码）
                codes = codes[:10]
                
                # 打印提取到的备份码用于调试
                if codes:
                    log(f"📋 提取到的备份码:")
                    for i, code in enumerate(codes, 1):
                        log(f"   {i}. {code}")
                
                # 通常会有10个备份验证码
                if len(codes) >= 8:
                    log(f"✅ 成功提取到 {len(codes)} 个备份验证码")
                    
                    # 保存到文件
                    save_backup_codes(email, codes, log_callback)
                    
                    # 更新数据库
                    try:
                        from database import DBManager
                        DBManager.update_backup_codes(email, codes)
                    except Exception as e:
                        log(f"⚠️ 更新数据库时出错: {e}")
                    
                    return True, codes, "成功获取备份验证码"
                else:
                    log(f"⚠️ 只找到 {len(codes)} 个验证码，可能提取不完整")
                    if codes:
                        save_backup_codes(email, codes, log_callback)
                        return True, codes, f"获取到 {len(codes)} 个备份验证码"
                    else:
                        return False, [], "未能提取到备份验证码"
                
    except Exception as e:
        log(f"❌ 获取备份验证码失败: {e}")
        return False, [], str(e)
    
    finally:
        if is_self_managed:
            if browser: 
                try: await browser.close()
                except: pass
            if playwright: 
                try: await playwright.stop()
                except: pass
            if close_browser:
                try:
                    closeBrowser(browser_id)
                except:
                    pass


async def one_click_security_update(browser_id: str, account_info: dict, 
                                     new_recovery_email: str = None,
                                     verification_code_callback=None,
                                     log_callback=None,
                                     imap_config: dict = None):
    """
    一键修改安全信息（2FA + Backup Codes + 辅助邮箱），共享浏览器会话
    
    Args:
        browser_id: BitBrowser窗口ID
        account_info: 账号信息字典
        new_recovery_email: 新的辅助邮箱地址（可选）
        verification_code_callback: 获取验证码的回调函数
        log_callback: 日志回调函数
        imap_config: IMAP配置字典，格式: {'email': 'xxx@163.com', 'password': 'auth_code'}
    
    Returns:
        dict: 包含各项操作结果的字典
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        try:
            print(msg)
        except:
            pass
    
    email = account_info.get('email', '')
    
    log(f"🚀 开始一键修改安全信息: {email}")
    log("=" * 50)
    
    results = {
        '2fa': {'success': False, 'new_secret': None, 'message': ''},
        'backup_codes': {'success': False, 'codes': [], 'message': ''},
        'recovery_email': {'success': False, 'new_email': None, 'message': ''}
    }
    
    playwright = None
    browser = None
    page = None
    
    try:
        # 1. 统一初始化浏览器连接
        log("🔌 初始化浏览器连接...")
        result = openBrowser(browser_id)
        if not result.get('success'):
            raise Exception("无法打开浏览器")
        
        ws_endpoint = result['data']['ws']
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        
        # 2. 统一检查登录状态
        log("📍 检查登录状态...")
        await page.goto("https://myaccount.google.com/", wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)
        
        login_success, login_msg = await ensure_logged_in(page, account_info, log_callback)
        if not login_success:
            raise Exception(f"登录失败: {login_msg}")
        
        # 第1步: 修改2FA密钥（传递 page）
        log("\n📌 第1步: 修改2FA密钥...")
        success, new_secret, message = await change_2fa_secret(
            browser_id, account_info, log_callback, close_browser=False, page=page
        )
        results['2fa'] = {
            'success': success,
            'new_secret': new_secret,
            'message': message
        }
        
        if success and new_secret:
            # 更新account_info中的secret，供后续步骤使用
            account_info['secret'] = new_secret
            log(f"✅ 2FA密钥修改成功: {new_secret}")
        else:
            log(f"❌ 2FA密钥修改失败: {message}")
            if "登录失败" in str(message):
                raise Exception("会话中断")
    
        await asyncio.sleep(3)
        
        # 第2步: 获取备份验证码（传递 page）
        log("\n📌 第2步: 获取备份验证码...")
        success, codes, message = await get_backup_codes(
            browser_id, account_info, log_callback, close_browser=False, page=page
        )
        results['backup_codes'] = {
            'success': success,
            'codes': codes,
            'message': message
        }
        
        if success:
            log(f"✅ 备份验证码获取成功: {len(codes)} 个")
        else:
            log(f"❌ 备份验证码获取失败: {message}")
    
        await asyncio.sleep(3)
        
        # 第3步: 修改辅助邮箱（如果提供了新邮箱）
        if new_recovery_email:
            log("\n📌 第3步: 修改辅助邮箱...")
            success, message = await change_recovery_email(
                browser_id, account_info, new_recovery_email,
                verification_code_callback, log_callback, close_browser=False, page=page,
                imap_config=imap_config
            )
            results['recovery_email'] = {
                'success': success,
                'new_email': new_recovery_email if success else None,
                'message': message
            }
            
            if success:
                log(f"✅ 辅助邮箱修改成功: {new_recovery_email}")
            else:
                log(f"❌ 辅助邮箱修改失败: {message}")
        else:
            log("\n📌 第3步: 跳过修改辅助邮箱（未提供新邮箱）")
            results['recovery_email']['message'] = '跳过'
            
    except Exception as e:
        log(f"❌ 一键修改过程中止: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 统一清理资源
        log("\n🧹 清理资源...")
        if browser:
            try: await browser.close()
            except: pass
        if playwright:
            try: await playwright.stop()
            except: pass
        try:
            closeBrowser(browser_id)
        except: pass
    
    # 汇总结果
    log("\n" + "=" * 50)
    log("📊 一键修改安全信息完成!")
    log(f"   2FA密钥: {'✅ 成功' if results['2fa']['success'] else '❌ 失败'}")
    log(f"   备份验证码: {'✅ 成功' if results['backup_codes']['success'] else '❌ 失败'}")
    log(f"   辅助邮箱: {'✅ 成功' if results['recovery_email']['success'] else ('⏭️ 跳过' if not new_recovery_email else '❌ 失败')}")
    log("=" * 50)
    
    return results


# 测试入口
if __name__ == "__main__":
    print("Google Security Automation Module")
    print("=" * 40)
    
    # 测试加载邮箱列表
    emails = load_recovery_emails()
    print(f"加载了 {len(emails)} 个备用邮箱")
    
    if emails:
        random_email = get_random_recovery_email(emails)
        print(f"随机选择: {random_email}")

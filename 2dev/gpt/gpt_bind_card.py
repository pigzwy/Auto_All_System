"""
GPT 绑卡订阅模块
- 支持 Plus 和 Business 订阅
- 支持一卡一绑 / 一卡多绑
"""
import asyncio
import os
import sys
from playwright.async_api import Page

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_base_path():
    """获取基础路径"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_cards():
    """
    从 cards.txt 加载信用卡信息
    
    Returns:
        list: 卡信息列表 [{'number', 'exp_month', 'exp_year', 'cvv'}, ...]
    """
    cards = []
    base_path = get_base_path()
    file_path = os.path.join(base_path, "cards.txt")
    
    if not os.path.exists(file_path):
        return cards
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split()
                if len(parts) >= 4:
                    cards.append({
                        'number': parts[0],
                        'exp_month': parts[1],
                        'exp_year': parts[2],
                        'cvv': parts[3]
                    })
    except Exception:
        pass
    
    return cards


async def gpt_navigate_to_upgrade(page: Page, sub_type: str = 'plus', log_callback=None):
    """
    导航到升级页面
    
    Args:
        page: Playwright Page 对象
        sub_type: 订阅类型 'plus' 或 'business'
        log_callback: 日志回调函数
    
    Returns:
        (success: bool, message: str)
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)
    
    try:
        log(f"📍 导航到 {sub_type.upper()} 升级页面...")
        
        # 根据类型选择不同的 URL
        if sub_type == 'business':
            # Business 订阅页面
            await page.goto("https://chatgpt.com/#settings/DataControls", 
                          wait_until='domcontentloaded', timeout=30000)
        else:
            # Plus 订阅页面
            await page.goto("https://chatgpt.com/#pricing", 
                          wait_until='domcontentloaded', timeout=30000)
        
        await asyncio.sleep(3)
        
        # 查找升级按钮
        upgrade_selectors = [
            'button:has-text("Upgrade")',
            'button:has-text("升级")',
            'button:has-text("Subscribe")',
            'button:has-text("订阅")',
            'a:has-text("Upgrade to Plus")',
            'a:has-text("Upgrade to Team")',
        ]
        
        for selector in upgrade_selectors:
            try:
                btn = page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    log(f"✅ 点击升级按钮")
                    await asyncio.sleep(3)
                    return True, "已进入升级页面"
            except:
                continue
        
        log("⚠️ 未找到升级按钮")
        return False, "未找到升级按钮"
        
    except Exception as e:
        log(f"❌ 导航失败: {e}")
        return False, str(e)


async def gpt_fill_card_stripe(page: Page, card_info: dict, log_callback=None):
    """
    填写 Stripe 支付表单
    
    Args:
        page: Playwright Page 对象
        card_info: 卡信息 {'number', 'exp_month', 'exp_year', 'cvv'}
        log_callback: 日志回调函数
    
    Returns:
        (success: bool, message: str)
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)
    
    log("💳 填写支付信息...")
    
    try:
        # 等待 Stripe iframe 加载
        await asyncio.sleep(3)
        
        # 方法1: 直接查找输入框 (无 iframe 的情况)
        card_number_selectors = [
            'input[name="cardNumber"]',
            'input[placeholder*="card number"]',
            'input[placeholder*="卡号"]',
            'input[data-elements-stable-field-name="cardNumber"]',
        ]
        
        card_input = None
        for selector in card_number_selectors:
            try:
                elem = page.locator(selector).first
                if await elem.count() > 0 and await elem.is_visible():
                    card_input = elem
                    break
            except:
                continue
        
        # 方法2: 查找 Stripe iframe
        if not card_input:
            log("🔍 查找 Stripe iframe...")
            
            iframe_selectors = [
                'iframe[name*="stripe"]',
                'iframe[src*="stripe.com"]',
                'iframe[title*="Secure card"]',
            ]
            
            for iframe_sel in iframe_selectors:
                try:
                    iframe_elem = page.frame_locator(iframe_sel).first
                    card_input = iframe_elem.locator('input[name="cardnumber"], input[placeholder*="number"]').first
                    if await card_input.count() > 0:
                        log("✅ 找到 Stripe iframe")
                        break
                except:
                    continue
        
        if not card_input:
            log("❌ 未找到卡号输入框")
            return False, "未找到卡号输入框"
        
        # 填写卡号
        log("📝 输入卡号...")
        await card_input.fill(card_info['number'])
        await asyncio.sleep(0.5)
        
        # 填写过期日期
        exp_selectors = [
            'input[name="cardExpiry"]',
            'input[placeholder*="MM"]',
            'input[placeholder*="expir"]',
        ]
        
        for selector in exp_selectors:
            try:
                exp_input = page.locator(selector).first
                if await exp_input.count() > 0 and await exp_input.is_visible():
                    exp_value = f"{card_info['exp_month']}/{card_info['exp_year']}"
                    await exp_input.fill(exp_value)
                    log("📝 输入过期日期")
                    break
            except:
                continue
        
        await asyncio.sleep(0.3)
        
        # 填写 CVV
        cvv_selectors = [
            'input[name="cardCvc"]',
            'input[placeholder*="CVC"]',
            'input[placeholder*="CVV"]',
            'input[placeholder*="安全码"]',
        ]
        
        for selector in cvv_selectors:
            try:
                cvv_input = page.locator(selector).first
                if await cvv_input.count() > 0 and await cvv_input.is_visible():
                    await cvv_input.fill(card_info['cvv'])
                    log("📝 输入 CVV")
                    break
            except:
                continue
        
        await asyncio.sleep(0.5)
        
        log("✅ 支付信息填写完成")
        return True, "卡信息已填写"
        
    except Exception as e:
        log(f"❌ 填写失败: {e}")
        return False, str(e)


async def gpt_confirm_subscribe(page: Page, log_callback=None):
    """
    确认订阅
    
    Returns:
        (success: bool, message: str)
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)
    
    log("🔄 确认订阅...")
    
    try:
        # 查找确认按钮
        confirm_selectors = [
            'button:has-text("Subscribe")',
            'button:has-text("订阅")',
            'button:has-text("Pay")',
            'button:has-text("支付")',
            'button:has-text("Confirm")',
            'button:has-text("确认")',
            'button[type="submit"]',
        ]
        
        for selector in confirm_selectors:
            try:
                btn = page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    log("✅ 点击订阅确认按钮")
                    break
            except:
                continue
        
        # 等待处理
        await asyncio.sleep(5)
        
        # 检查是否成功
        success_indicators = [
            'text="Thank you"',
            'text="Success"',
            'text="成功"',
            'text="Welcome to"',
            'text="You\'re all set"',
        ]
        
        for indicator in success_indicators:
            try:
                if await page.locator(indicator).is_visible():
                    log("✅ 订阅成功！")
                    return True, "订阅成功"
            except:
                continue
        
        log("⚠️ 无法确认订阅结果")
        return True, "可能成功，请手动验证"
        
    except Exception as e:
        log(f"❌ 确认订阅失败: {e}")
        return False, str(e)


async def gpt_subscribe(page: Page, card_info: dict, sub_type: str = 'plus', log_callback=None):
    """
    完整的订阅流程
    
    Args:
        page: Playwright Page 对象
        card_info: 卡信息
        sub_type: 订阅类型 'plus' 或 'business'
        log_callback: 日志回调函数
    
    Returns:
        (success: bool, message: str)
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)
    
    log(f"🚀 开始 {sub_type.upper()} 订阅流程...")
    
    # 1. 导航到升级页面
    success, msg = await gpt_navigate_to_upgrade(page, sub_type, log_callback)
    if not success:
        return False, msg
    
    # 2. 填写支付信息
    success, msg = await gpt_fill_card_stripe(page, card_info, log_callback)
    if not success:
        return False, msg
    
    # 3. 确认订阅
    success, msg = await gpt_confirm_subscribe(page, log_callback)
    
    return success, msg


def save_subscription_result(email: str, sub_type: str, success: bool, message: str):
    """保存订阅结果到文件"""
    base_path = get_base_path()
    
    if success:
        file_path = os.path.join(base_path, "gpt", "gpt_subscribed.txt")
    else:
        file_path = os.path.join(base_path, "gpt", "gpt_failed.txt")
    
    try:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp} | {email} | {sub_type} | {message}\n")
    except Exception:
        pass

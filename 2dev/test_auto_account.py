# -*- coding: utf-8 -*-
"""
测试脚本：为指定账号创建BitBrowser配置并运行一键全自动处理
"""
import asyncio
import sys
import os
import io

# 设置标准输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 测试账号信息
TEST_ACCOUNT = {
    'email': 'JenriMonroy486@gmail.com',
    'password': 'xdkih2i3w7x',
    'backup': 'JenriMonroy48671950@thienlong.site',
    '2fa_secret': '5dxz2nzak2oqhc7sc6a7kcqol3yst624',
    'full_line': 'JenriMonroy486@gmail.com----xdkih2i3w7x----JenriMonroy48671950@thienlong.site----5dxz2nzak2oqhc7sc6a7kcqol3yst624'
}

# API Key
API_KEY = '0c5cba479e6aa914d66a287d88b15bea'

# 卡片信息
CARD_INFO = {
    'number': '5177467406471398',
    'exp_month': '01',
    'exp_year': '29',
    'cvv': '947',
    'name': 'John Yadav'
}

from create_window import get_browser_list, get_browser_info, create_browser_window
from database import DBManager

def find_or_create_browser(account):
    """查找或创建浏览器配置"""
    # 先查找是否已有此账号的浏览器
    browsers = get_browser_list(page=0, pageSize=100)
    
    for b in browsers:
        user_name = b.get('userName', '')
        if user_name.lower() == account['email'].lower():
            print(f"[OK] Found existing browser: {b.get('id')}")
            return b.get('id'), None
    
    # 如果不存在，使用现有的浏览器作为模板创建
    if browsers:
        reference_id = browsers[0].get('id')
        print(f"Using template browser ID: {reference_id}")
        
        browser_id, error = create_browser_window(
            account=account,
            reference_browser_id=reference_id,
            name_prefix="Gemini"
        )
        
        if error:
            return None, error
        
        print(f"[OK] Created new browser: {browser_id}")
        return browser_id, None
    else:
        return None, "No template browser available"

async def run_single_account_test(browser_id, account, card_info, api_key):
    """运行单个账号的自动化测试"""
    from playwright.async_api import async_playwright
    from bit_api import openBrowser, closeBrowser
    from run_playwright_google import check_and_login, detect_account_status
    
    print(f"\n{'='*60}")
    print(f"Starting test for account: {account['email']}")
    print(f"Browser ID: {browser_id}")
    print(f"{'='*60}\n")
    
    # 打开浏览器
    result = openBrowser(browser_id)
    if not result.get('success'):
        print(f"[FAIL] Failed to open browser: {result}")
        return False, "Failed to open browser"
    
    ws_endpoint = result['data']['ws']
    print(f"[OK] Browser opened, WebSocket: {ws_endpoint[:50]}...")
    
    async with async_playwright() as playwright:
        try:
            chromium = playwright.chromium
            browser = await chromium.connect_over_cdp(ws_endpoint)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            
            account_info = {
                'email': account['email'],
                'password': account['password'],
                'backup': account['backup'],
                'secret': account['2fa_secret']
            }
            
            # Step 1: 登录检测
            print(f"  [Step 1] Login check...")
            target_url = "https://one.google.com/ai-student?g1_landing_page=75&utm_source=antigravity&utm_campaign=argon_limit_reached"
            
            login_success, login_msg = await check_and_login(page, account_info, target_url)
            if not login_success:
                print(f"  [FAIL] Login failed: {login_msg}")
                return False, f"Login failed: {login_msg}"
            
            print(f"  [OK] Login successful")
            
            # Step 2: 状态检测
            print(f"  [Step 2] Status detection...")
            await asyncio.sleep(3)
            
            status = await detect_account_status(page)
            print(f"  [INFO] Current status: {status}")
            
            # Step 3: 根据状态执行操作
            if status == "verified":
                print(f"  [INFO] SheerID verified, proceeding to card binding")
                # 这里可以导入并调用绑卡函数
                from auto_all_in_one_gui import AutoAllInOneWorker
                
                # 创建一个简单的日志发射器
                class LogEmitter:
                    def emit(self, msg):
                        print(f"    {msg}")
                
                # 创建一个简单的worker来处理绑卡
                worker = AutoAllInOneWorker([], [], 1, {}, api_key, 1)
                worker.log_signal = LogEmitter()
                
                delays = {
                    'after_offer': 8,
                    'after_add_card': 10,
                    'after_save': 18
                }
                
                success, message = await worker._handle_verified(page, card_info, account_info, delays)
                print(f"\n{'='*60}")
                if success:
                    print(f"[SUCCESS] Card binding successful: {message}")
                else:
                    print(f"[FAIL] Card binding failed: {message}")
                print(f"{'='*60}")
                return success, message
                
            elif status == "link_ready":
                print(f"  [INFO] Needs SheerID verification first")
                return False, "Needs SheerID verification"
                
            elif status == "subscribed":
                print(f"  [OK] Account already subscribed")
                return True, "Account already subscribed"
                
            elif status == "ineligible":
                print(f"  [FAIL] Account is ineligible")
                return False, "Account is ineligible"
            else:
                print(f"  [WARN] Unknown status: {status}")
                return False, f"Unknown status: {status}"
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, str(e)

def main():
    print("="*60)
    print("Auto All-in-One Test")
    print("="*60)
    
    # 1. 查找或创建浏览器配置
    print("\n[1] Finding/Creating browser profile...")
    browser_id, error = find_or_create_browser(TEST_ACCOUNT)
    
    if error:
        print(f"[ERROR] {error}")
        return
    
    # 2. 更新数据库中的账号状态
    print("\n[2] Checking account in database...")
    DBManager.init_db()
    conn = DBManager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email, status FROM accounts WHERE email = ?", (TEST_ACCOUNT['email'],))
    row = cursor.fetchone()
    if row:
        print(f"  Account status: {row[1]}")
    else:
        print(f"  [WARN] Account not in database")
    conn.close()
    
    # 3. 运行自动化测试
    print("\n[3] Running automation test...")
    asyncio.run(run_single_account_test(browser_id, TEST_ACCOUNT, CARD_INFO, API_KEY))

if __name__ == "__main__":
    main()

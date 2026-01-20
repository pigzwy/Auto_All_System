# -*- coding: utf-8 -*-
"""
验证脚本：检查当前页面状态确认订阅结果
"""
import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from playwright.async_api import async_playwright
from bit_api import openBrowser
from create_window import get_browser_list

async def verify():
    browsers = get_browser_list(page=0, pageSize=100)
    browser_id = None
    for b in browsers:
        if 'JenriMonroy486' in b.get('userName', ''):
            browser_id = b.get('id')
            break
    
    if not browser_id:
        print("Browser not found")
        return
    
    result = openBrowser(browser_id)
    if not result.get('success'):
        return
    
    ws_endpoint = result['data']['ws']
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        
        print(f"Current URL: {page.url}")
        
        # 检查页面上的文本内容
        print("\n=== Checking page content ===")
        
        # 检查是否有错误信息
        error_keywords = ['error', 'declined', 'failed', 'invalid', 'unable', 'cannot']
        for keyword in error_keywords:
            try:
                locator = page.locator(f'text=/{keyword}/i')
                count = await locator.count()
                if count > 0:
                    for i in range(min(count, 3)):
                        text = await locator.nth(i).text_content()
                        if text and len(text.strip()) < 200:
                            print(f"  Found '{keyword}': {text.strip()[:100]}")
            except:
                pass
        
        # 检查是否显示成功信息
        success_keywords = ['success', 'complete', 'thank you', 'subscribed', 'active']
        for keyword in success_keywords:
            try:
                locator = page.locator(f'text=/{keyword}/i')
                count = await locator.count()
                if count > 0:
                    for i in range(min(count, 3)):
                        text = await locator.nth(i).text_content()
                        if text and len(text.strip()) < 200:
                            print(f"  Found '{keyword}': {text.strip()[:100]}")
            except:
                pass
        
        # 检查所有frame中的对话框/弹窗内容
        print("\n=== Checking dialogs in all frames ===")
        for i, frame in enumerate(page.frames):
            try:
                # 查找可能的错误提示
                dialogs = await frame.locator('[role="dialog"], [role="alertdialog"], .dialog, .modal').all()
                if dialogs:
                    print(f"  Frame {i} ({frame.url[:50]}): Found {len(dialogs)} dialog(s)")
                    for d in dialogs[:2]:
                        text = await d.text_content()
                        if text:
                            print(f"    Dialog content: {text[:300]}")
            except:
                pass
        
        # 截图保存
        print("\nTaking screenshot...")
        await page.screenshot(path="verify_result.png", full_page=True)
        print("Screenshot saved to verify_result.png")

asyncio.run(verify())

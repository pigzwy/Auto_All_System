# -*- coding: utf-8 -*-
"""验证最终订阅状态"""
import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from playwright.async_api import async_playwright
from bit_api import openBrowser
from create_window import get_browser_list

async def verify_subscription():
    browsers = get_browser_list(page=0, pageSize=100)
    browser_id = None
    for b in browsers:
        if 'JenriMonroy486' in b.get('userName', ''):
            browser_id = b.get('id')
            break
    
    result = openBrowser(browser_id)
    ws_endpoint = result['data']['ws']
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
        context = browser.contexts[0]
        page = context.pages[0]
        
        print(f"Current URL: {page.url[:80]}")
        
        # 检查页面上的所有文本
        print("\n=== Page content summary ===")
        for i, frame in enumerate(page.frames):
            try:
                text = await frame.evaluate("document.body ? document.body.innerText : ''")
                if text and len(text) > 50:
                    # 查找关键词
                    keywords = ['subscribed', 'active', 'member', 'trial', 'thank', 'success', 'welcome', 'google one', 'ai pro']
                    for kw in keywords:
                        if kw.lower() in text.lower():
                            print(f"\nFrame {i} contains '{kw}':")
                            # 打印相关的行
                            lines = [l.strip() for l in text.split('\n') if l.strip() and kw.lower() in l.lower()][:5]
                            for line in lines:
                                if len(line) < 150:
                                    print(f"  {line}")
            except:
                pass
        
        # 检查是否还有 Subscribe 按钮
        print("\n=== Checking for Subscribe button ===")
        subscribe_found = False
        for frame in page.frames:
            try:
                locator = frame.locator('button:has-text("Subscribe")')
                if await locator.count() > 0 and await locator.first.is_visible():
                    subscribe_found = True
                    print("  Subscribe button is still visible - subscription may not be complete")
            except:
                pass
        
        if not subscribe_found:
            print("  Subscribe button NOT found - likely subscription is complete!")
        
        # 导航到 Google One 页面验证订阅状态
        print("\n=== Navigating to Google One to verify ===")
        await page.goto("https://one.google.com/", wait_until='domcontentloaded')
        await asyncio.sleep(5)
        
        text = await page.evaluate("document.body.innerText")
        if 'AI Pro' in text or 'Subscri' in text or 'member' in text.lower():
            print("Google One page shows subscription info:")
            lines = [l.strip() for l in text.split('\n') if l.strip()][:30]
            for line in lines:
                if len(line) < 100 and any(k in line.lower() for k in ['ai', 'pro', 'subscri', 'member', 'storage', 'tb', 'trial']):
                    print(f"  {line}")
        
        await page.screenshot(path="final_verify.png")
        print("\nScreenshot saved to final_verify.png")

asyncio.run(verify_subscription())

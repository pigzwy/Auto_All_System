# -*- coding: utf-8 -*-
"""调试 Save card 按钮选择器"""
import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from playwright.async_api import async_playwright
from bit_api import openBrowser
from create_window import get_browser_list

async def debug_save_card():
    browsers = get_browser_list(page=0, pageSize=100)
    browser_id = None
    for b in browsers:
        if 'JolinCandra' in b.get('userName', ''):
            browser_id = b.get('id')
            break
    
    if not browser_id:
        print("Browser not found")
        return
    
    result = openBrowser(browser_id)
    ws_endpoint = result['data']['ws']
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
        context = browser.contexts[0]
        page = context.pages[0]
        
        # 导航
        target_url = "https://one.google.com/ai-student?g1_landing_page=75&utm_source=antigravity&utm_campaign=argon_limit_reached"
        await page.goto(target_url, wait_until='domcontentloaded')
        await asyncio.sleep(3)
        
        # 点击 Get student offer
        print("Step 1: Click Get student offer...")
        try:
            await page.locator('button[jsname="eWp5Fc"]').first.click(force=True)
        except:
            pass
        
        await asyncio.sleep(8)
        
        # 点击 Add card
        print("Step 2: Click Add card...")
        for frame in page.frames:
            try:
                locator = frame.get_by_text("Add card", exact=True)
                if await locator.count() > 0:
                    await locator.first.click()
                    print("  Clicked Add card")
                    break
            except:
                pass
        
        await asyncio.sleep(8)
        
        # 找到表单 frame 并列出所有按钮
        print("\nStep 3: Looking for Save card button in all frames...")
        
        for i, frame in enumerate(page.frames):
            if 'payments.google.com' not in frame.url:
                continue
            
            print(f"\n[Frame {i}] {frame.url[:60]}")
            
            try:
                buttons = await frame.locator('button').all()
                if buttons:
                    print(f"  Found {len(buttons)} buttons:")
                    for j, btn in enumerate(buttons):
                        try:
                            text = await btn.text_content()
                            jsname = await btn.get_attribute('jsname') or ''
                            classes = await btn.get_attribute('class') or ''
                            visible = await btn.is_visible()
                            enabled = await btn.is_enabled()
                            
                            text_clean = text.strip()[:40] if text else 'NO TEXT'
                            print(f"    [{j}] text='{text_clean}' jsname={jsname} visible={visible} enabled={enabled}")
                            print(f"        class={classes[:60]}")
                        except:
                            pass
            except Exception as e:
                print(f"  Error: {e}")
        
        # 尝试查找包含 "Save" 的按钮
        print("\n\nStep 4: Looking for buttons with 'Save' text...")
        for frame in page.frames:
            try:
                locator = frame.locator('button:has-text("Save")')
                count = await locator.count()
                if count > 0:
                    print(f"  Frame {frame.url[:40]}: Found {count} 'Save' buttons")
                    for i in range(count):
                        btn = locator.nth(i)
                        text = await btn.text_content()
                        visible = await btn.is_visible()
                        print(f"    [{i}] text='{text.strip()[:50]}' visible={visible}")
            except:
                pass
        
        await page.screenshot(path="debug_save_card.png")
        print("\nScreenshot saved")

asyncio.run(debug_save_card())

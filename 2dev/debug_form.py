# -*- coding: utf-8 -*-
"""
调试脚本：完整流程并在每一步检查结果
"""
import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from playwright.async_api import async_playwright
from bit_api import openBrowser
from create_window import get_browser_list

# 卡片信息
CARD_INFO = {
    'number': '5177467406471398',
    'exp_month': '01',
    'exp_year': '29',
    'cvv': '947'
}

async def debug_full_flow():
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
        
        # 导航
        target_url = "https://one.google.com/ai-student?g1_landing_page=75&utm_source=antigravity&utm_campaign=argon_limit_reached"
        print("Step 1: Navigate...")
        await page.goto(target_url, wait_until='domcontentloaded')
        await asyncio.sleep(3)
        
        # 点击 Get student offer
        print("Step 2: Click Get student offer...")
        try:
            await page.locator('button[jsname="eWp5Fc"]').first.click(force=True)
            print("  OK")
        except Exception as e:
            print(f"  Error: {e}")
        
        await asyncio.sleep(10)
        
        # 点击 Add card
        print("Step 3: Click Add card...")
        add_card_clicked = False
        for _ in range(30):
            for frame in page.frames:
                try:
                    locator = frame.get_by_text("Add card", exact=True)
                    if await locator.count() > 0:
                        await locator.first.click()
                        add_card_clicked = True
                        print(f"  OK - clicked")
                        break
                except:
                    pass
            if add_card_clicked:
                break
            await asyncio.sleep(1)
        
        if not add_card_clicked:
            print("  Failed")
            return
        
        await asyncio.sleep(8)
        
        # 找到表单 frame
        print("Step 4: Find form frame...")
        form_frame = None
        for frame in page.frames:
            if 'payments.google.com' in frame.url and 'instrumentmanager' in frame.url:
                locator = frame.locator('#i5')
                if await locator.count() > 0:
                    form_frame = frame
                    print(f"  Found: {frame.url[:60]}")
                    break
        
        if not form_frame:
            print("  Form frame not found")
            return
        
        # 填写卡号
        print("Step 5: Fill card number...")
        try:
            locator = form_frame.locator('#i5')
            await locator.first.click()
            await locator.first.fill("")
            await locator.first.press_sequentially(CARD_INFO['number'], delay=100)
            value = await locator.first.input_value()
            print(f"  Filled: {value}")
        except Exception as e:
            print(f"  Error: {e}")
        
        await asyncio.sleep(0.5)
        
        # 填写有效期
        print("Step 6: Fill expiry...")
        try:
            locator = form_frame.locator('#i10')
            await locator.first.click()
            await locator.first.fill("")
            exp_value = f"{CARD_INFO['exp_month']}/{CARD_INFO['exp_year']}"
            await locator.first.press_sequentially(exp_value, delay=100)
            value = await locator.first.input_value()
            print(f"  Filled: {value}")
        except Exception as e:
            print(f"  Error: {e}")
        
        await asyncio.sleep(0.5)
        
        # 填写CVV
        print("Step 7: Fill CVV...")
        try:
            locator = form_frame.locator('#i15')
            await locator.first.click()
            await locator.first.fill("")
            await locator.first.press_sequentially(CARD_INFO['cvv'], delay=100)
            value = await locator.first.input_value()
            print(f"  Filled: {value}")
        except Exception as e:
            print(f"  Error: {e}")
        
        await asyncio.sleep(2)
        
        # 查找 Save card 按钮
        print("Step 8: Looking for Save card button...")
        
        # 列出所有可能的按钮
        for frame in page.frames:
            if 'payments.google.com' in frame.url:
                try:
                    buttons = await frame.locator('button').all()
                    print(f"  Frame {frame.url[:50]} has {len(buttons)} buttons")
                    for i, btn in enumerate(buttons[:10]):
                        text = await btn.text_content()
                        classes = await btn.get_attribute('class') or ''
                        jsname = await btn.get_attribute('jsname') or ''
                        print(f"    [{i}] text='{text.strip()[:30] if text else ''}', jsname={jsname}, class={classes[:50]}")
                except:
                    pass
        
        # 尝试点击 Save card
        print("\nStep 9: Click Save card...")
        save_selectors = [
            'button:has-text("Save card")',
            'button[jsname="LgbsSe"]',
            'button.n157.LMdhbb',
        ]
        
        for frame in page.frames:
            if 'payments.google.com' in frame.url:
                for sel in save_selectors:
                    try:
                        locator = frame.locator(sel)
                        count = await locator.count()
                        if count > 0:
                            print(f"  Found {sel} in frame, clicking...")
                            await locator.first.click()
                            print(f"  Clicked!")
                            break
                    except Exception as e:
                        print(f"  Error with {sel}: {e}")
        
        # 等待结果
        print("\nStep 10: Wait 20s and check result...")
        await asyncio.sleep(20)
        
        # 检查页面变化
        for frame in page.frames:
            try:
                # 检查是否有错误信息
                error_texts = await frame.locator('text=/error|declined|failed|invalid/i').all()
                for err in error_texts[:3]:
                    text = await err.text_content()
                    if text and len(text.strip()) < 200:
                        print(f"  ERROR found: {text.strip()[:100]}")
            except:
                pass
        
        # 截图
        await page.screenshot(path="debug_save_result.png")
        print("\nScreenshot saved to debug_save_result.png")

asyncio.run(debug_full_flow())

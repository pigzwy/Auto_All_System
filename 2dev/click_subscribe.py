# -*- coding: utf-8 -*-
"""使用精确选择器点击Subscribe"""
import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from playwright.async_api import async_playwright
from bit_api import openBrowser
from create_window import get_browser_list

async def click_subscribe():
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
        
        # 导航到目标页面
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
        
        # 使用用户提供的精确选择器
        # <span jsname="V67aGc" class="UywwFc-vQzf8d">Subscribe</span>
        print("\nStep 2: Looking for Subscribe span...")
        
        subscribe_selectors = [
            'span[jsname="V67aGc"].UywwFc-vQzf8d:has-text("Subscribe")',
            'span.UywwFc-vQzf8d:has-text("Subscribe")',
            'span[jsname="V67aGc"]:has-text("Subscribe")',
        ]
        
        clicked = False
        for frame in page.frames:
            for sel in subscribe_selectors:
                try:
                    locator = frame.locator(sel)
                    count = await locator.count()
                    if count > 0:
                        print(f"  Found with '{sel}' in {frame.url[:40]}, count={count}")
                        
                        for i in range(count):
                            elem = locator.nth(i)
                            text = await elem.text_content()
                            visible = await elem.is_visible()
                            
                            if text and text.strip() == 'Subscribe' and visible:
                                print(f"    >>> Clicking element (text='{text.strip()}')...")
                                await elem.click(force=True)
                                clicked = True
                                print("    Clicked!")
                                break
                        if clicked:
                            break
                except Exception as e:
                    print(f"  Error with {sel}: {e}")
            if clicked:
                break
        
        if not clicked:
            # 尝试 JavaScript 点击
            print("\n  Trying JavaScript click...")
            for frame in page.frames:
                try:
                    result = await frame.evaluate("""
                        () => {
                            // 查找 span.UywwFc-vQzf8d 包含 Subscribe
                            const spans = document.querySelectorAll('span.UywwFc-vQzf8d');
                            for (const span of spans) {
                                if (span.textContent.trim() === 'Subscribe') {
                                    span.click();
                                    return 'clicked span';
                                }
                            }
                            // 查找 jsname="V67aGc"
                            const jsSpans = document.querySelectorAll('span[jsname="V67aGc"]');
                            for (const span of jsSpans) {
                                if (span.textContent.trim() === 'Subscribe') {
                                    span.click();
                                    return 'clicked jsname span';
                                }
                            }
                            return 'not found';
                        }
                    """)
                    print(f"  JS result in {frame.url[:30]}: {result}")
                    if 'clicked' in result:
                        clicked = True
                        break
                except:
                    pass
        
        print(f"\nWaiting 15s for result...")
        await asyncio.sleep(15)
        
        # 检查结果
        print("\n=== Checking result ===")
        subscribe_gone = True
        for frame in page.frames:
            try:
                count = await frame.locator('span.UywwFc-vQzf8d:has-text("Subscribe")').count()
                if count > 0:
                    visible = await frame.locator('span.UywwFc-vQzf8d:has-text("Subscribe")').first.is_visible()
                    if visible:
                        subscribe_gone = False
                        print(f"  Subscribe still visible in {frame.url[:40]}")
            except:
                pass
        
        if subscribe_gone:
            print("  SUCCESS! Subscribe is gone!")
        
        await page.screenshot(path="subscribe_final.png")
        print("\nScreenshot saved")

asyncio.run(click_subscribe())

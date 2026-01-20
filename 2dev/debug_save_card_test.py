# -*- coding: utf-8 -*-
"""调试 Save card 按钮问题 - 测试特定账号"""
import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from playwright.async_api import async_playwright
from bit_api import openBrowser
from create_window import get_browser_list

# 测试账号
TEST_EMAIL = "JennyBachir331@gmail.com"

async def debug_save_card():
    print(f"Looking for browser with email: {TEST_EMAIL}")
    
    browsers = get_browser_list(page=0, pageSize=100)
    browser_id = None
    for b in browsers:
        user_name = b.get('userName', '')
        remark = b.get('remark', '')
        if TEST_EMAIL.lower() in user_name.lower() or TEST_EMAIL.lower() in remark.lower():
            browser_id = b.get('id')
            print(f"Found browser: {browser_id} (userName: {user_name})")
            break
    
    if not browser_id:
        print("Browser not found! Available browsers:")
        for b in browsers[:10]:
            print(f"  - {b.get('userName', '')} | {b.get('remark', '')[:50]}")
        return
    
    result = openBrowser(browser_id)
    if result.get('success') == False:
        print(f"Failed to open browser: {result}")
        return
    
    ws_endpoint = result['data']['ws']
    print(f"Connected to browser: {ws_endpoint}")
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
        context = browser.contexts[0]
        page = context.pages[0]
        
        # 导航到学生优惠页面
        target_url = "https://one.google.com/ai-student?g1_landing_page=75&utm_source=antigravity&utm_campaign=argon_limit_reached"
        print(f"\nNavigating to: {target_url}")
        await page.goto(target_url, wait_until='domcontentloaded')
        await asyncio.sleep(5)
        
        # 点击 Get student offer
        print("\n=== Step 1: Click Get student offer ===")
        get_offer_clicked = False
        for sel in ['button[jsname="eWp5Fc"]', 'button:has-text("Get student offer")', 'text="Get student offer"']:
            try:
                locator = page.locator(sel)
                if await locator.count() > 0:
                    await locator.first.click(force=True)
                    print(f"  Clicked Get student offer with: {sel}")
                    get_offer_clicked = True
                    break
            except Exception as e:
                print(f"  Selector {sel} failed: {e}")
        
        if not get_offer_clicked:
            print("  Could not find Get student offer button, checking page state...")
        
        await asyncio.sleep(8)
        
        # 点击 Add card
        print("\n=== Step 2: Click Add card ===")
        add_card_clicked = False
        for frame in page.frames:
            try:
                locator = frame.get_by_text("Add card", exact=True)
                if await locator.count() > 0:
                    await locator.first.click()
                    print(f"  Clicked Add card in frame: {frame.url[:60]}")
                    add_card_clicked = True
                    break
            except:
                pass
        
        if not add_card_clicked:
            # 尝试其他选择器
            for frame in page.frames:
                try:
                    locator = frame.locator('span.PjwE0:has-text("Add card")')
                    if await locator.count() > 0:
                        await locator.first.click()
                        print(f"  Clicked Add card (span.PjwE0)")
                        add_card_clicked = True
                        break
                except:
                    pass
        
        if not add_card_clicked:
            print("  Could not find Add card button!")
            await page.screenshot(path="debug_no_add_card.png")
            return
        
        await asyncio.sleep(10)
        
        # 分析表单 frame 中的按钮
        print("\n=== Step 3: Analyzing buttons in payment frame ===")
        
        form_frame = None
        for frame in page.frames:
            if 'payments.google.com' in frame.url and 'instrumentmanager' in frame.url:
                form_frame = frame
                print(f"  Found payment form frame: {frame.url[:80]}")
                break
        
        if not form_frame:
            print("  Payment frame not found, checking all frames...")
            for i, frame in enumerate(page.frames):
                print(f"  Frame {i}: {frame.url[:80]}")
        
        # 列出所有按钮详情
        print("\n=== Step 4: Listing all buttons in payment frame ===")
        if form_frame:
            try:
                buttons = await form_frame.locator('button').all()
                print(f"  Found {len(buttons)} buttons:")
                for j, btn in enumerate(buttons):
                    try:
                        text = (await btn.text_content() or '').strip()
                        jsname = await btn.get_attribute('jsname') or ''
                        classes = await btn.get_attribute('class') or ''
                        visible = await btn.is_visible()
                        enabled = await btn.is_enabled()
                        box = await btn.bounding_box() if visible else None
                        
                        print(f"\n    Button [{j}]:")
                        print(f"      text: '{text[:50]}'")
                        print(f"      jsname: {jsname}")
                        print(f"      class: {classes[:80]}")
                        print(f"      visible: {visible}, enabled: {enabled}")
                        if box:
                            print(f"      position: ({box['x']:.0f}, {box['y']:.0f}), size: ({box['width']:.0f}x{box['height']:.0f})")
                    except Exception as e:
                        print(f"    Button [{j}]: Error - {e}")
            except Exception as e:
                print(f"  Error listing buttons: {e}")
        
        # 查找所有包含 'Save' 的按钮
        print("\n=== Step 5: Finding 'Save' buttons specifically ===")
        save_buttons = []
        for frame in page.frames:
            try:
                locator = frame.locator('button:has-text("Save")')
                count = await locator.count()
                if count > 0:
                    url_short = frame.url[:50] if frame.url else 'main'
                    print(f"\n  Frame: {url_short}")
                    for i in range(count):
                        btn = locator.nth(i)
                        text = (await btn.text_content() or '').strip()
                        visible = await btn.is_visible()
                        jsname = await btn.get_attribute('jsname') or ''
                        classes = await btn.get_attribute('class') or ''
                        print(f"    [{i}] text='{text}' visible={visible} jsname={jsname}")
                        print(f"        class: {classes[:80]}")
                        if 'Save card' in text and visible:
                            save_buttons.append((frame, btn, text))
            except Exception as e:
                pass
        
        # 检查是否有两个类似的按钮（可能会导致点错）
        print(f"\n=== Step 6: Potential Save card buttons found: {len(save_buttons)} ===")
        
        # 截图当前状态
        await page.screenshot(path="debug_save_card_state.png")
        print("\nScreenshot saved to debug_save_card_state.png")
        
        # 分析可能的问题
        print("\n=== Step 7: Analysis ===")
        if len(save_buttons) == 0:
            print("  No Save card button found! Form may not be fully loaded.")
        elif len(save_buttons) > 1:
            print("  Multiple Save card buttons found - this could cause clicking the wrong one!")
        else:
            print("  Single Save card button found - checking click behavior...")
            frame, btn, text = save_buttons[0]
            
            # 检查按钮的父元素和周围结构
            try:
                parent_html = await frame.locator('button:has-text("Save card")').first.evaluate('el => el.parentElement.outerHTML')
                print(f"\n  Parent element HTML:\n{parent_html[:500]}")
            except:
                pass
        
        print("\n\nPress Enter to close browser...")
        input()

if __name__ == "__main__":
    asyncio.run(debug_save_card())

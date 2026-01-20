# -*- coding: utf-8 -*-
"""检查是否需要额外的确认步骤"""
import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from playwright.async_api import async_playwright
from bit_api import openBrowser
from create_window import get_browser_list

async def check_confirmation():
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
        
        print("Current page:", page.url[:80])
        
        # 查找所有按钮
        print("\n=== Looking for all buttons on page ===")
        all_buttons = []
        for i, frame in enumerate(page.frames):
            try:
                buttons = await frame.locator('button').all()
                if buttons:
                    print(f"\nFrame {i} ({frame.url[:50]}):")
                    for j, btn in enumerate(buttons[:15]):
                        try:
                            text = await btn.text_content()
                            visible = await btn.is_visible()
                            enabled = await btn.is_enabled()
                            if text and text.strip():
                                text_clean = text.strip()[:50]
                                print(f"  [{j}] '{text_clean}' (visible={visible}, enabled={enabled})")
                                all_buttons.append((frame, btn, text_clean))
                        except:
                            pass
            except:
                pass
        
        # 查找可能的确认/继续按钮
        print("\n=== Looking for confirmation buttons ===")
        confirm_keywords = ['confirm', 'continue', 'start', 'subscribe', 'accept', 'agree', 'ok', 'done', 'next', 'free trial']
        for frame, btn, text in all_buttons:
            for kw in confirm_keywords:
                if kw.lower() in text.lower():
                    visible = await btn.is_visible()
                    enabled = await btn.is_enabled()
                    print(f"  FOUND: '{text}' (visible={visible}, enabled={enabled})")
        
        # 检查主要的对话框内容
        print("\n=== Dialog content ===")
        for frame in page.frames:
            if 'tokenized.play.google.com' in frame.url or 'google.com' in frame.url:
                try:
                    dialogs = await frame.locator('[role="dialog"]').all()
                    for d in dialogs:
                        text = await d.text_content()
                        if text:
                            print(f"\nDialog in {frame.url[:40]}:")
                            print(text[:800])
                except:
                    pass

asyncio.run(check_confirmation())

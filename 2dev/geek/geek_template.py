#!/usr/bin/env python3
"""
GeekezBrowser 自动化模板
========================

支持三种浏览器操作方式:
1. DrissionPage (默认) - 简单易用
2. Playwright - 功能强大,async
3. CDP 直连 - 最底层,灵活

流程: 启动应用 → 创建Profile → 启动浏览器 → 执行业务 → 关闭浏览器
"""

import json
import uuid
import time
import subprocess
import requests
import os
import asyncio
from pathlib import Path
from datetime import datetime

# ============================================================
# 配置 - 根据你的环境修改
# ============================================================

CONTROL_PORT = 19527
CONTROL_HOST = "127.0.0.1"

# Windows 路径
APPDATA = os.getenv("APPDATA", r"C:\Users\Public\AppData\Roaming")
DATA_PATH = Path(APPDATA) / "geekez-browser" / "BrowserProfiles"
PROFILES_FILE = DATA_PATH / "profiles.json"
SETTINGS_FILE = DATA_PATH / "settings.json"

# GeekezBrowser 源码路径
SOURCE_PATH = r"D:\java\github\GeekezBrowser"

# 默认代理
DEFAULT_PROXY = "socks5://127.0.0.1:7897"

# 浏览器操作方式: "drission" | "playwright" | "cdp"
BROWSER_MODE = "drission"


# ============================================================
# 日志
# ============================================================

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


# ============================================================
# GeekezBrowser 核心函数
# ============================================================

def is_app_running():
    """检查应用是否运行"""
    try:
        requests.get(f"http://{CONTROL_HOST}:{CONTROL_PORT}/health", timeout=2)
        return True
    except:
        return False


def start_app():
    """启动 GeekezBrowser"""
    if is_app_running():
        log("✓ 应用已在运行")
        return True

    # 启用远程调试
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    settings = {}
    if SETTINGS_FILE.exists():
        settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    settings["enableRemoteDebugging"] = True
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    log(f"启动应用: {SOURCE_PATH}")
    subprocess.Popen(
        ["npm", "start", "--", f"--control-port={CONTROL_PORT}"],
        cwd=SOURCE_PATH,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=True,
    )

    for i in range(30):
        if is_app_running():
            log(f"✓ 应用就绪 ({i+1}s)")
            return True
        time.sleep(1)

    log("✗ 启动超时")
    return False


def create_profile(name, proxy="", width=1280, height=800):
    """创建 Profile, 返回 profile_id"""
    profiles = []
    if PROFILES_FILE.exists():
        profiles = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))

    profile_id = str(uuid.uuid4())
    profiles.append({
        "id": profile_id,
        "name": name,
        "proxyStr": proxy,
        "tags": [],
        "fingerprint": {"window": {"width": width, "height": height}},
        "preProxyOverride": "default",
        "isSetup": False,
        "debugPort": 0,
        "createdAt": int(time.time() * 1000),
        "metadata": {},
    })

    DATA_PATH.mkdir(parents=True, exist_ok=True)
    PROFILES_FILE.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")
    
    log(f"✓ 创建 Profile: {name}")
    return profile_id


def launch_browser(profile_id):
    """启动浏览器, 返回 (debug_port, ws_endpoint)"""
    try:
        url = f"http://{CONTROL_HOST}:{CONTROL_PORT}/profiles/{profile_id}/launch"
        resp = requests.post(url, json={"debugPort": 0, "enableRemoteDebugging": True})
        result = resp.json()
        debug_port = result.get("debugPort")
        ws_endpoint = result.get("wsEndpoint", f"ws://127.0.0.1:{debug_port}")
        
        if debug_port:
            log(f"✓ 浏览器启动 (端口: {debug_port})")
            return debug_port, ws_endpoint
    except Exception as e:
        log(f"✗ 启动失败: {e}")
    return None, None


def close_browser(profile_id):
    """关闭浏览器"""
    try:
        url = f"http://{CONTROL_HOST}:{CONTROL_PORT}/profiles/{profile_id}/close"
        requests.post(url, timeout=5)
        log("✓ 浏览器已关闭")
    except:
        pass


def delete_profile(profile_id):
    """删除 Profile"""
    if not PROFILES_FILE.exists():
        return
    profiles = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    profiles = [p for p in profiles if p["id"] != profile_id]
    PROFILES_FILE.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")
    log("✓ Profile 已删除")


# ============================================================
# 方式1: DrissionPage 连接
# ============================================================

def connect_drission(debug_port):
    """使用 DrissionPage 连接浏览器"""
    from DrissionPage import Chromium
    browser = Chromium(f"127.0.0.1:{debug_port}")
    log("✓ DrissionPage 已连接")
    return browser, browser.latest_tab


def do_task_drission(tab):
    """
    DrissionPage 业务逻辑
    
    Args:
        tab: DrissionPage 的 Tab 对象
    """
    tab.get("https://www.google.com")
    time.sleep(3)
    log(f"页面标题: {tab.title}")
    log(f"当前URL: {tab.url}")
    
    # ===== 在这里添加你的业务代码 =====
    # tab.ele("#id").click()
    # tab.ele("@type=text").input("hello")
    
    return True


# ============================================================
# 方式2: Playwright 连接 (async)
# ============================================================

async def connect_playwright(ws_endpoint):
    """使用 Playwright 连接浏览器"""
    from playwright.async_api import async_playwright
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else await context.new_page()
    
    log("✓ Playwright 已连接")
    return playwright, browser, page


async def do_task_playwright(page):
    """
    Playwright 业务逻辑 (async)
    
    Args:
        page: Playwright 的 Page 对象
    """
    await page.goto("https://www.google.com")
    await page.wait_for_load_state("networkidle")
    
    title = await page.title()
    url = page.url
    log(f"页面标题: {title}")
    log(f"当前URL: {url}")
    
    # ===== 在这里添加你的业务代码 =====
    # await page.click("#id")
    # await page.fill("input[type=text]", "hello")
    # await page.wait_for_selector(".result")
    
    return True


# ============================================================
# 方式3: CDP 直连 (底层)
# ============================================================

def connect_cdp(debug_port):
    """直接使用 CDP 连接 (返回 websocket url)"""
    import websocket
    
    # 获取页面列表
    resp = requests.get(f"http://127.0.0.1:{debug_port}/json")
    pages = resp.json()
    
    if pages:
        ws_url = pages[0].get("webSocketDebuggerUrl")
        log(f"✓ CDP 已连接: {ws_url}")
        return ws_url
    return None


def do_task_cdp(ws_url):
    """
    CDP 直连业务逻辑
    
    Args:
        ws_url: WebSocket 调试 URL
    """
    import websocket
    
    ws = websocket.create_connection(ws_url)
    
    # 导航到 Google
    ws.send(json.dumps({
        "id": 1,
        "method": "Page.navigate",
        "params": {"url": "https://www.google.com"}
    }))
    result = json.loads(ws.recv())
    log(f"导航结果: {result}")
    
    time.sleep(3)
    
    # 获取页面标题
    ws.send(json.dumps({
        "id": 2,
        "method": "Runtime.evaluate",
        "params": {"expression": "document.title"}
    }))
    result = json.loads(ws.recv())
    title = result.get("result", {}).get("result", {}).get("value", "")
    log(f"页面标题: {title}")
    
    ws.close()
    
    # ===== 在这里添加你的 CDP 命令 =====
    
    return True


# ============================================================
# 主流程
# ============================================================

def run(name=None, proxy=DEFAULT_PROXY, mode=BROWSER_MODE, auto_close=True, auto_delete=False):
    """
    执行完整流程
    
    Args:
        name: Profile 名称 (默认使用当前时间)
        proxy: 代理地址
        mode: 浏览器操作方式 - "drission" | "playwright" | "cdp"
        auto_close: 是否自动关闭浏览器
        auto_delete: 是否自动删除 Profile (默认不删除)
    """
    if name is None:
        name = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    log(f"\n{'='*50}")
    log(f"任务开始: {name}")
    log(f"操作模式: {mode}")
    log(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log('='*50)

    profile_id = None
    success = False

    try:
        # 1. 启动应用
        if not start_app():
            return False

        # 2. 创建 Profile
        profile_id = create_profile(name, proxy)

        # 3. 启动浏览器
        debug_port, ws_endpoint = launch_browser(profile_id)
        if not debug_port:
            return False

        # 4. 根据模式执行业务
        if mode == "drission":
            browser, tab = connect_drission(debug_port)
            success = do_task_drission(tab)
            
        elif mode == "playwright":
            async def _run_playwright():
                playwright, browser, page = await connect_playwright(ws_endpoint)
                try:
                    return await do_task_playwright(page)
                finally:
                    await playwright.stop()
            success = asyncio.run(_run_playwright())
            
        elif mode == "cdp":
            ws_url = connect_cdp(debug_port)
            if ws_url:
                success = do_task_cdp(ws_url)
        
        log(f"{'✓' if success else '✗'} 任务{'成功' if success else '失败'}")

    except Exception as e:
        log(f"✗ 异常: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 5. 关闭浏览器
        if auto_close and profile_id:
            close_browser(profile_id)

        # 6. 删除 Profile (默认不删除)
        if auto_delete and profile_id:
            delete_profile(profile_id)
        
        log(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log('='*50)

    return success


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    run(
        name=None,                      # 自动用时间戳命名
        proxy="socks5://127.0.0.1:7897",
        mode="drission",                # "drission" | "playwright" | "cdp"
        auto_close=True,
        auto_delete=False,
    )

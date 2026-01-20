# 浏览器替换指南

本文档说明如何将项目从比特浏览器 (BitBrowser) 切换到其他浏览器方案。

---

## 目录

1. [当前架构分析](#当前架构分析)
2. [Google 接口与页面清单](#google-接口与页面清单)
3. [方案选择](#方案选择)
4. [修改清单](#修改清单)
5. [方案一：纯 Playwright（无痕模式）](#方案一纯-playwright无痕模式)
6. [方案二：其他指纹浏览器](#方案二其他指纹浏览器)
7. [任务 TODO 清单](#任务-todo-清单)

---

## 当前架构分析

```
┌─────────────────────┐     HTTP API        ┌─────────────────────┐
│   Python 应用       │   localhost:54345   │   比特浏览器         │
│                     │ ──────────────────► │   (BitBrowser)      │
│  - PyQt6 GUI        │                     │                     │
│  - Playwright       │ ◄────────────────── │  返回 WebSocket     │
│                     │   ws://xxx          │  调试地址            │
└─────────────────────┘                     └─────────────────────┘
         │
         │ connect_over_cdp(ws)
         ▼
┌─────────────────────┐
│   浏览器实例         │
│   (自动化操作)       │
└─────────────────────┘
```

### 核心耦合点

项目与比特浏览器的耦合**仅在 `bit_api.py`**，其他文件通过以下两个函数调用：

```python
from bit_api import openBrowser, closeBrowser

# 打开浏览器，获取 WebSocket 地址
res = openBrowser(browser_id)
ws = res['data']['ws']

# 关闭浏览器
closeBrowser(browser_id)
```

**Playwright 的页面操作逻辑是通用的**，不需要修改。

---

## Google 接口与页面清单

本项目自动化操作涉及以下 Google 服务和页面：

### 1. Google 账号登录

| 页面/接口 | URL | 用途 | 所在文件 |
|-----------|-----|------|----------|
| Google 账号登录页 | `https://accounts.google.com` | 用户登录入口 | `run_playwright_google.py` (Line 41) |

**页面元素操作：**
```python
# 邮箱输入框
input[type="email"]

# 下一步按钮
#identifierNext >> button

# 密码输入框
input[type="password"]

# 密码下一步按钮
#passwordNext >> button

# 2FA 验证码输入框
input[name="totpPin"], input[id="totpPin"], input[type="tel"]

# 2FA 下一步按钮
#totpNext >> button
```

### 2. Google One 学生优惠页面

| 页面/接口 | URL | 用途 | 所在文件 |
|-----------|-----|------|----------|
| Google One AI 学生优惠 | `https://one.google.com/ai-student?g1_landing_page=75&utm_source=antigravity&utm_campaign=argon_limit_reached` | 检测学生资格、提取验证链接 | `run_playwright_google.py` (Line 90)<br>`auto_bind_card.py` (Line 714)<br>`auto_all_in_one_gui.py` (Line 167) |

**状态检测关键词：**

| 状态 | 检测关键词（多语言） | 含义 |
|------|---------------------|------|
| 有资格待验证 | `sheerid.com` (链接) | 可提取 SheerID 验证链接 |
| 已验证未绑卡 | `Get student offer`, `获取学生优惠`, `Nhận ưu đãi dành cho sinh viên` 等 | 已通过验证，待绑卡 |
| 已订阅 | `You're already subscribed`, `已订阅`, `Bạn đã đăng ký` 等 | 已完成订阅 |
| 无资格 | `This offer is not available`, `此优惠目前不可用` 等 | 无学生资格 |

**页面元素操作：**
```python
# 验证资格链接
a[href*="sheerid.com"]

# 获取优惠按钮
button:has-text("Get student offer")
button:has-text("Get offer")

# 状态检测文本
text="Subscribed"
text="Get student offer"
text="This offer is not available"
```

### 3. Google Payments 支付页面（iframe）

| 页面/接口 | URL | 用途 | 所在文件 |
|-----------|-----|------|----------|
| Google Payments iframe | `tokenized.play.google.com` | 绑定信用卡、完成订阅 | `auto_bind_card.py` (多处) |

**iframe 结构（嵌套）：**
```
主页面
└── iframe[src*="tokenized.play.google.com"]  ← 第一层 iframe
    └── iframe[name="hnyNZeIframe"]           ← 第二层 iframe（卡片输入表单）
        └── instrumentmanager                  ← 实际的支付表单
```

**页面元素操作：**
```python
# 第一层 iframe
page.frame_locator('iframe[src*="tokenized.play.google.com"]')

# 第二层 iframe（卡片输入）
iframe[name="hnyNZeIframe"]
iframe[src*="instrumentmanager"]

# 添加卡片按钮
span.PjwEQ:has-text("Add card")
:text("Add card")

# 卡片输入框（按顺序）
input  # 第1个：卡号
input  # 第2个：MM/YY
input  # 第3个：CVV

# 保存卡片按钮
button:has-text("Save card")
button:has-text("保存")

# 订阅按钮
span.UywwFc-vQzf8d:has-text("Subscribe")
span[jsname="V67aGc"]
button:has-text("Subscribe")

# 订阅成功标识
:text("Subscribed")
```

### 4. SheerID 验证服务（第三方）

| 页面/接口 | URL | 用途 | 所在文件 |
|-----------|-----|------|----------|
| SheerID 验证链接 | `https://xxx.sheerid.com/...` | 学生身份验证 | 从 Google One 页面提取 |
| 1Key.me 批量验证 API | `https://batch.1key.me/api/batch` | 批量自动验证 SheerID | `sheerid_verifier.py` |

**SheerID 验证器 API：**
```python
# 批量验证接口
POST https://batch.1key.me/api/batch
{
    "verificationIds": ["id1", "id2", ...],
    "hCaptchaToken": "your_api_key",
    "useLucky": false,
    "programId": ""
}

# 状态轮询接口
POST https://batch.1key.me/api/check-status
{
    "checkToken": "token_from_batch_response"
}

# 取消验证接口
POST https://batch.1key.me/api/cancel
{
    "verificationId": "id"
}
```

### 5. 完整业务流程图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         自动化业务流程                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. 登录阶段                                                        │
│  ┌─────────────────┐                                                │
│  │ accounts.google │ → 输入邮箱 → 输入密码 → 输入2FA → 登录成功     │
│  │      .com       │                                                │
│  └─────────────────┘                                                │
│           │                                                         │
│           ▼                                                         │
│  2. 资格检测阶段                                                     │
│  ┌─────────────────┐                                                │
│  │  one.google.com │ → 检测状态 → 提取 sheerid.com 链接             │
│  │   /ai-student   │                                                │
│  └─────────────────┘                                                │
│           │                                                         │
│           ▼                                                         │
│  3. SheerID 验证阶段                                                 │
│  ┌─────────────────┐                                                │
│  │  batch.1key.me  │ → 提交验证 → 轮询状态 → 验证成功               │
│  │   /api/batch    │                                                │
│  └─────────────────┘                                                │
│           │                                                         │
│           ▼                                                         │
│  4. 绑卡订阅阶段                                                     │
│  ┌─────────────────┐                                                │
│  │tokenized.play   │ → 点击Get Offer → Add Card → 填写卡信息        │
│  │ .google.com     │ → Save Card → Subscribe → 完成订阅             │
│  │   (iframe)      │                                                │
│  └─────────────────┘                                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 6. 各文件 Google 接口使用汇总

| 文件 | 使用的 Google 接口 | 功能 |
|------|-------------------|------|
| `run_playwright_google.py` | accounts.google.com<br>one.google.com/ai-student | 登录 + 资格检测 + 链接提取 |
| `auto_bind_card.py` | one.google.com/ai-student<br>tokenized.play.google.com | 登录检测 + 绑卡订阅 |
| `auto_all_in_one_gui.py` | one.google.com/ai-student | 全流程自动化 |
| `sheerid_verifier.py` | batch.1key.me（非 Google） | SheerID 批量验证 |

---

## 方案选择

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **纯 Playwright** | 无需额外软件、免费 | 无指纹伪装、易被检测 | 测试、个人使用 |
| **AdsPower** | 国内常用、API 类似 | 付费 | 跨境电商 |
| **VMLogin** | 功能强大 | 付费较贵 | 专业团队 |
| **Multilogin** | 业界标杆 | 最贵 | 企业级 |

---

## 修改清单

### 需要修改的文件

| 文件 | 修改内容 | 优先级 |
|------|----------|--------|
| `bit_api.py` | **核心文件**：替换为新浏览器 API 或纯 Playwright | 🔴 高 |
| `run_playwright_google.py` | 修改 `openBrowser`/`closeBrowser` 调用 | 🔴 高 |
| `auto_bind_card.py` | 修改 `openBrowser`/`closeBrowser` 调用 | 🔴 高 |
| `auto_all_in_one_gui.py` | 修改 `openBrowser`/`closeBrowser` 调用 | 🔴 高 |
| `bit_playwright.py` | 修改连接示例（可删除或保留参考） | 🟡 中 |
| `create_window.py` | 如需窗口管理功能，需重写 | 🟡 中 |
| `create_window_gui.py` | GUI 中的窗口管理逻辑 | 🟡 中 |

### 各文件调用位置

```
bit_api.py
├── openBrowser()     ← 核心：打开浏览器，返回 WebSocket
├── closeBrowser()    ← 核心：关闭浏览器
├── createBrowser()   ← 创建新窗口
├── updateBrowser()   ← 更新窗口配置
└── deleteBrowser()   ← 删除窗口

run_playwright_google.py
├── Line 9:   from bit_api import openBrowser, closeBrowser
├── Line 419: res = openBrowser(browser_id)
├── Line 425: closeBrowser(browser_id)
└── Line 443: closeBrowser(browser_id)

auto_bind_card.py
├── Line 7:   from bit_api import openBrowser, closeBrowser
├── Line 698: result = openBrowser(browser_id)
└── Line 741: # closeBrowser(browser_id)  [已注释]

auto_all_in_one_gui.py
├── Line 15:  from bit_api import openBrowser, closeBrowser
└── Line 149: result = openBrowser(browser_id)

bit_playwright.py
├── Line 1:   from bit_api import *
├── Line 12:  res = openBrowser(browser_id)
└── Line 31:  closeBrowser(browser_id)
```

---

## 方案一：纯 Playwright（无痕模式）

### 步骤 1：创建新的浏览器适配器

创建 `browser_adapter.py` 替代 `bit_api.py`：

```python
"""
browser_adapter.py - 纯 Playwright 浏览器适配器
替代 bit_api.py，无需依赖任何指纹浏览器
"""

from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
import asyncio

# 全局浏览器实例管理
_browsers = {}
_playwright_instance = None


class BrowserManager:
    """浏览器管理器 - 替代比特浏览器 API"""
    
    def __init__(self):
        self.browsers = {}
        self.playwright = None
    
    async def init(self):
        """初始化 Playwright"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
    
    async def create_browser(self, browser_id: str, proxy: dict = None, headless: bool = False):
        """
        创建浏览器实例
        
        Args:
            browser_id: 浏览器唯一标识
            proxy: 代理配置 {"server": "http://host:port", "username": "user", "password": "pass"}
            headless: 是否无头模式
        
        Returns:
            {"success": True, "data": {"ws": browser_id}}
        """
        await self.init()
        
        launch_options = {
            "headless": headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
        }
        
        if proxy:
            launch_options["proxy"] = proxy
        
        browser = await self.playwright.chromium.launch(**launch_options)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # 添加反检测脚本
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
        
        page = await context.new_page()
        
        self.browsers[browser_id] = {
            "browser": browser,
            "context": context,
            "page": page
        }
        
        return {"success": True, "data": {"ws": browser_id}}
    
    async def open_browser(self, browser_id: str):
        """
        打开浏览器（兼容旧 API）
        如果浏览器不存在，自动创建
        
        Returns:
            {"success": True, "data": {"ws": browser_id, "context": context, "page": page}}
        """
        if browser_id not in self.browsers:
            await self.create_browser(browser_id)
        
        browser_data = self.browsers[browser_id]
        return {
            "success": True, 
            "data": {
                "ws": browser_id,
                "context": browser_data["context"],
                "page": browser_data["page"]
            }
        }
    
    async def close_browser(self, browser_id: str):
        """关闭浏览器"""
        if browser_id in self.browsers:
            browser_data = self.browsers.pop(browser_id)
            await browser_data["browser"].close()
            print(f"浏览器 {browser_id} 已关闭")
    
    async def cleanup(self):
        """清理所有资源"""
        for browser_id in list(self.browsers.keys()):
            await self.close_browser(browser_id)
        if self.playwright:
            await self.playwright.stop()


# 全局实例
_manager = BrowserManager()


# 兼容旧 API 的同步包装函数
def openBrowser(browser_id: str, proxy: dict = None):
    """
    兼容旧 API：打开浏览器
    
    注意：这个函数返回的结构与比特浏览器不同！
    比特浏览器返回 WebSocket 地址，这里直接返回 context
    
    调用方需要修改连接方式：
    - 旧：browser = await chromium.connect_over_cdp(ws)
    - 新：直接使用返回的 context
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # 先创建浏览器
        loop.run_until_complete(_manager.create_browser(browser_id, proxy))
        # 再打开
        result = loop.run_until_complete(_manager.open_browser(browser_id))
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def closeBrowser(browser_id: str):
    """兼容旧 API：关闭浏览器"""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(_manager.close_browser(browser_id))
    else:
        loop.run_until_complete(_manager.close_browser(browser_id))


def createBrowser(name: str = "default", proxy: dict = None):
    """兼容旧 API：创建浏览器"""
    import uuid
    browser_id = uuid.uuid4().hex
    openBrowser(browser_id, proxy)
    return browser_id


def deleteBrowser(browser_id: str):
    """兼容旧 API：删除浏览器"""
    closeBrowser(browser_id)
```

### 步骤 2：修改调用文件

由于纯 Playwright 不返回 WebSocket 地址，需要修改连接方式：

**修改前（比特浏览器）：**
```python
from bit_api import openBrowser, closeBrowser

res = openBrowser(browser_id)
ws = res['data']['ws']

async with async_playwright() as playwright:
    browser = await playwright.chromium.connect_over_cdp(ws)
    context = browser.contexts[0]
    page = context.pages[0]
```

**修改后（纯 Playwright）：**
```python
from browser_adapter import openBrowser, closeBrowser

res = openBrowser(browser_id)
if res['success']:
    context = res['data']['context']
    page = res['data']['page']
    # 直接使用 page 进行操作
```

### 步骤 3：修改各文件的具体改动

#### `run_playwright_google.py` 修改

```python
# Line 9: 修改 import
# 旧：from bit_api import openBrowser, closeBrowser
# 新：
from browser_adapter import openBrowser, closeBrowser

# Line 418-427: 修改连接逻辑
# 旧：
#     res = openBrowser(browser_id)
#     ws_endpoint = res.get('data', {}).get('ws')
#     ...
#     browser = await chromium.connect_over_cdp(ws_endpoint)

# 新：
def process_browser(browser_id, log_callback=None):
    res = openBrowser(browser_id)
    if not res.get('success'):
        return False, f"Failed to open browser: {res}"
    
    context = res['data']['context']
    page = res['data']['page']
    
    # 直接使用 page，不再需要 async_playwright
    # ... 后续逻辑保持不变
```

#### `auto_bind_card.py` 修改

```python
# Line 7: 修改 import
from browser_adapter import openBrowser, closeBrowser

# Line 698-711: 修改连接逻辑
async def test_bind_card_with_browser(browser_id: str, account_info: dict = None):
    result = openBrowser(browser_id)
    
    if not result.get('success'):
        return False, f"打开浏览器失败: {result}"
    
    # 直接使用返回的 page
    page = result['data']['page']
    
    # 后续逻辑保持不变...
```

---

## 方案二：其他指纹浏览器

### AdsPower 示例

```python
"""
adspower_api.py - AdsPower 浏览器适配器
"""
import requests

URL = "http://local.adspower.net:50325"


def openBrowser(browser_id: str):
    """打开 AdsPower 浏览器"""
    res = requests.get(
        f"{URL}/api/v1/browser/start",
        params={"user_id": browser_id}
    ).json()
    
    if res.get("code") == 0:
        return {
            "success": True,
            "data": {
                "ws": res["data"]["ws"]["puppeteer"]  # 或 selenium
            }
        }
    return {"success": False, "error": res.get("msg")}


def closeBrowser(browser_id: str):
    """关闭 AdsPower 浏览器"""
    res = requests.get(
        f"{URL}/api/v1/browser/stop",
        params={"user_id": browser_id}
    ).json()
    print(f"关闭浏览器响应: {res}")


def createBrowser(name: str = "default", proxy: dict = None):
    """创建新浏览器配置"""
    data = {
        "name": name,
        "group_id": "0",
        # ... 其他配置
    }
    if proxy:
        data["user_proxy_config"] = {
            "proxy_type": proxy.get("type", "http"),
            "proxy_host": proxy.get("host"),
            "proxy_port": proxy.get("port"),
            "proxy_user": proxy.get("username"),
            "proxy_password": proxy.get("password")
        }
    
    res = requests.post(f"{URL}/api/v1/user/create", json=data).json()
    if res.get("code") == 0:
        return res["data"]["id"]
    raise Exception(f"创建失败: {res}")


def deleteBrowser(browser_id: str):
    """删除浏览器配置"""
    res = requests.post(
        f"{URL}/api/v1/user/delete",
        json={"user_ids": [browser_id]}
    ).json()
    print(f"删除浏览器响应: {res}")
```

### VMLogin 示例

```python
"""
vmlogin_api.py - VMLogin 浏览器适配器
"""
import requests

URL = "http://127.0.0.1:35000"


def openBrowser(browser_id: str):
    """打开 VMLogin 浏览器"""
    res = requests.get(
        f"{URL}/api/v1/profile/start",
        params={"profileId": browser_id}
    ).json()
    
    if res.get("status") == "OK":
        return {
            "success": True,
            "data": {
                "ws": res["value"]  # WebSocket 地址
            }
        }
    return {"success": False, "error": res.get("value")}


def closeBrowser(browser_id: str):
    """关闭 VMLogin 浏览器"""
    res = requests.get(
        f"{URL}/api/v1/profile/stop",
        params={"profileId": browser_id}
    ).json()
    print(f"关闭浏览器响应: {res}")
```

---

## 任务 TODO 清单

### 阶段一：准备工作 ✅

- [ ] 确定目标方案（纯 Playwright / AdsPower / VMLogin / 其他）
- [ ] 阅读目标浏览器的 API 文档
- [ ] 备份当前代码

### 阶段二：核心适配 🔴

- [ ] **创建 `browser_adapter.py`**
  - [ ] 实现 `openBrowser()` 函数
  - [ ] 实现 `closeBrowser()` 函数
  - [ ] 实现 `createBrowser()` 函数（如需要）
  - [ ] 实现 `deleteBrowser()` 函数（如需要）
  - [ ] 处理代理配置
  - [ ] **添加无头模式支持**（见下方说明）

- [ ] **修改 `run_playwright_google.py`**
  - [ ] 修改 import 语句（Line 9）
  - [ ] 修改 `process_browser()` 函数中的连接逻辑（Line 418-430）
  - [ ] 测试 SheerID 链接提取功能

- [ ] **修改 `auto_bind_card.py`**
  - [ ] 修改 import 语句（Line 7）
  - [ ] 修改 `test_bind_card_with_browser()` 中的连接逻辑（Line 698-711）
  - [ ] 测试自动绑卡功能

- [ ] **修改 `auto_all_in_one_gui.py`**
  - [ ] 修改 import 语句（Line 15）
  - [ ] 修改 `_process_single_account()` 中的连接逻辑（Line 149-160）
  - [ ] 测试一键全自动功能

### 阶段三：窗口管理（可选）🟡

- [ ] **修改 `create_window.py`**
  - [ ] 实现新的窗口列表获取
  - [ ] 实现新的窗口信息获取
  - [ ] 实现批量创建逻辑

- [ ] **修改 `create_window_gui.py`**
  - [ ] 适配新的窗口管理 API
  - [ ] 更新 GUI 显示

### 阶段四：测试验证 🟢

- [ ] 单个账号测试
  - [ ] 登录功能
  - [ ] 状态检测
  - [ ] SheerID 链接提取
  - [ ] 自动绑卡
  
- [ ] 批量测试
  - [ ] 多账号并发
  - [ ] 代理切换
  - [ ] 错误恢复

- [ ] 清理工作
  - [ ] 删除或注释旧的 `bit_api.py`
  - [ ] 更新 README.md
  - [ ] 更新 requirements.txt（如有新依赖）

### 阶段五：新功能开发（待实现）🟣

- [ ] **无头浏览器模式支持**
  - [ ] 在 `browser_adapter.py` 中添加 `headless` 参数
  - [ ] GUI 中添加"无头模式"开关选项
  - [ ] 测试无头模式下的登录、绑卡流程
  - [ ] 注意：无头模式可能被 Google 检测，需要额外反检测措施

- [ ] **修改密码功能**
  - [ ] 自动化页面：`https://myaccount.google.com/signinoptions/password`
  - [ ] 实现流程：输入当前密码 → 输入新密码 → 确认新密码 → 提交
  - [ ] 处理安全验证（可能需要手机/邮箱验证码）
  - [ ] 更新本地数据库中的密码记录

- [ ] **修改/重置 2FA 功能**
  - [ ] 自动化页面：`https://myaccount.google.com/signinoptions/two-step-verification`
  - [ ] 实现流程：验证身份 → 添加/更换验证器 → 扫描二维码或获取密钥 → 保存新密钥
  - [ ] 更新本地数据库中的 2FA 密钥
  - [ ] 注意：此操作风险较高，需要谨慎处理

- [ ] **添加/修改辅助邮箱**
  - [ ] 自动化页面：`https://myaccount.google.com/recovery/email`
  - [ ] 实现流程：输入辅助邮箱 → 验证辅助邮箱 → 完成绑定

---

## 无头浏览器模式说明

### 当前状态

**❌ 当前项目不支持无头浏览器模式**

原因：项目依赖比特浏览器 (BitBrowser)，这是一个有界面的指纹浏览器，不支持无头模式。

### 如何添加无头模式支持

切换到纯 Playwright 后，可以轻松支持无头模式：

```python
# browser_adapter.py 中添加 headless 参数

async def create_browser(self, browser_id: str, proxy: dict = None, headless: bool = False):
    """
    创建浏览器实例
    
    Args:
        browser_id: 浏览器唯一标识
        proxy: 代理配置
        headless: 是否无头模式（默认 False）
    """
    browser = await self.playwright.chromium.launch(
        headless=headless,  # 关键参数
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ]
    )
    # ...
```

### 无头模式注意事项

| 问题 | 说明 | 解决方案 |
|------|------|----------|
| **Google 检测** | 无头模式更容易被识别为机器人 | 添加反检测脚本、使用 stealth 插件 |
| **验证码** | 可能更频繁触发验证码 | 需要接入验证码识别服务 |
| **调试困难** | 看不到页面，难以排查问题 | 开发时使用有头模式，生产时切换无头 |
| **截图保存** | 无头模式下截图用于调试 | 已有 `page.screenshot()` 支持 |

### 推荐配置

```python
# 开发环境
headless = False  # 方便调试

# 生产环境（服务器）
headless = True   # 节省资源

# 反检测增强
await context.add_init_script("""
    // 隐藏 webdriver 标识
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    
    // 隐藏无头模式特征
    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
    
    // 模拟真实浏览器语言
    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
""")
```

---

## Google 安全设置页面（待开发功能）

以下是修改密码、2FA 等功能需要自动化的 Google 页面：

### 1. 修改密码

| 项目 | 内容 |
|------|------|
| **URL** | `https://myaccount.google.com/signinoptions/password` |
| **前置条件** | 需要已登录状态 |
| **页面元素** | 当前密码输入框、新密码输入框、确认密码输入框 |
| **难度** | 🔴 高（可能触发安全验证） |

**预期流程：**
```
1. 导航到密码修改页面
2. 可能需要重新验证身份（输入当前密码或 2FA）
3. 输入新密码
4. 确认新密码
5. 点击"更改密码"按钮
6. 处理可能的安全警告
7. 更新本地数据库
```

### 2. 修改 2FA（两步验证）

| 项目 | 内容 |
|------|------|
| **URL** | `https://myaccount.google.com/signinoptions/two-step-verification` |
| **前置条件** | 需要已登录状态 + 当前 2FA 验证 |
| **页面元素** | 验证器应用设置、备用码、安全密钥等 |
| **难度** | 🔴 高（多步骤、需要扫码或提取密钥） |

**预期流程：**
```
1. 导航到两步验证页面
2. 验证当前身份（可能需要当前 2FA 码）
3. 选择"验证器应用" → "更换手机"或"设置"
4. 获取新的 TOTP 密钥（从二维码或"无法扫描"选项）
5. 使用新密钥生成验证码并确认
6. 保存新密钥到本地数据库
```

### 3. 添加/修改辅助邮箱

| 项目 | 内容 |
|------|------|
| **URL** | `https://myaccount.google.com/recovery/email` |
| **前置条件** | 需要已登录状态 |
| **页面元素** | 辅助邮箱输入框、验证码输入框 |
| **难度** | 🟡 中（需要验证辅助邮箱） |

**预期流程：**
```
1. 导航到辅助邮箱页面
2. 输入新的辅助邮箱地址
3. Google 发送验证码到辅助邮箱
4. 获取验证码（需要访问辅助邮箱）
5. 输入验证码完成绑定
```

### 4. 其他安全设置页面

| 功能 | URL | 难度 |
|------|-----|------|
| 安全检查 | `https://myaccount.google.com/security-checkup` | 🟡 中 |
| 登录设备管理 | `https://myaccount.google.com/device-activity` | 🟢 低 |
| 应用密码 | `https://myaccount.google.com/apppasswords` | 🟡 中 |
| 账号恢复选项 | `https://myaccount.google.com/recovery` | 🟡 中 |

---

## 快速参考

### 核心修改（3 个文件 + 1 个新文件）

```bash
# 1. 创建新适配器
新建 browser_adapter.py

# 2. 修改这 3 个文件的 import
run_playwright_google.py  (Line 9)
auto_bind_card.py         (Line 7)
auto_all_in_one_gui.py    (Line 15)

# 将
from bit_api import openBrowser, closeBrowser
# 改为
from browser_adapter import openBrowser, closeBrowser
```

### 连接方式变化

| 浏览器类型 | 连接方式 |
|-----------|----------|
| 比特浏览器 | `chromium.connect_over_cdp(ws)` |
| AdsPower | `chromium.connect_over_cdp(ws)` |
| VMLogin | `chromium.connect_over_cdp(ws)` |
| 纯 Playwright | 直接使用返回的 `context` 和 `page` |

---

## 注意事项

1. **指纹浏览器** 返回的是 WebSocket 地址，连接方式与现有代码兼容
2. **纯 Playwright** 需要修改连接逻辑，因为没有 WebSocket
3. 所有 Playwright 页面操作代码（点击、填写、等待等）**无需修改**
4. 建议先在测试环境验证，再部署到生产环境

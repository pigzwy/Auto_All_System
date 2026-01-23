# 开发笔记 & 规划

> 合并自: AUTOMATION_TOOL_COMPARISON.md, BROWSER_MIGRATION_GUIDE.md, P工具箱_拆分规划.md, geek_task_progress.md, to do.md, 2dev/docs/Web版架构设计.md

---

## 1. 技术选型总结

### 自动化工具对比

| 工具 | 优势 | 劣势 | 适用场景 |
|------|------|------|----------|
| **Playwright** | 工程化、并发稳定、CDP支持 | 学习曲线 | ✅ 当前方案 |
| **DrissionPage** | Python友好、轻量 | 并发弱 | 简单场景 |
| **agent-browser** | 交互式调试 | 不适合批量 | 调试用 |

**当前方案**: Playwright + GeekezBrowser (CDP连接)

### 浏览器选择

| 浏览器 | 状态 |
|--------|------|
| BitBrowser | ❌ 已弃用（原方案） |
| GeekezBrowser | ✅ 当前使用 |
| AdsPower/VMLogin | 备选方案 |

---

## 2. 架构概览

```
geek_main_gui.py          # P工具箱主界面
    └─ GeekWorkerThread   # 后台线程
        └─ GeekProcess    # 流程编排 (geek_process.py)
            ├─ GeekezBrowserAPI  # 控制端口 (geek_browser_api.py)
            └─ 业务模块 (auto_bind_card, account_manager, database...)
```

### 核心文件

| 文件 | 职责 |
|------|------|
| `geek_main_gui.py` | GUI入口、任务分发 |
| `geek_process.py` | 流程编排、浏览器操作 |
| `geek_browser_api.py` | HTTP控制端口封装 |
| `geek_security.py` | 安全设置自动化 |
| `geek_security_gui.py` | 安全设置GUI |

### 控制端口 (默认 19527)

```
GET  /health              # 健康检查
POST /profiles/{id}/launch # 启动浏览器
POST /profiles/{id}/close  # 关闭浏览器
POST /shutdown            # 优雅退出
```

---

## 3. 涉及的 Google 页面

| 页面 | URL | 用途 |
|------|-----|------|
| 登录 | accounts.google.com | 账号登录/2FA |
| 学生资格 | one.google.com/ai-student | 资格检测/订阅 |
| 支付 | tokenized.play.google.com | 绑卡 (iframe) |
| 安全设置 | myaccount.google.com | 2FA/辅助邮箱 |

---

## 4. 换电脑恢复步骤

```bash
# 1. 拉代码
git clone <repo>
cd Auto_All_System

# 2. Python依赖
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. Playwright
python -m playwright install

# 4. 配置 GeekezBrowser 路径
# 修改 geek_main_gui.py 中的 GEEK_SOURCE_PATH

# 5. 数据文件
# 确保 accounts.txt / proxies.txt / cards.txt 存在
```

---

## 5. 待办事项

### P0 - 稳定性
- [ ] 验证控制端口兼容性 (`GET /health` → 200)
- [ ] 确认 `/profiles/{id}/launch` 返回正确的 debugPort

### P1 - 功能扩展
- [ ] 新增专区 (GB/GPT) 按开发者指南模板
- [ ] 运行状态展示增强

### P2 - 工程化
- [ ] 考虑迁移到上游新架构 (Web版)
- [ ] 拆分 GUI 层 (UI/Workers/Launcher)

---

## 6. 未来规划：迁移到 Web 架构（多浏览器抽象）

目标：从“单独 GUI + 直接绑 BitBrowser/GeekezBrowser”升级为“Web 端 + 业务插件 + 多浏览器可切换”的体系。

### 6.1 核心原则

- 业务逻辑与浏览器解耦：登录/绑卡/订阅/安全设置是业务代码，不应写死 BitBrowser 或 GeekezBrowser。
- 浏览器只是执行容器：通过统一接口选择执行载体（BitBrowser / GeekezBrowser / 未来 AdsPower 等）。
- P工具箱能力应回归业务插件：例如 Google 相关功能归到 `google_business` 插件，而不是“Geek 插件”。

概念分层：

```
业务层(专区/插件): Google Business / GPT / GB / ...
        ↓
通用执行层: AccountMgr / DBManager / Playwright Utils / DataLoader
        ↓
载体层(可切换): BitBrowserAdapter / GeekezBrowserAdapter / ...
```

### 6.2 推荐目录结构（Web 后端）

```
Auto_All_System_Web/backend/
  apps/
    integrations/              # 载体层：浏览器集成
      browser_base.py          # BrowserType + BaseBrowserAPI + BrowserManager
      bitbrowser/adapter.py
      geekez/adapter.py
    core/                      # 通用执行层：复用能力
      data_loader.py           # accounts/proxies/cards
      playwright_utils.py      # CDP连接、通用等待/重试
      google_login.py          # 登录/2FA通用逻辑
  plugins/
    google_business/           # 业务层：Google专区
      services/
        sheerlink.py
        bind_card.py
        subscription.py
        security.py
```

### 6.3 迁移映射（从 2dev/geek 到 Web 插件）

| 当前文件/能力 | 迁移目标 | 说明 |
|-------------|----------|------|
| `2dev/geek/geek_browser_api.py` | `apps/integrations/geekez/api.py` | GeekezBrowser 的控制端口封装，属于载体层 |
| `2dev/geek/geek_process.py` 的数据加载 | `apps/core/data_loader.py` | 通用能力（与业务无关） |
| `2dev/geek/geek_process.py` 的 Google 业务逻辑 | `plugins/google_business/services/*` | 业务归位 |
| `2dev/geek/geek_security.py` | `plugins/google_business/services/security.py` | Google 业务功能 |
| `2dev/geek/geek_main_gui.py` | Web 前端页面/组件 | 入口 UI 改为 Web |

### 6.4 BrowserManager 关键接口

统一入口让业务代码不再关心 BitBrowser/GeekezBrowser：

```python
manager = get_browser_manager()

# 指定浏览器类型启动
launch = manager.launch_profile(profile_id, browser_type=BrowserType.GEEKEZ)

# 业务层拿到 cdp_endpoint 后走 Playwright
page = connect_over_cdp(launch.cdp_endpoint)
```

### 6.5 当前建议

- 先保持 `2dev/geek/` 可用（生产力优先）。
- Web 化迁移按“先抽象 BrowserManager，再迁移 Google 插件服务层”的顺序做，避免一口吃成胖子。

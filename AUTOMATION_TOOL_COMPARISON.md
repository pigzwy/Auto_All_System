# 自动化方案对比：agent-browser vs Playwright vs DrissionPage

本文档把 `agent-browser`、Playwright、DrissionPage 三种方案的定位、差异、功能边界，以及在“登录网页端 → 输入账号密码/2FA → 查询数据 →（可选）支付/iframe 绑卡”这类场景中的适用性，整理成可落地的对比。

适用读者：已经有现成 Playwright 脚本/项目，想评估是否迁移到 `agent-browser` 或 DrissionPage。

---

## 1. 一句话结论

- `agent-browser`：Playwright 的“AI-first CLI 形态”。优势在交互式调试、低上下文、少样板代码；复杂业务仍需要外部编排层。
- Playwright：通用、成熟、生态强的浏览器自动化引擎。优势在工程化、可维护性、可测试性；缺点是样板代码多、调试迭代成本高。
- DrissionPage：偏“Python + CDP”的工程化库，并且把“浏览器控制 + requests/抓包”融合在一个工具里。优势是 Python 工程集成、抓包/请求联动、语法更省；缺点是 AI-first 的 ref/snapshot 工作流不如 agent-browser，跨语言集成不如 CLI。

---

## 2. 它们到底是什么（定位与形态）

### 2.1 agent-browser（vercel-labs/agent-browser）

- 形态：命令行工具（CLI）。
- 架构：Rust CLI + Node.js daemon + Playwright 浏览器实例（daemon 常驻提升连续命令速度）。
- 核心设计：`snapshot` 输出可访问性树（accessibility tree），并给每个元素生成 `ref`（例如 `@e1/@e2`），后续通过 ref 点击/填写。
- 关键词：`snapshot` / `@ref` / session / state save/load / trace / headed。

### 2.2 Playwright

- 形态：编程库（Node/Python/Java/.NET）。
- 引擎能力：Chromium / Firefox / WebKit；支持无头、trace、录制、网络拦截等。
- 典型使用：写脚本（同步或异步），通过 selector/locator 操作元素。
- 关键词：`locator` / `wait_for_*` / `connect_over_cdp` / `storage_state` / trace。

### 2.3 DrissionPage

- 形态：Python 库。
- 底层：围绕 Chromium 协议（CDP）实现浏览器控制；并提供 requests/收发包能力与浏览器联动（常见认知：既能“点页面”，也能“直接发包/抓包”）。
- 典型使用：写 Python 脚本，通过更“短”的定位语法和内置等待机制完成自动化；需要时切到“发包模式”获取数据。
- 关键词：CDP / 浏览器控制 + 发包 / Mix(Web)Page / 内置等待。

---

## 3. 能力对比总表（高频决策维度）

> 下面的“✅/⚠️/❌”是针对“开箱即用的体验”；不代表完全不能做，而是代表成本高/需要额外工程。

| 维度 | agent-browser | Playwright（现有脚本形态） | DrissionPage |
|---|---|---|---|
| 形态 | CLI 命令流 | 编程库（脚本/项目） | Python 编程库 |
| 代码量（单次任务） | ✅ 6~15 条命令可跑通 | ⚠️ 需要脚本，通常几十~几百行 | ⚠️ 需要脚本，通常比 Playwright 少 |
| “省上下文”能力（给 LLM/agent） | ✅ 强：snapshot + refs | ⚠️ 需要把 DOM/选择器信息喂给模型 | ⚠️ 仍以定位语法为主 |
| 调试方式 | ✅ 交互式逐步执行；`--headed` | ⚠️ 通常改代码重跑；也可截图/trace | ⚠️ 主要靠日志/截图/断点 |
| Headless 支持 | ✅ 默认 headless；可 `--headed` | ✅ 支持 `headless` | ✅ 通常支持（依赖 Chromium 配置） |
| 会话隔离/多账号 | ✅ `--session` 原生支持 | ✅ 多 context / storageState | ✅ 可多实例/多配置（方式不同） |
| 登录态复用 | ✅ `state save/load` | ✅ `storage_state` | ✅ 可通过 cookie/storage/配置复用 |
| 网络拦截/抓包 | ✅ 有 network 相关命令（能力取决于实现） | ✅ 很强（route/har/trace） | ✅ 强项之一（浏览器+发包联动） |
| 工程化/批量并发 | ⚠️ 需要外部编排（bash/python） | ✅ 最适合工程化 | ✅ 适合 Python 工程化 |
| 生态与跨语言 | ✅ CLI：任何语言可调用 | ✅ 多语言 SDK | ❌ 主要 Python |
| 典型风险 | refs 在复杂 iframe 上是否稳定需验证 | 选择器脆；脚本维护成本高 | 生态/团队熟悉度；复杂页面兼容性依赖版本 |

---

## 4. “你现在的项目”映射（从现状看它们分别能替代哪里）

以当前仓库的自动化链路为例：

- 登录入口：`https://accounts.google.com`
- 资格检测页：`https://one.google.com/ai-student...`
- 支付 iframe：`tokenized.play.google.com`（嵌套 iframe）
- 2FA：TOTP（`pyotp` 生成验证码）
- 现有浏览器管理：BitBrowser API → 返回 CDP WebSocket → Playwright `connect_over_cdp(ws)`

### 4.1 agent-browser 能替代的部分

- 替代“页面交互脚本层”
  - 把“打开页面/输入/点击/等待/取文本/截图/trace”从 Python 里挪到 CLI 命令。
  - 对“探索页面、调试选择器/流程”非常高效。

潜在难点（需要验证）：

- 复杂 iframe（Google Payments）里的 refs 是否稳定、是否好用。
- CDP 接入方式：你们现在拿到的是 `ws://...` endpoint；agent-browser 的 CDP 模式文档主要展示 `connect <port>` / `--cdp <port>`，是否支持直接 ws 需要进一步确认。

### 4.2 Playwright（维持现状）最擅长的部分

- 复杂状态机 + 批量并发 + 落库（SQLite） + GUI 驱动的工作流。
- 你们当前脚本已经把多语言、容错、嵌套 iframe 处理写得很细，这种复杂业务继续用 Playwright 最稳。

### 4.3 DrissionPage 可能带来的价值

- 仍然保持 Python 工程形态（对你们现有 PyQt6/SQLite 集成友好）。
- 如果你的“查数据”最终来自 XHR/Fetch JSON，DrissionPage 的“浏览器控制 + 发包/抓包联动”会让“登录一次 → 后续走接口抓数据”更舒服。

潜在难点（需要验证）：

- 对你们当前 Google Payments iframe 的交互兼容性。
- 团队是否熟悉它的对象模型与最佳实践（版本差异也需要注意）。

---

## 5. 按你的对比维度：代码量 / 配置 / 调试 / 集成

### 5.1 代码量

- agent-browser：
  - 单次流程（登录→点击→读文本）可以压缩成十几条命令。
  - 但“批量/并发/错误处理/落库”仍需要外部脚本（bash/python）做编排。

- Playwright：
  - 需要写脚本，样板代码多。
  - 复杂逻辑写起来最自然。

- DrissionPage：
  - 仍需要写脚本，但通常比 Playwright 更省（取决于你使用的 API 风格）。

### 5.2 配置

- agent-browser：
  - “项目内零配置”更接近事实；机器层面需要 Node/npm + `agent-browser install` 下载 Chromium。
  - Linux 可能要额外装依赖（可用 `agent-browser install --with-deps`）。

- Playwright：
  - 需要 Python 环境 + pip 依赖 +（如要）`playwright install`。
  - 你们还叠加了 BitBrowser 本地服务依赖。

- DrissionPage：
  - Python 环境 + pip 安装；通常还需要可用的 Chromium/Chrome。

### 5.3 调试

- agent-browser：
  - 天然适合“交互式调试”：跑到哪一步卡住，就在那一步继续试。
  - 支持 `--headed` 可视化调试，以及 `trace`/`screenshot` 等。

- Playwright：
  - 也能 trace/screenshot，但调试往往需要改代码重跑。
  - 对复杂流程（尤其登录+iframe）迭代成本更高。

- DrissionPage：
  - 调试方式更接近传统 Python 脚本调试：日志/截图/断点。

### 5.4 集成

- agent-browser：
  - 集成方式是“调用 CLI”。
  - 适合放在 Bash/CI/任意语言中；对 GUI/SQLite 集成需要你写一层编排代码。

- Playwright / DrissionPage：
  - 都是库形态，天然适合直接集成到 Python 项目里。
  - 你们当前项目已经是 Python 工程，库形态更自然。

---

## 6. 推荐选型（按典型目标）

### 目标 A：最快做出“能跑通的登录+查询”，且想省上下文

优先：`agent-browser`

- 用 `snapshot -i --json` + refs，模型更容易稳定地找到输入框/按钮。
- 用 `state save/load` 复用登录态，减少重复登录触发风控。

### 目标 B：长期维护、批量并发、落库、GUI 按钮触发

优先：保持 Playwright（或评估 DrissionPage 作为 Python 库替代）

- 你们已有的业务逻辑（多语言、容错、支付 iframe）已经很重，继续工程化更重要。

### 目标 C：登录一次后，主要通过接口抓数据（而非一直点页面）

优先：评估 DrissionPage

- 如果 DrissionPage 的“浏览器控制 + 发包/抓包”能让你稳定拿到 cookie/token，那么后续读数据可以走接口，更快更稳。

---

## 7. 风险与注意事项（特别针对 Google 登录/支付类页面）

- Headless 风险：无头模式对风控更敏感；无论用哪个方案，都建议先 headed 调试，生产再切 headless。
- 登录风控：反复从 `accounts.google.com` 走 UI 登录非常容易触发验证；优先考虑“复用登录态”。
- 支付 iframe：DOM/iframe 嵌套深且经常变化；无论 refs 还是 selector，都要准备“容错 + 截图 + trace”。
- 账号安全：涉及密码/2FA/支付操作，建议把“修改密码/重置 2FA”这类高风险功能与普通查询隔离（权限/审计/开关）。

---

## 8. 附：agent-browser 的典型命令流（概念示例）

下面仅作为“命令风格”参考（不是针对特定网站的可直接运行脚本）：

```bash
agent-browser open "https://accounts.google.com"
agent-browser snapshot -i

# 假设 snapshot 输出里 Email textbox ref 为 e3
agent-browser fill @e3 "user@example.com"

# 假设 Next button ref 为 e4
agent-browser click @e4

agent-browser wait --load networkidle
agent-browser snapshot -i

# 假设 Password textbox ref 为 e7
agent-browser fill @e7 "password"
agent-browser press Enter

# 等待登录完成后，打开业务页面
agent-browser open "https://one.google.com/ai-student"
agent-browser wait --load networkidle
agent-browser snapshot -i
```

---

## 9. 附：Playwright vs agent-browser 的关系（避免误解）

- agent-browser 并不是替代 Playwright 的“新引擎”。
- agent-browser 更像是“把 Playwright 的常用能力做成 CLI，并且对 LLM 加了 snapshot/ref 的低上下文工作流”。

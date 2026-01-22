# P工具箱：当前实现说明 & 后续拆分规划

本文档用于记录 `P工具箱`（当前实现：`2dev/geek/geek_main_gui.py`）的代码结构、依赖关系、边界约定，以及未来“拆分文件/模块化”的建议方案。

目标：
- 现在不拆分，先把功能堆起来，确保可用性和交付速度。
- 但在堆功能的同时，提前把“未来要拆出去的边界”定义好，避免后面拆分时变成大手术。

---

## 1. 当前现状（高层架构）

当前 `P工具箱` 的 GUI 主入口在：
- `2dev/geek/geek_main_gui.py`

它包含了三类职责：
1) UI：窗口布局、按钮、表格、日志面板、暗色主题。
2) 调度：`GeekWorkerThread` 负责在后台线程里跑任务（避免卡 UI），并做并发控制。
3) “胶水”：读取 `accounts.txt/proxies.txt/cards.txt`，将数据交给流程层执行；同时捕获 stdout/stderr 以显示原仓库大量 `print()` 日志。

核心业务逻辑并不都写在 GUI 里，仍然依赖仓库已有模块：
- 登录/绑卡流程：`auto_bind_card.py`
- DB/状态导出：`database.py`、`account_manager.py`
- SheerID 验证窗口/逻辑：`sheerid_gui.py`、`sheerid_verifier.py`
- GeekezBrowser 适配层（2dev）：
  - 控制与 profiles 文件：`2dev/geek/geek_browser_api.py`
  - 任务流程编排：`2dev/geek/geek_process.py`

GeekezBrowser 侧（外部仓库 `D:\\java\\github\\GeekezBrowser`）为了配合外部自动化，已提供控制端口：
- `GET /health`
- `POST /profiles/{id}/launch`
- `POST /profiles/{id}/close`
- `POST /shutdown`（用于 GUI 停止引擎时真正退出应用）

---

## 2. 当前代码的“拆分边界”（先约定，后执行）

为了后续拆分顺利，建议从现在开始按以下原则继续堆功能：

### 2.1 GUI 文件里允许存在的内容
- UI 布局、样式、控件定义。
- 任务入口（按钮点击）到“流程层”的调用。
- 线程管理（启动/停止/禁用按钮等）。
- 日志接入（stdout/stderr capture）——因为它属于“把外部模块输出接入 UI”的职责。

### 2.2 GUI 文件里尽量不要继续堆的内容
以下内容即使现在先堆，也请尽量放在 `geek_process.py` 或新建的 helper 中（即使暂时仍在同文件，也建议写成独立函数/类，便于后续剪切）：
- Playwright 的具体页面操作细节。
- 对 profiles.json/settings.json 的读写逻辑。
- “某个按钮”的业务流程串联（比如：先启动环境 -> 再跑某页面 -> 再解析结果 -> 再写 DB）。

### 2.3 建议的“调用链”保持不变
推荐保持这个方向，后续拆分成本最低：

`GUI (geek_main_gui.py)`
→ `GeekWorkerThread`（线程/并发/日志捕获）
→ `GeekProcess`（业务流程编排）
→ `GeekezBrowserAPI`（控制端口 + profiles 文件操作）
→ GeekezBrowser（Electron 应用）

仓库原有业务（auto_bind_card/database/account_manager/sheerid_verifier）仍由 `GeekProcess` 调用。

---

## 3. 后续拆分目标（建议文件结构）

当你决定“开始拆分”时，建议目标结构如下（不改变功能，仅移动代码）：

### 3.1 UI 层
- `2dev/geek/ui/p_toolbox_window.py`
  - `GeekezBrowserMainWindow`（窗口 UI + 控件创建 + 样式）
  - 表格渲染/行内按钮控件

### 3.2 Worker / 日志接入
- `2dev/geek/ui/workers.py`
  - `GeekWorkerThread`
  - stdout/stderr 捕获（目前的 `_QtStreamForwarder`）
  - logging handler（目前的 `_QtLogHandler`）

### 3.3 启动器
- `2dev/geek/launcher.py`
  - `AppLauncher`（npm start、shutdown、wait_until_ready/down）

### 3.4 主入口（保持启动方式不变）
- `2dev/geek/geek_main_gui.py`
  - 只保留 `main()`：创建 QApplication + window.show()，使启动命令不变：
    - `python 2dev/geek/geek_main_gui.py`

### 3.5 业务流程
- `2dev/geek/geek_process.py`
  - 继续作为“业务流程编排层”
  - 新增任务也优先放这里，而不是 UI 文件

---

## 4. 拆分时的执行策略（最小风险）

拆分遵循“剪切-验证-再剪切”的小步策略：

1) 先拆纯工具类：
   - `_QtStreamForwarder`、`_QtLogHandler` → `ui/workers.py`
2) 再拆 `GeekWorkerThread` → `ui/workers.py`
3) 再拆 `AppLauncher` → `launcher.py`
4) 最后拆 `GeekezBrowserMainWindow` → `ui/p_toolbox_window.py`
5) `geek_main_gui.py` 最后变薄

每一步完成后都做最小验证：
- `python -m py_compile ...`
- GUI 能启动
- 引擎启动/停止（/health up/down）
- 运行一个最短任务（比如 sheerlink）确认日志仍会显示

---

## 5. 当前已知技术约束/注意事项

### 5.1 引擎停止为什么要 /shutdown
仅靠 GUI 启动的 `Popen(npm start)` 来 terminate 并不可靠：
- 用户可能手动启动 GeekezBrowser
- 或 npm/electron 进程链不同

所以需要 GeekezBrowser 控制服务提供 `POST /shutdown`，由应用自我退出；GUI 再轮询 `/health` 下线确认。

### 5.2 日志为什么要捕获 stdout/stderr
原仓库多个模块大量使用 `print()` 输出（例如 DB 导出、登录步骤），如果不捕获，UI 看不到。
后续如果要更优雅，可以逐步把关键业务日志改为统一 logger，但这属于“业务改造”，不建议在拆分时一起做。

### 5.3 不要把 secrets 写进仓库
任何包含真实卡号、邮箱密码、2FA secret 的文件都不应提交。
（例如 cards.txt 真实卡号 / 邮箱配置 / 2FA 密钥等）

---

## 6. “先堆功能”的建议落点

你现在要继续堆功能的话，建议按下面方式堆，后续拆分几乎是“移动文件”级别：

1) 新功能优先加在 `2dev/geek/geek_process.py`
   - 让 GUI 只做按钮和参数采集

2) GUI 里新增的按钮/菜单
   - 只负责调用 `start_task("xxx")`
   - `GeekWorkerThread` 里新增 `task_type` 分支
   - 分支里调用 `GeekProcess.run_xxx(...)`

3) 每加一个任务，就在本文件或 README 中记录：
   - 输入（账号/代理/卡/配置）
   - 输出（写 DB？写 txt？写 profile？）
   - 成功/失败判定

---

## 7. 相关入口文件索引（便于定位）

- GUI 主入口：`2dev/geek/geek_main_gui.py`
- Geek 流程层：`2dev/geek/geek_process.py`
- Geek 控制/API：`2dev/geek/geek_browser_api.py`
- 登录/绑卡：`auto_bind_card.py`
- DB/导出：`database.py`、`account_manager.py`
- SheerID：`sheerid_gui.py`、`sheerid_verifier.py`

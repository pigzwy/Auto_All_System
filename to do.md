# To Do / 交接清单

用途：换电脑后可以按这个清单快速恢复上下文、继续开发，不需要回忆细节。

更新时间：2026-01-22

---

## 0. 当前状态（你现在在哪）

- 主仓库：`D:\java\github\auto_bitbrowser`
- 当前分支：`main`
- 近期已推送到远端：已（包含 Geek 开发者指南等文档）

注意：工作区里可能还有 `external/`（junction/临时目录），不要提交。

---

## 1. 关键入口 & 代码地图

- P工具箱（Geek 主 GUI）：`2dev/geek/geek_main_gui.py`
  - 启动：`python 2dev/geek/geek_main_gui.py`
  - 任务分发：`GeekWorkerThread.run()` 里的 `task_type`
  - 左侧工具箱：`_add_google_section()` / `_add_data_section()`
  - 引擎启动/停止：`AppLauncher.start()` / `AppLauncher.stop()`

- Geek 流程编排层：`2dev/geek/geek_process.py`
  - profiles 环境：`ensure_profiles()` / `ensure_profile()`
  - 启动/关闭：`launch_by_email()` / `close_by_email()`
  - SheerLink：`run_sheerlink()`
  - 全自动/仅绑卡：`run_auto()`

- Geek 控制与 profile 文件：`2dev/geek/geek_browser_api.py`
  - `GeekezBrowserAPI`：/health /launch /close /shutdown + profiles.json/settings.json

- 原仓库复用模块（被 GeekProcess 调用）：
  - 登录/绑卡：`auto_bind_card.py`（`check_and_login()` / `auto_bind_card()`）
  - 状态落盘：`account_manager.py`（`AccountManager.*`）
  - 状态落库：`database.py`（`DBManager.update_status()` 等）
  - SheerID API：`sheerid_verifier.py`（`SheerIDVerifier.verify_single()` / `verify_batch()`）
  - SheerID 批量窗口：`sheerid_gui.py`（`SheerIDWindow`）

- 文档：
  - 拆分规划：`P工具箱_拆分规划.md`
  - Geek 开发者指南：`2dev/geek/开发者指南.md`

---

## 2. 换电脑后 5 分钟恢复步骤

1) 拉代码

```bash
git clone <your-repo>
cd auto_bitbrowser
git pull
```

2) Python 依赖（建议使用 venv）

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3) Playwright（如果需要跑自动化）

```bash
python -m playwright install
```

4) GeekezBrowser 源码（另一个仓库）

- 默认路径写死在 `2dev/geek/geek_main_gui.py`：`GEEK_SOURCE_PATH = r"D:\java\github\GeekezBrowser"`
- 换电脑后基本一定要改这个路径，或者把仓库放到同一路径。
- 启动方式：GUI 内部会执行 `npm start -- --control-port=19527`

5) 数据文件

- 根目录（exe/源码同级）：`accounts.txt` / `proxies.txt` / `cards.txt`
- 这些文件不要提交真实敏感信息。

---

## 3. 待做事项（按优先级）

### P0（跑得起来 & 稳）

- 校验 GeekezBrowser 控制端口是否与当前实现一致
  - 目标：`GET http://127.0.0.1:19527/health` 为 200
  - 目标：`POST /profiles/{id}/launch` 返回 `debugPort` 和可用的 `wsEndpoint`（或至少 `debugPort`）
  - 目标：`POST /profiles/{id}/close` 可关闭
  - 目标：`POST /shutdown` 可优雅退出

- 如果不同版本 GeekezBrowser 端点不一致
  - 需要在 `2dev/geek/geek_browser_api.py` 做兼容（多 endpoint 尝试 / fallback）
  - 或者在 GeekezBrowser 仓库补齐端点（更推荐）

- P工具箱停止引擎可靠性
  - 当前逻辑：优先走 `/shutdown`，再 terminate 进程，再轮询 `/health` 下线
  - 需要确认在用户“手动打开的 GeekezBrowser”场景下是否仍符合预期

### P1（功能扩展）

- 新增专区（例如 GB 专区）
  - 目标：遵循 `2dev/geek/开发者指南.md` 的模板
  - 放置位置：优先在 `2dev/geek/geek_process.py` 新增 `run_gb_xxx()`；GUI 只加按钮 + task_type

- 补齐/统一任务命名
  - 现有：`start_app`, `ensure_profiles`, `launch`, `close`, `sheerlink`, `bind`, `auto`
  - 新专区建议用前缀：`gb_xxx`, `gpt_xxx`，避免冲突

- 运行状态展示（可选增强）
  - 现在 GUI 对“profile 是否正在运行”是 best-effort，本地 set 维护
  - 如果 GeekezBrowser 能提供 `GET /profiles/running` 或 `GET /profiles` 含运行态，会更可靠

### P2（工程化/维护成本）

- 文档补充（如需要）
  - 把“新增专区的最小契约（输入/输出/判定）”做成固定模板

- 未来拆分（暂不做，等功能稳定再动）
  - 已写规划：`P工具箱_拆分规划.md`

---

## 4. 低风险验证清单（每次换电脑/改大逻辑后）

- `python -m py_compile 2dev/geek/geek_main_gui.py 2dev/geek/geek_process.py 2dev/geek/geek_browser_api.py`
- 启动 GUI：`python 2dev/geek/geek_main_gui.py`
- 点一次“启动引擎”，确认状态灯变为运行中
- 点一次“环境创建/更新”，确认 profiles.json 有更新
- 勾选一个账号，点“▶️”启动，确认表格状态/日志有输出

# GeekezBrowser API 变更适配说明

最后更新：2026-01-27

本文档用于记录 GeekezBrowser（GeekezBrowser / GeekezBrowser 上游）控制 API 的关键变更点，并说明对 Auto All System（Google 业务插件）的影响与适配建议。

## 背景

Auto All System 的 Google 业务插件支持使用 GeekezBrowser 作为浏览器环境管理器（创建/启动环境 + 通过 CDP 连接 Playwright）。

官方 API 文档（GeekezBrowser）：

- https://browser.geekez.net/docs#doc-api

上游 GeekezBrowser 更新后，API 体系被拆分成两套：

- `Control Server`：轻量控制端口（不带 `/api` 前缀），主要用于自动化启动并获取 `debugPort/wsEndpoint`
- `API Server`：完整 REST API（带 `/api` 前缀），提供 profile CRUD、导入导出、stop 等功能，并带 UI/IPC 集成

如果我们仍按旧版“单一 API”假设调用，会导致部分功能（尤其关闭环境）失效，影响 Google 自动化稳定性。

## 当前系统集成位置

- 后端 Geekez 适配层：`backend/apps/integrations/geekez/api.py`、`backend/apps/integrations/geekez/adapter.py`
- Google 业务使用位置（浏览器池）：`backend/plugins/google_business/services/browser_pool.py`
- UI 触发 Geekez 启动（示例）：Google 账号模块“启动 Geekez 环境”相关接口

## 上游新版本：两套服务说明

### 1) Control Server（不带 /api）

> 说明：Control Server 目前在官方文档中未单独列出，但在上游代码（`main.js`）中存在。
> Auto All System 的自动化链路依赖它返回 `debugPort/wsEndpoint`。

特点：

- 只有在显式配置 `control-port` 时才会启动（否则不会 listen）
- 支持可选鉴权：`Authorization: Bearer <token>`
- 端点较少，主要用于自动化启动

控制端口配置（上游 main.js）：

- Host：`--control-host` 或 `GEEKEZ_CONTROL_HOST`，默认 `127.0.0.1`
- Port：`--control-port` 或 `GEEKEZ_CONTROL_PORT`，默认空（未设置则不启动 Control Server）
- Token：`--control-token` 或 `GEEKEZ_CONTROL_TOKEN`，可选

Token 是否必须？

- 本机默认不需要 token（不开 control token 的情况下）
- 只有你在 GeekezBrowser 里显式配置了 `GEEKEZ_CONTROL_TOKEN`（或启动参数 `--control-token`）时，才必须带 `Authorization: Bearer <token>`

核心端点（上游）：

- `GET /health` → `{ ok: true }`
- `GET /profiles` → `{ ok: true, profiles: [{ id, name, debugPort, tags }] }`
- `POST /profiles/{uuid}/launch`（uuid 为 36 位）
  - 请求：`{ debugPort: 0|"auto"|number, enableRemoteDebugging?: boolean, watermarkStyle?: string }`
  - 响应：`{ ok: true, profileId, debugPort, wsEndpoint }`

重要变化：

- 上游 Control Server **没有发现** `POST /profiles/{uuid}/close` 端点

### 2) API Server（/api 前缀）

特点：

- 端点多（profile CRUD、导入导出、stop 等）
- 支持 `idOrName`（id 或 name 都可匹配）
- profile 创建支持自动唯一命名 `generateUniqueName()`
- profile 创建/删除会通知 UI 刷新 `notifyUIRefresh()`

核心端点（上游）：

- `GET /api/status`
- `GET /api/profiles`
- `GET /api/profiles/:idOrName`
- `POST /api/profiles`（create，自动生成唯一 name）
- `PUT /api/profiles/:idOrName`
- `DELETE /api/profiles/:idOrName`（删除后会通知 UI 刷新）
- `GET /api/open/:idOrName`（触发 UI/IPC 启动）
- `POST /api/profiles/:idOrName/stop`（停止/回收环境）
- `GET /api/export/all?password=xxx`（加密导出）
- `GET /api/export/fingerprint`（YAML 导出）
- `POST /api/import`（YAML/加密备份导入）

启动方式（官方文档）：

1. GeekezBrowser → Settings → Advanced → API Server
2. 开启 `Enable API Server`
3. 设置端口（默认：`12138`）
4. API 地址：`http://127.0.0.1:12138`

认证（官方文档）：

- API Server 仅监听 `127.0.0.1`，默认不需要鉴权（依赖“仅本机可访问”的安全模型）

注意：

- API Server 绑定在 `127.0.0.1`，如果 Auto All System 运行在 Docker 容器里，容器**无法直接**访问宿主机的 `127.0.0.1:12138`。
  - 需要使用 `host.docker.internal` / host network / 或让 GeekezBrowser API Server listen 到可达地址（上游默认不建议）。

## 上游 vs 当前系统（旧实现）对比

| 功能 | 上游版本（新） | 当前系统旧实现（Auto All System） |
|------|----------------|----------------------------------|
| API 端点数量 | Control Server 少量 + API Server 完整（12+） | 主要只对接 Control Server（health/launch/close 假设） |
| Profile 查找 | API Server 支持 `idOrName` | 主要按 profile id；name 只用于读写 `profiles.json` |
| 自动唯一命名 | ✅ `generateUniqueName()`（API Server） | ❌（文件写入时不保证唯一） |
| UI 刷新通知 | ✅ `notifyUIRefresh()`（API Server） | ❌（直接改 `profiles.json` 时 UI 不会自动刷新） |
| stop/close | ✅ `POST /api/profiles/:idOrName/stop` | 旧代码可能调用 `POST /profiles/{id}/close`（上游新版本可能已不存在） |
| 导入导出 | ✅ `/api/export/*`、`/api/import` | ❌ |
| Control Token | ✅ `Authorization: Bearer ...` | 旧实现不支持 token |
| Control Server 启动 | 新版需要显式设置 `GEEKEZ_CONTROL_PORT` 才会启动 | 旧实现默认假设 19527 恒可用 |

## 对 Google 业务的影响评估

高风险（必须关注）：

- 关闭环境失效：如果上游没有 `/profiles/{id}/close`，我们关不掉 Geekez 环境，会导致进程/端口堆积，长期跑任务会越来越不稳定
- Control Server 未启动：如果升级后未设置 `GEEKEZ_CONTROL_PORT`，`/health` 会连不上，Google 插件无法 launch
- 控制端口开启 token：如果设置了 `GEEKEZ_CONTROL_TOKEN`，不带 Authorization 会直接 401

中风险（体验/一致性）：

- 直接写 `profiles.json` 不会触发 Geekez UI 刷新，需要手动刷新或改走 `/api/profiles` 来做 CRUD

## Auto All System 适配建议（推荐实现）

建议对 `backend/apps/integrations/geekez/api.py` 做最小兼容改造（同时兼容新旧 Geekez）：

1) Control Token 支持
- 新增环境变量（建议）：`GEEKEZ_CONTROL_TOKEN`（或在现有配置里新增）
- 请求 Control Server 时带 `Authorization: Bearer <token>`

2) close/stop 兼容
- 关闭 profile 时（兼容顺序）：
  - 优先 `POST /profiles/{uuid}/stop`（Control Server，新版上游存在）
  - Control Server 不可用时 fallback：`POST /api/profiles/{idOrName}/stop`（API Server）
  - 最后兼容极老版本：`POST /profiles/{id}/close`

3) Name → ID 映射（可选）
- 如果上游 API Server 可用，可以用 `/api/profiles/:idOrName` 直接查
- 如果只启用 Control Server，可以先 `GET /profiles` 拿到 `id/name` 再映射

4) profile CRUD 的 UI 刷新（可选）
- 为了让 Geekez UI 立即可见：推荐走上游 `/api/profiles` 做 CRUD（可获得 `generateUniqueName()` + `notifyUIRefresh()`）
- 如果继续文件写入 `profiles.json`：UI 可能需要手动刷新（或重启 Geekez）

5) profile delete 兼容（建议）
- 删除 profile 时：
  - 优先 `DELETE /api/profiles/{idOrName}`（API Server，会通知 UI 刷新）
  - 失败时 fallback 到本地 `profiles.json`（历史行为）

## 兼容模式（本项目实现）

说明：为了同时兼容新旧 GeekezBrowser，Auto All System Web 后端采用“优先官方服务、失败再 fallback 文件”的策略。

当前调用顺序（重点）：

- `list_profiles`：`GET /api/profiles` → `GET /profiles` → 读取本地 `profiles.json`
- `create_or_update_profile`：`POST/PUT /api/profiles` → 写本地 `profiles.json`
- `delete_profile`：`DELETE /api/profiles/{idOrName}` → 读写本地 `profiles.json`
- `launch_profile`：`POST /profiles/{uuid}/launch`（Control Server，返回 `wsEndpoint`）
- `stop_profile/close_profile`：`POST /profiles/{uuid}/stop` → `POST /api/profiles/{idOrName}/stop` → `POST /profiles/{id}/close`

## 部署/配置建议

### 环境变量（Auto All System 后端）

为兼容新旧 GeekezBrowser，本系统目前支持这些变量：

- Control Server（用于 launch/wsEndpoint）
  - `GEEKEZ_CONTROL_HOST` / `GEEKEZ_CONTROL_PORT`
  - `GEEKEZ_CONTROL_TOKEN`（可选）
  - 兼容旧变量：`GEEKEZ_API_HOST` / `GEEKEZ_API_PORT` / `GEEKEZ_API_TOKEN`
- API Server（用于 stop fallback，官方文档默认 12138）
  - `GEEKEZ_API_SERVER_HOST`（默认 `127.0.0.1`）
  - `GEEKEZ_API_SERVER_PORT`（默认 `12138`）

建议：

- 在 Docker 场景下，如果你希望容器能访问宿主机 GeekezBrowser，需要把 `GEEKEZ_*_HOST` 指向宿主机可达地址（例如 `host.docker.internal`）。

### 必需：确保 Control Server 启动

如果你希望 Auto All System 继续通过 Control Server 获取 `debugPort/wsEndpoint`：

- 在 GeekezBrowser 启动环境中设置：
  - `GEEKEZ_CONTROL_PORT=19527`
  - （可选）`GEEKEZ_CONTROL_HOST=127.0.0.1`
  - （可选）`GEEKEZ_CONTROL_TOKEN=...`

在 Auto All System（后端）中配置 Geekez 控制地址（当前代码使用）：

- `GEEKEZ_API_HOST`：Geekez 控制端口 Host
- `GEEKEZ_API_PORT`：Geekez 控制端口 Port（默认 19527）

> 建议：后续统一命名为 `GEEKEZ_CONTROL_*`，避免和 API Server 混淆。

## 自检命令（排障）

1) Control Server 是否在线：

```bash
curl -sS http://127.0.0.1:19527/health
```

2) Control Server 是否要求 token：

```bash
curl -sS http://127.0.0.1:19527/health -H 'Authorization: Bearer <token>'
```

3) API Server 是否启用：

```bash
curl -sS http://127.0.0.1:12138/api/status
```

4) stop 环境（新上游）：

```bash
curl -sS -X POST http://127.0.0.1:12138/api/profiles/<idOrName>/stop
```

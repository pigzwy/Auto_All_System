# Upstream 合并方案（32c70c6 / v2.1.0）

## 1. 目标

- 将上游 `upstream/main` 的 4 个提交同步到本地 `dev`。
- 对 2FA 相关逻辑做择优合并，不盲目覆盖本地已有能力。
- 合并后保持现有 Web 插件 2FA 能力不回退，并引入上游 PyQt 新增能力。

## 2. 上游更新明细

上游缺失提交（本地相对 `upstream/main` 落后 4）：

1. `7b922c6` - docs: add sponsor ad for Google account wholesale
2. `32c70c6` - feat: v2.1.0（核心功能更新）
3. `c99ae80` - docs: add USDT TRC20 donation address
4. `2247e55` - docs: add USDT QR code image

### 2.1 `7b922c6`

- 变更：`README.md`
- 规模：`1 file changed, 18 insertions`
- 类型：文档增补

### 2.2 `32c70c6`（重点）

- 规模：`73 files changed, 36153 insertions(+), 892 deletions(-)`
- 核心热点：
  - `Auto_All_System_Pyqt/src/google/backend/change_2fa_service.py`（新增，约 1086 行）
  - `Auto_All_System_Pyqt/src/google/backend/google_auth.py`（`+772/-303`）
  - `Auto_All_System_Pyqt/src/google/backend/bind_card_service.py`（`+827/-201`）
  - `Auto_All_System_Pyqt/src/google/backend/all_in_one_service.py`（`+985/-109`）
  - `Auto_All_System_Pyqt/src/web/*`、`Auto_All_System_Pyqt/src/system/*` 大量新增/重构
  - `Auto_All_System_Pyqt/src/core/{database.py,bit_api.py}`
- 类型：功能 + 架构增强 + Web/GUI 扩展

### 2.3 `c99ae80`

- 变更：`README.md`、`Auto_All_System_Pyqt/README.md`
- 规模：`2 files changed, 12 insertions`
- 类型：文档增补（TRC20 地址）

### 2.4 `2247e55`

- 变更：`README.md`、`Auto_All_System_Pyqt/README.md`、`Auto_All_System_Pyqt/resources/OKX.jpg`
- 规模：`3 files changed, 14 insertions, 6 deletions` + 新增图片
- 类型：文档 + 资源文件

## 3. 本地 2FA 现状（合并前）

### 3.1 Web 插件（本地）

关键路径：

- `Auto_All_System_Web/backend/plugins/google_business/services/security_service.py`
- `Auto_All_System_Web/backend/plugins/google_business/tasks.py`
- `Auto_All_System_Web/backend/plugins/google_business/views.py`
- `Auto_All_System_Web/backend/plugins/google_business/serializers.py`

能力特征：

- `change_2fa_secret` 已完整实现（重认证、切换流程、密钥提取、验证、日志、截图诊断）。
- 任务编排 `security_change_2fa` 已落地，持久化 `new_2fa_secret` 等字段。
- 选择器与多语言兜底较充分，错误可观测性强。

### 3.2 PyQt（本地）

关键路径：

- `Auto_All_System_Pyqt/src/google/backend/google_auth.py`
- `Auto_All_System_Pyqt/src/google/backend/all_in_one_service.py`
- `Auto_All_System_Pyqt/src/google/backend/bind_card_service.py`

能力特征：

- 登录流程已含 `totpPin` 处理，可读取 `secret/2fa_secret`。
- 但缺少独立、完整的「变更 2FA」服务模块。

## 4. 2FA 择优结论

对比结果：

- Web 插件本地 `security_service.py`：在鲁棒性、可观测性、多语言与回退策略上更成熟。
- 上游 `change_2fa_service.py`：优点是直接适配 PyQt 批处理链路，补齐了 PyQt 侧独立改 2FA 能力。

择优策略：

1. **保留本地 Web 2FA 逻辑为主实现，不回退。**
2. **引入上游 PyQt 的 `change_2fa_service.py` 与其链路改动。**
3. PyQt 发生冲突时，优先保留以下特性：
   - 重认证完整性（密码 + 当前 2FA）
   - 新密钥提取校验严谨性
   - 错误日志可定位性（必要时保留截图/上下文信息）
   - 批处理可恢复与失败隔离

## 5. 合并执行顺序

1. 同步文档提交：`7b922c6`、`c99ae80`、`2247e55`
2. 合并核心提交：`32c70c6`
3. 冲突处理原则：
   - Web 插件目录 `Auto_All_System_Web/backend/plugins/google_business/**`：**保持本地现状**（上游该提交未覆盖此目录）
   - PyQt 目录：按上游主线合并，再对 2FA 逻辑做择优修正
4. 验证：
   - Python 语法检查（受影响关键文件）
   - 关键流程静态检查（2FA 入口、绑卡入口、批处理入口）

## 6. 风险与回滚点

主要风险：

- `32c70c6` 体量极大，潜在冲突点集中在 `Auto_All_System_Pyqt/src/google/backend/*` 与 `README`。
- 引入 `src/system/**` 镜像架构后，需避免重复入口导致误调用。

回滚建议：

- 使用 `ORIG_HEAD` 作为整次 merge/cherry-pick 的回滚锚点。
- 每处理完一个提交后立即记录状态，必要时按提交粒度回退。

## 7. 验收标准

- 上游 4 个提交内容已落到本地工作区。
- Web 插件现有 `change_2fa_secret` 能力未退化。
- PyQt 具备上游新增的改 2FA 模块与调用路径。
- 无新增语法错误，关键入口可正常导入。

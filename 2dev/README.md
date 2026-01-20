# 二次开发扩展功能 (2dev)

本目录包含基于 [auto_bitbrowser](https://github.com/Leclee/auto_bitbrowser) 的二次开发扩展功能。

> **上游仓库**: https://github.com/Leclee/auto_bitbrowser  
> **Fork 仓库**: https://github.com/pigzwy/Auto_All_System

---

## 功能概览

| 模块 | 功能 | 说明 |
|------|------|------|
| [绑卡订阅 GUI](#1-绑卡订阅-gui) | 可视化绑卡界面 | 批量绑卡订阅操作 |
| [Google 安全自动化](#2-google-安全自动化) | 2FA/辅助邮箱修改 | 批量修改账号安全设置 |
| [邮件验证码读取](#3-邮件验证码读取) | IMAP 自动读取 | 自动获取 Google 验证码 |
| [订阅状态检测](#4-订阅状态检测) | 状态验证工具 | 检测订阅是否成功 |

---

## 核心功能模块

### 1. 绑卡订阅 GUI

**文件**: `bind_card_gui.py`

功能完整的图形化绑卡界面，支持：

- 批量选择浏览器窗口
- 自动填写卡片信息（卡号、有效期、CVV）
- 实时日志输出
- 多任务并行处理

**使用方法**:
```bash
python 2dev/bind_card_gui.py
```

---

### 2. Google 安全自动化

**文件**: 
- `google_security_gui.py` - GUI 界面
- `google_security_automation.py` - 核心自动化逻辑

支持批量自动化修改 Google 账号安全设置：

| 功能 | 说明 |
|------|------|
| **批量修改 2FA 密钥** | 自动生成新的 TOTP 密钥并绑定 |
| **批量修改辅助邮箱** | 自动设置备用恢复邮箱 |
| **IMAP 验证码自动读取** | 配合 `email_verifier.py` 自动获取验证码 |

**使用方法**:
```bash
python 2dev/google_security_gui.py
```

**配置文件**:
- `recovery_emails.txt` - 辅助邮箱列表（每行一个）
- `email_config.ini` - IMAP 邮箱配置

---

### 3. 邮件验证码读取

**文件**: `email_verifier.py`

通过 IMAP 协议自动读取邮箱中的 Google 验证码：

- 支持 163 邮箱等主流邮箱
- 自动解析邮件内容提取验证码
- 支持超时重试机制

**配置示例** (`email_config.ini`):
```ini
[imap]
server = imap.163.com
email = your_email@163.com
password = your_authorization_code
```

---

### 4. 订阅状态检测

**文件**:
- `verify_subscription.py` - 验证订阅状态
- `check_result.py` - 检查确认步骤
- `click_subscribe.py` - 点击订阅按钮

用于验证 Google One / Gemini 订阅是否成功完成。

---

## 测试与调试工具

| 文件 | 说明 |
|------|------|
| `test_auto_account.py` | 自动账号测试 |
| `test_email_features.py` | 邮箱功能测试 |
| `test_find_browser.py` | 浏览器查找测试 |
| `test_imap_debug.py` | IMAP 连接调试 |
| `debug_form.py` | 表单填写调试 |
| `debug_save_card.py` | 保存卡片调试 |
| `debug_save_card_test.py` | 保存卡片测试 |
| `create_test_browser.py` | 创建测试浏览器 |
| `list_browsers_simple.py` | 简易浏览器列表 |

---

## 数据文件

| 文件 | 说明 |
|------|------|
| `backup_codes.txt` | Google 备份码 |
| `new_2fa_secrets.txt` | 新生成的 2FA 密钥 |
| `recovery_emails.txt` | 辅助邮箱列表 |
| `email_config.ini` | 邮箱 IMAP 配置 |

---

## 文档

| 文件 | 说明 |
|------|------|
| `GUI使用说明.md` | GUI 界面使用指南 |
| `新功能说明.md` | 新功能详细说明 |
| `更新总结.md` | 更新日志总结 |
| `gpt/` | GPT 相关资料 |

---

## 同步上游

本项目设计为最小化对上游的影响：

1. **所有新增文件集中在 `2dev/` 目录**
2. **对原文件的修改尽量保持兼容**
3. **定期同步上游更新**

### 同步命令

```bash
# 添加上游仓库（首次）
git remote add upstream https://github.com/Leclee/auto_bitbrowser.git

# 获取上游更新
git fetch upstream

# 合并上游更新
git merge upstream/main

# 推送到自己的仓库
git push origin main
```

---

## 依赖

除了上游的依赖外，本扩展还需要：

```bash
pip install pyotp imaplib email
```

---

## 许可证

遵循上游项目 [MIT License](../LICENSE)

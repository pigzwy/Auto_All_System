# 二次开发扩展功能 (2dev)

基于 [auto_bitbrowser](https://github.com/Leclee/auto_bitbrowser) 的二次开发扩展。

> **上游仓库**: https://github.com/Leclee/auto_bitbrowser  
> **Fork 仓库**: https://github.com/pigzwy/Auto_All_System

---

## 快速开始

### P工具箱（推荐入口）

```bash
python 2dev/geek/geek_main_gui.py
```

这是主要的图形化界面，集成了所有功能。

---

## 功能模块

### 1. Google 专区

| 功能 | 说明 |
|------|------|
| **SheerLink 获取** | 获取学生验证链接 |
| **仅绑卡** | 已验证账号直接绑卡 |
| **全自动** | 验证 + 绑卡一体化 |
| **SheerID 批量验证** | 批量验证学生身份 |
| **🔐 安全设置修改** | 修改 2FA / 辅助邮箱 / 获取备份码 |
| **📋 验证订阅状态** | 检测订阅状态并截图 |
| **🔘 点击订阅按钮** | 自动点击订阅并处理确认框 |

### 2. 数据管理

| 功能 | 说明 |
|------|------|
| **环境创建/更新** | 根据 accounts.txt 创建浏览器环境 |
| **账号/代理/卡号编辑** | 可视化编辑数据文件 |

---

## 目录结构

```
2dev/
├── geek/                    # GeekezBrowser 版核心模块
│   ├── geek_main_gui.py     # P工具箱主界面
│   ├── geek_process.py      # 流程编排层
│   ├── geek_browser_api.py  # 浏览器控制 API
│   ├── geek_security.py     # 安全设置自动化
│   ├── geek_security_gui.py # 安全设置 GUI
│   └── 开发者指南.md         # 开发文档
├── gpt/                     # GPT 相关模块
├── email_verifier.py        # IMAP 验证码读取
├── email_config.ini         # 邮箱配置
├── recovery_emails.txt      # 辅助邮箱列表
├── backup_codes.txt         # 备份验证码输出
├── new_2fa_secrets.txt      # 新 2FA 密钥输出
└── README.md                # 本文档
```

---

## 配置文件

### 1. 账号文件（根目录）

**accounts.txt** - 账号列表
```
邮箱----密码----辅助邮箱----2FA密钥
```

**proxies.txt** - 代理列表
```
socks5://user:pass@host:port
```

**cards.txt** - 卡号列表
```
卡号 月份 年份 CVV
```

### 2. IMAP 邮箱配置

**email_config.ini** - 用于自动读取验证码
```ini
[imap_163]
email = your@163.com
password = 授权码（非登录密码）

[domain_email]
domain = yourdomain.com
```

**获取 163 授权码**：
1. 登录 163 邮箱网页版
2. 设置 → POP3/SMTP/IMAP
3. 开启 IMAP 服务
4. 生成授权码

---

## 输出文件

| 文件 | 写入时机 |
|------|----------|
| `sheerIDlink.txt` | SheerLink 获取成功 |
| `已验证未绑卡.txt` | 学生身份已验证 |
| `已绑卡号.txt` | 订阅成功 |
| `无资格号.txt` | 无学生资格 |
| `2dev/new_2fa_secrets.txt` | 修改 2FA 成功 |
| `2dev/backup_codes.txt` | 获取备份码成功 |
| `screenshots/*.png` | 订阅验证截图 |

---

## 开发文档

详细的开发指南请参考：[2dev/geek/开发者指南.md](geek/开发者指南.md)

包含：
- 架构说明
- API 参考
- 新增功能指南
- task_type 完整列表

---

## 依赖

```bash
pip install pyotp playwright PyQt6
python -m playwright install
```

---

## 同步上游

```bash
# 添加上游仓库（首次）
git remote add upstream https://github.com/Leclee/auto_bitbrowser.git

# 获取并合并上游更新
git fetch upstream
git merge upstream/main
git push origin main
```

---

## 许可证

遵循上游项目 [MIT License](../LICENSE)

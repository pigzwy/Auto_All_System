#!/usr/bin/env python3
"""
Windows 版本的 GeekezBrowser 自动化脚本
使用源码版（npm start）启动
自动登录 Google AI Student - 支持多账号批量处理
"""

import json
import uuid
import time
import subprocess
import requests
import os
import pyotp
import random
import logging
import re
from pathlib import Path
from datetime import datetime

CONTROL_PORT = 19527
CONTROL_HOST = "127.0.0.1"

# Windows 数据路径
APPDATA = os.getenv("APPDATA", r"C:\Users\Public\AppData\Roaming")
DATA_PATH = Path(APPDATA) / "geekez-browser" / "BrowserProfiles"
PROFILES_FILE = DATA_PATH / "profiles.json"
SETTINGS_FILE = DATA_PATH / "settings.json"

# 源码路径
SOURCE_PATH = r"D:\java\github\GeekezBrowser"

# 配置文件路径
SCRIPT_DIR = Path(__file__).parent
ACCOUNTS_FILE = SCRIPT_DIR / "accounts.txt"
PROGRESS_FILE = SCRIPT_DIR / "progress.json"
LOG_FILE = SCRIPT_DIR / "auto-goo.log"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
    force=True,
)
logger = logging.getLogger(__name__)


def load_accounts() -> list:
    """从配置文件加载账号列表"""
    accounts = []
    if not ACCOUNTS_FILE.exists():
        logger.warning(f"账号配置文件不存在: {ACCOUNTS_FILE}")
        return accounts

    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            accounts.append(parse_account(line))

    return accounts


def load_progress() -> dict:
    """加载进度记录"""
    if PROGRESS_FILE.exists():
        try:
            content = PROGRESS_FILE.read_text(encoding="utf-8").strip()
            if content:
                return json.loads(content)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"进度文件损坏，将重新创建: {e}")
    return {}


def save_progress(progress: dict):
    """保存进度记录"""
    PROGRESS_FILE.write_text(
        json.dumps(progress, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def update_progress(email: str, status: str, profile_id: str = "", error: str = ""):
    """更新单个账号的进度"""
    progress = load_progress()
    progress[email] = {
        "status": status,
        "profile_id": profile_id,
        "updated_at": datetime.now().isoformat(),
        "error": error,
    }
    save_progress(progress)
    logger.info(f"进度已更新: {email} -> {status}")


def get_pending_accounts(accounts: list) -> list:
    """获取未处理的账号列表"""
    progress = load_progress()
    pending = []
    for acc in accounts:
        email = acc["email"]
        if email not in progress or progress[email]["status"] != "success":
            pending.append(acc)
    return pending


def parse_account(account_str: str) -> dict:
    """解析账号信息，使用正则匹配分隔符"""
    # 匹配常见分隔符: ---- --- | \t ,
    parts = re.split(r"----+|---+|\||\t|,", account_str)
    parts = [p.strip() for p in parts if p.strip()]

    return {
        "email": parts[0] if len(parts) > 0 else "",
        "password": parts[1] if len(parts) > 1 else "",
        "recovery_email": parts[2] if len(parts) > 2 else "",
        "totp_secret": parts[3] if len(parts) > 3 else "",
    }


def get_2fa_code(secret: str) -> str:
    """生成2FA验证码"""
    secret = secret.replace(" ", "").upper()
    totp = pyotp.TOTP(secret)
    return totp.now()


def load_profiles() -> list:
    """加载配置文件"""
    if PROFILES_FILE.exists():
        return json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    return []


def save_profiles(profiles: list):
    """保存配置文件"""
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    PROFILES_FILE.write_text(
        json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def enable_remote_debugging():
    """启用远程调试"""
    settings = {}
    if SETTINGS_FILE.exists():
        settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    settings["enableRemoteDebugging"] = True
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def create_profile(
    name: str,
    proxy_str: str = "",
    tags: list = None,
    metadata: dict = None,
    window_width: int = 1280,
    window_height: int = 800,
) -> dict:
    """创建新的浏览器配置"""
    profiles = load_profiles()
    new_profile = {
        "id": str(uuid.uuid4()),
        "name": name,
        "proxyStr": proxy_str,
        "tags": tags if tags else [],
        "fingerprint": {"window": {"width": window_width, "height": window_height}},
        "preProxyOverride": "default",
        "isSetup": False,
        "debugPort": 0,
        "createdAt": int(time.time() * 1000),
        "metadata": metadata or {},
    }
    profiles.append(new_profile)
    save_profiles(profiles)
    return new_profile


def launch_profile(profile_id: str) -> dict:
    """通过控制端口启动配置"""
    url = f"http://{CONTROL_HOST}:{CONTROL_PORT}/profiles/{profile_id}/launch"
    resp = requests.post(url, json={"debugPort": 0, "enableRemoteDebugging": True})
    return resp.json()


def update_profile(
    profile_id: str, name: str = None, tags: list = None, metadata: dict = None
):
    """更新配置"""
    profiles = load_profiles()
    for p in profiles:
        if p["id"] == profile_id:
            if name:
                p["name"] = name
            if tags is not None:
                p["tags"] = tags
            if metadata is not None:
                p["metadata"] = {**(p.get("metadata") or {}), **metadata}
            break
    save_profiles(profiles)


def is_app_running() -> bool:
    """检查应用控制端口是否可用"""
    try:
        requests.get(f"http://{CONTROL_HOST}:{CONTROL_PORT}/health", timeout=2)
        return True
    except Exception:
        return False


def start_app() -> subprocess.Popen:
    """使用 npm start 启动源码版应用"""
    if is_app_running():
        logger.info("应用已在运行（控制端口可用）")
        return None

    enable_remote_debugging()

    logger.info(f"启动源码版应用: {SOURCE_PATH}")
    logger.info(f"控制端口: {CONTROL_PORT}")

    process = subprocess.Popen(
        ["npm", "start", "--", f"--control-port={CONTROL_PORT}"],
        cwd=SOURCE_PATH,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=True,
    )

    logger.info("等待应用启动...")
    for i in range(30):
        if is_app_running():
            logger.info("应用已就绪")
            return process
        time.sleep(1)

    logger.error("启动超时")
    return None


class GeekezAutomation:
    """GeekEZ Browser 自动化类"""

    def __init__(self):
        self.process = None
        self.browser = None
        self.profile_id = None

    def start_app(self) -> bool:
        """启动应用"""
        self.process = start_app()
        return is_app_running()

    def stop_app(self):
        """停止应用"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def create_env(
        self,
        name: str,
        proxy: str = "",
        tags: list = None,
        metadata: dict = None,
        window_width: int = 1280,
        window_height: int = 800,
    ) -> dict:
        """创建环境"""
        profile = create_profile(
            name, proxy, tags, metadata, window_width, window_height
        )
        self.profile_id = profile["id"]
        return profile

    def launch_env(self) -> tuple:
        """启动环境，返回 (成功, 调试端口)"""
        if not self.profile_id:
            return False, None
        result = launch_profile(self.profile_id)
        debug_port = result.get("debugPort")
        return (debug_port is not None, debug_port)

    def connect_browser(self, debug_port: int):
        """连接浏览器"""
        from DrissionPage import Chromium

        self.browser = Chromium(f"127.0.0.1:{debug_port}")
        return self.browser

    def save_info(self, name: str = None, tags: list = None, metadata: dict = None):
        """保存环境信息"""
        if self.profile_id:
            update_profile(self.profile_id, name, tags, metadata)

    def disconnect(self):
        """断开浏览器连接（不关闭浏览器）"""
        self.browser = None
        self.profile_id = None


def random_sleep(min_sec: float = 0.5, max_sec: float = 1.5):
    """随机等待，模拟人工操作"""
    time.sleep(random.uniform(min_sec, max_sec))


def human_type(element, text: str, min_delay: float = 0.05, max_delay: float = 0.15):
    """模拟人工逐字输入"""
    element.clear()
    for char in text:
        element.input(char)
        time.sleep(random.uniform(min_delay, max_delay))


def wait_element_clickable(tab, locator: str, timeout: int = 15):
    """等待元素可见且可交互"""
    logger.info(f"等待元素可交互: {locator}")
    for i in range(timeout):
        try:
            ele = tab.ele(locator, timeout=1)
            if ele and ele.states.is_displayed and ele.states.is_enabled:
                # 额外检查元素有尺寸（说明已渲染）
                try:
                    size = ele.rect.size
                    if size[0] > 0 and size[1] > 0:
                        logger.info(f"元素可交互 ({i + 1}s)")
                        return ele
                except:
                    # 如果获取 size 失败，但元素可见可用，也认为可交互
                    logger.info(f"元素可交互（无法获取尺寸）({i + 1}s)")
                    return ele
        except:
            pass
        time.sleep(1)
    logger.warning(f"等待元素超时: {locator}")
    return None


def wait_for_page_load(tab, max_wait: int = 30) -> bool:
    """等待页面加载完成"""
    logger.info("等待页面加载...")
    for i in range(max_wait):
        try:
            # 检查页面是否有登录相关元素
            if tab.ele("@type=email", timeout=1) or tab.ele(
                "@type=password", timeout=1
            ):
                logger.info(f"页面加载完成 ({i + 1}s)")
                return True
        except:
            pass
        time.sleep(1)
        if i > 0 and i % 5 == 0:
            logger.info(f"等待页面加载中... {i}s")
    logger.warning(f"页面加载超时 ({max_wait}s)")
    return False


def login_google(tab, account: dict) -> bool:
    """登录 Google 账号 - 模拟人工操作规避风控，返回是否成功"""
    logger.info(f"开始登录: {account['email']}")

    # 等待页面加载
    if not wait_for_page_load(tab, 60):
        logger.error("页面加载超时，可能是网络问题")
        user_input = (
            input("页面加载超时，按回车重试，输入 s 跳过此账号: ").strip().lower()
        )
        if user_input == "s":
            return False
        # 重试等待
        if not wait_for_page_load(tab, 30):
            logger.error("重试后仍然超时")
            return False

    random_sleep(1, 2)

    # Step 1: 输入邮箱 - 使用等待可交互的方式
    logger.info("查找邮箱输入框...")
    email_input = wait_element_clickable(tab, "@type=email", timeout=20)

    if not email_input:
        logger.error("未找到邮箱输入框，可能是网络问题或页面结构变化")
        user_input = (
            input("未找到邮箱输入框，按回车重试，输入 s 跳过: ").strip().lower()
        )
        if user_input == "s":
            return False
        # 最后一次尝试
        email_input = wait_element_clickable(tab, "@type=email", timeout=15)
        if not email_input:
            return False

    try:
        logger.info("找到邮箱输入框")
        random_sleep(0.5, 1.0)
        email_input.click()
        random_sleep(0.3, 0.6)
        human_type(email_input, account["email"])
        random_sleep(0.8, 1.5)

        next_btn = tab.ele("#identifierNext", timeout=5)
        if not next_btn:
            next_btn = tab.ele("tag:button@@text():下一步", timeout=3)
        if not next_btn:
            next_btn = tab.ele("tag:button@@text():Next", timeout=3)

        if next_btn:
            random_sleep(0.3, 0.8)
            next_btn.click()
            logger.info("点击下一步")
        else:
            email_input.input("\n")
        random_sleep(3, 5)
    except Exception as e:
        logger.error(f"邮箱输入异常: {e}")
        return False

    # Step 2: 输入密码 - 使用等待可交互的方式
    logger.info("查找密码输入框...")
    password_input = wait_element_clickable(tab, "@type=password", timeout=20)

    if not password_input:
        # 检查是否有错误提示或验证码
        logger.warning("未找到可交互的密码输入框，检查页面状态...")
        page_html = tab.html.lower()
        if "captcha" in page_html or "验证" in page_html:
            logger.error("检测到验证码，需要手动处理")
            input("请手动完成验证后按回车继续...")
            password_input = wait_element_clickable(tab, "@type=password", timeout=15)
        elif "couldn't find" in page_html or "找不到" in page_html:
            logger.error("Google 提示找不到账号")
            return False
        else:
            # 最后尝试
            logger.info("等待更长时间...")
            random_sleep(3, 5)
            password_input = wait_element_clickable(tab, "@type=password", timeout=15)

    if not password_input:
        logger.error("未找到密码输入框")
        return False

    try:
        logger.info("找到密码输入框")
        random_sleep(0.5, 1.0)
        password_input.click()
        random_sleep(0.3, 0.6)
        human_type(password_input, account["password"])
        random_sleep(0.8, 1.5)

        next_btn = tab.ele("#passwordNext", timeout=5)
        if not next_btn:
            next_btn = tab.ele("tag:button@@text():下一步", timeout=3)
        if not next_btn:
            next_btn = tab.ele("tag:button@@text():Next", timeout=3)

        if next_btn:
            random_sleep(0.3, 0.8)
            next_btn.click()
            logger.info("点击登录")
        else:
            password_input.input("\n")
        random_sleep(3, 5)
    except Exception as e:
        logger.error(f"密码输入异常: {e}")
        return False

    # Step 3: 处理2FA验证
    logger.info("检查2FA验证...")
    try:
        # 使用等待可交互方式查找2FA输入框
        totp_input = wait_element_clickable(tab, "@type=tel", timeout=8)
        if not totp_input:
            totp_input = wait_element_clickable(tab, "@name=totpPin", timeout=5)

        if totp_input and account["totp_secret"]:
            logger.info("需要2FA验证")
            code = get_2fa_code(account["totp_secret"])
            logger.info("2FA验证码已生成（不写入日志）")

            random_sleep(0.5, 1.0)
            totp_input.click()
            random_sleep(0.3, 0.6)
            human_type(totp_input, code, 0.1, 0.25)
            random_sleep(0.8, 1.5)

            next_btn = tab.ele("#totpNext", timeout=5)
            if not next_btn:
                next_btn = tab.ele("tag:button@@text():下一步", timeout=3)
            if not next_btn:
                next_btn = tab.ele("tag:button@@text():Next", timeout=3)

            if next_btn:
                random_sleep(0.3, 0.8)
                next_btn.click()
                logger.info("提交2FA验证码")
            else:
                totp_input.input("\n")
            random_sleep(2, 4)
        else:
            logger.info("无需2FA或未找到输入框")
    except Exception as e:
        logger.warning(f"2FA处理: {e}")

    # Step 4: 检查辅助邮箱验证
    try:
        page_text = tab.html
        if (
            "辅助邮箱" in page_text or "recovery email" in page_text.lower()
        ) and account["recovery_email"]:
            logger.info("可能需要辅助邮箱验证")
            recovery_input = tab.ele("@type=email", timeout=5)
            if recovery_input:
                random_sleep(0.5, 1.0)
                recovery_input.click()
                random_sleep(0.3, 0.6)
                human_type(recovery_input, account["recovery_email"])
                random_sleep(0.8, 1.5)

                next_btn = tab.ele("tag:button@@text():下一步", timeout=3)
                if not next_btn:
                    next_btn = tab.ele("tag:button@@text():Next", timeout=3)
                if next_btn:
                    next_btn.click()
                random_sleep(2, 4)
    except Exception as e:
        logger.warning(f"辅助邮箱处理: {e}")

    logger.info("登录流程完成")
    random_sleep(2, 3)
    return True


def process_single_account(auto: GeekezAutomation, account: dict) -> bool:
    """处理单个账号的登录流程"""
    email = account["email"]
    logger.info(f"\n{'=' * 50}")
    logger.info(f"处理账号: {email}")
    logger.info("=" * 50)

    try:
        # 创建环境
        auto.create_env(
            name=email,
            proxy="socks5://127.0.0.1:7897",
            tags=["Google", "AI-Student"],
            metadata={"email": email},
            window_width=1024,
            window_height=768,
        )
        logger.info(f"创建环境: {auto.profile_id}")

        # 启动环境
        success, debug_port = auto.launch_env()
        if not success:
            logger.error("启动环境失败")
            update_progress(email, "failed", error="启动环境失败")
            return False

        logger.info(f"环境已启动, 调试端口: {debug_port}")

        # 连接浏览器
        browser = auto.connect_browser(debug_port)
        tab = browser.latest_tab

        # 访问 Google AI Student 页面
        target_url = "https://one.google.com/ai-student"
        logger.info(f"访问: {target_url}")
        tab.get(target_url)
        random_sleep(2, 4)
        logger.info(f"页面标题: {tab.title}")

        # 执行登录
        login_success = login_google(tab, account)

        # 等待登录完成
        random_sleep(3, 5)
        current_url = tab.url
        logger.info(f"当前页面: {current_url}")

        # 保存环境信息
        auto.save_info(
            name=email,
            tags=["Google", "AI-Student", "已登录" if login_success else "登录失败"],
            metadata={
                "email": email,
                "login_time": datetime.now().isoformat(),
                "url": current_url,
            },
        )
        logger.info("环境信息已保存")

        # 更新进度
        if login_success:
            update_progress(email, "success", profile_id=auto.profile_id or "")
            logger.info(f"✓ 账号 {email} 登录成功")
        else:
            update_progress(
                email, "failed", profile_id=auto.profile_id or "", error="登录流程异常"
            )
            logger.warning(f"✗ 账号 {email} 登录失败")

        # 断开连接，保持浏览器运行
        auto.disconnect()
        return login_success

    except Exception as e:
        logger.error(f"处理账号异常: {e}")
        update_progress(email, "failed", error=str(e))
        auto.disconnect()
        return False


def print_progress_summary():
    """打印进度汇总"""
    progress = load_progress()
    if not progress:
        logger.info("暂无进度记录")
        return

    logger.info(f"\n{'=' * 50}")
    logger.info("进度汇总")
    logger.info("=" * 50)

    success_count = 0
    failed_count = 0

    for email, info in progress.items():
        status = info["status"]
        if status == "success":
            success_count += 1
            logger.info(f"✓ {email} - 成功")
        else:
            failed_count += 1
            error = info.get("error", "未知错误")
            logger.info(f"✗ {email} - 失败: {error}")

    logger.info(f"\n总计: 成功 {success_count}, 失败 {failed_count}")


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("GeekEZ Browser - Google AI Student 批量登录")
    logger.info(f"源码路径: {SOURCE_PATH}")
    logger.info(f"账号配置: {ACCOUNTS_FILE}")
    logger.info(f"进度记录: {PROGRESS_FILE}")
    logger.info(f"日志文件: {LOG_FILE}")
    logger.info("=" * 50)

    # 加载账号
    accounts = load_accounts()
    if not accounts:
        logger.error("没有找到账号，请在 accounts.txt 中配置")
        exit(1)

    logger.info(f"共加载 {len(accounts)} 个账号")

    # 获取待处理账号
    pending = get_pending_accounts(accounts)
    logger.info(f"待处理: {len(pending)} 个")

    if not pending:
        logger.info("所有账号已处理完成")
        print_progress_summary()
        exit(0)

    # 启动应用
    auto = GeekezAutomation()
    if not auto.start_app():
        logger.error("启动应用失败")
        exit(1)

    # 批量处理
    for i, account in enumerate(pending):
        logger.info(f"\n[{i + 1}/{len(pending)}] 处理中...")
        process_single_account(auto, account)

        # 每个账号处理完后暂停，等待用户确认
        if i < len(pending) - 1:
            logger.info("\n" + "=" * 50)
            logger.info(f"当前账号处理完成: {account['email']}")
            logger.info(f"剩余账号: {len(pending) - i - 1} 个")
            logger.info("=" * 50)

            user_input = input("\n按回车继续下一个账号，输入 q 退出: ").strip().lower()
            if user_input == "q":
                logger.info("用户选择退出")
                break

            # 随机等待
            wait_time = random.randint(3, 8)
            logger.info(f"等待 {wait_time} 秒后处理下一个账号...")
            time.sleep(wait_time)

    # 打印汇总
    print_progress_summary()
    logger.info("全部处理完成!")

"""
OpenAI 协议注册机 (Protocol Keygen) v5 — 全流程纯 HTTP 实现
========================================================
协议注册机实现

核心架构（全流程纯 HTTP，零浏览器依赖）：

  【注册流程】全步骤纯 HTTP：
    步骤0：GET  /oauth/authorize         → 获取 login_session cookie（PKCE + screen_hint=signup）
    步骤0：POST /api/accounts/authorize/continue → 提交邮箱（需 sentinel token）
    步骤2：POST /api/accounts/user/register      → 注册用户（username+password，需 sentinel）
    步骤3：GET  /api/accounts/email-otp/send      → 触发验证码发送
    步骤4：POST /api/accounts/email-otp/validate  → 提交邮箱验证码
    步骤5：POST /api/accounts/create_account      → 提交姓名+生日完成注册

  【OAuth 登录流程】纯 HTTP（perform_codex_oauth_login_http）：
    步骤1：GET  /oauth/authorize                  → 获取 login_session
    步骤2：POST /api/accounts/authorize/continue   → 提交邮箱
    步骤3：POST /api/accounts/password/verify       → 提交密码
    步骤4：consent 多步流程 → 提取 code → POST /oauth/token 换取 tokens

  Sentinel Token PoW 生成（纯 Python，逆向 SDK JS 的 PoW 算法）：
    - FNV-1a 哈希 + xorshift 混合
    - 伪造浏览器环境数据数组
    - 暴力搜索直到哈希前缀 ≤ 难度阈值
    - t 字段传空字符串（服务端不校验），c 字段从 sentinel API 实时获取

关键协议字段（逆向还原）：
  - oai-client-auth-session: OAuth 流程中由服务端 Set-Cookie 设置的会话 cookie
  - openai-sentinel-token:   JSON 对象 {p, t, c, id, flow}
  - Cookie 链式传递:         每步 Set-Cookie 自动累积
  - oai-did:                 设备唯一标识（UUID v4）

环境依赖：
  pip install requests
"""

import json
import os
import re
import sys
import time
import uuid
import math
import random
import string
import secrets
import hashlib
import base64
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs, urlencode, quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# =================== 配置加载 ===================


def load_config():
    """加载外部配置文件"""
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "config.json"
    )
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            parsed = json.load(f)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


_config = load_config()

# 基础配置
TOTAL_ACCOUNTS = _config.get("total_accounts", 30)
CONCURRENT_WORKERS = _config.get("concurrent_workers", 1)  # 并发数（默认串行）
HEADLESS = _config.get("headless", False)  # 是否无头模式运行浏览器
PROXY = _config.get("proxy", "")

# 邮箱配置
EMAIL_PROVIDER = str(_config.get("email_provider", "mailtm")).strip().lower()
CF_WORKER_DOMAIN = _config.get("cf_worker_domain", "email.tuxixilax.cfd")
CF_EMAIL_DOMAIN = _config.get("cf_email_domain", "tuxixilax.cfd")
CF_ADMIN_PASSWORD = _config.get("cf_admin_password", "")
MAILTM_BASE_URL = _config.get("mailtm_base_url", "https://api.mail.tm")
MAILTM_DOMAIN = _config.get("mailtm_domain", "")

# OAuth 配置
OAUTH_ISSUER = _config.get("oauth_issuer", "https://auth.openai.com")
OAUTH_CLIENT_ID = _config.get("oauth_client_id", "app_EMoamEEZ73f0CkXaXp7hrann")
OAUTH_REDIRECT_URI = _config.get(
    "oauth_redirect_uri", "http://localhost:1455/auth/callback"
)

# 上传配置
UPLOAD_API_URL = _config.get("upload_api_url", "")
UPLOAD_API_TOKEN = _config.get("upload_api_token", "")

# 输出文件
ACCOUNTS_FILE = _config.get("accounts_file", "accounts.txt")
CSV_FILE = _config.get("csv_file", "registered_accounts.csv")
AK_FILE = _config.get("ak_file", "ak.txt")
RK_FILE = _config.get("rk_file", "rk.txt")

# 并发文件写入锁（多线程共享文件时防止数据竞争）
_file_lock = threading.Lock()

# OpenAI 认证域名
OPENAI_AUTH_BASE = "https://auth.openai.com"

# ChatGPT 域名（用于 OAuth 登录获取 Token）
CHATGPT_BASE = "https://chatgpt.com"


# =================== HTTP 会话管理 ===================


def create_session():
    """创建带重试策略的 HTTP 会话"""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    if PROXY:
        session.proxies = {"http": PROXY, "https": PROXY}
    return session


# 使用普通 session（全流程纯 HTTP，无需浏览器）


# =================== 工具函数 ===================

# 浏览器 UA（需与 sec-ch-ua 版本一致）
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)

# API 请求头模板（从 cURL 逆向提取）
COMMON_HEADERS = {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": OPENAI_AUTH_BASE,
    "user-agent": USER_AGENT,
    "sec-ch-ua": '"Google Chrome";v="145", "Not?A_Brand";v="8", "Chromium";v="145"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}

# 页面导航请求头（用于 GET 类请求）
NAVIGATE_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "user-agent": USER_AGENT,
    "sec-ch-ua": '"Google Chrome";v="145", "Not?A_Brand";v="8", "Chromium";v="145"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
}


def generate_device_id():
    """生成设备唯一标识（oai-did），UUID v4 格式"""
    return str(uuid.uuid4())


def generate_random_password(length=16):
    """生成符合 OpenAI 要求的随机密码"""
    chars = string.ascii_letters + string.digits + "!@#$%"
    pwd = list(
        random.choice(string.ascii_uppercase)
        + random.choice(string.ascii_lowercase)
        + random.choice(string.digits)
        + random.choice("!@#$%")
        + "".join(random.choice(chars) for _ in range(length - 4))
    )
    random.shuffle(pwd)
    return "".join(pwd)


def generate_random_name():
    """随机生成自然的英文姓名"""
    first = [
        "James",
        "Robert",
        "John",
        "Michael",
        "David",
        "William",
        "Richard",
        "Mary",
        "Jennifer",
        "Linda",
        "Elizabeth",
        "Susan",
        "Jessica",
        "Sarah",
        "Emily",
        "Emma",
        "Olivia",
        "Sophia",
        "Liam",
        "Noah",
        "Oliver",
        "Ethan",
    ]
    last = [
        "Smith",
        "Johnson",
        "Williams",
        "Brown",
        "Jones",
        "Garcia",
        "Miller",
        "Davis",
        "Wilson",
        "Anderson",
        "Thomas",
        "Taylor",
        "Moore",
        "Martin",
    ]
    return random.choice(first), random.choice(last)


def generate_random_birthday():
    """生成随机生日字符串，格式 YYYY-MM-DD（20~30岁）"""
    year = random.randint(1996, 2006)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{year:04d}-{month:02d}-{day:02d}"


def generate_datadog_trace():
    """生成 Datadog APM 追踪头（从 cURL 中逆向提取的格式）"""
    trace_id = str(random.getrandbits(64))
    parent_id = str(random.getrandbits(64))
    trace_hex = format(int(trace_id), "016x")
    parent_hex = format(int(parent_id), "016x")
    return {
        "traceparent": f"00-0000000000000000{trace_hex}-{parent_hex}-01",
        "tracestate": "dd=s:1;o:rum",
        "x-datadog-origin": "rum",
        "x-datadog-parent-id": parent_id,
        "x-datadog-sampling-priority": "1",
        "x-datadog-trace-id": trace_id,
    }


def generate_pkce():
    """生成 PKCE code_verifier 和 code_challenge"""
    code_verifier = (
        base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode("ascii")
    )
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


# =================== Sentinel Token 逆向生成 ===================
#
# 以下代码基于对 sentinel.openai.com 的 SDK JS 代码的逆向分析：
#   https://sentinel.openai.com/sentinel/20260124ceb8/sdk.js
#
# 核心算法：
#   1. _getConfig() → 收集浏览器环境数据（18个元素的数组）
#   2. _runCheck(startTime, seed, difficulty, config, nonce) → PoW 计算
#      a) config[3] = nonce（第4个元素设为当前尝试次数）
#      b) config[9] = performance.now() - startTime（耗时）
#      c) data = base64(JSON.stringify(config))
#      d) hash = fnv1a_32(seed + data)
#      e) 若 hash 的 hex 前缀 ≤ difficulty → 返回 data + "~S"
#   3. 最终 token = "gAAAAAB" + answer
#
# FNV-1a 32位哈希：
#   offset_basis = 2166136261
#   prime = 16777619
#   for each byte: hash ^= byte; hash = (hash * prime) >>> 0
#   然后做 xorshift 混合 + 转 8 位 hex
#


class SentinelTokenGenerator:
    """
    Sentinel Token 纯 Python 生成器

    通过逆向 sentinel SDK 的 PoW 算法，
    纯 Python 构造合法的 openai-sentinel-token。
    """

    MAX_ATTEMPTS = 500000  # 最大 PoW 尝试次数
    ERROR_PREFIX = "wQ8Lk5FbGpA2NcR9dShT6gYjU7VxZ4D"  # SDK 中的错误前缀常量

    def __init__(self, device_id=None):
        self.device_id = device_id or generate_device_id()
        self.requirements_seed = str(random.random())
        self.sid = str(uuid.uuid4())

    @staticmethod
    def _fnv1a_32(text):
        """
        FNV-1a 32位哈希算法（从 SDK JS 逆向还原）

        逆向来源：SDK 中的匿名函数，特征码：
          e = 2166136261  (FNV offset basis)
          e ^= t.charCodeAt(r)
          e = Math.imul(e, 16777619) >>> 0  (FNV prime)

        最后做 xorshift 混合（murmurhash3 风格的 finalizer）：
          e ^= e >>> 16
          e = Math.imul(e, 2246822507) >>> 0
          e ^= e >>> 13
          e = Math.imul(e, 3266489909) >>> 0
          e ^= e >>> 16
        """
        h = 2166136261  # FNV offset basis
        for ch in text:
            code = ord(ch)
            h ^= code
            # Math.imul(h, 16777619) >>> 0 模拟无符号32位乘法
            h = (h * 16777619) & 0xFFFFFFFF

        # xorshift 混合（murmurhash3 finalizer）
        h ^= h >> 16
        h = (h * 2246822507) & 0xFFFFFFFF
        h ^= h >> 13
        h = (h * 3266489909) & 0xFFFFFFFF
        h ^= h >> 16
        h = h & 0xFFFFFFFF

        # 转为8位 hex 字符串，左补零
        return format(h, "08x")

    def _get_config(self):
        """
        构造浏览器环境数据数组（_getConfig 方法逆向还原）

        SDK 中的元素对应关系（按索引）：
          [0]  screen.width + screen.height     → "1920x1080" 格式
          [1]  new Date().toString()             → 时间字符串
          [2]  performance.memory.jsHeapSizeLimit → 内存限制
          [3]  Math.random()                      → 随机数（后被 nonce 覆盖）
          [4]  navigator.userAgent                → UA
          [5]  随机 script src                    → 随机选一个页面 script 的 src
          [6]  脚本版本匹配                       → script src 匹配 c/[^/]*/_
          [7]  document.documentElement.data-build → 构建版本
          [8]  navigator.language                  → 语言
          [9]  navigator.languages.join(',')       → 语言列表（后被耗时覆盖）
          [10] Math.random()                       → 随机数
          [11] 随机 navigator 属性                 → 随机取 navigator 原型链上的一个属性
          [12] Object.keys(document) 随机一个       → document 属性
          [13] Object.keys(window) 随机一个         → window 属性
          [14] performance.now()                    → 高精度时间
          [15] self.sid                             → 会话标识 UUID
          [16] URLSearchParams 参数                 → URL 搜索参数
          [17] navigator.hardwareConcurrency        → CPU 核心数
          [18] performance.timeOrigin               → 时间起点
        """
        # 模拟真实的浏览器环境数据
        screen_info = f"1920x1080"
        now = datetime.now(timezone.utc)
        # 格式化为 JS Date.toString() 格式
        date_str = now.strftime(
            "%a %b %d %Y %H:%M:%S GMT+0000 (Coordinated Universal Time)"
        )
        js_heap_limit = 4294705152  # Chrome 典型值
        nav_random1 = random.random()
        ua = USER_AGENT
        # 模拟 sentinel SDK 的 script src
        script_src = "https://sentinel.openai.com/sentinel/20260124ceb8/sdk.js"
        # 匹配 c/[^/]*/_
        script_version = None
        data_build = None
        language = "en-US"
        languages = "en-US,en"
        nav_random2 = random.random()
        # 模拟随机 navigator 属性
        nav_props = [
            "vendorSub",
            "productSub",
            "vendor",
            "maxTouchPoints",
            "scheduling",
            "userActivation",
            "doNotTrack",
            "geolocation",
            "connection",
            "plugins",
            "mimeTypes",
            "pdfViewerEnabled",
            "webkitTemporaryStorage",
            "webkitPersistentStorage",
            "hardwareConcurrency",
            "cookieEnabled",
            "credentials",
            "mediaDevices",
            "permissions",
            "locks",
            "ink",
        ]
        nav_prop = random.choice(nav_props)
        # 模拟属性值
        nav_val = f"{nav_prop}−undefined"  # SDK 用 − (U+2212) 而非 - (U+002D)
        doc_key = random.choice(
            ["location", "implementation", "URL", "documentURI", "compatMode"]
        )
        win_key = random.choice(
            ["Object", "Function", "Array", "Number", "parseFloat", "undefined"]
        )
        perf_now = random.uniform(1000, 50000)
        hardware_concurrency = random.choice([4, 8, 12, 16])
        # 模拟 performance.timeOrigin（毫秒级 Unix 时间戳）
        time_origin = time.time() * 1000 - perf_now

        config = [
            screen_info,  # [0] 屏幕尺寸
            date_str,  # [1] 时间
            js_heap_limit,  # [2] 内存限制
            nav_random1,  # [3] 占位，后被 nonce 替换
            ua,  # [4] UserAgent
            script_src,  # [5] script src
            script_version,  # [6] 脚本版本
            data_build,  # [7] 构建版本
            language,  # [8] 语言
            languages,  # [9] 占位，后被耗时替换
            nav_random2,  # [10] 随机数
            nav_val,  # [11] navigator 属性
            doc_key,  # [12] document key
            win_key,  # [13] window key
            perf_now,  # [14] performance.now
            self.sid,  # [15] 会话 UUID
            "",  # [16] URL 参数
            hardware_concurrency,  # [17] CPU 核心数
            time_origin,  # [18] 时间起点
        ]
        return config

    @staticmethod
    def _base64_encode(data):
        """
        模拟 SDK 的 E() 函数：JSON.stringify → TextEncoder.encode → btoa
        """
        json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        encoded = json_str.encode("utf-8")
        return base64.b64encode(encoded).decode("ascii")

    def _run_check(self, start_time, seed, difficulty, config, nonce):
        """
        单次 PoW 检查（_runCheck 方法逆向还原）

        参数:
            start_time: 起始时间（秒）
            seed: PoW 种子字符串
            difficulty: 难度字符串（hex 前缀阈值）
            config: 环境配置数组
            nonce: 当前尝试序号

        返回:
            成功时返回 base64(config) + "~S"
            失败时返回 None
        """
        # 设置 nonce 和耗时
        config[3] = nonce
        config[9] = round((time.time() - start_time) * 1000)  # 毫秒

        # base64 编码环境数据
        data = self._base64_encode(config)

        # 计算 FNV-1a 哈希：hash(seed + data)
        hash_input = seed + data
        hash_hex = self._fnv1a_32(hash_input)

        # 难度校验：哈希前缀 ≤ 难度值
        diff_len = len(difficulty)
        if hash_hex[:diff_len] <= difficulty:
            return data + "~S"

        return None

    def generate_token(self, seed=None, difficulty=None):
        """
        生成 sentinel token（完整 PoW 流程）

        参数:
            seed: PoW 种子（来自服务端的 proofofwork.seed）
            difficulty: 难度值（来自服务端的 proofofwork.difficulty）

        返回:
            格式为 "gAAAAAB..." 的 sentinel token 字符串
        """
        # 如果没有服务端提供的 seed/difficulty，使用 requirements token 模式
        if seed is None:
            seed = self.requirements_seed
            difficulty = difficulty or "0"

        start_time = time.time()

        config = self._get_config()

        for i in range(self.MAX_ATTEMPTS):
            result = self._run_check(start_time, seed, difficulty, config, i)
            if result:
                elapsed = time.time() - start_time
                print(f"  ✅ PoW 完成: {i + 1} 次迭代, 耗时 {elapsed:.2f}s")
                return "gAAAAAB" + result

        # PoW 失败（超过最大尝试次数），返回错误 token
        print(f"  ⚠️ PoW 超过最大尝试次数 ({self.MAX_ATTEMPTS})")
        return "gAAAAAB" + self.ERROR_PREFIX + self._base64_encode(str(None))

    def generate_requirements_token(self):
        """
        生成 requirements token（不需要服务端参数）

        这是 SDK 中 getRequirementsToken() 的还原。
        用于不需要服务端 seed 的场景（如注册页面初始化）。
        """
        config = self._get_config()
        config[3] = 1
        config[9] = round(random.uniform(5, 50))  # 模拟小延迟
        data = self._base64_encode(config)
        return "gAAAAAC" + data  # 注意前缀是 C 不是 B


# =================== 临时邮箱（多提供商） ===================


def _normalize_mail_auth(provider, token):
    """统一邮箱鉴权结构，避免调用方依赖单一提供商字段。"""
    if not token:
        return None
    return {"provider": provider, "token": token}


def _resolve_mail_auth_token(mail_auth):
    """兼容旧字符串 token 和新 dict 结构。"""
    if isinstance(mail_auth, dict):
        return mail_auth.get("token", "")
    if isinstance(mail_auth, str):
        return mail_auth
    return ""


def _create_temp_email_cf_worker(session):
    """通过 Cloudflare Worker 创建临时邮箱。"""
    print("📧 创建临时邮箱（cf_worker）...")
    name_len = random.randint(10, 14)
    name_chars = list(random.choices(string.ascii_lowercase, k=name_len))
    for _ in range(random.choice([1, 2])):
        pos = random.randint(2, len(name_chars) - 1)
        name_chars.insert(pos, random.choice(string.digits))
    name = "".join(name_chars)

    try:
        res = session.post(
            f"https://{CF_WORKER_DOMAIN}/admin/new_address",
            json={"enablePrefix": True, "name": name, "domain": CF_EMAIL_DOMAIN},
            headers={
                "x-admin-auth": CF_ADMIN_PASSWORD,
                "Content-Type": "application/json",
            },
            timeout=10,
            verify=False,
        )
        if res.status_code == 200:
            data = res.json()
            email = data.get("address")
            token = data.get("jwt")
            if email:
                print(f"  ✅ 邮箱: {email}")
                return email, _normalize_mail_auth("cf_worker", token)
        print(f"  ❌ 创建失败: {res.status_code}")
    except Exception as e:
        print(f"  ❌ 异常: {e}")
    return None, None


def _create_temp_email_mailtm(session):
    """通过 Mail.tm 创建临时邮箱。"""
    print("📧 创建临时邮箱（mailtm）...")
    try:
        domain_resp = session.get(
            f"{MAILTM_BASE_URL}/domains", timeout=15, verify=False
        )
        if domain_resp.status_code != 200:
            print(f"  ❌ 获取 Mail.tm 域名失败: {domain_resp.status_code}")
            return None, None

        domains = domain_resp.json().get("hydra:member", [])
        if not domains:
            print("  ❌ Mail.tm 未返回可用域名")
            return None, None

        domain = MAILTM_DOMAIN
        if domain:
            if not any(
                d.get("domain") == domain for d in domains if isinstance(d, dict)
            ):
                print(f"  ⚠️ 配置域名 {domain} 不可用，改用默认域名")
                domain = ""
        if not domain:
            domain = (domains[0] or {}).get("domain", "")
        if not domain:
            print("  ❌ Mail.tm 域名为空")
            return None, None

        local_part = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=12)
        )
        email = f"{local_part}@{domain}"
        mailbox_password = "".join(
            random.choices(string.ascii_letters + string.digits, k=16)
        )

        create_resp = session.post(
            f"{MAILTM_BASE_URL}/accounts",
            json={"address": email, "password": mailbox_password},
            timeout=15,
            verify=False,
        )
        if create_resp.status_code not in (200, 201):
            print(
                f"  ❌ Mail.tm 创建账号失败: {create_resp.status_code} - {create_resp.text[:200]}"
            )
            return None, None

        token_resp = session.post(
            f"{MAILTM_BASE_URL}/token",
            json={"address": email, "password": mailbox_password},
            timeout=15,
            verify=False,
        )
        if token_resp.status_code != 200:
            print(
                f"  ❌ Mail.tm 获取 token 失败: {token_resp.status_code} - {token_resp.text[:200]}"
            )
            return None, None

        token = token_resp.json().get("token")
        if not token:
            print("  ❌ Mail.tm token 为空")
            return None, None

        print(f"  ✅ 邮箱: {email}")
        return email, _normalize_mail_auth("mailtm", token)
    except Exception as e:
        print(f"  ❌ Mail.tm 异常: {e}")
        return None, None


def create_temp_email(session):
    """创建临时邮箱（按 email_provider 切换）。"""
    if EMAIL_PROVIDER == "mailtm":
        return _create_temp_email_mailtm(session)
    return _create_temp_email_cf_worker(session)


def _fetch_emails_cf_worker(session, mail_auth):
    """获取 Cloudflare Worker 邮箱中的邮件。"""
    token = _resolve_mail_auth_token(mail_auth)
    if not token:
        return []
    try:
        res = session.get(
            f"https://{CF_WORKER_DOMAIN}/api/mails",
            params={"limit": 10, "offset": 0},
            headers={"Authorization": f"Bearer {token}"},
            verify=False,
            timeout=30,
        )
        if res.status_code == 200:
            return res.json().get("results", [])
    except Exception:
        pass
    return []


def _fetch_emails_mailtm(session, mail_auth):
    """获取 Mail.tm 邮箱中的邮件，并归一化结构。"""
    token = _resolve_mail_auth_token(mail_auth)
    if not token:
        return []

    headers = {"Authorization": f"Bearer {token}"}
    try:
        list_resp = session.get(
            f"{MAILTM_BASE_URL}/messages",
            headers=headers,
            verify=False,
            timeout=30,
        )
        if list_resp.status_code != 200:
            return []

        members = list_resp.json().get("hydra:member", [])
        emails = []
        for item in members:
            if not isinstance(item, dict):
                continue

            message_id = item.get("id")
            subject = item.get("subject", "")
            source = (item.get("from") or {}).get("address", "未知")
            raw_chunks = [subject, item.get("intro", "")]

            if message_id:
                detail_resp = session.get(
                    f"{MAILTM_BASE_URL}/messages/{message_id}",
                    headers=headers,
                    verify=False,
                    timeout=30,
                )
                if detail_resp.status_code == 200:
                    detail = detail_resp.json()
                    text_body = detail.get("text", "")
                    html_body = "\n".join(detail.get("html", []) or [])
                    if text_body:
                        raw_chunks.append(text_body)
                    if html_body:
                        raw_chunks.append(html_body)

            emails.append(
                {
                    "id": message_id,
                    "raw": "\n".join(chunk for chunk in raw_chunks if chunk),
                    "source": source,
                    "subject": subject,
                }
            )
        return emails
    except Exception:
        return []


def fetch_emails(session, email, mail_auth):
    """获取邮箱中的邮件。"""
    if EMAIL_PROVIDER == "mailtm":
        return _fetch_emails_mailtm(session, mail_auth)
    return _fetch_emails_cf_worker(session, mail_auth)


def extract_verification_code(content):
    """从邮件内容提取6位验证码"""
    if not content:
        return None
    # 策略1：HTML body 样式匹配
    m = re.search(
        r"background-color:\s*#F3F3F3[^>]*>[\s\S]*?(\d{6})[\s\S]*?</p>", content
    )
    if m:
        return m.group(1)
    # 策略2：Subject
    m = re.search(r"Subject:.*?(\d{6})", content)
    if m and m.group(1) != "177010":
        return m.group(1)
    # 策略3：通用正则
    for pat in [r">\s*(\d{6})\s*<", r"(?<![#&])\b(\d{6})\b"]:
        for code in re.findall(pat, content):
            if code != "177010":
                return code
    return None


def wait_for_verification_code(session, email, mail_auth, timeout=120):
    """等待验证邮件并提取验证码"""
    print(f"  ⏳ 等待验证码 (最大 {timeout}s)...")
    # 记录旧邮件 ID
    old_ids = set()
    old = fetch_emails(session, email, mail_auth)
    if old:
        old_ids = {e.get("id") for e in old if isinstance(e, dict) and "id" in e}
        print(f"    已有 {len(old_ids)} 封旧邮件")
        # 先检查旧邮件中是否已有验证码
        for item in old:
            if not isinstance(item, dict):
                continue
            raw = item.get("raw", "")
            code = extract_verification_code(raw)
            if code:
                print(f"  ✅ 从旧邮件中提取到验证码: {code}")
                return code

    start = time.time()
    poll_count = 0
    while time.time() - start < timeout:
        poll_count += 1
        emails = fetch_emails(session, email, mail_auth)
        if emails:
            if poll_count <= 3:
                print(f"    第{poll_count}次轮询: 收到 {len(emails)} 封邮件")
            for item in emails or []:
                if not isinstance(item, dict):
                    continue
                if item.get("id") in old_ids:
                    continue
                raw = item.get("raw", "")
                source = item.get("source", "未知")
                subject = item.get("subject", "无标题")
                print(f"    📩 新邮件: from={source[:40]}, subject={subject[:40]}")
                code = extract_verification_code(raw)
                if code:
                    print(f"  ✅ 验证码: {code}")
                    return code
                else:
                    print(f"    ⚠️ 未从此邮件中提取到验证码")
                    if raw:
                        print(f"    raw预览: {raw[:200]}")
        time.sleep(3)
    print("  ⏰ 等待验证码超时")
    return None


# =================== 协议注册核心流程（纯 HTTP，零浏览器） ===================


class ProtocolRegistrar:
    """
    协议注册机核心类 v3 — 纯 HTTP 实现

    架构：
      全部步骤均通过 requests 构造 HTTP 请求完成。
      Sentinel token 通过逆向的 PoW 算法纯 Python 生成。

    流程（基于浏览器抓包验证的真实 API 链）：
      步骤0:   OAuth 会话初始化 → 获取 login_session cookie（纯 HTTP 302 跟随）
      步骤1+2: 注册账号         → POST /api/accounts/user/register {username, password}
      步骤3:   触发验证码       → GET  /api/accounts/email-otp/send
      步骤4:   验证邮箱         → POST /api/accounts/email-otp/validate
      步骤5:   创建账号         → POST /api/accounts/create_account
    """

    def __init__(self):
        # HTTP 会话（全流程纯 HTTP，cookies 通过 302 跟随自动累积）
        self.session = create_session()
        self.device_id = generate_device_id()
        self.sentinel_gen = SentinelTokenGenerator(device_id=self.device_id)
        self.code_verifier = None
        self.state = None

    def _build_headers(self, referer, with_sentinel=False):
        """
        构造完整的 API 请求头

        参数:
            referer: 页面来源 URL
            with_sentinel: 是否附加 sentinel token
        """
        headers = dict(COMMON_HEADERS)
        headers["referer"] = referer
        headers["oai-device-id"] = self.device_id
        headers.update(generate_datadog_trace())

        if with_sentinel:
            token = self.sentinel_gen.generate_token()
            headers["openai-sentinel-token"] = token

        return headers

    def step0_init_oauth_session(self, email):
        """
        步骤0：OAuth 会话初始化 + 邮箱提交（纯 HTTP）

        已验证核心结论：auth.openai.com 的 API 端点不需要通过 Cloudflare Challenge，
        perform_codex_oauth_login_http() 已证明 GET /oauth/authorize → POST authorize/continue
        全链路纯 HTTP 可行。

        流程（2 步替代原浏览器 7 步）：
          1. GET /oauth/authorize?...&screen_hint=signup → 302 跟随获取 session cookies
          2. POST /api/accounts/authorize/continue       → 提交邮箱

        与 OAuth 登录的差异：
          - authorize URL 含 screen_hint=signup 和 prompt=login
          - authorize/continue body 含 screen_hint=signup（关键！指示注册流程）
          - referer: /create-account（而非 /log-in）
          - 后续步骤走 user/register 而非 password/verify

        参数:
            email: 注册用的邮箱地址
        返回:
            bool: 是否成功提交邮箱并建立 session
        """
        print("\n🔗 [步骤0] OAuth 会话初始化 + 邮箱提交（纯 HTTP，零浏览器）")

        # ===== 设置 oai-did cookie（两种 domain 格式兼容） =====
        self.session.cookies.set("oai-did", self.device_id, domain=".auth.openai.com")
        self.session.cookies.set("oai-did", self.device_id, domain="auth.openai.com")

        # ===== 生成 PKCE 参数 =====
        # 注意：ChatGPT Web client_id (DRivsnm2Mu42T3KOpqdtwB3NYviHYzwD) 在纯 HTTP 调用
        # /oauth/authorize 时被服务端拒绝（返回 AuthApiFailure），必须使用 Codex client_id。
        # screen_hint=signup 在 authorize/continue body 中指示注册流程。
        code_verifier, code_challenge = generate_pkce()
        self.code_verifier = code_verifier
        self.state = secrets.token_urlsafe(32)

        # authorize 参数（使用 Codex client_id + screen_hint=signup）
        authorize_params = {
            "response_type": "code",
            "client_id": OAUTH_CLIENT_ID,
            "redirect_uri": OAUTH_REDIRECT_URI,
            "scope": "openid profile email offline_access",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": self.state,
            "screen_hint": "signup",
            "prompt": "login",
        }

        authorize_url = (
            f"{OPENAI_AUTH_BASE}/oauth/authorize?{urlencode(authorize_params)}"
        )

        # ===== 步骤0a: GET /oauth/authorize → 获取 login_session cookie =====
        print("\n  --- [步骤0a] GET /oauth/authorize ---")
        try:
            resp = self.session.get(
                authorize_url,
                headers=NAVIGATE_HEADERS,
                allow_redirects=True,
                verify=False,
                timeout=30,
            )
            print(f"  步骤0a: {resp.status_code}")
        except Exception as e:
            print(f"  ❌ OAuth 授权请求失败: {e}")
            return False

        # 检查是否获取到 login_session cookie
        has_login_session = any(c.name == "login_session" for c in self.session.cookies)
        print(f"  login_session: {'✅ 已获取' if has_login_session else '❌ 未获取'}")
        if not has_login_session:
            print("  ⚠️ 未获得 login_session cookie，后续步骤可能失败")
            # 打印响应内容片段用于诊断
            print(f"  响应预览: {resp.text[:300]}")
            return False

        # ===== 步骤0b: POST /api/accounts/authorize/continue → 提交邮箱 =====
        print("\n  --- [步骤0b] POST /api/accounts/authorize/continue ---")

        # 构造请求头（参考 perform_codex_oauth_login_http 的步骤2）
        headers = dict(COMMON_HEADERS)
        headers["referer"] = (
            f"{OPENAI_AUTH_BASE}/create-account"  # 注册流程用 /create-account
        )
        headers["oai-device-id"] = self.device_id
        headers.update(generate_datadog_trace())

        # 获取 authorize_continue 的 sentinel token
        sentinel_token = build_sentinel_token(
            self.session, self.device_id, flow="authorize_continue"
        )
        if not sentinel_token:
            print("  ❌ 无法获取 authorize_continue 的 sentinel token")
            return False
        headers["openai-sentinel-token"] = sentinel_token

        try:
            resp = self.session.post(
                f"{OPENAI_AUTH_BASE}/api/accounts/authorize/continue",
                json={
                    "username": {"kind": "email", "value": email},
                    "screen_hint": "signup",
                },
                headers=headers,
                verify=False,
                timeout=30,
            )
        except Exception as e:
            print(f"  ❌ 邮箱提交失败: {e}")
            return False

        if resp.status_code != 200:
            print(f"  ❌ 邮箱提交失败: HTTP {resp.status_code}")
            return False

        try:
            data = resp.json()
            page_type = data.get("page", {}).get("type", "")
        except Exception:
            page_type = "?"
        print(f"  步骤0b: {resp.status_code} → {page_type}")

        return True

    def step1_visit_create_account(self):
        """步骤1：访问注册页面（建立前端路由状态）"""
        url = f"{OPENAI_AUTH_BASE}/create-account"
        headers = dict(NAVIGATE_HEADERS)
        headers["referer"] = f"{OPENAI_AUTH_BASE}/authorize"
        resp = self.session.get(
            url, headers=headers, verify=False, timeout=30, allow_redirects=True
        )
        return resp.status_code == 200

    def step2_register_user(self, email, password):
        """
        步骤2：注册用户（邮箱+密码一次性提交）

        POST /api/accounts/user/register

        基于浏览器抓包确认的真实请求格式：
        请求体：{"username": "xxx@xxx.com", "password": "xxx"}

        注意：
        - 邮箱字段名是 'username' 而非 'email'（已通过抓包验证）
        - 此端点可能需要 sentinel token（通过请求头传递）
        """
        print(f"\n🔑 [步骤2-HTTP] 注册用户: {email}")

        url = f"{OPENAI_AUTH_BASE}/api/accounts/user/register"
        headers = self._build_headers(
            referer=f"{OPENAI_AUTH_BASE}/create-account/password",
            with_sentinel=True,
        )
        # 浏览器抓包确认的请求格式：username + password
        payload = {
            "username": email,
            "password": password,
        }
        resp = self.session.post(
            url, json=payload, headers=headers, verify=False, timeout=30
        )

        if resp.status_code == 200:
            print("  ✅ 注册成功")
            return True
        else:
            print(f"  ❌ 失败: {resp.text[:300]}")
            # 某些 302 重定向也算成功
            if resp.status_code in (301, 302):
                redirect_url = resp.headers.get("Location", "")
                print(f"  ℹ️ 重定向到: {redirect_url[:100]}")
                if "email-otp" in redirect_url or "email-verification" in redirect_url:
                    return True
            return False

    def step3_send_otp(self):
        """
        步骤3：触发验证码发送（HTTP GET 页面导航请求）
        GET /api/accounts/email-otp/send
        GET /email-verification

        这两个都是 GET 请求，不需要 sentinel token。
        """
        print("\n📬 [步骤3-HTTP] 触发验证码发送")

        # 3a: 请求 send 端点（触发邮件发送）
        url_send = f"{OPENAI_AUTH_BASE}/api/accounts/email-otp/send"
        headers = dict(NAVIGATE_HEADERS)
        headers["referer"] = f"{OPENAI_AUTH_BASE}/create-account/password"

        resp = self.session.get(
            url_send, headers=headers, verify=False, timeout=30, allow_redirects=True
        )
        print(f"  send 状态码: {resp.status_code}")

        # 3b: 请求 email-verification 页面（获取后续 cookie）
        url_verify = f"{OPENAI_AUTH_BASE}/email-verification"
        headers["referer"] = f"{OPENAI_AUTH_BASE}/create-account/password"

        resp = self.session.get(
            url_verify, headers=headers, verify=False, timeout=30, allow_redirects=True
        )
        print(f"  email-verification 状态码: {resp.status_code}")
        print("  ✅ 验证码发送触发完成")
        return True

    def step4_validate_otp(self, code):
        """
        步骤4：提交邮箱验证码（HTTP POST）
        POST /api/accounts/email-otp/validate

        从 cURL 分析确认：此步骤不需要 sentinel token。
        """
        print(f"\n🔢 [步骤4-HTTP] 验证邮箱 OTP: {code}")
        url = f"{OPENAI_AUTH_BASE}/api/accounts/email-otp/validate"
        headers = self._build_headers(
            referer=f"{OPENAI_AUTH_BASE}/email-verification",
        )
        payload = {"code": code}

        resp = self.session.post(
            url, json=payload, headers=headers, verify=False, timeout=30
        )
        print(f"  状态码: {resp.status_code}")

        if resp.status_code == 200:
            print("  ✅ 邮箱验证成功")
            return True
        else:
            print(f"  ❌ 失败: {resp.text[:300]}")
            return False

    def step5_create_account(self, first_name, last_name, birthdate):
        """
        步骤5：提交姓名 + 生日完成注册（HTTP POST）
        POST /api/accounts/create_account
        """
        print(f"\n📝 [步骤5-HTTP] 创建账号（{first_name} {last_name}, {birthdate}）")
        url = f"{OPENAI_AUTH_BASE}/api/accounts/create_account"
        headers = self._build_headers(
            referer=f"{OPENAI_AUTH_BASE}/about-you",
        )
        payload = {
            "name": f"{first_name} {last_name}",
            "birthdate": birthdate,
        }

        resp = self.session.post(
            url, json=payload, headers=headers, verify=False, timeout=30
        )
        print(f"  状态码: {resp.status_code}")

        if resp.status_code == 200:
            print("  ✅ 账号创建完成！")
            return True
        elif resp.status_code == 403 and "sentinel" in resp.text.lower():
            print("  ⚠️ 需要 sentinel token，重试...")
            # 带 sentinel 重试
            headers["openai-sentinel-token"] = self.sentinel_gen.generate_token()
            resp = self.session.post(
                url, json=payload, headers=headers, verify=False, timeout=30
            )
            if resp.status_code == 200:
                print("  ✅ 账号创建完成（带 sentinel 重试成功）！")
                return True
            print(f"  ❌ 重试仍失败: {resp.text[:300]}")
            return False
        else:
            print(f"  ❌ 失败: {resp.text[:300]}")
            if resp.status_code in (301, 302):
                print("  ℹ️ 收到重定向，可能已成功")
                return True
            return False

    def register(self, email, mail_auth, password):
        """
        执行完整的注册流程（全 6 步纯 HTTP）
        """
        first_name, last_name = generate_random_name()
        birthdate = generate_random_birthday()

        print(f"\n� 注册: {email}")

        try:
            # ===== 步骤0：OAuth 会话初始化 + 邮箱提交（纯 HTTP）=====
            if not self.step0_init_oauth_session(email):
                print("❌ 步骤0失败：OAuth 会话初始化失败")
                return False, email, password

            time.sleep(1)

            # 注意：邮箱已在步骤0中通过 POST authorize/continue 提交完成
            # 步骤2提交用户名（邮箱）+ 密码完成注册
            if not self.step2_register_user(email, password):
                print("❌ 步骤2失败：用户注册失败")
                return False, email, password

            time.sleep(1)

            # ===== 步骤3：触发验证码发送 =====
            self.step3_send_otp()

            # 等待验证码（通过邮箱提供商 API）
            mail_session = create_session()  # 用独立会话访问邮箱 API
            code = wait_for_verification_code(mail_session, email, mail_auth)
            if not code:
                print("❌ 未收到验证码")
                return False, email, password

            # ===== 步骤4：验证 OTP =====
            if not self.step4_validate_otp(code):
                return False, email, password

            time.sleep(1)

            # ===== 步骤5：创建账号 =====
            if not self.step5_create_account(first_name, last_name, birthdate):
                return False, email, password

            print("\n🎉 注册成功！")
            return True, email, password

        except Exception as e:
            print(f"\n❌ 注册异常: {e}")
            import traceback

            traceback.print_exc()
            return False, email, password


# =================== Sentinel API（纯 HTTP 获取 c 字段） ===================


def fetch_sentinel_challenge(session, device_id, flow="authorize_continue"):
    """
    调用 sentinel 后端 API 获取 challenge 数据（c 字段 + PoW 参数）

    请求目标：POST https://sentinel.openai.com/backend-api/sentinel/req
    该端点不需要任何 cookies，直接用 requests 调用即可。

    参数:
        session: requests.Session 实例
        device_id: 设备 ID（UUID v4）
        flow: 业务流类型（"authorize_continue" 或 "password_verify"）
    返回:
        dict: 包含 token(c), proofofwork.seed/difficulty；失败返回 None
    """
    # 生成 requirements token 作为请求体的 p 字段
    gen = SentinelTokenGenerator(device_id=device_id)
    p_token = gen.generate_requirements_token()

    req_body = {
        "p": p_token,
        "id": device_id,
        "flow": flow,
    }

    headers = {
        "Content-Type": "text/plain;charset=UTF-8",
        "Referer": "https://sentinel.openai.com/backend-api/sentinel/frame.html",
        "User-Agent": USER_AGENT,
        "Origin": "https://sentinel.openai.com",
        "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    try:
        resp = session.post(
            "https://sentinel.openai.com/backend-api/sentinel/req",
            data=json.dumps(req_body),
            headers=headers,
            timeout=15,
            verify=False,
        )
        if resp.status_code != 200:
            print(f"  ❌ sentinel API 返回 {resp.status_code}: {resp.text[:200]}")
            return None
        return resp.json()
    except Exception as e:
        print(f"  ❌ sentinel API 调用异常: {e}")
        return None


def build_sentinel_token(session, device_id, flow="authorize_continue"):
    """
    构建完整的 openai-sentinel-token JSON 字符串（纯 Python，零浏览器）

    核心结论（已验证）：
      - t 字段传空字符串即可（服务端不校验）
      - c 字段从 POST /backend-api/sentinel/req 实时获取
      - p 字段用服务端返回的 seed/difficulty 重新计算 PoW

    参数:
        session: requests.Session 实例
        device_id: 设备 ID
        flow: 业务流类型
    返回:
        str: JSON 字符串格式的 sentinel token；失败返回 None
    """
    challenge = fetch_sentinel_challenge(session, device_id, flow)
    if not challenge:
        return None

    c_value = challenge.get("token", "")
    pow_data = challenge.get("proofofwork", {})
    gen = SentinelTokenGenerator(device_id=device_id)

    if pow_data.get("required") and pow_data.get("seed"):
        p_value = gen.generate_token(
            seed=pow_data["seed"], difficulty=pow_data.get("difficulty", "0")
        )
    else:
        p_value = gen.generate_requirements_token()

    sentinel_token = json.dumps(
        {
            "p": p_value,
            "t": "",
            "c": c_value,
            "id": device_id,
            "flow": flow,
        }
    )
    return sentinel_token


def perform_codex_oauth_login_http(
    email, password, registrar_session=None, mail_auth=None
):
    """
    纯 HTTP 方式执行 Codex OAuth 登录获取 Token（零浏览器）。

    已验证的纯 HTTP OAuth 流程（4~5 步）：
      步骤1: GET  /oauth/authorize       → 获取 login_session cookie
      步骤2: POST /api/accounts/authorize/continue  → 提交邮箱
      步骤3: POST /api/accounts/password/verify      → 提交密码
      步骤3.5: （可选）邮箱验证 — 新注册账号首次登录时触发
      步骤4: GET  consent URL → 302 重定向提取 code → POST /oauth/token 换取 tokens

    参数:
        email: 登录邮箱
        password: 登录密码
        registrar_session: 注册时的 session（可选，本模式未使用）
        mail_auth: 邮箱鉴权信息（用于接收 OTP 验证码，新注册账号首次登录时需要）
    返回:
        dict: tokens 字典（含 access_token/refresh_token/id_token），失败返回 None
    """
    print("\n🔐 执行 Codex OAuth 登录（纯 HTTP 模式）...")

    session = create_session()
    device_id = generate_device_id()

    # 在 session 中设置 oai-did cookie（两种 domain 格式兼容）
    session.cookies.set("oai-did", device_id, domain=".auth.openai.com")
    session.cookies.set("oai-did", device_id, domain="auth.openai.com")

    # 生成 PKCE 参数和 state
    code_verifier, code_challenge = generate_pkce()
    state = secrets.token_urlsafe(32)

    authorize_params = {
        "response_type": "code",
        "client_id": OAUTH_CLIENT_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "scope": "openid profile email offline_access",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    authorize_url = f"{OAUTH_ISSUER}/oauth/authorize?{urlencode(authorize_params)}"

    # ===== 步骤1: GET /oauth/authorize =====
    try:
        resp = session.get(
            authorize_url,
            headers=NAVIGATE_HEADERS,
            allow_redirects=True,
            verify=False,
            timeout=30,
        )
        print(f"  状态码: {resp.status_code}")
        print(f"  最终URL: {resp.url[:120]}")
    except Exception as e:
        print(f"  ❌ OAuth 授权请求失败: {e}")
        return None

    has_login_session = any(c.name == "login_session" for c in session.cookies)
    if not has_login_session:
        print("  ⚠️ 未获得 login_session")

    # ===== 步骤2: POST authorize/continue =====

    # 构造请求头（参考 test_oauth_quick.py）
    headers = dict(COMMON_HEADERS)
    headers["referer"] = f"{OAUTH_ISSUER}/log-in"
    headers["oai-device-id"] = device_id
    headers.update(generate_datadog_trace())

    # 获取 authorize_continue 的 sentinel token
    sentinel_email = build_sentinel_token(session, device_id, flow="authorize_continue")
    if not sentinel_email:
        print("  ❌ 无法获取 authorize_continue 的 sentinel token")
        return None
    headers["openai-sentinel-token"] = sentinel_email

    try:
        resp = session.post(
            f"{OAUTH_ISSUER}/api/accounts/authorize/continue",
            json={"username": {"kind": "email", "value": email}},
            headers=headers,
            verify=False,
            timeout=30,
        )
        print(f"  步骤2: {resp.status_code}")
    except Exception as e:
        print(f"  ❌ 邮箱提交失败: {e}")
        return None

    if resp.status_code != 200:
        print("  ❌ 邮箱提交失败")
        return None

    try:
        data = resp.json()
        page_type = data.get("page", {}).get("type", "")
    except Exception:
        pass

    # ===== 步骤3: POST password/verify =====

    headers["referer"] = f"{OAUTH_ISSUER}/log-in/password"
    headers.update(generate_datadog_trace())

    # 获取 password_verify 的 sentinel token（每个 flow 需要独立的 token）
    sentinel_pwd = build_sentinel_token(session, device_id, flow="password_verify")
    if not sentinel_pwd:
        print("  ❌ 无法获取 password_verify 的 sentinel token")
        return None
    headers["openai-sentinel-token"] = sentinel_pwd

    try:
        resp = session.post(
            f"{OAUTH_ISSUER}/api/accounts/password/verify",
            json={"password": password},
            headers=headers,
            verify=False,
            timeout=30,
            allow_redirects=False,
        )
        print(f"  步骤3: {resp.status_code} → {page_type}")
    except Exception as e:
        print(f"  ❌ 密码提交失败: {e}")
        return None

    if resp.status_code != 200:
        print("  ❌ 密码验证失败")
        return None

    continue_url = None
    try:
        data = resp.json()
        continue_url = data.get("continue_url", "")
        page_type = data.get("page", {}).get("type", "")
    except Exception:
        page_type = ""

    if not continue_url:
        print("  ❌ 未获取到 continue_url")
        return None

    # ===== 步骤3.5: 邮箱验证（新注册账号首次登录时可能触发） =====
    if page_type == "email_otp_verification" or "email-verification" in continue_url:
        print("\n  --- [步骤3.5] 邮箱验证（新注册账号首次登录） ---")

        if not mail_auth:
            print("  ❌ 无 mail_auth，无法接收验证码")
            return None

        mail_session = create_session()

        # 关键认知：当 password/verify 返回 email_otp_verification 时，
        # 服务端已经自动发送了 OTP 邮件！立即开始轮询检查。

        # 记录初始邮件数量（注册阶段的）
        initial_emails = fetch_emails(mail_session, email, mail_auth)
        initial_count = len(initial_emails) if initial_emails else 0

        # 轮询等待邮件到达，收集所有验证码并依次尝试
        print(f"  ⏳ 开始监视邮箱（当前 {initial_count} 封）...")
        code = None
        tried_codes = set()  # 已尝试过的验证码，避免重复提交
        start_time = time.time()

        h_val = dict(COMMON_HEADERS)
        h_val["referer"] = f"{OAUTH_ISSUER}/email-verification"
        h_val["oai-device-id"] = device_id
        h_val.update(generate_datadog_trace())

        while time.time() - start_time < 120:
            all_emails = fetch_emails(mail_session, email, mail_auth)
            if not all_emails:
                time.sleep(2)
                continue

            # 收集所有唯一验证码（保持顺序，API 最新在前）
            all_codes = []
            for e_item in all_emails:
                if isinstance(e_item, dict):
                    c = extract_verification_code(e_item.get("raw", ""))
                    if c and c not in tried_codes:
                        all_codes.append(c)

            if not all_codes:
                time.sleep(2)
                continue

            # 依次尝试每个未试过的验证码
            for try_code in all_codes:
                tried_codes.add(try_code)
                print(f"  🔢 尝试验证码: {try_code}")
                resp = session.post(
                    f"{OAUTH_ISSUER}/api/accounts/email-otp/validate",
                    json={"code": try_code},
                    headers=h_val,
                    verify=False,
                    timeout=30,
                )
                if resp.status_code == 200:
                    code = try_code
                    print(f"  ✅ 验证码 {code} 验证通过！")
                    try:
                        data = resp.json()
                        continue_url = data.get("continue_url", "")
                        page_type = data.get("page", {}).get("type", "")
                        print(f"  continue_url: {continue_url}")
                        print(f"  page.type: {page_type}")
                    except Exception:
                        pass
                    break
                else:
                    print(f"  ❌ 验证码 {try_code} 失败: {resp.status_code}")

            if code:
                break
            time.sleep(2)

        if not code:
            print("  ❌ 验证码等待超时")
            return None

        # 如果验证后进入 about-you（填写姓名生日），需要处理
        if "about-you" in continue_url:
            print("  📝 处理 about-you 步骤...")

            # 先 GET about-you 页面（服务端可能因账号已存在而跳转 consent）
            h_about = dict(NAVIGATE_HEADERS)
            h_about["referer"] = f"{OAUTH_ISSUER}/email-verification"
            resp_about = session.get(
                f"{OAUTH_ISSUER}/about-you",
                headers=h_about,
                verify=False,
                timeout=30,
                allow_redirects=True,
            )
            print(
                f"  GET about-you: {resp_about.status_code}, URL: {resp_about.url[:80]}"
            )

            # 检查是否已经跳转到 consent（说明账号已存在，跳过 about-you）
            if "consent" in resp_about.url or "organization" in resp_about.url:
                continue_url = resp_about.url
                print(f"  ✅ 已跳转到 consent: {continue_url}")
            else:
                # 尝试 POST create_account
                import random

                first_names = ["James", "Mary", "John", "Linda", "Robert", "Sarah"]
                last_names = [
                    "Smith",
                    "Johnson",
                    "Williams",
                    "Brown",
                    "Jones",
                    "Wilson",
                ]
                name = f"{random.choice(first_names)} {random.choice(last_names)}"
                year = random.randint(1995, 2002)
                month = random.randint(1, 12)
                day = random.randint(1, 28)
                birthdate = f"{year}-{month:02d}-{day:02d}"

                h_create = dict(COMMON_HEADERS)
                h_create["referer"] = f"{OAUTH_ISSUER}/about-you"
                h_create["oai-device-id"] = device_id
                h_create.update(generate_datadog_trace())
                resp_create = session.post(
                    f"{OAUTH_ISSUER}/api/accounts/create_account",
                    json={"name": name, "birthdate": birthdate},
                    headers=h_create,
                    verify=False,
                    timeout=30,
                )
                print(f"  create_account: {resp_create.status_code}")

                if resp_create.status_code == 200:
                    try:
                        data = resp_create.json()
                        continue_url = data.get("continue_url", "")
                        print(f"  ✅ 个人信息已提交，continue_url: {continue_url}")
                    except Exception:
                        pass
                elif (
                    resp_create.status_code == 400
                    and "already_exists" in resp_create.text
                ):
                    # 账号已存在（注册时已创建），直接跳到 consent
                    print("  ⚠️ 账号已存在，直接跳转 consent 页面...")
                    continue_url = f"{OAUTH_ISSUER}/sign-in-with-chatgpt/codex/consent"
                else:
                    print(f"  ⚠️ create_account 失败: {resp_create.text[:200]}")

        # consent 直接返回的情况（page.type 已经是 consent）
        if "consent" in page_type:
            continue_url = f"{OAUTH_ISSUER}/sign-in-with-chatgpt/codex/consent"

        if not continue_url or "email-verification" in continue_url:
            print("  ❌ 邮箱验证后未获取到 consent URL")
            return None

    # ===== 步骤4: consent 多步流程 → 提取 authorization code → 换 token =====
    #
    # 逆向分析结果（consent 页面的 React Router route-D83ftS1Y.js）：
    #   clientLoader: 从 oai-client-auth-session cookie 中读取 workspaces
    #   clientAction: POST /api/accounts/workspace/select → {"workspace_id": "..."}
    #   然后从响应的 data.orgs 中提取 org，POST organization/select
    #   最终通过重定向链获取 authorization code
    #
    print("\n  --- [步骤4] consent 多步流程 → 提取 code ---")

    # consent URL 可能是相对路径，拼接完整 URL
    if continue_url.startswith("/"):
        consent_url = f"{OAUTH_ISSUER}{continue_url}"
    else:
        consent_url = continue_url
    print(f"  consent URL: {consent_url}")

    # ----- 辅助：从 URL 提取 code -----
    def _extract_code_from_url(url):
        if not url or "code=" not in url:
            return None
        try:
            return parse_qs(urlparse(url).query).get("code", [None])[0]
        except Exception:
            return None

    # ----- 辅助：从 oai-client-auth-session cookie 解码 JSON -----
    def _decode_auth_session(session_obj):
        """
        oai-client-auth-session 是 Flask/itsdangerous 格式：
        base64(json).timestamp.signature
        第一段 base64 解码后就是 JSON，包含 workspaces/orgs/projects 等核心数据
        """
        for c in session_obj.cookies:
            if c.name == "oai-client-auth-session":
                val = c.value
                first_part = val.split(".")[0] if "." in val else val
                # 补齐 base64 padding
                pad = 4 - len(first_part) % 4
                if pad != 4:
                    first_part += "=" * pad
                try:
                    import base64

                    raw = base64.urlsafe_b64decode(first_part)
                    return json.loads(raw.decode("utf-8"))
                except Exception:
                    pass
        return None

    # ----- 辅助：从 302 Location 或 ConnectionError 中提取 code -----
    def _follow_and_extract_code(session_obj, url, max_depth=10):
        """跟随 URL，从 302 Location 或 ConnectionError 中提取 code"""
        if max_depth <= 0:
            return None
        try:
            r = session_obj.get(
                url,
                headers=NAVIGATE_HEADERS,
                verify=False,
                timeout=15,
                allow_redirects=False,
            )
            if r.status_code in (301, 302, 303, 307, 308):
                loc = r.headers.get("Location", "")
                code = _extract_code_from_url(loc)
                if code:
                    return code
                # 不包含 code，继续跟踪
                if loc.startswith("/"):
                    loc = f"{OAUTH_ISSUER}{loc}"
                return _follow_and_extract_code(session_obj, loc, max_depth - 1)
            elif r.status_code == 200:
                return _extract_code_from_url(r.url)
        except requests.exceptions.ConnectionError as e:
            # 预期：localhost 连接失败，从错误信息中提取回调 URL
            url_match = re.search(r'(https?://localhost[^\s\'"]+)', str(e))
            if url_match:
                return _extract_code_from_url(url_match.group(1))
        except Exception:
            pass
        return None

    auth_code = None

    # ----- 步骤4a: GET consent 页面（设置 cookies + 触发服务端状态更新） -----
    print("  [4a] GET consent 页面...")
    consent_html = ""
    try:
        resp = session.get(
            consent_url,
            headers=NAVIGATE_HEADERS,
            verify=False,
            timeout=30,
            allow_redirects=False,
        )

        # 如果直接 302 带 code（少数情况）
        if resp.status_code in (301, 302, 303, 307, 308):
            loc = resp.headers.get("Location", "")
            auth_code = _extract_code_from_url(loc)
            if auth_code:
                print(f"  ✅ consent 直接 302 获取到 code（长度: {len(auth_code)}）")
            else:
                # 继续跟踪重定向
                auth_code = _follow_and_extract_code(session, loc)
                if auth_code:
                    print(f"  ✅ consent 302 跟踪获取到 code（长度: {len(auth_code)}）")
        elif resp.status_code == 200:
            consent_html = resp.text
            print(f"  ✅ consent 页面已加载（HTML {len(consent_html)} 字节）")
    except requests.exceptions.ConnectionError as e:
        # 可能直接被重定向到 localhost
        url_match = re.search(r'(https?://localhost[^\s\'"]+)', str(e))
        if url_match:
            auth_code = _extract_code_from_url(url_match.group(1))
            if auth_code:
                print(f"  ✅ consent ConnectionError 中获取到 code")
    except Exception as e:
        print(f"  ⚠️ consent 请求异常: {e}")

    # ----- 步骤4b: 从 cookie 提取 workspace_id，POST workspace/select -----
    if not auth_code:
        print("  [4b] 解码 session → 提取 workspace_id...")
        session_data = _decode_auth_session(session)

        workspace_id = None
        if session_data:
            # 打印 session 中的所有 key，便于调试
            print(f"  session keys: {list(session_data.keys())}")
            workspaces = session_data.get("workspaces", [])
            if workspaces:
                workspace_id = workspaces[0].get("id")
                ws_kind = workspaces[0].get("kind", "?")
                print(f"  ✅ workspace_id: {workspace_id} (kind: {ws_kind})")
            else:
                print(f"  ⚠️ session 中无 workspaces 数据")
                # 打印 session 完整内容供调试
                print(
                    f"  session 完整内容: {json.dumps(session_data, indent=2)[:1500]}"
                )
        else:
            print(f"  ⚠️ 无法解码 oai-client-auth-session cookie")

        if workspace_id:
            print(f"  [4b] POST workspace/select...")
            h_consent = dict(COMMON_HEADERS)
            h_consent["referer"] = consent_url
            h_consent["oai-device-id"] = device_id
            h_consent.update(generate_datadog_trace())

            try:
                resp = session.post(
                    f"{OAUTH_ISSUER}/api/accounts/workspace/select",
                    json={"workspace_id": workspace_id},
                    headers=h_consent,
                    verify=False,
                    timeout=30,
                    allow_redirects=False,
                )
                print(f"  状态码: {resp.status_code}")

                if resp.status_code in (301, 302, 303, 307, 308):
                    auth_code = _extract_code_from_url(resp.headers.get("Location", ""))
                    if auth_code:
                        print(
                            f"  ✅ workspace/select 302 获取到 code（长度: {len(auth_code)}）"
                        )
                elif resp.status_code == 200:
                    ws_data = resp.json()
                    ws_next = ws_data.get("continue_url", "")
                    ws_page = ws_data.get("page", {}).get("type", "")
                    print(f"  continue_url: {ws_next}")
                    print(f"  page.type: {ws_page}")

                    # ----- 步骤4c: organization/select -----
                    if "organization" in ws_next or "organization" in ws_page:
                        org_url = (
                            ws_next
                            if ws_next.startswith("http")
                            else f"{OAUTH_ISSUER}{ws_next}"
                        )
                        print(f"  [4c] 准备 organization/select...")

                        # org_id 和 project_id 在 workspace/select 响应的 data.orgs 中
                        org_id = None
                        project_id = None
                        ws_orgs = ws_data.get("data", {}).get("orgs", [])
                        if ws_orgs and len(ws_orgs) > 0:
                            org_id = ws_orgs[0].get("id")
                            projects = ws_orgs[0].get("projects", [])
                            if projects:
                                project_id = projects[0].get("id")
                            print(f"  ✅ org_id: {org_id}")
                            print(f"  ✅ project_id: {project_id}")

                        if org_id:
                            print(f"  [4c] POST organization/select...")
                            body = {"org_id": org_id}
                            if project_id:
                                body["project_id"] = project_id

                            h_org = dict(COMMON_HEADERS)
                            h_org["referer"] = org_url
                            h_org["oai-device-id"] = device_id
                            h_org.update(generate_datadog_trace())

                            resp = session.post(
                                f"{OAUTH_ISSUER}/api/accounts/organization/select",
                                json=body,
                                headers=h_org,
                                verify=False,
                                timeout=30,
                                allow_redirects=False,
                            )
                            print(f"  状态码: {resp.status_code}")

                            if resp.status_code in (301, 302, 303, 307, 308):
                                loc = resp.headers.get("Location", "")
                                auth_code = _extract_code_from_url(loc)
                                if auth_code:
                                    print(
                                        f"  ✅ organization/select 获取到 code（长度: {len(auth_code)}）"
                                    )
                                else:
                                    # 继续跟踪重定向链
                                    auth_code = _follow_and_extract_code(session, loc)
                                    if auth_code:
                                        print(
                                            f"  ✅ 跟踪重定向获取到 code（长度: {len(auth_code)}）"
                                        )
                            elif resp.status_code == 200:
                                org_data = resp.json()
                                org_next = org_data.get("continue_url", "")
                                print(f"  org continue_url: {org_next}")
                                if org_next:
                                    full_next = (
                                        org_next
                                        if org_next.startswith("http")
                                        else f"{OAUTH_ISSUER}{org_next}"
                                    )
                                    auth_code = _follow_and_extract_code(
                                        session, full_next
                                    )
                                    if auth_code:
                                        print(
                                            f"  ✅ 跟踪获取到 code（长度: {len(auth_code)}）"
                                        )
                        else:
                            print(f"  ⚠️ 未找到 org_id，尝试直接跟踪 consent URL...")
                            auth_code = _follow_and_extract_code(session, org_url)
                            if auth_code:
                                print(
                                    f"  ✅ 直接跟踪获取到 code（长度: {len(auth_code)}）"
                                )
                    else:
                        # workspace/select 返回了非 organization 的 continue_url，直接跟踪
                        if ws_next:
                            full_next = (
                                ws_next
                                if ws_next.startswith("http")
                                else f"{OAUTH_ISSUER}{ws_next}"
                            )
                            auth_code = _follow_and_extract_code(session, full_next)
                            if auth_code:
                                print(f"  ✅ 跟踪获取到 code（长度: {len(auth_code)}）")
            except Exception as e:
                print(f"  ⚠️ workspace/select 异常: {e}")
                import traceback

                traceback.print_exc()

    # ----- 步骤4d: 备用策略 — allow_redirects=True 捕获 ConnectionError -----
    if not auth_code:
        print("  [4d] 备用策略: GET consent (allow_redirects=True)...")
        try:
            resp = session.get(
                consent_url,
                headers=NAVIGATE_HEADERS,
                verify=False,
                timeout=30,
                allow_redirects=True,
            )
            print(f"  最终: {resp.status_code}, URL: {resp.url[:200]}")
            auth_code = _extract_code_from_url(resp.url)
            if auth_code:
                print(f"  ✅ 最终 URL 中提取到 code")
            # 检查重定向链
            if not auth_code and resp.history:
                for r in resp.history:
                    loc = r.headers.get("Location", "")
                    auth_code = _extract_code_from_url(loc)
                    if auth_code:
                        print(f"  ✅ 重定向链中提取到 code")
                        break
        except requests.exceptions.ConnectionError as e:
            url_match = re.search(r'(https?://localhost[^\s\'"]+)', str(e))
            if url_match:
                auth_code = _extract_code_from_url(url_match.group(1))
                if auth_code:
                    print(f"  ✅ ConnectionError 中提取到 code")
        except Exception as e:
            print(f"  ⚠️ 备用策略异常: {e}")

    if not auth_code:
        print("  ❌ 未获取到 authorization code")
        return None

    # 用 code 换 token（复用已有的 codex_exchange_code 函数）
    return codex_exchange_code(auth_code, code_verifier)


# =================== Codex OAuth 登录 + CPA 回调（浏览器版，作为 fallback） ===================


def perform_codex_oauth_login(email, password, registrar_session=None):
    """
    注册成功后，通过浏览器混合模式执行 Codex OAuth 登录获取 Token。

    混合架构：
      浏览器层：完成 OAuth 登录全流程（邮箱+密码提交）
        - sentinel SDK 在浏览器内自动生成 t/c 字段（反机器人遥测+challenge response）
        - 通过 CDP 网络事件监听捕获 authorization code
      HTTP 层：用 code 换取 tokens（POST /oauth/token，无需 sentinel）

    使用 Codex 专用配置（来自 config.json）：
      client_id:    app_EMoamEEZ73f0CkXaXp7hrann（Codex CLI）
      redirect_uri: http://localhost:1455/auth/callback
      scope:        openid profile email offline_access

    参数:
        email: 注册的邮箱
        password: 注册的密码
        registrar_session: 注册时的 requests.Session（含 CF cookies，可选，本模式暂未使用）
    返回:
        dict: tokens 字典（含 access_token/refresh_token/id_token），失败返回 None
    """
    print("\n🔐 执行 Codex OAuth 登录获取 Token（浏览器混合模式）...")

    # 1. 构造 PKCE 参数
    code_verifier, code_challenge = generate_pkce()
    state = secrets.token_urlsafe(32)

    authorize_params = {
        "response_type": "code",
        "client_id": OAUTH_CLIENT_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "scope": "openid profile email offline_access",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    authorize_url = f"{OAUTH_ISSUER}/oauth/authorize?{urlencode(authorize_params)}"

    try:
        import undetected_chromedriver as uc
        from selenium.webdriver.common.by import By
    except ImportError:
        print("  ❌ 需要安装 undetected-chromedriver:")
        print("     pip install undetected-chromedriver selenium")
        return None

    driver = None
    try:
        # 2. 启动浏览器（带 CDP 网络事件监听）
        mode_str = "无头模式" if HEADLESS else "有头模式"
        print(
            f"  🌐 启动浏览器执行 OAuth 登录（{mode_str}，sentinel SDK 自动处理 t/c 字段）..."
        )
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=800,600")
        options.add_argument(f"--user-agent={USER_AGENT}")
        if HEADLESS:
            options.add_argument("--headless=new")
        if PROXY:
            options.add_argument(f"--proxy-server={PROXY}")

        driver = uc.Chrome(version_main=145, options=options, use_subprocess=True)

        # 启用 CDP 网络事件监听（捕获请求中的 authorization code 回调）
        driver.execute_cdp_cmd("Network.enable", {})

        # 注入 JS Hook：拦截所有导航/请求，捕获回调 URL 中的 code
        # 由于 redirect_uri 是 localhost:1455（不可达），浏览器会导航失败但 URL 仍可读取
        # 同时注入 sentinel token 拦截 Hook（调试用，可查看 t/c 内容）
        hook_js = """
        // 拦截 XHR 请求头，捕获 sentinel token（调试用）
        (function() {
            window.__sentinel_tokens = [];
            const origOpen = XMLHttpRequest.prototype.open;
            const origSetHeader = XMLHttpRequest.prototype.setRequestHeader;
            XMLHttpRequest.prototype.setRequestHeader = function(name, value) {
                if (name === 'openai-sentinel-token') {
                    try {
                        window.__sentinel_tokens.push(JSON.parse(value));
                        console.log('SENTINEL_CAPTURED:', value.substring(0, 80));
                    } catch(e) {}
                }
                return origSetHeader.call(this, name, value);
            };

            // 同时拦截 fetch
            const origFetch = window.fetch;
            window.fetch = function(input, init) {
                if (init && init.headers) {
                    let sentinel = null;
                    if (init.headers instanceof Headers) {
                        sentinel = init.headers.get('openai-sentinel-token');
                    } else if (typeof init.headers === 'object') {
                        sentinel = init.headers['openai-sentinel-token'];
                    }
                    if (sentinel) {
                        try {
                            window.__sentinel_tokens.push(JSON.parse(sentinel));
                            console.log('SENTINEL_CAPTURED_FETCH:', sentinel.substring(0, 80));
                        } catch(e) {}
                    }
                }
                return origFetch.apply(this, arguments);
            };
        })();
        """
        # 在新文档加载前注入 Hook
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument", {"source": hook_js}
        )

        # 3. 导航到 OAuth authorize URL
        print(f"  📡 访问 OAuth authorize URL...")
        driver.get(authorize_url)

        # 4. 等待 Cloudflare Challenge 完成 + 页面加载
        print("  ⏳ 等待 Cloudflare Challenge + 登录页面加载...")
        for i in range(60):
            try:
                current_url = driver.current_url
                # 检查是否已到达回调（极快通过的情况）
                if "localhost" in current_url and "code=" in current_url:
                    print(f"  ✅ 快速到达回调（第 {i + 1}s）")
                    break
                # 检查是否有输入框或按钮（登录页加载完成）
                inputs = driver.find_elements(By.CSS_SELECTOR, "input")
                if inputs:
                    print(f"  ✅ 登录页面加载完成（第 {i + 1}s）")
                    break
            except Exception:
                pass
            if i % 15 == 0 and i > 0:
                print(f"  ... 已等待 {i}s")
            time.sleep(1)

        time.sleep(1)

        # 辅助函数：检测并点击错误页面的重试按钮
        def _check_and_retry_error():
            """检测 OAuth 错误页面并点击重试按钮"""
            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    try:
                        btn_text = btn.text.strip().lower()
                        if btn_text in ["重试", "retry", "try again", "重新尝试"]:
                            if btn.is_displayed():
                                driver.execute_script("arguments[0].click();", btn)
                                print(f"  🔁 检测到错误页面，已点击重试")
                                time.sleep(3)
                                return True
                    except Exception:
                        continue
            except Exception:
                pass
            return False

        # 5. 自动化 OAuth 登录流程（邮箱 → 密码 → 确认）
        auth_code = None
        max_steps = 30  # 最大步骤数（防止无限循环）

        for step_i in range(max_steps):
            try:
                current_url = driver.current_url

                # ===== 检查是否已到达回调 URL =====
                if (
                    "localhost" in current_url or "callback" in current_url
                ) and "code=" in current_url:
                    parsed = urlparse(current_url)
                    params = parse_qs(parsed.query)
                    auth_code = params.get("code", [None])[0]
                    if auth_code:
                        print(
                            f"  ✅ 获取到 authorization code（URL 回调，长度: {len(auth_code)}）"
                        )
                        break

                # ===== 检是否是错误页面 =====
                if _check_and_retry_error():
                    continue

                # ===== 邮箱输入页面 =====
                email_inputs = driver.find_elements(
                    By.CSS_SELECTOR,
                    'input[type="email"], input[name="email"], input[name="username"], input[id="email"]',
                )
                visible_email = [e for e in email_inputs if e.is_displayed()]
                if visible_email:
                    print(f"  📧 [OAuth] 输入邮箱: {email}")
                    inp = visible_email[0]
                    inp.clear()
                    inp.send_keys(email)
                    time.sleep(0.5)
                    # 点击 Continue/Submit 按钮
                    submit_btns = driver.find_elements(
                        By.CSS_SELECTOR, 'button[type="submit"]'
                    )
                    if submit_btns:
                        driver.execute_script("arguments[0].click();", submit_btns[0])
                    else:
                        # 回退：查找任何按钮
                        buttons = driver.find_elements(By.TAG_NAME, "button")
                        for btn in buttons:
                            text = btn.text.strip().lower()
                            if text in (
                                "continue",
                                "继续",
                                "next",
                                "sign in",
                                "log in",
                            ):
                                driver.execute_script("arguments[0].click();", btn)
                                break
                    print("  ✅ 邮箱已提交")
                    time.sleep(3)
                    continue

                # ===== 密码输入页面 =====
                pwd_inputs = driver.find_elements(
                    By.CSS_SELECTOR, 'input[type="password"], input[name="password"]'
                )
                visible_pwd = [e for e in pwd_inputs if e.is_displayed()]
                if visible_pwd:
                    print("  🔑 [OAuth] 输入密码...")
                    inp = visible_pwd[0]
                    inp.clear()
                    # 逐字符输入密码（模拟真实打字，避免反机器人检测）
                    for char in password:
                        inp.send_keys(char)
                        time.sleep(0.03)
                    time.sleep(0.5)
                    # 点击 Submit
                    submit_btns = driver.find_elements(
                        By.CSS_SELECTOR, 'button[type="submit"]'
                    )
                    if submit_btns:
                        driver.execute_script("arguments[0].click();", submit_btns[0])
                    else:
                        buttons = driver.find_elements(By.TAG_NAME, "button")
                        for btn in buttons:
                            text = btn.text.strip().lower()
                            if text in ("continue", "继续", "log in", "sign in"):
                                driver.execute_script("arguments[0].click();", btn)
                                break
                    print("  ✅ 密码已提交")
                    time.sleep(3)
                    continue

                # ===== 授权确认页面 / Continue 按钮 =====
                buttons = driver.find_elements(By.TAG_NAME, "button")
                clicked_consent = False
                for btn in buttons:
                    try:
                        btn_text = btn.text.strip().lower()
                        if btn_text in (
                            "continue",
                            "继续",
                            "allow",
                            "approve",
                            "accept",
                            "authorize",
                        ):
                            if btn.is_displayed() and btn.is_enabled():
                                driver.execute_script("arguments[0].click();", btn)
                                print(
                                    f"  ✅ [OAuth] 已点击确认按钮: '{btn.text.strip()}'"
                                )
                                clicked_consent = True
                                time.sleep(3)
                                break
                    except Exception:
                        continue

                if clicked_consent:
                    continue

                # ===== 没有可操作的元素，等待页面变化 =====
                time.sleep(2)

            except Exception as e:
                print(f"  ⚠️ OAuth 步骤异常: {e}")
                time.sleep(2)

        # 6. 如果通过 URL 未获取到 code，尝试从网络日志中获取
        if not auth_code:
            print("  🔍 尝试从浏览器网络日志中提取 authorization code...")
            try:
                # 检查 performance log（如果可用）
                logs = driver.get_log("performance")
                for entry in logs:
                    try:
                        msg = json.loads(entry["message"])
                        method = msg.get("message", {}).get("method", "")
                        if method in (
                            "Network.requestWillBeSent",
                            "Network.responseReceived",
                        ):
                            url = msg.get("message", {}).get("params", {}).get(
                                "request", {}
                            ).get("url", "") or msg.get("message", {}).get(
                                "params", {}
                            ).get("response", {}).get("url", "")
                            if "code=" in url and "localhost" in url:
                                parsed = urlparse(url)
                                params = parse_qs(parsed.query)
                                auth_code = params.get("code", [None])[0]
                                if auth_code:
                                    print(
                                        f"  ✅ 从网络日志中获取到 code（长度: {len(auth_code)}）"
                                    )
                                    break
                    except Exception:
                        continue
            except Exception:
                pass

        # 7. 最后尝试：直接读取当前 URL
        if not auth_code:
            try:
                final_url = driver.current_url
                if "code=" in final_url:
                    parsed = urlparse(final_url)
                    params = parse_qs(parsed.query)
                    auth_code = params.get("code", [None])[0]
                    if auth_code:
                        print(f"  ✅ 从最终 URL 获取到 code（长度: {len(auth_code)}）")
            except Exception:
                pass

        # 调试：打印捕获到的 sentinel tokens（如果有）
        try:
            captured = driver.execute_script("return window.__sentinel_tokens || [];")
            if captured:
                print(f"  📋 调试: 共捕获 {len(captured)} 个 sentinel tokens")
                for idx, st in enumerate(captured[:3]):  # 最多打印3个
                    t_val = st.get("t", "")
                    c_val = st.get("c", "")
                    flow = st.get("flow", "")
                    print(
                        f"    [{idx}] flow={flow}, t长度={len(t_val)}, c长度={len(c_val)}"
                    )
        except Exception:
            pass

        # 8. 用 authorization code 换取 tokens
        if auth_code:
            return codex_exchange_code(auth_code, code_verifier)

        print("  ❌ 未获取到 authorization code")
        try:
            print(f"  最终 URL: {driver.current_url[:200]}")
        except Exception:
            pass
        return None

    except Exception as e:
        print(f"  ❌ Codex OAuth 登录异常: {e}")
        import traceback

        traceback.print_exc()
        return None
    finally:
        if driver:
            try:
                driver.quit()
                print("  🔒 OAuth 浏览器已关闭")
            except (OSError, Exception):
                pass


def codex_exchange_code(code, code_verifier):
    """
    用 authorization code 换取 Codex tokens

    POST https://auth.openai.com/oauth/token
    Content-Type: application/x-www-form-urlencoded
    """
    print("  🔄 换取 Codex Token...")
    session = create_session()

    for attempt in range(2):
        try:
            resp = session.post(
                f"{OAUTH_ISSUER}/oauth/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": OAUTH_REDIRECT_URI,
                    "client_id": OAUTH_CLIENT_ID,
                    "code_verifier": code_verifier,
                },
                verify=False,
                timeout=60,
            )
            break
        except Exception as e:
            if attempt == 0:
                print(f"  ⚠️ Token 交换超时，重试...")
                time.sleep(2)
                continue
            print(f"  ❌ Token 交换失败: {e}")
            return None

    if resp.status_code == 200:
        data = resp.json()
        print(f"  ✅ Codex Token 获取成功！")
        print(f"    Access Token 长度: {len(data.get('access_token', ''))}")
        print(f"    Refresh Token: {'✅' if data.get('refresh_token') else '❌'}")
        print(f"    ID Token: {'✅' if data.get('id_token') else '❌'}")
        return data
    else:
        print(f"  ❌ Token 交换失败: {resp.status_code}")
        print(f"  响应: {resp.text[:300]}")
        return None


# =================== Token JSON 保存 + CPA 上传 ===================


def decode_jwt_payload(token):
    """解析 JWT token 的 payload 部分"""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload = parts[1]
        # 补齐 base64 padding
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception:
        return {}


def save_token_json(email, access_token, refresh_token=None, id_token=None):
    """
    保存完整的 Token JSON 文件（格式兼容 Codex），并自动上传到 CPA 管理平台。

    JSON 格式与 codex_ultimate.py 一致：
    {
        "type": "codex",
        "email": "xxx@xxx.com",
        "expired": "2026-02-20T15:30:00+08:00",
        "id_token": "...",
        "account_id": "...",
        "access_token": "...",
        "last_refresh": "2026-02-18T15:30:00+08:00",
        "refresh_token": "..."
    }
    """
    try:
        from datetime import datetime, timezone, timedelta

        payload = decode_jwt_payload(access_token)

        # 提取 account_id
        auth_info = payload.get("https://api.openai.com/auth", {})
        account_id = auth_info.get("chatgpt_account_id", "")

        # 计算过期时间
        exp_timestamp = payload.get("exp", 0)
        if exp_timestamp:
            exp_dt = datetime.fromtimestamp(
                exp_timestamp, tz=timezone(timedelta(hours=8))
            )
            expired_str = exp_dt.strftime("%Y-%m-%dT%H:%M:%S+08:00")
        else:
            expired_str = ""

        now = datetime.now(tz=timezone(timedelta(hours=8)))
        last_refresh_str = now.strftime("%Y-%m-%dT%H:%M:%S+08:00")

        token_data = {
            "type": "codex",
            "email": email,
            "expired": expired_str,
            "id_token": id_token or "",
            "account_id": account_id,
            "access_token": access_token,
            "last_refresh": last_refresh_str,
            "refresh_token": refresh_token or "",
        }

        filename = f"{email}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(token_data, f, ensure_ascii=False)
        print(f"  ✅ Token JSON 已保存到 {filename}")

        # 上传到 CPA 管理平台
        if UPLOAD_API_URL:
            upload_token_json(filename)

    except Exception as e:
        print(f"  ❌ 保存 Token JSON 失败: {e}")


def upload_token_json(filename):
    """上传 Token JSON 文件到 CPA 管理平台"""
    try:
        session = create_session()
        with open(filename, "rb") as f:
            files = {"file": (filename, f, "application/json")}
            headers = {"Authorization": f"Bearer {UPLOAD_API_TOKEN}"}

            resp = session.post(
                UPLOAD_API_URL,
                files=files,
                headers=headers,
                verify=False,
                timeout=30,
            )

            if resp.status_code == 200:
                print(f"  ✅ Token JSON 已上传到 CPA 管理平台")
            else:
                print(f"  ❌ CPA 上传失败: {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        print(f"  ❌ CPA 上传异常: {e}")


def save_tokens(email, tokens):
    """保存 tokens 到所有目标（txt + JSON + CPA 上传），线程安全"""
    access_token = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")
    id_token = tokens.get("id_token", "")

    with _file_lock:
        if access_token:
            with open(AK_FILE, "a", encoding="utf-8") as f:
                f.write(f"{access_token}\n")
        if refresh_token:
            with open(RK_FILE, "a", encoding="utf-8") as f:
                f.write(f"{refresh_token}\n")

    if access_token:
        save_token_json(email, access_token, refresh_token, id_token)


# =================== 账号持久化 ===================


def save_account(email, password):
    """保存账号信息（线程安全）"""
    try:
        with _file_lock:
            with open(ACCOUNTS_FILE, "a", encoding="utf-8") as f:
                f.write(f"{email}:{password}\n")
            file_exists = os.path.exists(CSV_FILE)
            with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                import csv

                w = csv.writer(f)
                if not file_exists:
                    w.writerow(["email", "password", "timestamp"])
                w.writerow([email, password, time.strftime("%Y-%m-%d %H:%M:%S")])
        print(f"  ✅ 账号已保存")
    except Exception as e:
        print(f"  ⚠️ 保存失败: {e}")


# =================== 批量执行入口 ===================


def register_one(worker_id=0, task_index=0, total=1):
    """
    注册单个账号的完整流程（线程安全）
    返回: (email, password, success, reg_time, total_time)
    """
    tag = f"[W{worker_id}]" if CONCURRENT_WORKERS > 1 else ""
    t_start = time.time()
    session = create_session()

    # 1. 创建临时邮箱
    email, mail_auth = create_temp_email(session)
    if not email:
        return None, None, False, 0, 0

    password = generate_random_password()

    # 2. 协议注册
    registrar = ProtocolRegistrar()
    success, email, password = registrar.register(email, mail_auth, password)
    save_account(email, password)

    t_reg = time.time() - t_start  # 注册耗时

    if not success:
        return email, password, False, t_reg, t_reg

    print(f"  📝 注册耗时: {t_reg:.1f}s")

    # 3. Codex OAuth 登录
    tokens = None
    try:
        tokens = perform_codex_oauth_login_http(
            email,
            password,
            registrar_session=registrar.session,
            mail_auth=mail_auth,
        )

        if not tokens:
            print(f"{tag}  ❌ 纯 HTTP OAuth 失败")

        t_total = time.time() - t_start
        if tokens:
            save_tokens(email, tokens)
            print(
                f"{tag} ✅ {email} | 注册 {t_reg:.1f}s + OAuth {t_total - t_reg:.1f}s = 总 {t_total:.1f}s"
            )
        else:
            print(f"{tag} ⚠️ OAuth 失败（注册已成功）")
    except Exception as e:
        t_total = time.time() - t_start
        print(f"{tag} ⚠️ OAuth 异常: {e}")

    return email, password, True, t_reg, t_total


def run_batch():
    """批量注册入口（支持并发）"""
    workers = max(1, CONCURRENT_WORKERS)
    batch_start = time.time()

    mail_domain = (
        (MAILTM_DOMAIN or "auto") if EMAIL_PROVIDER == "mailtm" else CF_EMAIL_DOMAIN
    )
    print(
        f"\n🚀 协议注册机 v5 — {TOTAL_ACCOUNTS} 个账号 | 并发 {workers} | 邮箱源 {EMAIL_PROVIDER} | 域名 {mail_domain}"
    )

    ok = 0
    fail = 0
    results_lock = threading.Lock()
    reg_times = []  # 注册耗时列表
    total_times = []  # 总耗时列表

    if workers == 1:
        for i in range(TOTAL_ACCOUNTS):
            print(f"\n--- [{i + 1}/{TOTAL_ACCOUNTS}] ---")

            email, password, success, t_reg, t_total = register_one(
                worker_id=0, task_index=i + 1, total=TOTAL_ACCOUNTS
            )

            if success:
                ok += 1
                reg_times.append(t_reg)
                total_times.append(t_total)
            else:
                fail += 1

            wall = time.time() - batch_start
            throughput = wall / ok if ok > 0 else 0
            print(
                f"📊 {i + 1}/{TOTAL_ACCOUNTS} | ✅{ok} ❌{fail} | 吞吐 {throughput:.1f}s/个 | 已用 {wall:.0f}s"
            )

            if i < TOTAL_ACCOUNTS - 1:
                wait = random.randint(3, 8)
                time.sleep(wait)
    else:
        print(f"🔀 启动 {workers} 个并发 worker...\n")

        def _worker_task(task_index, worker_id):
            if task_index > 1:
                jitter = random.uniform(1, 3) * worker_id
                time.sleep(jitter)
            try:
                email, password, success, t_reg, t_total = register_one(
                    worker_id=worker_id, task_index=task_index, total=TOTAL_ACCOUNTS
                )
                return task_index, email, password, success, t_reg, t_total
            except Exception as e:
                print(f"[W{worker_id}] ❌ 异常: {e}")
                return task_index, None, None, False, 0, 0

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {}
            for i in range(TOTAL_ACCOUNTS):
                worker_id = (i % workers) + 1
                future = executor.submit(_worker_task, i + 1, worker_id)
                futures[future] = i + 1

            for future in as_completed(futures):
                task_idx = futures[future]
                try:
                    _, email, password, success, t_reg, t_total = future.result()
                    with results_lock:
                        if success:
                            ok += 1
                            reg_times.append(t_reg)
                            total_times.append(t_total)
                        else:
                            fail += 1
                        done = ok + fail
                        wall = time.time() - batch_start
                        throughput = wall / ok if ok > 0 else 0
                        print(
                            f"📊 {done}/{TOTAL_ACCOUNTS} | ✅{ok} ❌{fail} | 吞吐 {throughput:.1f}s/个 | 已用 {wall:.0f}s"
                        )
                except Exception as e:
                    with results_lock:
                        fail += 1
                        print(f"❌ 任务 {task_idx} 异常: {e}")

    elapsed = time.time() - batch_start
    throughput = elapsed / ok if ok > 0 else 0
    avg_reg = sum(reg_times) / len(reg_times) if reg_times else 0
    avg_total = sum(total_times) / len(total_times) if total_times else 0
    print(
        f"\n🏁 完成: ✅{ok} ❌{fail} | 总耗时 {elapsed:.1f}s | 吞吐 {throughput:.1f}s/个 | 单号(注册 {avg_reg:.1f}s + OAuth {avg_total - avg_reg:.1f}s = {avg_total:.1f}s)"
    )


if __name__ == "__main__":
    run_batch()

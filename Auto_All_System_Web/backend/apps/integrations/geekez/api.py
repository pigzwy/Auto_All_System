"""
GeekezBrowser API 封装
迁移自: 2dev/geek/geek_browser_api.py

控制端口默认: 19527
"""

import os
import json
import logging
import platform
import re
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from urllib.parse import urlparse, urlunparse, quote

logger = logging.getLogger(__name__)


@dataclass
class LaunchInfo:
    """浏览器启动信息"""

    profile_id: str
    debug_port: int
    cdp_endpoint: str
    ws_endpoint: Optional[str] = None
    pid: Optional[int] = None


@dataclass
class ProfileInfo:
    """Profile 信息"""

    id: str
    name: str
    proxy: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class GeekezBrowserAPI:
    """
    GeekezBrowser 控制端口 API 封装

    功能:
    - 健康检查
    - Profile 管理 (创建/更新/删除/列表)
    - 浏览器启动/关闭
    - 设置管理
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        timeout: int = 30,
        *,
        control_token: str | None = None,
        api_server_host: str | None = None,
        api_server_port: int | None = None,
        use_db_config: bool = True,
    ):
        db_cfg = None
        if use_db_config and host is None and port is None and control_token is None and api_server_host is None and api_server_port is None:
            try:
                from .models import GeekezIntegrationConfig

                db_cfg = GeekezIntegrationConfig.get_solo()
            except Exception:
                db_cfg = None

        # 兼容历史环境变量：GEEKEZ_API_HOST/GEEKEZ_API_PORT 指向 control server
        # 上游新版本里，control server 可通过 GEEKEZ_CONTROL_HOST/GEEKEZ_CONTROL_PORT/GEEKEZ_CONTROL_TOKEN 配置。
        self.host = (
            host
            or (db_cfg.control_host if db_cfg else None)
            or os.environ.get("GEEKEZ_CONTROL_HOST")
            or os.environ.get("GEEKEZ_API_HOST", "127.0.0.1")
        )
        self.port = int(
            port
            or (db_cfg.control_port if db_cfg else None)
            or os.environ.get("GEEKEZ_CONTROL_PORT")
            or os.environ.get("GEEKEZ_API_PORT", "19527")
        )
        self.timeout = timeout

        if control_token is not None:
            self.control_token = str(control_token).strip()
        else:
            self.control_token = (
                (db_cfg.get_control_token() if db_cfg else "")
                or os.environ.get("GEEKEZ_CONTROL_TOKEN")
                or os.environ.get("GEEKEZ_API_TOKEN")
                or ""
            ).strip()

        # API Server（官方文档：https://browser.geekez.net/docs#doc-api）
        # 默认端口 12138，且通常只监听 127.0.0.1。
        self.api_server_host = (
            api_server_host
            or (db_cfg.api_server_host if db_cfg else None)
            or os.environ.get("GEEKEZ_API_SERVER_HOST", "127.0.0.1")
        )
        self.api_server_port = int(
            api_server_port
            or (db_cfg.api_server_port if db_cfg else None)
            or os.environ.get("GEEKEZ_API_SERVER_PORT", "12138")
        )

        self.base_url = f"http://{self.host}:{self.port}"  # control server
        self.api_server_url = f"http://{self.api_server_host}:{self.api_server_port}"

    _uuid_re = re.compile(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )

    def _control_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.control_token:
            headers["Authorization"] = f"Bearer {self.control_token}"
        return headers

    def _control_base_urls(self) -> List[str]:
        """Return candidate control server base URLs.

        Geekez control server in Linux desktop often binds to 127.0.0.1 only.
        When backend runs in Docker, direct access via host gateway may be refused.
        We support an optional host forwarder port: 19528 -> 19527.
        """

        urls = [self.base_url]

        is_docker = os.environ.get("DJANGO_ENVIRONMENT") == "docker"
        # Host-network detection:
        # - explicit flag: USE_HOST_NETWORK=1
        # - implicit: DB_HOST=127.0.0.1 (our linux.hostnet compose sets this)
        use_hostnet = (
            os.environ.get("USE_HOST_NETWORK") == "1"
            or os.environ.get("DB_HOST") in ("127.0.0.1", "localhost")
        )

        # Host network mode: prefer host-local endpoints first (dynamic CDP ports bind to localhost).
        if use_hostnet:
            localhost_urls: list[str] = []
            localhost_urls.append(f"http://127.0.0.1:{int(self.port)}")
            if int(self.port) != 19527:
                localhost_urls.append("http://127.0.0.1:19527")
            urls = localhost_urls + urls

        # If user configured the default port, try the forwarded port too.
        if int(self.port) == 19527:
            urls.append(f"http://{self.host}:19528")

        # If user configured localhost inside Docker, also try host gateway.
        if is_docker and self.host in ("127.0.0.1", "localhost"):
            urls.append("http://host.docker.internal:19528")

        # de-dup while keeping order
        seen: set[str] = set()
        out: list[str] = []
        for u in urls:
            if u in seen:
                continue
            seen.add(u)
            out.append(u)
        return out

    def _api_base_urls(self) -> List[str]:
        """Return candidate API server base URLs.

        Official API server (docs) defaults to 127.0.0.1:12138, which is not reachable
        from Docker containers. For Linux dev we support a host forwarder: 12139 -> 12138.
        """

        urls = [self.api_server_url]

        is_docker = os.environ.get("DJANGO_ENVIRONMENT") == "docker"
        use_hostnet = (
            os.environ.get("USE_HOST_NETWORK") == "1"
            or os.environ.get("DB_HOST") in ("127.0.0.1", "localhost")
        )

        # Host network mode: API server can be accessed via localhost directly.
        if use_hostnet:
            localhost_urls: list[str] = []
            localhost_urls.append(f"http://127.0.0.1:{int(self.api_server_port)}")
            if int(self.api_server_port) != 12138:
                localhost_urls.append("http://127.0.0.1:12138")
            urls = localhost_urls + urls

        # If configured to default port, try forwarded port too.
        if int(self.api_server_port) == 12138:
            urls.append(f"http://{self.api_server_host}:12139")

        # If user configured localhost inside Docker, also try host gateway forwarded port.
        if is_docker and self.api_server_host in ("127.0.0.1", "localhost"):
            urls.append("http://host.docker.internal:12139")

        seen: set[str] = set()
        out: list[str] = []
        for u in urls:
            if u in seen:
                continue
            seen.add(u)
            out.append(u)
        return out

    def _api_request_json(self, method: str, path: str, *, json_body: dict | None = None) -> dict | None:
        method = method.upper().strip()
        for base_url in self._api_base_urls():
            url = f"{base_url}{path}"
            try:
                resp = requests.request(method, url, json=json_body, timeout=self.timeout)
                if resp.status_code != 200:
                    continue
                data = resp.json() if resp.content else {}
                if isinstance(data, dict) and data.get("success") is True:
                    return data
            except Exception:
                continue
        return None

    def _normalize_profile_id(self, profile_id_or_name: str) -> str:
        """control server 的 launch 只支持 UUID。这里允许传 name（email）自动映射。"""

        value = str(profile_id_or_name or "").strip()
        if not value:
            return ""

        if self._uuid_re.match(value):
            return value

        p = self.get_profile_by_name(value)
        return p.id if p else ""

    # ==================== 健康检查 ====================

    def health_check(self) -> bool:
        """检查 GeekezBrowser 是否在线"""
        headers = self._control_headers()
        for base_url in self._control_base_urls():
            try:
                resp = requests.get(f"{base_url}/health", timeout=5, headers=headers)
                if resp.status_code == 200:
                    return True
            except Exception:
                continue
        return False

    # ==================== Profile 管理 ====================

    def list_profiles(self) -> List[ProfileInfo]:
        """获取所有 Profile 列表"""
        api_data = self._api_request_json("GET", "/api/profiles")
        if api_data and isinstance(api_data.get("profiles"), list):
            out: list[ProfileInfo] = []
            for p in api_data.get("profiles") or []:
                if not isinstance(p, dict):
                    continue
                out.append(
                    ProfileInfo(
                        id=str(p.get("id", "")),
                        name=str(p.get("name", "")),
                        proxy=None,
                        metadata={},
                    )
                )
            return out

        # fallback: control server /profiles (新版本 control server 提供 name/id/debugPort)
        headers = self._control_headers()
        for base_url in self._control_base_urls():
            try:
                resp = requests.get(
                    f"{base_url}/profiles",
                    timeout=self.timeout,
                    headers=headers,
                )
                if resp.status_code != 200:
                    continue

                data = resp.json() if resp.content else {}
                profiles = data.get("profiles")
                if not isinstance(profiles, list):
                    continue

                out: list[ProfileInfo] = []
                for p in profiles:
                    if not isinstance(p, dict):
                        continue
                    out.append(
                        ProfileInfo(
                            id=str(p.get("id", "")),
                            name=str(p.get("name", "")),
                            proxy=None,
                            metadata={},
                        )
                    )
                return out
            except Exception:
                continue

        # fallback: local profiles.json (legacy behavior)
        profiles = self._read_profiles_json()
        return [
            ProfileInfo(
                id=str(p.get("id", "")),
                name=str(p.get("name", "")),
                proxy=p.get("proxyStr") or None,
                metadata=p.get("metadata", {}) or {},
            )
            for p in profiles
            if isinstance(p, dict)
        ]

    def get_profile_by_name(self, name: str) -> Optional[ProfileInfo]:
        """根据名称获取 Profile"""
        profiles = self.list_profiles()
        for p in profiles:
            if p.name == name:
                return p
        return None

    def create_or_update_profile(
        self,
        name: str,
        proxy: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProfileInfo:
        """
        创建或更新 Profile

        Args:
            name: Profile 名称 (通常使用 email)
            proxy: 代理地址
            metadata: 元数据 (如账号信息)
        """
        # Prefer official API server (matches Geekez UI / refresh semantics)
        existing = self.get_profile_by_name(name)
        if existing:
            # best-effort update proxy via API server
            if proxy is not None:
                self._api_request_json(
                    "PUT",
                    f"/api/profiles/{quote(existing.id, safe='')}",
                    json_body={"proxyStr": proxy},
                )
            return existing

        api_created = self._api_request_json(
            "POST",
            "/api/profiles",
            json_body={
                "name": name,
                "proxyStr": proxy or "",
                "tags": [],
            },
        )
        if api_created and isinstance(api_created.get("profile"), dict):
            p = api_created["profile"]
            return ProfileInfo(
                id=str(p.get("id", "")),
                name=str(p.get("name", name)),
                proxy=str(p.get("proxyStr", "")) or None,
                metadata={},
            )

        # fallback: write local profiles.json (legacy behavior)
        import uuid

        profiles_list = self._read_profiles_json()

        # 查找是否已存在
        existing_json: Optional[Dict[str, Any]] = None
        for p in profiles_list:
            if isinstance(p, dict) and p.get("name") == name:
                existing_json = p
                break

        if existing_json is not None:
            if proxy is not None:
                existing_json["proxyStr"] = proxy
            if metadata is not None:
                existing_json["metadata"] = metadata
            profile_id = str(existing_json.get("id", ""))
        else:
            profile_id = str(uuid.uuid4())
            new_profile = {
                "id": profile_id,
                "name": name,
                "proxyStr": proxy or "",
                "tags": [],
                "fingerprint": {"window": {"width": 1280, "height": 800}},
                "preProxyOverride": "default",
                "isSetup": False,
                "debugPort": 0,
                "createdAt": int(time.time() * 1000),
                "metadata": metadata or {},
            }
            profiles_list.append(new_profile)

        self._write_profiles_json(profiles_list)

        return ProfileInfo(id=profile_id, name=name, proxy=proxy, metadata=metadata or {})

    def delete_profile(self, profile_id: str) -> bool:
        """删除 Profile"""
        profiles_list = self._read_profiles_json()
        new_list = [
            p
            for p in profiles_list
            if isinstance(p, dict) and str(p.get("id")) != str(profile_id)
        ]
        if len(new_list) == len(profiles_list):
            return False  # 未找到

        self._write_profiles_json(new_list)
        return True

    # ==================== 浏览器控制 ====================

    def launch_profile(self, profile_id: str) -> Optional[LaunchInfo]:
        """
        启动浏览器 Profile

        Returns:
            LaunchInfo 包含 cdp_endpoint 用于 Playwright 连接
        """
        # GeekezBrowser 有概率返回 debugPort 但 Chromium 没有实际监听，
        # 这里做启动 + 探活重试，提升稳定性。
        try:
            import socket

            cdp_host = socket.gethostbyname(self.host)
        except Exception:
            cdp_host = self.host

        normalized_id = self._normalize_profile_id(profile_id)
        if not normalized_id:
            logger.error(f"Invalid profile id/name: {profile_id}")
            return None

        launch_payload = {
            "debugPort": 0,
            "enableRemoteDebugging": True,
            # 关键：让 DevTools 端口对 Docker 容器可达
            "remoteDebuggingAddress": "0.0.0.0",
        }

        headers = self._control_headers()
        base_urls = self._control_base_urls()

        last_status: dict[str, int] = {}

        for attempt in range(1, 4):
            try:
                resp = None
                for base_url in base_urls:
                    try:
                        resp = requests.post(
                            f"{base_url}/profiles/{normalized_id}/launch",
                            json=launch_payload,
                            timeout=self.timeout,
                            headers=headers,
                        )
                        if resp.status_code == 200:
                            break
                        last_status[base_url] = resp.status_code
                        logger.warning(
                            f"Launch failed (attempt {attempt}) via {base_url}: {resp.status_code}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Launch errored (attempt {attempt}) via {base_url}: {e}"
                        )

                if resp is None or resp.status_code != 200:
                    # If all candidates return 404, likely the current Geekez control server
                    # does not support /profiles/{uuid}/launch (newer Geekez versions expose
                    # only API server /api/open and /api/profiles).
                    if last_status and all(code == 404 for code in last_status.values()):
                        logger.error(
                            "Geekez control server does not support /profiles/{uuid}/launch (404). "
                            "Please enable Control Server or use a compatible Geekez version. "
                            f"candidates={last_status}"
                        )
                        return None
                    time.sleep(1)
                    continue

                data = resp.json() if resp.content else {}
                debug_port = data.get("debugPort", 0)
                if not isinstance(debug_port, int) or debug_port <= 0:
                    logger.error(
                        f"Launch returned invalid debugPort (attempt {attempt}): {debug_port}"
                    )
                    time.sleep(1)
                    continue

                # Some Geekez builds may return a debugPort that is not actually the active
                # DevTools port when the environment is already running. In that case,
                # wsEndpoint may contain the real port.
                ws_port: int | None = None
                raw_ws = data.get("wsEndpoint")
                if isinstance(raw_ws, str) and raw_ws:
                    try:
                        parsed_ws = urlparse(raw_ws)
                        if parsed_ws.netloc and ":" in parsed_ws.netloc:
                            _, port_s = parsed_ws.netloc.rsplit(":", 1)
                            ws_port = int(port_s)
                    except Exception:
                        ws_port = None

                cdp_endpoint = f"http://{cdp_host}:{debug_port}"

                ws_endpoint: Optional[str] = None
                ready = False
                last_error: Optional[Exception] = None
                deadline = time.monotonic() + 20

                candidate_ports = [debug_port]
                if ws_port and ws_port != debug_port:
                    candidate_ports.append(ws_port)

                while time.monotonic() < deadline:
                    try:
                        for port in candidate_ports:
                            v = requests.get(
                                f"http://{cdp_host}:{int(port)}/json/version",
                                timeout=2,
                                headers={"Host": cdp_host},
                            )
                            if v.status_code != 200:
                                continue

                            payload = v.json() if v.content else {}
                            raw_ws2 = payload.get("webSocketDebuggerUrl")
                            if isinstance(raw_ws2, str) and raw_ws2:
                                debug_port = int(port)
                                cdp_endpoint = f"http://{cdp_host}:{debug_port}"
                                ws_endpoint = self._rewrite_ws_endpoint_host(
                                    raw_ws2, cdp_host, debug_port
                                )
                                ready = True
                                break

                        if ready:
                            break
                    except Exception as e:
                        last_error = e

                    time.sleep(0.6)

                if not ready:
                    if last_error is not None:
                        logger.warning(
                            f"DevTools not ready (attempt {attempt}) for {cdp_endpoint}: {last_error}"
                        )
                    else:
                        logger.warning(
                            f"DevTools not ready (attempt {attempt}) for {cdp_endpoint}"
                        )

                    # Best-effort close before retry
                    try:
                        self.close_profile(normalized_id)
                    except Exception:
                        pass
                    time.sleep(1)
                    continue

                if ws_endpoint is None:
                    raw_ws = data.get("wsEndpoint")
                    if isinstance(raw_ws, str) and raw_ws:
                        ws_endpoint = self._rewrite_ws_endpoint_host(
                            raw_ws, cdp_host, debug_port
                        )

                return LaunchInfo(
                    profile_id=normalized_id,
                    debug_port=debug_port,
                    cdp_endpoint=cdp_endpoint,
                    ws_endpoint=ws_endpoint,
                    pid=data.get("pid"),
                )
            except Exception as e:
                logger.warning(f"Launch attempt {attempt} errored: {e}")
                time.sleep(1)

        return None

    @staticmethod
    def _rewrite_ws_endpoint_host(ws_endpoint: str, host: str, debug_port: int) -> str:
        """将 wsEndpoint 的 host 强制改为可达的 IP/host，并补齐端口。

        Geekez/Chrome 可能返回 ws://127.0.0.1:<port>/...，当后端在 Docker 中运行时不可达。
        """

        try:
            parsed = urlparse(ws_endpoint)
            if not parsed.scheme.startswith("ws"):
                return ws_endpoint

            if not parsed.netloc:
                return ws_endpoint

            # netloc = "host:port" or "host"
            if ":" in parsed.netloc:
                _, port = parsed.netloc.rsplit(":", 1)
                netloc = f"{host}:{port}"
            else:
                # Geekez/Chrome 某些版本会返回不带端口的 ws url，例如:
                # ws://192.168.65.254/devtools/browser/<id>
                # 这种情况下需要补齐 debug_port。
                netloc = f"{host}:{int(debug_port)}"

            return urlunparse(
                (
                    parsed.scheme,
                    netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            )
        except Exception:
            return ws_endpoint

    def stop_profile(self, profile_id_or_name: str) -> bool:
        """使用上游 API Server 停止 profile（/api/profiles/:idOrName/stop）。

        注意：API Server 默认只监听 127.0.0.1；如果后端运行在 Docker，需要将
        `GEEKEZ_API_SERVER_HOST` 指向宿主机可达地址（例如 host.docker.internal）。
        """

        value = str(profile_id_or_name or "").strip()
        if not value:
            return False

        def try_url(url: str) -> bool:
            encoded = quote(value, safe="")
            resp = requests.post(
                f"{url}/api/profiles/{encoded}/stop",
                timeout=self.timeout,
            )
            return resp.status_code == 200

        urls = [self.api_server_url]

        # Docker 场景：提供默认转发端口 12139 -> 12138
        if self.api_server_port == 12138:
            urls.append(f"http://{self.api_server_host}:12139")
        if os.environ.get("DJANGO_ENVIRONMENT") == "docker" and self.api_server_host in (
            "127.0.0.1",
            "localhost",
        ):
            urls.append("http://host.docker.internal:12139")

        for url in urls:
            try:
                if try_url(url):
                    return True
            except Exception as e:
                logger.warning(f"Stop profile via API server failed ({url}): {e}")

        return False

    def close_profile(self, profile_id_or_name: str) -> bool:
        """关闭浏览器 Profile。

        兼容策略：
        1) 先尝试旧 control server 的 /profiles/{id}/close（部分旧版本存在）
        2) 如果 404/405，再 fallback 到新 API server 的 /api/profiles/:idOrName/stop
        """

        value = str(profile_id_or_name or "").strip()
        if not value:
            return False

        # 旧接口（control server）
        headers = self._control_headers()
        for base_url in self._control_base_urls():
            try:
                resp = requests.post(
                    f"{base_url}/profiles/{value}/close",
                    timeout=self.timeout,
                    headers=headers,
                )
                if resp.status_code == 200:
                    return True
                if resp.status_code not in (404, 405):
                    logger.warning(
                        f"Close profile failed via {base_url}: {resp.status_code} {resp.text}"
                    )
            except Exception as e:
                logger.warning(f"Close profile (control) errored via {base_url}: {e}")

        # 新接口（API server）
        return self.stop_profile(value)

    def shutdown(self) -> bool:
        """关闭 GeekezBrowser 服务"""
        for base_url in self._control_base_urls():
            try:
                resp = requests.post(
                    f"{base_url}/shutdown",
                    timeout=5,
                    headers=self._control_headers(),
                )
                if resp.status_code == 200:
                    return True
            except Exception:
                continue
        return False

    # ==================== 设置管理 ====================

    def ensure_remote_debugging(self) -> bool:
        """确保启用远程调试 (Playwright CDP 连接需要)"""
        settings_data = self._read_settings_json()
        if not settings_data.get("enableRemoteDebugging"):
            settings_data["enableRemoteDebugging"] = True
            self._write_settings_json(settings_data)
            return True
        return False

    # ==================== 文件操作 (私有) ====================

    def _get_data_dir(self) -> Path:
        """获取 GeekezBrowser 数据目录"""
        # Docker 场景：通过挂载把宿主机 GeekezBrowser Profiles 目录映射进容器
        # 然后用环境变量指定映射后的容器内路径。
        override = os.environ.get("GEEKEZ_DATA_DIR")
        if override:
            return Path(override)

        if platform.system() == "Windows":
            base = os.environ.get("APPDATA", os.path.expanduser("~"))
            return Path(base) / "geekez-browser" / "BrowserProfiles"
        else:
            return Path.home() / ".config" / "geekez-browser" / "BrowserProfiles"

    def _read_profiles_json(self) -> List[Dict[str, Any]]:
        """读取 profiles.json

        GeekezBrowser 的 profiles.json 格式为: List[Dict]
        (与 2dev/geek/geek_browser_api.py 一致)
        """
        path = self._get_data_dir() / "profiles.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
                # 兼容旧格式：{"profiles": [...]}（历史版本）
                if isinstance(data, dict) and isinstance(data.get("profiles"), list):
                    return data["profiles"]
            except Exception:
                pass
        return []

    def _write_profiles_json(self, profiles: List[Dict[str, Any]]) -> None:
        """写入 profiles.json"""
        path = self._get_data_dir() / "profiles.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(profiles, ensure_ascii=False), encoding="utf-8")

    def _read_settings_json(self) -> Dict[str, Any]:
        """读取 settings.json"""
        path = self._get_data_dir() / "settings.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _write_settings_json(self, data: Dict[str, Any]) -> None:
        """写入 settings.json"""
        path = self._get_data_dir() / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )


class GeekezBrowserManager:
    """
    GeekezBrowser 管理器 (高级封装)

    对应原 GeekProcess 中的浏览器管理功能
    """

    def __init__(self, api: Optional[GeekezBrowserAPI] = None):
        self.api = api or GeekezBrowserAPI()

    def ensure_profile_for_account(
        self, email: str, account_info: Dict[str, Any], proxy: Optional[str] = None
    ) -> ProfileInfo:
        """
        为账号创建/更新 Profile

        Args:
            email: 邮箱 (作为 Profile 名称)
            account_info: 账号信息 (存入 metadata)
            proxy: 代理地址
        """
        return self.api.create_or_update_profile(
            name=email, proxy=proxy, metadata={"account": account_info}
        )

    def launch_by_email(self, email: str) -> Optional[LaunchInfo]:
        """根据邮箱启动浏览器"""
        profile = self.api.get_profile_by_name(email)
        if not profile:
            logger.error(f"Profile not found: {email}")
            return None
        return self.api.launch_profile(profile.id)

    def close_by_email(self, email: str) -> bool:
        """根据邮箱关闭浏览器"""
        profile = self.api.get_profile_by_name(email)
        if not profile:
            return False
        return self.api.close_profile(profile.id)

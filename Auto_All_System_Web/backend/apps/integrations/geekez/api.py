"""
GeekezBrowser API 封装
迁移自: 2dev/geek/geek_browser_api.py

控制端口默认: 19527
"""

import os
import json
import logging
import platform
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from urllib.parse import urlparse, urlunparse

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
        self, host: str | None = None, port: int | None = None, timeout: int = 30
    ):
        # 优先从环境变量读取，支持 Docker 环境
        self.host = host or os.environ.get("GEEKEZ_API_HOST", "127.0.0.1")
        self.port = port or int(os.environ.get("GEEKEZ_API_PORT", "19527"))
        self.timeout = timeout
        self.base_url = f"http://{self.host}:{self.port}"

    # ==================== 健康检查 ====================

    def health_check(self) -> bool:
        """检查 GeekezBrowser 是否在线"""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    # ==================== Profile 管理 ====================

    def list_profiles(self) -> List[ProfileInfo]:
        """获取所有 Profile 列表"""
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
        import uuid

        profiles_list = self._read_profiles_json()

        # 查找是否已存在
        existing: Optional[Dict[str, Any]] = None
        for p in profiles_list:
            if isinstance(p, dict) and p.get("name") == name:
                existing = p
                break

        if existing is not None:
            # 更新（按 GeekezBrowser profiles.json 结构）
            if proxy is not None:
                existing["proxyStr"] = proxy
            if metadata is not None:
                existing["metadata"] = metadata

            profile_id = str(existing.get("id", ""))
        else:
            # 创建
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

        return ProfileInfo(
            id=profile_id, name=name, proxy=proxy, metadata=metadata or {}
        )

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

        launch_payload = {
            "debugPort": 0,
            "enableRemoteDebugging": True,
            # 关键：让 DevTools 端口对 Docker 容器可达
            "remoteDebuggingAddress": "0.0.0.0",
        }

        for attempt in range(1, 4):
            try:
                resp = requests.post(
                    f"{self.base_url}/profiles/{profile_id}/launch",
                    json=launch_payload,
                    timeout=self.timeout,
                )
                if resp.status_code != 200:
                    logger.error(f"Launch failed (attempt {attempt}): {resp.text}")
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

                cdp_endpoint = f"http://{cdp_host}:{debug_port}"

                ws_endpoint: Optional[str] = None
                ready = False
                last_error: Optional[Exception] = None
                deadline = time.monotonic() + 20

                while time.monotonic() < deadline:
                    try:
                        v = requests.get(
                            f"{cdp_endpoint}/json/version",
                            timeout=2,
                            headers={"Host": cdp_host},
                        )
                        if v.status_code == 200:
                            payload = v.json() if v.content else {}
                        raw_ws = payload.get("webSocketDebuggerUrl")
                        if isinstance(raw_ws, str) and raw_ws:
                            ws_endpoint = self._rewrite_ws_endpoint_host(
                                raw_ws, cdp_host, debug_port
                            )
                            ready = True
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
                        self.close_profile(profile_id)
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
                    profile_id=profile_id,
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

    def close_profile(self, profile_id: str) -> bool:
        """关闭浏览器 Profile"""
        try:
            resp = requests.post(
                f"{self.base_url}/profiles/{profile_id}/close", timeout=self.timeout
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Close profile failed: {e}")
            return False

    def shutdown(self) -> bool:
        """关闭 GeekezBrowser 服务"""
        try:
            resp = requests.post(f"{self.base_url}/shutdown", timeout=5)
            return resp.status_code == 200
        except Exception:
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

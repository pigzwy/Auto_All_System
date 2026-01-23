"""
GeekezBrowser API 封装
迁移自: 2dev/geek/geek_browser_api.py

控制端口默认: 19527
"""

import os
import json
import logging
import platform
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from django.conf import settings

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

    def __init__(self, host: str = "127.0.0.1", port: int = 19527, timeout: int = 30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"

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
        profiles_data = self._read_profiles_json()
        return [
            ProfileInfo(
                id=p.get("id", ""),
                name=p.get("name", ""),
                proxy=p.get("proxy"),
                metadata=p.get("metadata", {}),
            )
            for p in profiles_data.get("profiles", [])
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

        profiles_data = self._read_profiles_json()
        profiles_list = profiles_data.get("profiles", [])

        # 查找是否已存在
        existing = None
        for p in profiles_list:
            if p.get("name") == name:
                existing = p
                break

        if existing:
            # 更新
            if proxy is not None:
                existing["proxy"] = proxy
            if metadata is not None:
                existing["metadata"] = metadata
            profile_id = existing["id"]
        else:
            # 创建
            profile_id = str(uuid.uuid4())
            new_profile = {
                "id": profile_id,
                "name": name,
                "proxy": proxy or "",
                "metadata": metadata or {},
            }
            profiles_list.append(new_profile)

        profiles_data["profiles"] = profiles_list
        self._write_profiles_json(profiles_data)

        return ProfileInfo(
            id=profile_id, name=name, proxy=proxy, metadata=metadata or {}
        )

    def delete_profile(self, profile_id: str) -> bool:
        """删除 Profile"""
        profiles_data = self._read_profiles_json()
        profiles_list = profiles_data.get("profiles", [])

        new_list = [p for p in profiles_list if p.get("id") != profile_id]
        if len(new_list) == len(profiles_list):
            return False  # 未找到

        profiles_data["profiles"] = new_list
        self._write_profiles_json(profiles_data)
        return True

    # ==================== 浏览器控制 ====================

    def launch_profile(self, profile_id: str) -> Optional[LaunchInfo]:
        """
        启动浏览器 Profile

        Returns:
            LaunchInfo 包含 cdp_endpoint 用于 Playwright 连接
        """
        try:
            resp = requests.post(
                f"{self.base_url}/profiles/{profile_id}/launch", timeout=self.timeout
            )
            if resp.status_code != 200:
                logger.error(f"Launch failed: {resp.text}")
                return None

            data = resp.json()
            debug_port = data.get("debugPort", 0)

            return LaunchInfo(
                profile_id=profile_id,
                debug_port=debug_port,
                cdp_endpoint=f"http://127.0.0.1:{debug_port}",
                ws_endpoint=data.get("wsEndpoint"),
                pid=data.get("pid"),
            )
        except Exception as e:
            logger.error(f"Launch profile failed: {e}")
            return None

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
        if platform.system() == "Windows":
            base = os.environ.get("APPDATA", os.path.expanduser("~"))
            return Path(base) / "geekez-browser" / "BrowserProfiles"
        else:
            return Path.home() / ".config" / "geekez-browser" / "BrowserProfiles"

    def _read_profiles_json(self) -> Dict[str, Any]:
        """读取 profiles.json"""
        path = self._get_data_dir() / "profiles.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"profiles": []}

    def _write_profiles_json(self, data: Dict[str, Any]) -> None:
        """写入 profiles.json"""
        path = self._get_data_dir() / "profiles.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

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

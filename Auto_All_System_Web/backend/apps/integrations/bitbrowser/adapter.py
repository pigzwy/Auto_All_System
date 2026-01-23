"""
比特浏览器适配器

将 BitBrowserAPI 适配为统一的 BaseBrowserAPI 接口
"""

import logging
from typing import Optional, Dict, Any, List

from apps.integrations.browser_base import (
    BaseBrowserAPI,
    BrowserType,
    LaunchInfo,
    ProfileInfo,
)
from apps.integrations.bitbrowser.api import BitBrowserAPI

logger = logging.getLogger(__name__)


class BitBrowserAdapter(BaseBrowserAPI):
    """
    比特浏览器适配器

    实现统一的浏览器接口
    """

    browser_type = BrowserType.BITBROWSER

    def __init__(self, api_url: str = None):
        self._api = BitBrowserAPI(api_url=api_url)

    def health_check(self) -> bool:
        """检查比特浏览器服务是否在线"""
        try:
            # 尝试获取浏览器列表来验证连接
            result = self._api.get_browser_list(page=0, page_size=1)
            return result.get("success", False)
        except Exception:
            return False

    def list_profiles(self) -> List[ProfileInfo]:
        """获取所有 Profile 列表"""
        try:
            result = self._api.get_browser_list(page=0, page_size=1000)
            if not result.get("success"):
                return []

            data = result.get("data", {})
            browsers = data.get("list", [])

            return [
                ProfileInfo(
                    id=b.get("id", ""),
                    name=b.get("name", ""),
                    browser_type=self.browser_type,
                    proxy=self._extract_proxy(b),
                    metadata=b,
                )
                for b in browsers
            ]
        except Exception as e:
            logger.error(f"Failed to list profiles: {e}")
            return []

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
        """创建或更新 Profile"""
        existing = self.get_profile_by_name(name)

        browser_config = {
            "name": name,
            **(metadata or {}),
        }

        if proxy:
            browser_config["proxyConfig"] = self._parse_proxy(proxy)

        if existing:
            # 更新
            browser_config["id"] = existing.id
            result = self._api.update_browser(browser_config)
        else:
            # 创建
            result = self._api.create_browser(browser_config)

        if not result.get("success"):
            raise Exception(f"Failed to create/update profile: {result.get('msg')}")

        profile_id = result.get("data", {}).get("id") or existing.id if existing else ""

        return ProfileInfo(
            id=profile_id,
            name=name,
            browser_type=self.browser_type,
            proxy=proxy,
            metadata=metadata or {},
        )

    def delete_profile(self, profile_id: str) -> bool:
        """删除 Profile"""
        try:
            result = self._api.delete_browser([profile_id])
            return result.get("success", False)
        except Exception:
            return False

    def launch_profile(self, profile_id: str) -> Optional[LaunchInfo]:
        """启动浏览器 Profile"""
        try:
            result = self._api.open_browser(profile_id)
            if not result.get("success"):
                logger.error(f"Failed to launch: {result.get('msg')}")
                return None

            data = result.get("data", {})
            ws_endpoint = data.get("ws", "")
            http_endpoint = data.get("http", "")

            # 从 ws 端点提取端口
            debug_port = 0
            if ws_endpoint:
                import re

                match = re.search(r":(\d+)/", ws_endpoint)
                if match:
                    debug_port = int(match.group(1))

            return LaunchInfo(
                profile_id=profile_id,
                browser_type=self.browser_type,
                debug_port=debug_port,
                cdp_endpoint=http_endpoint or f"http://127.0.0.1:{debug_port}",
                ws_endpoint=ws_endpoint,
                pid=data.get("pid"),
            )
        except Exception as e:
            logger.error(f"Failed to launch profile: {e}")
            return None

    def close_profile(self, profile_id: str) -> bool:
        """关闭浏览器 Profile"""
        try:
            result = self._api.close_browser(profile_id)
            return result.get("success", False)
        except Exception:
            return False

    # ==================== 私有方法 ====================

    def _extract_proxy(self, browser_data: Dict[str, Any]) -> Optional[str]:
        """从浏览器数据中提取代理地址"""
        proxy_config = browser_data.get("proxyConfig", {})
        if not proxy_config:
            return None

        proxy_type = proxy_config.get("proxyType", "noproxy")
        if proxy_type == "noproxy":
            return None

        host = proxy_config.get("proxyHost", "")
        port = proxy_config.get("proxyPort", "")
        user = proxy_config.get("proxyUser", "")
        passwd = proxy_config.get("proxyPassword", "")

        if not host:
            return None

        if user and passwd:
            return f"{proxy_type}://{user}:{passwd}@{host}:{port}"
        else:
            return f"{proxy_type}://{host}:{port}"

    def _parse_proxy(self, proxy_url: str) -> Dict[str, Any]:
        """解析代理 URL 为比特浏览器格式"""
        import re

        # 格式: protocol://user:pass@host:port 或 protocol://host:port
        pattern = r"^(https?|socks5)://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)$"
        match = re.match(pattern, proxy_url)

        if not match:
            return {"proxyType": "noproxy"}

        proxy_type, user, passwd, host, port = match.groups()

        config = {
            "proxyType": proxy_type,
            "proxyHost": host,
            "proxyPort": port,
        }

        if user:
            config["proxyUser"] = user
        if passwd:
            config["proxyPassword"] = passwd

        return config

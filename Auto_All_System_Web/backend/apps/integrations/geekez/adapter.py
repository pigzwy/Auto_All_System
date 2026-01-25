"""
GeekezBrowser 适配器

将 GeekezBrowserAPI 适配为统一的 BaseBrowserAPI 接口
"""

import logging
from typing import Optional, Dict, Any, List

from apps.integrations.browser_base import (
    BaseBrowserAPI,
    BrowserType,
    LaunchInfo,
    ProfileInfo,
)
from apps.integrations.geekez.api import GeekezBrowserAPI

logger = logging.getLogger(__name__)


class GeekezBrowserAdapter(BaseBrowserAPI):
    """
    GeekezBrowser 适配器

    实现统一的浏览器接口
    """

    browser_type = BrowserType.GEEKEZ

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        # When running in Docker, the GeekezBrowser control server is on the host machine,
        # so we must respect env vars (GEEKEZ_API_HOST/GEEKEZ_API_PORT). Passing explicit
        # defaults like 127.0.0.1 would incorrectly point to the container itself.
        self._api = GeekezBrowserAPI(host=host, port=port)

    def health_check(self) -> bool:
        """检查 GeekezBrowser 服务是否在线"""
        return self._api.health_check()

    def list_profiles(self) -> List[ProfileInfo]:
        """获取所有 Profile 列表"""
        profiles = self._api.list_profiles()
        return [
            ProfileInfo(
                id=p.id,
                name=p.name,
                browser_type=self.browser_type,
                proxy=p.proxy,
                metadata=p.metadata,
            )
            for p in profiles
        ]

    def get_profile_by_name(self, name: str) -> Optional[ProfileInfo]:
        """根据名称获取 Profile"""
        p = self._api.get_profile_by_name(name)
        if not p:
            return None
        return ProfileInfo(
            id=p.id,
            name=p.name,
            browser_type=self.browser_type,
            proxy=p.proxy,
            metadata=p.metadata,
        )

    def create_or_update_profile(
        self,
        name: str,
        proxy: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProfileInfo:
        """创建或更新 Profile"""
        p = self._api.create_or_update_profile(name, proxy, metadata)
        return ProfileInfo(
            id=p.id,
            name=p.name,
            browser_type=self.browser_type,
            proxy=p.proxy,
            metadata=p.metadata,
        )

    def delete_profile(self, profile_id: str) -> bool:
        """删除 Profile"""
        return self._api.delete_profile(profile_id)

    def launch_profile(self, profile_id: str) -> Optional[LaunchInfo]:
        """启动浏览器 Profile"""
        info = self._api.launch_profile(profile_id)
        if not info:
            return None
        return LaunchInfo(
            profile_id=info.profile_id,
            browser_type=self.browser_type,
            debug_port=info.debug_port,
            cdp_endpoint=info.cdp_endpoint,
            ws_endpoint=info.ws_endpoint,
            pid=info.pid,
        )

    def close_profile(self, profile_id: str) -> bool:
        """关闭浏览器 Profile"""
        return self._api.close_profile(profile_id)

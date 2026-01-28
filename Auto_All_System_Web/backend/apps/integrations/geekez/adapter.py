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
        # DO NOT cache a GeekezBrowserAPI instance here.
        #
        # Reason: Geekez connection settings are editable from the "集成管理" UI and stored
        # in DB. If we cache the API object at process startup, the worker will keep using
        # old host/port until a restart, which looks like the code is "hard-coded".
        self._host = host
        self._port = port

    def _get_api(self) -> GeekezBrowserAPI:
        return GeekezBrowserAPI(host=self._host, port=self._port)

    def health_check(self) -> bool:
        """检查 GeekezBrowser 服务是否在线"""
        return self._get_api().health_check()

    def list_profiles(self) -> List[ProfileInfo]:
        """获取所有 Profile 列表"""
        profiles = self._get_api().list_profiles()
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
        p = self._get_api().get_profile_by_name(name)
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
        p = self._get_api().create_or_update_profile(name, proxy, metadata)
        return ProfileInfo(
            id=p.id,
            name=p.name,
            browser_type=self.browser_type,
            proxy=p.proxy,
            metadata=p.metadata,
        )

    def delete_profile(self, profile_id: str) -> bool:
        """删除 Profile"""
        return self._get_api().delete_profile(profile_id)

    def launch_profile(self, profile_id: str) -> Optional[LaunchInfo]:
        """启动浏览器 Profile"""
        info = self._get_api().launch_profile(profile_id)
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
        return self._get_api().close_profile(profile_id)

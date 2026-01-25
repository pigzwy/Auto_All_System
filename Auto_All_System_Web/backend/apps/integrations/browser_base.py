"""
浏览器抽象层

统一比特浏览器 (BitBrowser) 和 GeekezBrowser 的接口
允许业务逻辑在不同浏览器之间切换
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum


class BrowserType(str, Enum):
    """浏览器类型"""

    BITBROWSER = "bitbrowser"
    GEEKEZ = "geekez"


@dataclass
class LaunchInfo:
    """浏览器启动信息 (通用)"""

    profile_id: str
    browser_type: BrowserType
    debug_port: int
    cdp_endpoint: str
    ws_endpoint: Optional[str] = None
    pid: Optional[int] = None


@dataclass
class ProfileInfo:
    """Profile 信息 (通用)"""

    id: str
    name: str
    browser_type: BrowserType
    proxy: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseBrowserAPI(ABC):
    """
    浏览器 API 抽象基类

    所有浏览器集成必须实现此接口
    """

    browser_type: BrowserType

    @abstractmethod
    def health_check(self) -> bool:
        """检查浏览器服务是否在线"""
        pass

    @abstractmethod
    def list_profiles(self) -> List[ProfileInfo]:
        """获取所有 Profile 列表"""
        pass

    @abstractmethod
    def get_profile_by_name(self, name: str) -> Optional[ProfileInfo]:
        """根据名称获取 Profile"""
        pass

    @abstractmethod
    def create_or_update_profile(
        self,
        name: str,
        proxy: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProfileInfo:
        """创建或更新 Profile"""
        pass

    @abstractmethod
    def delete_profile(self, profile_id: str) -> bool:
        """删除 Profile"""
        pass

    @abstractmethod
    def launch_profile(self, profile_id: str) -> Optional[LaunchInfo]:
        """启动浏览器 Profile"""
        pass

    @abstractmethod
    def close_profile(self, profile_id: str) -> bool:
        """关闭浏览器 Profile"""
        pass


class BrowserManager:
    """
    浏览器管理器

    统一管理多种浏览器类型，提供统一的接口
    """

    def __init__(self):
        self._apis: Dict[BrowserType, BaseBrowserAPI] = {}
        # NOTE: Prefer GeekezBrowser as default when available.
        # We still register BitBrowser and keep all its code paths untouched.
        # If GeekezBrowser is not registered/available, fallback remains BitBrowser.
        self._default_type: BrowserType = BrowserType.BITBROWSER

    def register(self, api: BaseBrowserAPI) -> None:
        """注册浏览器 API"""
        self._apis[api.browser_type] = api

    def set_default(self, browser_type: BrowserType) -> None:
        """设置默认浏览器类型"""
        self._default_type = browser_type

    def get_api(self, browser_type: Optional[BrowserType] = None) -> BaseBrowserAPI:
        """获取指定类型的浏览器 API"""
        bt = browser_type or self._default_type
        if bt not in self._apis:
            raise ValueError(f"Browser type {bt} not registered")
        return self._apis[bt]

    def list_available(self) -> List[Dict[str, Any]]:
        """列出所有可用的浏览器及其状态"""
        result = []
        for bt, api in self._apis.items():
            result.append(
                {
                    "type": bt.value,
                    "online": api.health_check(),
                    "is_default": bt == self._default_type,
                }
            )
        return result

    # ==================== 代理方法 (使用默认浏览器) ====================

    def health_check(self, browser_type: Optional[BrowserType] = None) -> bool:
        return self.get_api(browser_type).health_check()

    def list_profiles(
        self, browser_type: Optional[BrowserType] = None
    ) -> List[ProfileInfo]:
        return self.get_api(browser_type).list_profiles()

    def launch_profile(
        self, profile_id: str, browser_type: Optional[BrowserType] = None
    ) -> Optional[LaunchInfo]:
        return self.get_api(browser_type).launch_profile(profile_id)

    def close_profile(
        self, profile_id: str, browser_type: Optional[BrowserType] = None
    ) -> bool:
        return self.get_api(browser_type).close_profile(profile_id)


# ==================== 单例实例 ====================

_browser_manager: Optional[BrowserManager] = None


def get_browser_manager() -> BrowserManager:
    """获取浏览器管理器单例"""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
        _init_default_browsers()
    return _browser_manager


def _init_default_browsers():
    """初始化默认浏览器"""
    global _browser_manager

    if _browser_manager is None:
        # 正常情况下不会发生（由 get_browser_manager 初始化）
        _browser_manager = BrowserManager()

    manager = _browser_manager

    # 注册比特浏览器
    try:
        from apps.integrations.bitbrowser.adapter import BitBrowserAdapter

        manager.register(BitBrowserAdapter())
    except Exception:
        pass

    # 注册 GeekezBrowser
    try:
        from apps.integrations.geekez.adapter import GeekezBrowserAdapter

        manager.register(GeekezBrowserAdapter())
    except Exception:
        pass

    # 默认浏览器选择策略：优先 GeekezBrowser
    # 这样新增功能（安全设置/订阅验证等）默认走 GeekezBrowser，
    # 同时保留 BitBrowser 的所有功能且不需要改动其实现。
    try:
        if BrowserType.GEEKEZ in manager._apis:
            manager.set_default(BrowserType.GEEKEZ)
    except Exception:
        # 保持现有默认值即可
        pass

"""
浏览器自动化服务 - 通过 Geekez 浏览器进行操作
"""
import logging
import os
import random
import time
from typing import Any

from DrissionPage import ChromiumPage, ChromiumOptions

logger = logging.getLogger(__name__)


class BrowserService:
    """浏览器服务封装 - 使用 Geekez 浏览器环境"""

    def __init__(
        self,
        profile_id: str | None = None,
        profile_name: str | None = None,
        proxy: str | None = None,
        headless: bool = False,
    ):
        self.profile_id = profile_id
        self.profile_name = profile_name
        self.proxy = proxy
        self.headless = headless
        self.page: ChromiumPage | None = None
        self._geekez_api: Any = None
        self._launched_profile_id: str | None = None

    def start(self) -> "BrowserService":
        """启动浏览器 - 通过 Geekez API"""
        from apps.integrations.geekez.api import GeekezBrowserAPI

        # GeekezBrowserAPI 内部会自动读取 DB 配置（GeekezIntegrationConfig.get_solo）
        # 并兼容历史环境变量；这里不再依赖旧的 GeekezConfig 模型。
        self._geekez_api = GeekezBrowserAPI()

        if not self._geekez_api.health_check():
            raise RuntimeError(
                "Geekez 浏览器服务不可用，请先在 /api/v1/geekez/config/ 配置并通过 /api/v1/geekez/config/test/ 测试连通"
            )

        if self.profile_id:
            profile_id = self.profile_id
        elif self.profile_name:
            profile_info = self._geekez_api.create_or_update_profile(
                name=self.profile_name,
                proxy=self.proxy,
            )
            profile_id = profile_info.id
        else:
            profile_info = self._geekez_api.create_or_update_profile(
                name=f"gpt_auto_{int(time.time())}",
                proxy=self.proxy,
            )
            profile_id = profile_info.id

        launch_info = self._geekez_api.launch_profile(profile_id)
        if not launch_info or not launch_info.debug_port:
            raise RuntimeError(f"启动 Geekez profile 失败: {profile_id}")

        self._launched_profile_id = profile_id
        debug_port = launch_info.debug_port

        # 确定连接地址（Docker 环境需要用 host.docker.internal）
        # 与 openai_register.connect_to_browser 保持一致
        is_docker = os.environ.get("DJANGO_ENVIRONMENT") == "docker"
        use_hostnet = (
            os.environ.get("USE_HOST_NETWORK") == "1"
            or os.environ.get("DB_HOST") in ("127.0.0.1", "localhost")
        )
        if is_docker and not use_hostnet:
            host = "host.docker.internal"
        else:
            host = "127.0.0.1"

        # Docker bridge 网络下需要 TCP 转发
        if host != "127.0.0.1":
            from plugins.gpt_business.services.openai_register import _start_tcp_forwarder
            logger.info(f"Docker 环境：启动 TCP 转发 127.0.0.1:{debug_port} → {host}:{debug_port}")
            _start_tcp_forwarder(debug_port, host, debug_port)
            connect_addr = f"127.0.0.1:{debug_port}"
        else:
            connect_addr = f"{host}:{debug_port}"

        # 使用 set_address 连接到已启动的 Geekez 浏览器（而非 set_local_port 启动新进程）
        opts = ChromiumOptions()
        opts.set_address(connect_addr)

        self.page = ChromiumPage(opts)
        logger.info(f"Geekez 浏览器已启动: profile={profile_id}, addr={connect_addr}")
        return self

    def quit(self) -> None:
        """关闭浏览器"""
        if self.page:
            try:
                self.page.quit()
            except Exception as e:
                logger.warning(f"关闭 DrissionPage 失败: {e}")
            finally:
                self.page = None
        
        if self._geekez_api and self._launched_profile_id:
            try:
                self._geekez_api.close_profile(self._launched_profile_id)
                logger.info(f"Geekez profile 已关闭: {self._launched_profile_id}")
            except Exception as e:
                logger.warning(f"关闭 Geekez profile 失败: {e}")

    def __enter__(self) -> "BrowserService":
        return self.start()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.quit()

    def goto(self, url: str, wait: float = 2.0) -> None:
        if not self.page:
            raise RuntimeError("浏览器未启动")
        self.page.get(url)
        time.sleep(wait)

    def current_url(self) -> str:
        if not self.page:
            return ""
        return self.page.url or ""

    def wait_for_url_contains(self, keyword: str, timeout: float = 30.0) -> bool:
        if not self.page:
            return False
        start = time.time()
        while time.time() - start < timeout:
            if keyword in self.current_url():
                return True
            time.sleep(0.5)
        return False

    def find_element(self, selector: str, timeout: float = 10.0) -> Any:
        if not self.page:
            return None
        start = time.time()
        while time.time() - start < timeout:
            try:
                ele = self.page.ele(selector)
                if ele:
                    return ele
            except Exception:
                pass
            time.sleep(0.3)
        return None

    def click(self, selector: str, timeout: float = 10.0) -> bool:
        ele = self.find_element(selector, timeout)
        if ele:
            try:
                ele.click()
                return True
            except Exception as e:
                logger.warning(f"点击失败 {selector}: {e}")
        return False

    def type_text(self, selector: str, text: str, human_like: bool = True) -> bool:
        ele = self.find_element(selector)
        if not ele:
            return False
        try:
            ele.clear()
            if human_like:
                for char in text:
                    ele.input(char)
                    time.sleep(random.uniform(0.05, 0.15))
            else:
                ele.input(text)
            return True
        except Exception as e:
            logger.warning(f"输入失败 {selector}: {e}")
            return False

    def get_text(self, selector: str) -> str:
        ele = self.find_element(selector)
        if ele:
            return ele.text or ""
        return ""

    def exists(self, selector: str, timeout: float = 3.0) -> bool:
        return self.find_element(selector, timeout) is not None

    def wait(self, seconds: float) -> None:
        time.sleep(seconds)

    def human_delay(self, min_sec: float = 0.5, max_sec: float = 1.5) -> None:
        time.sleep(random.uniform(min_sec, max_sec))

    def screenshot(self, path: str) -> bool:
        if not self.page:
            return False
        try:
            self.page.get_screenshot(path)
            return True
        except Exception as e:
            logger.warning(f"截图失败: {e}")
            return False

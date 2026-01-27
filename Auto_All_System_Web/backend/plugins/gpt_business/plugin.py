import logging

from django.urls import include, path

from apps.plugins.base import BasePlugin, PluginStatus

logger = logging.getLogger(__name__)


class Plugin(BasePlugin):
    name = "gpt_business"
    display_name = "GPT Business"
    version = "1.0.0"
    description = "OpenAI Team 批量开通/邀请自动化"

    dependencies: list[str] = []
    shared_resources: list[str] = []

    def install(self) -> bool:
        # 目前不引入独立 DB Model，配置与任务记录存放在 PluginState.settings
        return True

    def uninstall(self) -> bool:
        return True

    def enable(self) -> bool:
        try:
            if not self.validate_shared_resources():
                return False

            self._enabled = True
            self.status = PluginStatus.ACTIVE
            return True
        except Exception as e:
            logger.error(f"Failed to enable {self.display_name}: {e}", exc_info=True)
            return False

    def disable(self) -> bool:
        try:
            self._enabled = False
            self.status = PluginStatus.DISABLED
            return True
        except Exception as e:
            logger.error(f"Failed to disable {self.display_name}: {e}", exc_info=True)
            return False

    def get_urls(self):
        from . import urls

        return [
            path("api/v1/plugins/gpt-business/", include(urls)),
        ]

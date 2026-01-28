"""GeekezBrowser 集成配置

目标：把 Geekez 的 host/port/token 等配置从环境变量迁移到 Web 的“集成管理”里。
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


def _get_cipher() -> Fernet:
    # 与 apps.integrations.models.UserAPIKey 的加密方式保持一致
    key = settings.ENCRYPTION_KEY.encode()
    derived_key = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
    return Fernet(derived_key)


class GeekezIntegrationConfig(models.Model):
    """GeekezBrowser 全局配置（singleton via key='default'）"""

    key = models.CharField(max_length=50, unique=True, default="default")

    control_host = models.CharField(max_length=255, default="127.0.0.1")
    control_port = models.PositiveIntegerField(default=19527)
    control_token_encrypted = models.TextField(blank=True, default="")

    api_server_host = models.CharField(max_length=255, default="127.0.0.1")
    api_server_port = models.PositiveIntegerField(default=12138)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "geekez_integration_configs"
        verbose_name = "GeekezBrowser 配置"
        verbose_name_plural = "GeekezBrowser 配置"

    @classmethod
    def get_solo(cls) -> "GeekezIntegrationConfig":
        # 首次创建时尽量继承环境变量配置，避免升级后立刻覆盖旧部署。
        defaults = {
            "control_host": os.environ.get("GEEKEZ_CONTROL_HOST")
            or os.environ.get("GEEKEZ_API_HOST", "127.0.0.1"),
            "control_port": int(
                os.environ.get("GEEKEZ_CONTROL_PORT")
                or os.environ.get("GEEKEZ_API_PORT", "19527")
            ),
            "api_server_host": os.environ.get("GEEKEZ_API_SERVER_HOST", "127.0.0.1"),
            "api_server_port": int(os.environ.get("GEEKEZ_API_SERVER_PORT", "12138")),
        }

        obj, created = cls.objects.get_or_create(key="default", defaults=defaults)
        if created:
            token = (
                os.environ.get("GEEKEZ_CONTROL_TOKEN")
                or os.environ.get("GEEKEZ_API_TOKEN")
                or ""
            ).strip()
            if token:
                obj.set_control_token(token)
                obj.save(update_fields=["control_token_encrypted", "updated_at"])
        return obj

    def get_control_token(self) -> str:
        if not self.control_token_encrypted:
            return ""
        try:
            decrypted = _get_cipher().decrypt(self.control_token_encrypted.encode())
            return decrypted.decode()
        except Exception:
            return ""

    def set_control_token(self, token: str):
        token = str(token or "")
        if not token:
            self.control_token_encrypted = ""
            return

        encrypted = _get_cipher().encrypt(token.encode())
        self.control_token_encrypted = encrypted.decode()

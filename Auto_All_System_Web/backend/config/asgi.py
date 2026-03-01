"""
ASGI config for Auto_All_System project.
Supports WebSocket
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# WebSocket 路由占位，待实际 consumers 实现后再导入

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            # 待实现: 添加 WebSocket URL patterns
            []
        )
    ),
})

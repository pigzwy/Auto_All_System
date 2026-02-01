"""
Cloud Mail 配置视图
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

from .models import CloudMailConfig
from .serializers import (
    CloudMailConfigSerializer,
    CloudMailConfigListSerializer,
    TestEmailSerializer,
)
from .services.client import CloudMailClient

logger = logging.getLogger(__name__)


class CloudMailConfigViewSet(viewsets.ModelViewSet):
    """
    Cloud Mail 配置管理

    提供域名邮箱配置的 CRUD 操作和测试功能
    """

    queryset = CloudMailConfig.objects.all().order_by("-is_default", "-created_at")
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == "list":
            return CloudMailConfigListSerializer
        return CloudMailConfigSerializer

    @action(detail=True, methods=["post"])
    def test_connection(self, request, pk=None):
        """
        测试 API 连接

        验证配置的 API 地址和 Token 是否有效
        """
        config = self.get_object()

        try:
            domains = CloudMailConfigSerializer._normalize_domains(config.domains)
            client = CloudMailClient(
                api_base=config.api_base,
                api_token=config.api_token,
                domains=domains,
                default_role=config.default_role,
            )

            # 尝试列出邮件来测试连接
            client.list_emails(size=1)
            client.close()

            return Response(
                {"success": True, "message": "连接成功！API 配置有效"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Cloud Mail connection test failed: {e}")
            return Response(
                {"success": False, "message": f"连接失败: {str(e)}"},
                status=status.HTTP_200_OK,
            )

    @action(detail=True, methods=["post"])
    def test_email(self, request, pk=None):
        """
        测试发送邮件

        创建一个临时邮箱并查询邮件列表
        """
        config = self.get_object()
        to_email = request.data.get("to_email", "")

        if not to_email:
            return Response(
                {"success": False, "message": "请提供收件人邮箱"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            domains = CloudMailConfigSerializer._normalize_domains(config.domains)
            client = CloudMailClient(
                api_base=config.api_base,
                api_token=config.api_token,
                domains=domains,
                default_role=config.default_role,
            )

            # 创建一个测试邮箱
            test_email, test_password = client.create_random_user()
            client.close()

            return Response(
                {
                    "success": True,
                    "message": "测试邮箱创建成功！",
                    "data": {
                        "email": test_email,
                        "password": test_password,
                    },
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Cloud Mail test email failed: {e}")
            return Response(
                {"success": False, "message": f"测试失败: {str(e)}"},
                status=status.HTTP_200_OK,
            )

    @action(detail=True, methods=["post"])
    def set_default(self, request, pk=None):
        """设置为默认配置"""
        config = self.get_object()
        config.is_default = True
        config.save()  # save 方法会自动处理其他配置的 is_default

        return Response(
            {"success": True, "message": f"已将 {config.name} 设置为默认配置"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def get_default(self, request):
        """获取默认配置"""
        config = CloudMailConfig.get_default()
        if config:
            serializer = CloudMailConfigListSerializer(config)
            return Response(serializer.data)
        return Response(
            {"message": "暂无可用配置"},
            status=status.HTTP_404_NOT_FOUND,
        )

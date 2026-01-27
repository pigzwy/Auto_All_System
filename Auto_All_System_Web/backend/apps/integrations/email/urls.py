"""
Cloud Mail URL 配置
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CloudMailConfigViewSet

router = DefaultRouter()
router.register(r"configs", CloudMailConfigViewSet, basename="cloudmail-config")

urlpatterns = [
    path("", include(router.urls)),
]

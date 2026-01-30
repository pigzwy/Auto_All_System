"""
虚拟卡URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CardViewSet, CardUsageLogViewSet, CardApiConfigViewSet

router = DefaultRouter()
# 注意：具体路径要放在空路径前面，否则会被拦截
router.register('api-configs', CardApiConfigViewSet, basename='card-api-config')
router.register('usage-logs', CardUsageLogViewSet, basename='card-usage-log')
router.register('', CardViewSet, basename='card')

urlpatterns = [
    path('', include(router.urls)),
]

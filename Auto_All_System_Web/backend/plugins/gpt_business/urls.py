from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AccountsViewSet, CeleryTaskViewSet, SettingsViewSet, StatisticsViewSet, TaskViewSet


router = DefaultRouter()
router.register(r"settings", SettingsViewSet, basename="gpt-business-settings")
router.register(r"tasks", TaskViewSet, basename="gpt-business-tasks")
router.register(r"accounts", AccountsViewSet, basename="gpt-business-accounts")
router.register(r"celery-tasks", CeleryTaskViewSet, basename="gpt-business-celery-tasks")
router.register(r"statistics", StatisticsViewSet, basename="gpt-business-statistics")


urlpatterns = [
    path("", include(router.urls)),
]

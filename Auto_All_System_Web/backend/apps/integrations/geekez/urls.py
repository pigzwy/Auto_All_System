from django.urls import path

from .views import GeekezConfigView, GeekezTestConnectionView


urlpatterns = [
    path("config/", GeekezConfigView.as_view(), name="geekez-config"),
    path("config/test/", GeekezTestConnectionView.as_view(), name="geekez-config-test"),
]

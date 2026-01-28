from __future__ import annotations

from rest_framework import serializers

from .models import GeekezIntegrationConfig


class GeekezIntegrationConfigSerializer(serializers.ModelSerializer):
    has_control_token = serializers.SerializerMethodField()
    # write-only: 前端不回显 token
    control_token = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = GeekezIntegrationConfig
        fields = [
            "control_host",
            "control_port",
            "api_server_host",
            "api_server_port",
            "has_control_token",
            "control_token",
        ]

    def get_has_control_token(self, obj: GeekezIntegrationConfig) -> bool:
        return bool(obj.control_token_encrypted)

    def update(self, instance: GeekezIntegrationConfig, validated_data):
        token_provided = "control_token" in validated_data
        token = validated_data.pop("control_token", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if token_provided:
            instance.set_control_token(token)

        instance.save()
        return instance


class GeekezTestRequestSerializer(serializers.Serializer):
    # 允许传入临时值，不保存
    control_host = serializers.CharField(required=False, allow_blank=True)
    control_port = serializers.IntegerField(required=False, min_value=1, max_value=65535)
    control_token = serializers.CharField(required=False, allow_blank=True)

    api_server_host = serializers.CharField(required=False, allow_blank=True)
    api_server_port = serializers.IntegerField(required=False, min_value=1, max_value=65535)

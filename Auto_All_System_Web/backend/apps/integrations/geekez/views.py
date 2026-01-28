from __future__ import annotations

import os
import time
from typing import Any, Dict

import requests
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .api import GeekezBrowserAPI
from .models import GeekezIntegrationConfig
from .serializers import GeekezIntegrationConfigSerializer, GeekezTestRequestSerializer


class GeekezConfigView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        cfg = GeekezIntegrationConfig.get_solo()
        return Response(GeekezIntegrationConfigSerializer(cfg).data)

    def put(self, request):
        cfg = GeekezIntegrationConfig.get_solo()
        serializer = GeekezIntegrationConfigSerializer(cfg, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        cfg = serializer.save()
        return Response(GeekezIntegrationConfigSerializer(cfg).data)


class GeekezTestConnectionView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        # 支持传入临时配置（不保存）
        cfg = GeekezIntegrationConfig.get_solo()

        req = GeekezTestRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        data = req.validated_data

        control_host = data.get("control_host") or cfg.control_host
        control_port = data.get("control_port") or cfg.control_port
        control_token = (
            data["control_token"]
            if "control_token" in data
            else cfg.get_control_token()
        )

        api_host = data.get("api_server_host") or cfg.api_server_host
        api_port = data.get("api_server_port") or cfg.api_server_port

        api = GeekezBrowserAPI(
            host=control_host,
            port=control_port,
            timeout=8,
            control_token=control_token,
            api_server_host=api_host,
            api_server_port=api_port,
            use_db_config=False,
        )

        result: Dict[str, Any] = {
            "control": self._test_control(api),
            "api_server": self._test_api_server(api),
        }
        return Response(result)

    def _test_control(self, api: GeekezBrowserAPI) -> Dict[str, Any]:
        start = time.time()

        def probe(url: str):
            resp = requests.get(url, timeout=8, headers=api._control_headers())
            ok = resp.status_code == 200
            data = resp.json() if resp.content and ok else None
            return ok, resp.status_code, data

        def probe_profiles(base_url: str) -> bool:
            # Control Server in older versions provides /profiles (required for /profiles/{uuid}/launch).
            try:
                resp = requests.get(
                    f"{base_url}/profiles",
                    timeout=8,
                    headers=api._control_headers(),
                )
                return resp.status_code == 200
            except Exception:
                return False

        attempts: list[dict[str, Any]] = []
        last_error: str | None = None

        primary_url = f"{api.base_url}/health"
        urls = [primary_url]

        # Docker 场景：宿主机 Geekez 往往只监听 127.0.0.1，容器无法直连。
        # 我们在 docker-compose.linux.yml 提供了默认转发端口：19528 -> 19527
        if api.port == 19527:
            urls.append(f"http://{api.host}:19528/health")

        for url in urls:
            try:
                ok, status_code, data = probe(url)
                attempts.append({"url": url, "ok": ok, "status_code": status_code})
                if ok:
                    ms = int((time.time() - start) * 1000)
                    note = None
                    if url != primary_url:
                        note = "Control Server 通过转发端口 19528 访问成功（宿主机可能仅监听 127.0.0.1）"

                    supports_launch = probe_profiles(url.rsplit("/health", 1)[0])
                    return {
                        "ok": True,
                        "base_url": api.base_url,
                        "url": url,
                        "latency_ms": ms,
                        "status_code": status_code,
                        "data": data,
                        "attempts": attempts,
                        "supports_launch": supports_launch,
                        **({"note": note} if note else {}),
                    }
            except Exception as e:
                last_error = str(e)
                attempts.append({"url": url, "ok": False, "error": last_error})

        ms = int((time.time() - start) * 1000)
        return {
            "ok": False,
            "base_url": api.base_url,
            "url": primary_url,
            "latency_ms": ms,
            "error": last_error or "Unknown error",
            "attempts": attempts,
        }

    def _test_api_server(self, api: GeekezBrowserAPI) -> Dict[str, Any]:
        start = time.time()

        def probe(url: str):
            resp = requests.get(url, timeout=8)
            ok = resp.status_code == 200
            payload = resp.json() if resp.content and ok else None
            return ok, resp.status_code, payload

        attempts: list[dict[str, Any]] = []
        last_error: str | None = None

        primary_url = f"{api.api_server_url}/api/status"
        urls = [primary_url]

        # Docker 场景默认转发端口：12139 -> 12138
        if api.api_server_port == 12138:
            urls.append(f"http://{api.api_server_host}:12139/api/status")

        for url in urls:
            try:
                ok, status_code, payload = probe(url)
                attempts.append({"url": url, "ok": ok, "status_code": status_code})
                if ok:
                    ms = int((time.time() - start) * 1000)
                    note = None
                    if url != primary_url:
                        note = "API Server 通过转发端口 12139 访问成功（宿主机可能仅监听 127.0.0.1）"
                    return {
                        "ok": True,
                        "url": url,
                        "latency_ms": ms,
                        "status_code": status_code,
                        "data": payload,
                        "attempts": attempts,
                        **({"note": note} if note else {}),
                    }
            except Exception as e:
                last_error = str(e)
                attempts.append({"url": url, "ok": False, "error": last_error})

        ms = int((time.time() - start) * 1000)
        return {
            "ok": False,
            "url": primary_url,
            "latency_ms": ms,
            "error": last_error or "Unknown error",
            "attempts": attempts,
        }

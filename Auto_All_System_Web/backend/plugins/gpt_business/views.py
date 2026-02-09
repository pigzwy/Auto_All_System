from __future__ import annotations

from collections import deque
import os
import secrets
import string
from pathlib import Path
import uuid
from typing import Any

from celery.result import AsyncResult
from django.conf import settings as django_settings
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from .serializers import (
    AccountCreateChildSerializer,
    AccountCreateMotherSerializer,
    AccountUpdateSerializer,
    CrsTestSerializer,
    S2aTestSerializer,
    SettingsUpdateSerializer,
    TaskCreateSerializer,
)
from .storage import (
    add_account,
    add_task,
    clear_tasks,
    clear_tasks_for_mother,
    delete_account,
    find_account,
    find_task,
    get_settings,
    list_accounts,
    list_tasks,
    patch_account,
    patch_task,
    update_settings,
)
from .tasks import (
    auto_invite_task,
    invite_only_task,
    launch_geekez_task,
    self_register_task,
    sub2api_sink_task,
    team_push_task,
)
from .trace_cleanup import cleanup_trace_files, get_trace_cleanup_settings


def _normalize_id_list(raw: Any) -> list[str]:
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(",") if part.strip()]
    if isinstance(raw, list):
        values: list[str] = []
        for item in raw:
            if item is None:
                continue
            val = str(item).strip()
            if val:
                values.append(val)
        return values
    return []


def _batch_countdown(index: int, concurrency: int) -> int:
    if concurrency <= 0:
        return 0
    return int(index // concurrency)


def _parse_self_register_card_options(data: Any) -> tuple[str, int | None, str | None]:
    card_mode = str((data or {}).get("card_mode") or "random").strip().lower()
    if card_mode not in {"selected", "random", "manual"}:
        return "", None, "card_mode must be one of: selected, random, manual"

    selected_card_id: int | None = None
    selected_raw = (data or {}).get("selected_card_id")
    if card_mode == "selected":
        if selected_raw in (None, ""):
            return "", None, "selected_card_id is required when card_mode=selected"
        try:
            selected_card_id = int(selected_raw)
        except (TypeError, ValueError):
            return "", None, "selected_card_id must be an integer"

        from apps.cards.models import Card

        card = Card.objects.filter(id=selected_card_id).first()
        if not card:
            return "", None, "selected_card_id not found"
        if not card.is_available():
            return "", None, "selected_card_id is not available"

    return card_mode, selected_card_id, None


def _parse_keep_profile_on_fail(data: Any) -> bool:
    raw = (data or {}).get("keep_profile_on_fail")
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _mask_secret(value: str) -> str:
    value = str(value or "")
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:3]}***{value[-3:]}"


def _mask_settings(settings: dict[str, Any]) -> dict[str, Any]:
    masked = {**settings}
    gptmail = {**(masked.get("gptmail") or {})}
    if "api_key" in gptmail:
        gptmail["api_key"] = _mask_secret(str(gptmail.get("api_key") or ""))
    masked["gptmail"] = gptmail

    teams: list[dict[str, Any]] = []
    for t in masked.get("teams") or []:
        if not isinstance(t, dict):
            continue
        item = {**t}
        if "auth_token" in item:
            item["auth_token"] = _mask_secret(str(item.get("auth_token") or ""))
        if "owner_password" in item:
            item["owner_password"] = _mask_secret(str(item.get("owner_password") or ""))
        teams.append(item)
    masked["teams"] = teams

    # 其它敏感信息
    if isinstance(masked.get("crs"), dict) and "admin_token" in masked["crs"]:
        masked["crs"] = {**masked["crs"], "admin_token": _mask_secret(str(masked["crs"].get("admin_token") or ""))}
    if isinstance(masked.get("cpa"), dict) and "admin_password" in masked["cpa"]:
        masked["cpa"] = {**masked["cpa"], "admin_password": _mask_secret(str(masked["cpa"].get("admin_password") or ""))}
    if isinstance(masked.get("s2a"), dict):
        s2a = {**masked["s2a"]}
        if "admin_key" in s2a:
            s2a["admin_key"] = _mask_secret(str(s2a.get("admin_key") or ""))
        if "admin_token" in s2a:
            s2a["admin_token"] = _mask_secret(str(s2a.get("admin_token") or ""))
        masked["s2a"] = s2a

    # s2a_targets
    s2a_targets_masked: list[dict[str, Any]] = []
    if isinstance(masked.get("s2a_targets"), list):
        for t in masked.get("s2a_targets") or []:
            if not isinstance(t, dict):
                continue
            item = {**t}
            cfg = item.get("config")
            if isinstance(cfg, dict):
                cfg2 = {**cfg}
                if "admin_key" in cfg2:
                    cfg2["admin_key"] = _mask_secret(str(cfg2.get("admin_key") or ""))
                if "admin_token" in cfg2:
                    cfg2["admin_token"] = _mask_secret(str(cfg2.get("admin_token") or ""))
                item["config"] = cfg2
            s2a_targets_masked.append(item)
    if s2a_targets_masked:
        masked["s2a_targets"] = s2a_targets_masked

    # proxies 里的密码也做脱敏
    proxies: list[dict[str, Any]] = []
    for p in masked.get("proxies") or []:
        if not isinstance(p, dict):
            continue
        item = {**p}
        if "password" in item:
            item["password"] = _mask_secret(str(item.get("password") or ""))
        proxies.append(item)
    if proxies:
        masked["proxies"] = proxies

    if isinstance(masked.get("checkout"), dict):
        checkout = {**masked["checkout"]}
        if "card_number" in checkout:
            card = str(checkout.get("card_number") or "")
            checkout["card_number"] = f"****{card[-4:]}" if len(card) >= 4 else "****"
        if "card_cvc" in checkout:
            checkout["card_cvc"] = "***"
        masked["checkout"] = checkout

    return masked


class SettingsViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def list(self, request):
        settings = get_settings()
        return Response(_mask_settings(settings))

    @action(detail=False, methods=["get", "put"], url_path="current")
    def current(self, request):
        if request.method == "GET":
            settings = get_settings()
            return Response(_mask_settings(settings))

        serializer = SettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        def mutator(settings: dict[str, Any]) -> dict[str, Any]:
            if "gptmail" in payload:
                current = settings.get("gptmail") or {}
                settings["gptmail"] = {**current, **payload["gptmail"]}
            if "teams" in payload:
                settings["teams"] = payload["teams"]

            # multiple s2a targets (merge + preserve secrets)
            if "s2a_targets" in payload:
                incoming = payload.get("s2a_targets") or []
                existing = settings.get("s2a_targets") if isinstance(settings.get("s2a_targets"), list) else []

                existing_by_key: dict[str, dict[str, Any]] = {}
                for t in existing:
                    if not isinstance(t, dict):
                        continue
                    k = str(t.get("key") or "").strip()
                    if k:
                        existing_by_key[k] = t

                merged: list[dict[str, Any]] = []
                for t in incoming:
                    if not isinstance(t, dict):
                        continue
                    key = str(t.get("key") or "").strip()
                    if not key:
                        continue

                    prev = existing_by_key.get(key) or {}
                    prev_cfg = prev.get("config") if isinstance(prev.get("config"), dict) else {}
                    new_cfg = t.get("config") if isinstance(t.get("config"), dict) else {}

                    cfg = {**prev_cfg, **new_cfg}
                    for secret_field in ["admin_key", "admin_token"]:
                        v = str(new_cfg.get(secret_field) or "").strip()
                        # empty or masked -> keep existing
                        if not v or "*" in v:
                            if secret_field in prev_cfg:
                                cfg[secret_field] = prev_cfg.get(secret_field)

                    merged.append({**prev, **t, "key": key, "config": cfg})

                settings["s2a_targets"] = merged
            if "s2a_default_target" in payload:
                settings["s2a_default_target"] = payload["s2a_default_target"]

            # 兼容 oai-team-auto-provisioner 的配置项
            for key in [
                "proxy_enabled",
                "proxies",
                "auth_provider",
                "include_team_owners",
                "request",
                "verification",
                "browser",
                "default_password",
                "accounts_per_team",
            ]:
                if key in payload:
                    settings[key] = payload[key]

            for section in ["crs", "cpa", "s2a", "checkout"]:
                if section in payload:
                    current_section = settings.get(section) or {}
                    if isinstance(current_section, dict) and isinstance(payload[section], dict):
                        merged = {**current_section, **payload[section]}

                        # preserve secrets when payload is empty/masked
                        if section == "crs":
                            v = str((payload[section] or {}).get("admin_token") or "").strip()
                            if (not v or "*" in v) and "admin_token" in current_section:
                                merged["admin_token"] = current_section.get("admin_token")

                        settings[section] = merged
                    else:
                        settings[section] = payload[section]
            return settings

        new_settings = update_settings(mutator)
        return Response(_mask_settings(new_settings))

    @action(detail=False, methods=["post"], url_path="s2a/test")
    def s2a_test(self, request):
        """测试 S2A API Base + admin_key/admin_token 是否可用。

        支持两种方式：
        - 传 target_key：从 settings.s2a_targets 中读取 config
        - 传 config：直接用该 config 测试（不依赖保存）
        """
        serializer = S2aTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        settings = get_settings()
        target_key = str(payload.get("target_key") or "").strip()
        config = payload.get("config") if isinstance(payload.get("config"), dict) else None

        if not config:
            if target_key and isinstance(settings.get("s2a_targets"), list):
                for t in settings.get("s2a_targets") or []:
                    if not isinstance(t, dict):
                        continue
                    if str(t.get("key") or "").strip() == target_key and isinstance(t.get("config"), dict):
                        config = t.get("config")
                        break
            if not config:
                config = settings.get("s2a") if isinstance(settings.get("s2a"), dict) else {}

        api_base = str((config or {}).get("api_base") or "").strip()
        admin_key = str((config or {}).get("admin_key") or "").strip()
        admin_token = str((config or {}).get("admin_token") or "").strip()

        if not api_base:
            return Response({"success": False, "message": "missing s2a.api_base"}, status=status.HTTP_400_BAD_REQUEST)
        if not admin_key and not admin_token:
            return Response({"success": False, "message": "missing s2a.admin_key/admin_token"}, status=status.HTTP_400_BAD_REQUEST)

        timeout = int(((settings.get("request") or {}).get("timeout") or 20))

        from .services.sub2api_sink_service import sub2api_test_connection

        ok, msg = sub2api_test_connection(
            api_base=api_base,
            admin_key=admin_key,
            admin_token=admin_token,
            timeout=timeout,
        )
        return Response({"success": bool(ok), "message": msg, "target_key": target_key or ""})

    @action(detail=False, methods=["get", "post"], url_path="trace-cleanup")
    def trace_cleanup(self, request):
        settings = get_settings()
        payload = request.data if isinstance(request.data, dict) else {}
        query = request.query_params

        def _pick_int(key: str):
            if key in payload:
                val = payload.get(key)
            else:
                val = query.get(key)
            if val is None:
                return None
            try:
                return int(val)
            except Exception:
                return None

        overrides: dict[str, int | str] = {}
        for key in ["max_age_days", "max_total_size_mb", "max_files", "min_keep_files"]:
            v = _pick_int(key)
            if v is not None:
                overrides[key] = v

        pattern = payload.get("pattern") or query.get("pattern")
        if pattern:
            overrides["pattern"] = str(pattern)

        apply_flag = payload.get("apply") if request.method == "POST" else None
        apply = False
        if request.method == "POST" and apply_flag is not None:
            apply = str(apply_flag).lower() in ["1", "true", "yes"]

        result = cleanup_trace_files(settings, dry_run=not apply, overrides=overrides)
        effective_settings = get_trace_cleanup_settings(settings)
        if overrides:
            if "max_age_days" in overrides:
                effective_settings["max_age_days"] = int(overrides["max_age_days"])
            if "max_total_size_mb" in overrides:
                effective_settings["max_total_size_mb"] = int(overrides["max_total_size_mb"])
            if "max_files" in overrides:
                effective_settings["max_files"] = int(overrides["max_files"])
            if "min_keep_files" in overrides:
                effective_settings["min_keep_files"] = int(overrides["min_keep_files"])
            if "pattern" in overrides:
                effective_settings["pattern"] = str(overrides["pattern"])

        return Response({"applied": apply, "settings": effective_settings, **result})

    @action(detail=False, methods=["post"], url_path="crs/test")
    def crs_test(self, request):
        """测试 CRS api_base + admin_token 是否可用。"""
        serializer = CrsTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        settings = get_settings()
        config = payload.get("config") if isinstance(payload.get("config"), dict) else None
        if not config:
            config = settings.get("crs") if isinstance(settings.get("crs"), dict) else {}

        api_base = str((config or {}).get("api_base") or "").strip()
        admin_token = str((config or {}).get("admin_token") or "").strip()

        if not api_base:
            return Response({"success": False, "message": "missing crs.api_base"}, status=status.HTTP_400_BAD_REQUEST)
        if not admin_token:
            return Response({"success": False, "message": "missing crs.admin_token"}, status=status.HTTP_400_BAD_REQUEST)

        timeout = int(((settings.get("request") or {}).get("timeout") or 20))
        from .services.sub2api_sink_service import crs_test_connection

        ok, msg = crs_test_connection(api_base=api_base, admin_token=admin_token, timeout=timeout)
        return Response({"success": bool(ok), "message": msg})


class TaskViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def list(self, request):
        settings = get_settings()
        tasks = list_tasks(settings)
        return Response(tasks)

    def retrieve(self, request, pk=None):
        settings = get_settings()
        task = find_task(settings, str(pk))
        if not task:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(task)

    def create(self, request):
        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        flow = str(payload.get("flow") or "invite_only")

        settings = get_settings()
        teams = settings.get("teams") or []
        team_cfg = next((x for x in teams if x.get("name") == payload["team_name"]), None)
        if not team_cfg:
            return Response(
                {"detail": "Team not found in settings"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        gptmail_cfg = settings.get("gptmail") or {}
        if not gptmail_cfg.get("api_base") or not gptmail_cfg.get("api_key"):
            return Response(
                {"detail": "GPTMail settings missing api_base/api_key"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if flow == "invite_only":
            if not str(team_cfg.get("auth_token") or "").strip():
                return Response(
                    {"detail": "invite_only requires team.auth_token"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response({"detail": "Unknown flow"}, status=status.HTTP_400_BAD_REQUEST)

        record_id = uuid.uuid4().hex
        record = {
            "id": record_id,
            "type": flow,
            "team_name": payload["team_name"],
            "count": payload.get("count") or 4,
            "password": payload.get("password") or "",
            "legacy_args": payload.get("legacy_args") or [],
            "status": "queued",
            "created_at": None,
            "started_at": None,
            "finished_at": None,
            "celery_task_id": "",
        }

        def add_record(settings: dict[str, Any]) -> dict[str, Any]:
            tasks = list_tasks(settings)
            record["created_at"] = timezone.now().isoformat()
            tasks.insert(0, record)
            settings["tasks"] = tasks
            return settings

        update_settings(add_record)

        celery_result = invite_only_task.delay(record_id)
        patched = patch_task(record_id, {"celery_task_id": celery_result.id})
        return Response(patched or record, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def artifacts(self, request, pk=None):
        settings = get_settings()
        task = find_task(settings, str(pk))
        if not task:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()

        def add_name(name: str) -> None:
            name = str(name or "")
            if not name or name in seen:
                return
            seen.add(name)
            normalized.append(
                {
                    "name": name,
                    "download_url": request.build_absolute_uri(
                        f"/api/v1/plugins/gpt-business/tasks/{task['id']}/download/{name}/"
                    ),
                }
            )

        # 任务完成后写入的 artifacts
        result = task.get("result") or {}
        artifacts = result.get("artifacts") or []
        for a in artifacts:
            if not isinstance(a, dict):
                continue
            add_name(str(a.get("name") or ""))

        # 任务运行中就会持续落盘 run.log（以及截图等），但 result.artifacts 可能还没 patch 回来。
        media_root = Path(str(getattr(django_settings, "MEDIA_ROOT", "")))
        job_dir = media_root / "gpt_business" / "jobs" / str(task.get("id") or "")
        if job_dir.exists() and job_dir.is_dir():
            for p in sorted(job_dir.glob("*")):
                if p.is_file():
                    add_name(p.name)

        return Response(normalized)

    @action(detail=True, methods=["get"], url_path=r"download/(?P<filename>[^/]+)")
    def download(self, request, pk=None, filename: str | None = None):
        settings = get_settings()
        task = find_task(settings, str(pk))
        if not task:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        result = task.get("result") or {}
        artifacts = result.get("artifacts") or []
        filename = str(filename or "")
        artifact = next((a for a in artifacts if isinstance(a, dict) and str(a.get("name")) == filename), None)

        file_path: Path | None = None
        if artifact:
            file_path = Path(str(artifact.get("path") or ""))
        else:
            # 兼容任务运行中：run.log 等文件已经生成，但还没写回 result.artifacts
            media_root = Path(str(getattr(django_settings, "MEDIA_ROOT", "")))
            job_dir = media_root / "gpt_business" / "jobs" / str(task.get("id") or "")
            candidate = job_dir / filename
            if candidate.exists() and candidate.is_file():
                file_path = candidate

        if not file_path or not file_path.exists():
            return Response({"detail": "File missing"}, status=status.HTTP_404_NOT_FOUND)

        media_root = Path(str(getattr(django_settings, "MEDIA_ROOT", "")))
        try:
            file_path.relative_to(media_root)
        except Exception:
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        response = FileResponse(file_path.open("rb"), as_attachment=True, filename=file_path.name)
        response["Content-Length"] = os.path.getsize(str(file_path))
        return response

    @action(detail=True, methods=["get"], url_path="log")
    def log(self, request, pk=None):
        settings = get_settings()
        task = find_task(settings, str(pk))
        if not task:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        filename = str(request.query_params.get("filename") or "run.log")
        tail = request.query_params.get("tail")
        try:
            tail_lines = max(0, min(5000, int(tail))) if tail is not None else 2000
        except Exception:
            tail_lines = 2000

        media_root = Path(str(getattr(django_settings, "MEDIA_ROOT", "")))
        job_dir = media_root / "gpt_business" / "jobs" / str(task.get("id") or "")
        log_path = job_dir / filename

        if not log_path.exists() or not log_path.is_file():
            return Response(
                {
                    "filename": filename,
                    "exists": False,
                    "text": "",
                    "download_url": request.build_absolute_uri(
                        f"/api/v1/plugins/gpt-business/tasks/{task['id']}/download/{filename}/"
                    ),
                }
            )

        # 保证只能读取 MEDIA_ROOT 内文件
        try:
            log_path.relative_to(media_root)
        except Exception:
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        buf: deque[str] = deque(maxlen=tail_lines)
        try:
            with log_path.open("r", encoding="utf-8", errors="replace") as fp:
                for line in fp:
                    buf.append(line)
        except Exception:
            return Response({"detail": "Failed to read log"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        text = "".join(buf)
        return Response(
            {
                "filename": log_path.name,
                "exists": True,
                "text": text,
                "download_url": request.build_absolute_uri(
                    f"/api/v1/plugins/gpt-business/tasks/{task['id']}/download/{log_path.name}/"
                ),
            }
        )


class AccountsViewSet(ViewSet):
    """GPT 专区账号列表（母号/子号）

    说明：
    - 账号数据存储在 PluginState.settings['accounts']（JSON List）
    - 邮箱通过 CloudMail（域名邮箱）创建，返回邮箱与邮箱密码
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    @staticmethod
    def _generate_account_password(length: int = 16) -> str:
        # OpenAI 密码要求：8+，包含大小写、数字、特殊字符
        length = max(8, int(length))
        lower = string.ascii_lowercase
        upper = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*_-+=?"

        rng = secrets.SystemRandom()
        chars = [
            rng.choice(lower),
            rng.choice(upper),
            rng.choice(digits),
            rng.choice(special),
        ]
        all_chars = lower + upper + digits + special
        chars.extend(rng.choice(all_chars) for _ in range(length - len(chars)))
        rng.shuffle(chars)
        return "".join(chars)

    @staticmethod
    def _get_cloudmail_client(config_id: int):
        import json
        import re
        from apps.integrations.email.models import CloudMailConfig
        from apps.integrations.email.services.client import CloudMailClient

        cfg = CloudMailConfig.objects.filter(id=int(config_id), is_active=True).first()
        if not cfg:
            raise ValueError("CloudMailConfig not found")

        # 解析 domains，处理各种错误格式
        def parse_domains(value):
            """递归解析嵌套的 JSON 字符串"""
            if not value:
                return []
            if isinstance(value, str):
                value = value.strip()
                if value.startswith("["):
                    # 修复末尾多余逗号: ,] -> ]
                    fixed = re.sub(r',\s*]', ']', value)
                    try:
                        value = json.loads(fixed)
                    except json.JSONDecodeError:
                        return [value] if value else []
                else:
                    return [value] if value else []
            if isinstance(value, list):
                result = []
                for item in value:
                    result.extend(parse_domains(item))
                return result
            return [str(value)] if value else []

        raw_domains = parse_domains(cfg.domains)
        raw_domains = [str(x).strip() for x in raw_domains if str(x).strip()]
        if not raw_domains:
            raise ValueError(f"CloudMailConfig id={config_id} domains is empty, raw value: {cfg.domains!r}")

        # 使用 CloudMailClient 的域名标准化逻辑预检查
        normalized = [CloudMailClient._normalize_domain(d) for d in raw_domains]
        valid_domains = [d for d in normalized if d]
        if not valid_domains:
            raise ValueError(f"CloudMailConfig id={config_id} domains are all invalid after normalization. Raw: {raw_domains!r}, Normalized: {normalized!r}")

        return CloudMailClient(
            api_base=str(cfg.api_base),
            api_token=str(cfg.api_token),
            domains=valid_domains,
            default_role=str(cfg.default_role or "user"),
        )

    def list(self, request):
        settings = get_settings()
        accounts = list_accounts(settings)
        tasks = list_tasks(settings)

        active_tasks_by_mother: dict[str, dict[str, Any]] = {}
        for t in tasks:
            status = str(t.get("status") or "").strip()
            if status not in {"pending", "running"}:
                continue
            mid = str(t.get("mother_id") or "").strip()
            if not mid or mid in active_tasks_by_mother:
                continue
            active_tasks_by_mother[mid] = {
                "id": t.get("id"),
                "type": t.get("type"),
                "status": status,
                "progress_current": int(t.get("progress_current") or 0),
                "progress_total": int(t.get("progress_total") or 0),
                "progress_percent": int(t.get("progress_percent") or 0),
                "progress_label": str(t.get("progress_label") or ""),
                "created_at": t.get("created_at"),
                "started_at": t.get("started_at"),
            }

        mothers = [a for a in accounts if str(a.get("type")) == "mother"]
        children_by_parent: dict[str, list[dict[str, Any]]] = {}
        for a in accounts:
            if str(a.get("type")) != "child":
                continue
            parent_id = str(a.get("parent_id") or "")
            if not parent_id:
                continue
            children_by_parent.setdefault(parent_id, []).append(a)

        # 读取一次 Geekez profiles.json，供前端展示“Geek 环境是否存在”。
        geekez_names: set[str] = set()
        geekez_profile_ids: set[str] = set()
        try:
            from apps.integrations.browser_base import BrowserType, get_browser_manager

            manager = get_browser_manager()
            api = manager.get_api(BrowserType.GEEKEZ)
            profiles = api.list_profiles()
            geekez_names = {
                str(p.name)
                for p in profiles
                if getattr(p, "name", None)
            }
            geekez_profile_ids = {
                str(p.id)
                for p in profiles
                if getattr(p, "id", None)
            }
        except Exception:
            geekez_names = set()
            geekez_profile_ids = set()

        def _get_email_domains() -> list[str]:
            try:
                from apps.integrations.email.models import CloudMailConfig

                cfg = CloudMailConfig.get_default()
                if cfg and isinstance(cfg.domains, list):
                    return [str(x) for x in cfg.domains if str(x).strip()]
            except Exception:
                return []
            return []

        def _annotate_account(acc: dict[str, Any]) -> dict[str, Any]:
            email = str(acc.get("email") or "").strip()
            geekez_env = acc.get("geekez_env")
            # 优先使用本地记录的 geekez_profile 判断环境是否存在
            # geekez_profile 是在 launch_geekez 成功后保存的，比调用远程 API 更可靠
            geekez_profile = acc.get("geekez_profile")
            # 兼容新旧两种 profile name 格式：gpt_{email} 和 {email}
            profile_name_new = f"gpt_{email}" if email else ""
            profile_id_saved = ""
            profile_name_saved = ""
            if isinstance(geekez_profile, dict):
                profile_id_saved = str(geekez_profile.get("profile_id") or "").strip()
                profile_name_saved = str(geekez_profile.get("profile_name") or "").strip()

            has_profile = bool(
                profile_id_saved and profile_id_saved in geekez_profile_ids
            ) or bool(profile_name_saved and profile_name_saved in geekez_names) or bool(profile_name_new and profile_name_new in geekez_names) or bool(email and email in geekez_names)

            # 状态字段兜底（兼容旧数据）
            open_status = str(acc.get("open_status") or "").strip()
            register_status = str(acc.get("register_status") or "").strip()
            login_status = str(acc.get("login_status") or "").strip()
            pool_status = str(acc.get("pool_status") or "").strip()
            invite_status = str(acc.get("invite_status") or "").strip()
            team_join_status = str(acc.get("team_join_status") or "").strip()

            if not register_status:
                if open_status in {"registered", "activated"}:
                    register_status = "success"
                else:
                    register_status = "not_started"

            if not login_status:
                # mother 可能会缓存 auth_token（child 不缓存）
                if str(acc.get("auth_token") or "").strip():
                    login_status = "success"
                else:
                    login_status = "not_started"

            if not pool_status:
                pool_status = "not_started"

            if not invite_status:
                invite_status = "not_started"

            if not team_join_status:
                if str(acc.get("team_account_id") or "").strip():
                    team_join_status = "success"
                else:
                    team_join_status = "not_started"
            active_task = None
            if str(acc.get("type")) == "mother":
                active_task = active_tasks_by_mother.get(str(acc.get("id") or "").strip())

            return {
                **acc,
                "geekez_profile_exists": has_profile,
                "open_status": open_status or ("not_started" if str(acc.get("type")) == "mother" else open_status),
                "register_status": register_status,
                "login_status": login_status,
                "pool_status": pool_status,
                "invite_status": invite_status,
                "team_join_status": team_join_status,
                **({"active_task": active_task} if active_task else {}),
                **({"geekez_env": geekez_env} if isinstance(geekez_env, dict) else {}),
            }

        normalized_mothers: list[dict[str, Any]] = []
        for m in mothers:
            mid = str(m.get("id") or "")
            children = [_annotate_account(c) for c in (children_by_parent.get(mid, []) or [])]
            seat_total = int(m.get("seat_total") or 0)
            seat_used = len(children)
            normalized_mothers.append(
                {
                    **_annotate_account(m),
                    "seat_total": seat_total,
                    "seat_used": seat_used,
                    "children": children,
                }
            )

        return Response({"mothers": normalized_mothers, "email_domains": _get_email_domains()})

    @action(detail=True, methods=["get", "delete"], url_path="tasks")
    def tasks(self, request, pk=None):
        settings = get_settings()
        acc = find_account(settings, str(pk))
        if not isinstance(acc, dict) or str(acc.get("type")) != "mother":
            return Response({"detail": "Mother account not found"}, status=status.HTTP_400_BAD_REQUEST)

        if request.method.upper() == "DELETE":
            removed = clear_tasks_for_mother(str(pk), keep_in_progress=True)
            return Response({"status": "cleared", "removed": removed})

        tasks = [t for t in list_tasks(settings) if str(t.get("mother_id") or "") == str(pk)]
        return Response({"tasks": tasks})

    @action(detail=False, methods=["post"], url_path="mothers")
    def create_mother(self, request):
        serializer = AccountCreateMotherSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        config_id = int(payload["cloudmail_config_id"])
        domain = str(payload.get("domain") or "").strip() or None
        count = int(payload.get("count") or 1)
        # serializer 已提供 default=4，但这里要保留 seat_total=0 的语义
        seat_total_raw = payload.get("seat_total")
        seat_total = int(seat_total_raw) if seat_total_raw is not None else 4
        note = str(payload.get("note") or "")

        try:
            client = self._get_cloudmail_client(config_id)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if domain and domain not in (client.domains or []):
            return Response({"detail": "Domain not allowed"}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now().isoformat()
        created: list[dict[str, Any]] = []
        for _ in range(count):
            try:
                email, email_password = client.create_random_user(domain=domain)
            except Exception as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

            record_id = uuid.uuid4().hex
            account_password = self._generate_account_password()
            actual_domain = email.split("@", 1)[1] if "@" in email else ""
            created.append(
                {
                    "id": record_id,
                    "type": "mother",
                    "parent_id": "",
                    "cloudmail_config_id": config_id,
                    "cloudmail_domain": actual_domain,
                    "email": email,
                    "email_password": email_password,
                    "account_password": account_password,
                    "seat_total": seat_total,
                    "note": note,
                    # 状态字段（便于前端展示/任务跳过策略）
                    "open_status": "not_started",
                    "register_status": "not_started",
                    "register_updated_at": "",
                    "login_status": "not_started",
                    "login_updated_at": "",
                    "pool_status": "not_started",
                    "pool_updated_at": "",
                    "invite_status": "not_started",
                    "invite_updated_at": "",
                    "created_at": now,
                    "updated_at": now,
                }
            )

        def mutator(settings: dict[str, Any]) -> dict[str, Any]:
            accounts = list_accounts(settings)
            for r in reversed(created):
                accounts.insert(0, r)
            settings["accounts"] = accounts
            settings["last_updated"] = timezone.now().isoformat()
            return settings

        update_settings(mutator)
        return Response({"created": created}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="children")
    def create_child(self, request):
        serializer = AccountCreateChildSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        parent_id = str(payload.get("parent_id") or "").strip()
        settings = get_settings()
        parent_raw = find_account(settings, parent_id)
        if not isinstance(parent_raw, dict) or str(parent_raw.get("type")) != "mother":
            return Response({"detail": "Mother account not found"}, status=status.HTTP_400_BAD_REQUEST)

        parent: dict[str, Any] = parent_raw

        config_id = int(payload.get("cloudmail_config_id") or parent.get("cloudmail_config_id") or 0)
        if config_id <= 0:
            return Response({"detail": "cloudmail_config_id missing"}, status=status.HTTP_400_BAD_REQUEST)

        domain = str(payload.get("domain") or "").strip() or None
        count = int(payload.get("count") or 1)
        note = str(payload.get("note") or "")

        # seat_total=0 代表不限制
        seat_total = int(parent.get("seat_total") or 0)
        existing_children = [
            a
            for a in list_accounts(settings)
            if str(a.get("type")) == "child" and str(a.get("parent_id")) == parent_id
        ]
        if seat_total > 0 and (len(existing_children) + count) > seat_total:
            return Response({"detail": "No available seats"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            client = self._get_cloudmail_client(config_id)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if domain and domain not in (client.domains or []):
            return Response({"detail": "Domain not allowed"}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now().isoformat()
        created: list[dict[str, Any]] = []
        for _ in range(count):
            try:
                email, email_password = client.create_random_user(domain=domain)
            except Exception as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

            record_id = uuid.uuid4().hex
            account_password = self._generate_account_password()
            actual_domain = email.split("@", 1)[1] if "@" in email else ""
            created.append(
                {
                    "id": record_id,
                    "type": "child",
                    "parent_id": parent_id,
                    "cloudmail_config_id": config_id,
                    "cloudmail_domain": actual_domain,
                    "email": email,
                    "email_password": email_password,
                    "account_password": account_password,
                    "note": note,
                    # 状态字段
                    "register_status": "not_started",
                    "register_updated_at": "",
                    "login_status": "not_started",
                    "login_updated_at": "",
                    "pool_status": "not_started",
                    "pool_updated_at": "",
                    "team_join_status": "not_started",
                    "team_join_updated_at": "",
                    "created_at": now,
                    "updated_at": now,
                }
            )

        def mutator(settings: dict[str, Any]) -> dict[str, Any]:
            accounts = list_accounts(settings)
            for r in reversed(created):
                accounts.insert(0, r)
            settings["accounts"] = accounts
            settings["last_updated"] = timezone.now().isoformat()
            return settings

        update_settings(mutator)
        return Response({"created": created}, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        serializer = AccountUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patch: dict[str, Any] = {**serializer.validated_data}
        patch["updated_at"] = timezone.now().isoformat()

        account_id = str(pk)
        updated = patch_account(account_id, patch)
        if not updated:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(updated)

    def destroy(self, request, pk=None):
        account_id = str(pk)
        
        # 先获取账号信息，以便删除 geekez 环境
        settings = get_settings()
        acc = find_account(settings, account_id)
        
        # 尝试删除 geekez 环境（如果存在）
        if isinstance(acc, dict):
            email = str(acc.get("email") or "").strip()
            if email:
                try:
                    from apps.integrations.browser_base import BrowserType, get_browser_manager
                    manager = get_browser_manager()
                    api = manager.get_api(BrowserType.GEEKEZ)
                    if api.health_check():
                        profile_name_new = f"gpt_{email}"
                        geekez_profile = acc.get("geekez_profile")
                        delete_targets: list[str] = []
                        if isinstance(geekez_profile, dict):
                            saved_profile_id = str(geekez_profile.get("profile_id") or "").strip()
                            saved_profile_name = str(geekez_profile.get("profile_name") or "").strip()
                            if saved_profile_id:
                                delete_targets.append(saved_profile_id)
                            if saved_profile_name:
                                delete_targets.append(saved_profile_name)
                        delete_targets.extend([profile_name_new, email])
                        seen: set[str] = set()
                        for target in delete_targets:
                            t = str(target or "").strip()
                            if not t or t in seen:
                                continue
                            seen.add(t)
                            api.delete_profile(t)
                except Exception:
                    pass  # 静默失败，不阻止账号删除
        
        ok = delete_account(account_id)
        if not ok:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="launch_geekez")
    def launch_geekez(self, request, pk=None):
        settings = get_settings()
        acc_raw = find_account(settings, str(pk))
        if not isinstance(acc_raw, dict):
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        acc: dict[str, Any] = acc_raw

        email = str(acc.get("email") or "").strip()
        if not email:
            return Response({"detail": "Email missing"}, status=status.HTTP_400_BAD_REQUEST)

        from apps.integrations.browser_base import BrowserType, get_browser_manager

        manager = get_browser_manager()
        try:
            api = manager.get_api(BrowserType.GEEKEZ)
        except Exception:
            return Response({"detail": "GeekezBrowser 未配置或不可用"}, status=status.HTTP_400_BAD_REQUEST)

        if not api.health_check():
            return Response({"detail": "GeekezBrowser 服务不在线"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        profile_name_new = f"gpt_{email}"

        # 优先复用已有 profile（保留 cookie）
        # 先尝试新格式 gpt_{email}，再尝试旧格式 {email}
        created_profile = False
        profile = api.get_profile_by_name(profile_name_new)
        if not profile:
            profile = api.get_profile_by_name(email)
        if not profile:
            created_profile = True
            profile = api.create_or_update_profile(
                name=profile_name_new,
                proxy=None,
                metadata={"account": {"email": email}},
            )

        launch_info = api.launch_profile(profile.id)
        if not launch_info:
            return Response({"detail": "启动 Geekez profile 失败"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        now = timezone.now().isoformat()
        existing_profile_value = acc.get("geekez_profile")
        existing_profile: dict[str, Any] = (
            existing_profile_value if isinstance(existing_profile_value, dict) else {}
        )
        patch = {
            "geekez_profile": {
                "browser_type": BrowserType.GEEKEZ.value,
                "profile_id": profile.id,
                "profile_name": profile.name,
                "created_by_system": True,
                "created_at": str(existing_profile.get("created_at") or now),
            },
            "geekez_env": {
                "browser_type": BrowserType.GEEKEZ.value,
                "profile_id": launch_info.profile_id,
                "debug_port": launch_info.debug_port,
                "cdp_endpoint": launch_info.cdp_endpoint,
                "ws_endpoint": launch_info.ws_endpoint,
                "pid": launch_info.pid,
                "launched_at": now,
            },
            "updated_at": now,
        }

        saved = patch_account(str(pk), patch)

        return Response(
            {
                "success": True,
                "created_profile": created_profile,
                "browser_type": BrowserType.GEEKEZ.value,
                "profile_id": launch_info.profile_id,
                "debug_port": launch_info.debug_port,
                "cdp_endpoint": launch_info.cdp_endpoint,
                "ws_endpoint": launch_info.ws_endpoint,
                "pid": launch_info.pid,
                "saved": bool(saved),
            }
        )

    @action(detail=True, methods=["post"], url_path="self_register")
    def self_register(self, request, pk=None):
        settings = get_settings()
        acc = find_account(settings, str(pk))
        if not isinstance(acc, dict) or str(acc.get("type")) != "mother":
            return Response({"detail": "Mother account not found"}, status=status.HTTP_400_BAD_REQUEST)

        card_mode, selected_card_id, card_error = _parse_self_register_card_options(request.data)
        if card_error:
            return Response({"detail": card_error}, status=status.HTTP_400_BAD_REQUEST)
        keep_profile_on_fail = _parse_keep_profile_on_fail(request.data)

        record_id = uuid.uuid4().hex
        now = timezone.now().isoformat()
        add_task({
            "id": record_id,
            "type": "self_register",
            "mother_id": str(pk),
            "card_mode": card_mode,
            "selected_card_id": selected_card_id,
            "keep_profile_on_fail": keep_profile_on_fail,
            "status": "pending",
            "progress_current": 0,
            "progress_total": 3,
            "progress_percent": 0,
            "progress_label": "",
            "created_at": now,
        })

        async_result = self_register_task.delay(record_id)
        return Response({"message": "已启动：自动开通", "task_id": async_result.id, "record_id": record_id})

    @action(detail=True, methods=["post"], url_path="auto_invite")
    def auto_invite(self, request, pk=None):
        settings = get_settings()
        acc = find_account(settings, str(pk))
        if not isinstance(acc, dict) or str(acc.get("type")) != "mother":
            return Response({"detail": "Mother account not found"}, status=status.HTTP_400_BAD_REQUEST)

        mother_id = str(pk)
        seat_total = int(acc.get("seat_total") or 0)
        accounts = list_accounts(settings)
        children = [
            a
            for a in accounts
            if isinstance(a, dict)
            and str(a.get("type")) == "child"
            and str(a.get("parent_id") or "") == mother_id
        ]

        if seat_total <= 0 and not children:
            return Response(
                {"message": "该母号暂无子号，请先生成子号或设置座位数", "skipped": True}
            )

        if seat_total <= 0 or len(children) >= seat_total:
            pending_children: list[str] = []
            for child in children:
                join_status = str(child.get("team_join_status") or "").strip()
                team_account_id_saved = str(child.get("team_account_id") or "").strip()
                if join_status == "success" or team_account_id_saved:
                    continue
                child_email = str(child.get("email") or "").strip()
                if child_email:
                    pending_children.append(child_email)
            if not pending_children:
                return Response({"message": "全部子号已入队，无需邀请", "skipped": True})

        record_id = uuid.uuid4().hex
        now = timezone.now().isoformat()
        add_task({
            "id": record_id,
            "type": "auto_invite",
            "mother_id": mother_id,
            "status": "pending",
            "progress_current": 0,
            "progress_total": 3,
            "progress_percent": 0,
            "progress_label": "",
            "created_at": now,
        })

        async_result = auto_invite_task.delay(record_id)
        return Response({"message": "已启动：自动邀请", "task_id": async_result.id, "record_id": record_id})

    @action(detail=True, methods=["post"], url_path="sub2api_sink")
    def sub2api_sink(self, request, pk=None):
        settings = get_settings()
        acc = find_account(settings, str(pk))
        if not isinstance(acc, dict) or str(acc.get("type")) != "mother":
            return Response({"detail": "Mother account not found"}, status=status.HTTP_400_BAD_REQUEST)

        target_key = str(request.data.get("target_key") or request.data.get("s2a_target_key") or "").strip()
        mode = str(request.data.get("mode") or request.data.get("pool_mode") or "").strip() or "crs_sync"

        record_id = uuid.uuid4().hex
        now = timezone.now().isoformat()
        add_task({
            "id": record_id,
            "type": "sub2api_sink",
            "mother_id": str(pk),
            "s2a_target_key": target_key,
            "pool_mode": mode,
            "status": "pending",
            "progress_current": 0,
            "progress_total": 3,
            "progress_percent": 0,
            "progress_label": "",
            "created_at": now,
        })

        async_result = sub2api_sink_task.delay(record_id)
        return Response(
            {
                "message": "已启动：自动入池",
                "task_id": async_result.id,
                "record_id": record_id,
                "target_key": target_key,
                "mode": mode,
            }
        )

    @action(detail=True, methods=["post"], url_path="team_push")
    def team_push(self, request, pk=None):
        """推送母号 session 到外部兑换系统"""
        settings = get_settings()
        acc = find_account(settings, str(pk))
        if not isinstance(acc, dict) or str(acc.get("type")) != "mother":
            return Response({"detail": "Mother account not found"}, status=status.HTTP_400_BAD_REQUEST)

        target_url = str(request.data.get("target_url") or "").strip()
        admin_password = str(request.data.get("password") or "").strip()
        is_warranty = bool(request.data.get("is_warranty", True))
        seat_total = int(request.data.get("seat_total") or 5)
        note = str(request.data.get("note") or "").strip()

        if not target_url:
            return Response({"detail": "target_url is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not admin_password:
            return Response({"detail": "password is required"}, status=status.HTTP_400_BAD_REQUEST)

        record_id = uuid.uuid4().hex
        now = timezone.now().isoformat()
        add_task({
            "id": record_id,
            "type": "team_push",
            "mother_id": str(pk),
            "target_url": target_url,
            "status": "pending",
            "progress_current": 0,
            "progress_total": 3,
            "progress_percent": 0,
            "progress_label": "",
            "created_at": now,
        })

        async_result = team_push_task.delay(record_id, str(pk), target_url, admin_password, is_warranty, seat_total, note)
        return Response({
            "message": "已启动：推送到兑换系统",
            "task_id": async_result.id,
            "record_id": record_id,
        })

    @action(detail=False, methods=["post"], url_path="batch/self_register")
    def batch_self_register(self, request):
        settings = get_settings()
        mother_ids = _normalize_id_list(request.data.get("mother_ids") or request.data.get("ids"))
        if not mother_ids:
            return Response({"detail": "mother_ids is required"}, status=status.HTTP_400_BAD_REQUEST)

        card_mode, selected_card_id, card_error = _parse_self_register_card_options(request.data)
        if card_error:
            return Response({"detail": card_error}, status=status.HTTP_400_BAD_REQUEST)
        keep_profile_on_fail = _parse_keep_profile_on_fail(request.data)

        concurrency = int(request.data.get("concurrency") or 5)
        # open_geekez 参数已废弃，self_register_task 内部会自动启动浏览器
        # 不再单独调用 launch_geekez_task，避免并发冲突

        results: list[dict[str, Any]] = []
        for idx, mother_id in enumerate(mother_ids):
            acc = find_account(settings, str(mother_id))
            if not isinstance(acc, dict) or str(acc.get("type")) != "mother":
                results.append({"mother_id": mother_id, "skipped": True, "message": "Mother account not found"})
                continue

            delay_seconds = _batch_countdown(idx, concurrency)

            record_id = uuid.uuid4().hex
            now = timezone.now().isoformat()
            add_task({
                "id": record_id,
                "type": "self_register",
                "mother_id": str(mother_id),
                "card_mode": card_mode,
                "selected_card_id": selected_card_id,
                "keep_profile_on_fail": keep_profile_on_fail,
                "status": "pending",
                "progress_current": 0,
                "progress_total": 3,
                "progress_percent": 0,
                "progress_label": "",
                "created_at": now,
            })

            async_result = self_register_task.apply_async(args=[record_id], countdown=delay_seconds)
            results.append({
                "mother_id": mother_id,
                "record_id": record_id,
                "task_id": async_result.id,
            })

        return Response({"message": "已启动：批量自动开通", "results": results})

    @action(detail=False, methods=["post"], url_path="batch/auto_invite")
    def batch_auto_invite(self, request):
        settings = get_settings()
        mother_ids = _normalize_id_list(request.data.get("mother_ids") or request.data.get("ids"))
        if not mother_ids:
            return Response({"detail": "mother_ids is required"}, status=status.HTTP_400_BAD_REQUEST)

        concurrency = int(request.data.get("concurrency") or 5)
        # open_geekez 参数已废弃，auto_invite_task 内部会自动启动浏览器
        # 不再单独调用 launch_geekez_task，避免并发冲突
        accounts = list_accounts(settings)

        results: list[dict[str, Any]] = []
        for idx, mother_id in enumerate(mother_ids):
            acc = find_account(settings, str(mother_id))
            if not isinstance(acc, dict) or str(acc.get("type")) != "mother":
                results.append({"mother_id": mother_id, "skipped": True, "message": "Mother account not found"})
                continue

            seat_total = int(acc.get("seat_total") or 0)
            children = [
                a
                for a in accounts
                if isinstance(a, dict)
                and str(a.get("type")) == "child"
                and str(a.get("parent_id") or "") == str(mother_id)
            ]

            if seat_total <= 0 and not children:
                results.append({"mother_id": mother_id, "skipped": True, "message": "该母号暂无子号"})
                continue

            if seat_total <= 0 or len(children) >= seat_total:
                pending_children: list[str] = []
                for child in children:
                    join_status = str(child.get("team_join_status") or "").strip()
                    team_account_id_saved = str(child.get("team_account_id") or "").strip()
                    if join_status == "success" or team_account_id_saved:
                        continue
                    child_email = str(child.get("email") or "").strip()
                    if child_email:
                        pending_children.append(child_email)
                if not pending_children:
                    results.append({"mother_id": mother_id, "skipped": True, "message": "全部子号已入队"})
                    continue

            delay_seconds = _batch_countdown(idx, concurrency)

            record_id = uuid.uuid4().hex
            now = timezone.now().isoformat()
            add_task({
                "id": record_id,
                "type": "auto_invite",
                "mother_id": str(mother_id),
                "status": "pending",
                "progress_current": 0,
                "progress_total": 3,
                "progress_percent": 0,
                "progress_label": "",
                "created_at": now,
            })

            async_result = auto_invite_task.apply_async(args=[record_id], countdown=delay_seconds)
            results.append({
                "mother_id": mother_id,
                "record_id": record_id,
                "task_id": async_result.id,
            })

        return Response({"message": "已启动：批量自动邀请", "results": results})

    @action(detail=False, methods=["post"], url_path="batch/sub2api_sink")
    def batch_sub2api_sink(self, request):
        settings = get_settings()
        mother_ids = _normalize_id_list(request.data.get("mother_ids") or request.data.get("ids"))
        if not mother_ids:
            return Response({"detail": "mother_ids is required"}, status=status.HTTP_400_BAD_REQUEST)

        concurrency = int(request.data.get("concurrency") or 5)
        # open_geekez 参数已废弃，sub2api_sink_task 内部会自动启动浏览器
        # 不再单独调用 launch_geekez_task，避免并发冲突
        target_key = str(request.data.get("target_key") or request.data.get("s2a_target_key") or "").strip()
        mode = str(request.data.get("mode") or request.data.get("pool_mode") or "").strip() or "crs_sync"

        results: list[dict[str, Any]] = []
        for idx, mother_id in enumerate(mother_ids):
            acc = find_account(settings, str(mother_id))
            if not isinstance(acc, dict) or str(acc.get("type")) != "mother":
                results.append({"mother_id": mother_id, "skipped": True, "message": "Mother account not found"})
                continue

            delay_seconds = _batch_countdown(idx, concurrency)

            record_id = uuid.uuid4().hex
            now = timezone.now().isoformat()
            add_task({
                "id": record_id,
                "type": "sub2api_sink",
                "mother_id": str(mother_id),
                "s2a_target_key": target_key,
                "pool_mode": mode,
                "status": "pending",
                "progress_current": 0,
                "progress_total": 3,
                "progress_percent": 0,
                "progress_label": "",
                "created_at": now,
            })

            async_result = sub2api_sink_task.apply_async(args=[record_id], countdown=delay_seconds)
            results.append({
                "mother_id": mother_id,
                "record_id": record_id,
                "task_id": async_result.id,
                "target_key": target_key,
                "mode": mode,
            })

        return Response({"message": "已启动：批量自动入池", "results": results})


class CeleryTaskViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def retrieve(self, request, pk=None):
        task_id = str(pk)
        result = AsyncResult(task_id)
        response = {
            "task_id": task_id,
            "state": result.state,
        }

        if result.state == "FAILURE":
            response["error"] = str(result.result)
        else:
            response["result"] = result.result

        return Response(response)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        task_id = str(pk)
        result = AsyncResult(task_id)
        result.revoke(terminate=False)
        return Response({"status": "cancelled"})

    @action(detail=False, methods=["post"], url_path="clear")
    def clear(self, request):
        settings = get_settings()
        count = len(list_tasks(settings))
        cleared = clear_tasks()
        return Response({"status": "cleared", "count": count, "cleared": cleared})

    @action(detail=True, methods=["get"], url_path="trace")
    def trace(self, request, pk=None):
        if not pk:
            return Response({"error": "task_id required"}, status=status.HTTP_400_BAD_REQUEST)

        settings = get_settings()
        task_id = str(pk)
        matched_task: dict[str, Any] | None = None
        for t in list_tasks(settings):
            if str(t.get("celery_task_id") or "") == task_id:
                matched_task = t
                break

        if not matched_task:
            return Response({"error": "task not found"}, status=status.HTTP_404_NOT_FOUND)

        record_id = str(matched_task.get("id") or "").strip()
        if not record_id:
            return Response({"error": "task record missing"}, status=status.HTTP_404_NOT_FOUND)

        filename = str(request.query_params.get("filename") or "run.log")
        email = (request.query_params.get("email") or "").strip()
        if not email:
            mother_id = str(matched_task.get("mother_id") or "").strip()
            if mother_id:
                mother = find_account(settings, mother_id)
                if isinstance(mother, dict):
                    email = str(mother.get("email") or "").strip()

        safe_email = email.replace("@", "_").replace(".", "_") if email else ""
        direction = (request.query_params.get("direction") or "backward").strip()
        if direction not in ("backward", "forward"):
            direction = "backward"

        try:
            limit_bytes = int(request.query_params.get("limit_bytes") or 262144)
        except Exception:
            limit_bytes = 262144
        limit_bytes = max(4096, min(limit_bytes, 1024 * 1024))

        cursor_raw = request.query_params.get("cursor")
        cursor_in: int | None
        try:
            cursor_in = int(cursor_raw) if cursor_raw is not None else None
        except Exception:
            cursor_in = None

        base_dir = Path(getattr(django_settings, "BASE_DIR", "."))
        trace_dir = (base_dir / "logs" / "trace").resolve()
        if safe_email:
            trace_rel = Path("logs") / "trace" / f"trace_{task_id}_{safe_email}.log"
        else:
            trace_rel = Path("logs") / "trace" / f"trace_{task_id}.log"

        trace_abs = (base_dir / trace_rel).resolve()
        try:
            trace_abs.relative_to(trace_dir)
        except Exception:
            return Response({"error": "invalid trace path"}, status=status.HTTP_400_BAD_REQUEST)

        file_path: Path | None = None
        trace_file = str(trace_rel)
        if trace_abs.exists() and trace_abs.is_file():
            file_path = trace_abs
        else:
            media_root = Path(str(getattr(django_settings, "MEDIA_ROOT", "")))
            job_dir = media_root / "gpt_business" / "jobs" / record_id
            log_path = job_dir / filename
            if log_path.exists() and log_path.is_file():
                try:
                    log_path.relative_to(media_root)
                except Exception:
                    return Response({"error": "invalid trace path"}, status=status.HTTP_400_BAD_REQUEST)
                file_path = log_path
                trace_file = str(Path("gpt_business") / "jobs" / record_id / filename)
            else:
                return Response(
                    {
                        "error": "trace file not found",
                        "trace_file": trace_file,
                        "run_log": str(Path("gpt_business") / "jobs" / record_id / filename),
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        size = os.path.getsize(file_path)
        if direction == "backward":
            end = size if cursor_in is None else max(0, min(cursor_in, size))
            start = max(0, end - limit_bytes)
            with open(file_path, "rb") as f:
                f.seek(start)
                data = f.read(end - start)
            text = data.decode("utf-8", errors="ignore")
            lines = text.splitlines()
            if start > 0 and lines:
                lines = lines[1:]
            cursor_out = start
            has_more = start > 0
        else:
            start = 0 if cursor_in is None else max(0, min(cursor_in, size))
            end = min(size, start + limit_bytes)
            with open(file_path, "rb") as f:
                f.seek(start)
                data = f.read(end - start)
            text = data.decode("utf-8", errors="ignore")
            lines = text.splitlines()
            cursor_out = end
            has_more = end < size

        if len(lines) > 5000:
            lines = lines[-5000:] if direction == "backward" else lines[:5000]

        return Response(
            {
                "task_id": task_id,
                "direction": direction,
                "trace_file": trace_file,
                "email": email,
                "cursor_in": cursor_in,
                "cursor_out": cursor_out,
                "has_more": has_more,
                "size": size,
                "lines": lines,
            }
        )


class StatisticsViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        settings = get_settings()
        teams = settings.get("teams") or []
        tasks = list_tasks(settings)

        accounts_total = 0
        for task in tasks:
            result = task.get("result") or {}
            if task.get("type") == "legacy_run":
                accounts_total += int(result.get("accounts_count") or 0)
                continue

            invited = result.get("invited") or []
            if isinstance(invited, list):
                accounts_total += len(invited)

        return Response(
            {
                "teams": len(teams) if isinstance(teams, list) else 0,
                "accounts": accounts_total,
                "tasks": len(tasks),
            }
        )

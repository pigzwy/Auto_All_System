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
    SettingsUpdateSerializer,
    TaskCreateSerializer,
)
from .storage import (
    add_account,
    add_task,
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
from .tasks import auto_invite_task, invite_only_task, legacy_run_task, self_register_task, sub2api_sink_task


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

            # 兼容 oai-team-auto-provisioner 的配置项
            for key in [
                "legacy_repo_path",
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
                        settings[section] = {**current_section, **payload[section]}
                    else:
                        settings[section] = payload[section]
            return settings

        new_settings = update_settings(mutator)
        return Response(_mask_settings(new_settings))


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
        elif flow == "legacy_run":
            if not str(team_cfg.get("owner_email") or "").strip() or not str(team_cfg.get("owner_password") or "").strip():
                return Response(
                    {"detail": "legacy_run requires team.owner_email and team.owner_password"},
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

        if flow == "legacy_run":
            celery_result = legacy_run_task.delay(record_id)
        else:
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
        try:
            from apps.integrations.browser_base import BrowserType, get_browser_manager

            manager = get_browser_manager()
            api = manager.get_api(BrowserType.GEEKEZ)
            geekez_names = {
                str(p.name)
                for p in api.list_profiles()
                if getattr(p, "name", None)
            }
        except Exception:
            geekez_names = set()

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
            has_profile = bool(
                isinstance(geekez_profile, dict) and geekez_profile.get("profile_id")
            ) or bool(profile_name_new and profile_name_new in geekez_names) or bool(email and email in geekez_names)
            return {
                **acc,
                "geekez_profile_exists": has_profile,
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

    @action(detail=True, methods=["get"], url_path="tasks")
    def tasks(self, request, pk=None):
        settings = get_settings()
        acc = find_account(settings, str(pk))
        if not isinstance(acc, dict) or str(acc.get("type")) != "mother":
            return Response({"detail": "Mother account not found"}, status=status.HTTP_400_BAD_REQUEST)

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

        # 统一使用 gpt_ 前缀作为 profile name（新格式）
        profile_name_new = f"gpt_{email}"

        # 优先复用已有 profile（避免重复创建环境）
        # 先尝试新格式 gpt_{email}，再尝试旧格式 {email}
        created_profile = False
        profile = api.get_profile_by_name(profile_name_new)
        if not profile:
            # 兼容旧格式：直接用邮箱作为 profile name
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

        record_id = uuid.uuid4().hex
        now = timezone.now().isoformat()
        add_task({
            "id": record_id,
            "type": "self_register",
            "mother_id": str(pk),
            "status": "pending",
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

        record_id = uuid.uuid4().hex
        now = timezone.now().isoformat()
        add_task({
            "id": record_id,
            "type": "auto_invite",
            "mother_id": str(pk),
            "status": "pending",
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

        record_id = uuid.uuid4().hex
        now = timezone.now().isoformat()
        add_task({
            "id": record_id,
            "type": "sub2api_sink",
            "mother_id": str(pk),
            "status": "pending",
            "created_at": now,
        })

        async_result = sub2api_sink_task.delay(record_id)
        return Response({"message": "已启动：自动入池", "task_id": async_result.id, "record_id": record_id})


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

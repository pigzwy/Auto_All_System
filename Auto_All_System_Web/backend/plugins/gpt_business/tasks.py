from __future__ import annotations

import logging
import random
import time
import csv
import json
import re
import asyncio
import sys
import secrets
import string
import uuid
import traceback
from urllib.parse import unquote
from pathlib import Path
from typing import Any

import requests
from celery import shared_task
from django.conf import settings as django_settings
from django.utils import timezone

from .legacy_runner import prepare_artifacts
from .storage import add_account, find_account, get_settings, list_accounts, patch_account, patch_task
from .trace_cleanup import cleanup_trace_files


logger = logging.getLogger(__name__)


def _safe_email_for_trace(email: str | None) -> str:
    return (email or "").replace("@", "_").replace(".", "_")


def _mask_secret(value: str, prefix: int = 4, suffix: int = 4) -> str:
    v = (value or "").replace(" ", "").strip()
    if not v:
        return ""
    if len(v) <= prefix + suffix:
        return "***"
    return f"{v[:prefix]}***{v[-suffix:]}"


def _generate_random_profile_name(email: str) -> str:
    local_part = str(email or "").split("@")[0].strip().lower()
    normalized = "".join(ch if ch.isalnum() else "_" for ch in local_part).strip("_")
    prefix = (normalized or "acct")[:24]
    suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    return f"gpt_{prefix}_{suffix}"


def _set_task_progress(record_id: str, current: int, total: int, label: str) -> None:
    try:
        total_int = max(int(total), 1)
        current_int = max(0, min(int(current), total_int))
        percent = int(round(current_int / total_int * 100))
        patch_task(
            record_id,
            {
                "progress_current": current_int,
                "progress_total": total_int,
                "progress_label": str(label or ""),
                "progress_percent": percent,
                "progress_updated_at": timezone.now().isoformat(),
            },
        )
    except Exception:
        pass


class SensitiveDataFilter:
    PATTERNS = [
        (
            re.compile(r'password["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE),
            r'password="***"',
        ),
        (
            re.compile(r'secret["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE),
            r'secret="***"',
        ),
        (
            re.compile(r'card_number["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE),
            r'card_number="****"',
        ),
        (
            re.compile(r'cvv["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE),
            r'cvv="***"',
        ),
        (re.compile(r"\d{13,19}"), r"****-****-****-****"),
    ]

    @staticmethod
    def filter(message: str) -> str:
        for pattern, replacement in SensitiveDataFilter.PATTERNS:
            message = pattern.sub(replacement, message)
        return message


def _get_trace_file(celery_task_id: str | None, email: str | None) -> Path | None:
    celery_task_id = str(celery_task_id or "").strip()
    safe_email = _safe_email_for_trace(email)
    if not celery_task_id and not safe_email:
        return None

    base_dir = Path(getattr(django_settings, "BASE_DIR", "."))
    trace_dir = base_dir / "logs" / "trace"
    trace_dir.mkdir(parents=True, exist_ok=True)

    if celery_task_id and safe_email:
        filename = f"trace_{celery_task_id}_{safe_email}.log"
    elif celery_task_id:
        filename = f"trace_{celery_task_id}.log"
    else:
        filename = f"trace_{safe_email}.log"

    return trace_dir / filename


def _context_prefix(kind: str | None, celery_task_id: str | None, email: str | None) -> str:
    parts: list[str] = []
    if kind:
        parts.append(kind)
    if celery_task_id:
        parts.append(f"celery={celery_task_id}")
    if email:
        parts.append(email)
    if not parts:
        return ""
    return "[" + "][".join(parts) + "] "


def _append_trace_line(
    celery_task_id: str | None,
    email: str | None,
    message: str,
    *,
    step: str = "task",
    action: str = "log",
    level: str = "info",
    kind: str = "gpt",
    mask_secret: bool = False,
) -> None:
    try:
        trace_file = _get_trace_file(celery_task_id, email)
        if not trace_file:
            return

        ts = timezone.now().isoformat()
        safe_message = str(message).replace("\r", " ").rstrip("\n")
        if mask_secret:
            safe_message = _mask_secret(safe_message)
        safe_message = SensitiveDataFilter.filter(safe_message)
        payload = {
            "ts": ts,
            "level": level,
            "step": step,
            "action": action,
            "message": safe_message,
            "celery_task_id": str(celery_task_id or ""),
            "email": str(email or ""),
            "kind": kind,
        }
        json_line = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
        prefix = _context_prefix(kind, str(celery_task_id or ""), str(email or ""))
        human = f"[{ts}] {prefix}{step}/{action}: {safe_message}\n"

        trace_file.parent.mkdir(parents=True, exist_ok=True)
        with trace_file.open("a", encoding="utf-8", errors="ignore") as f:
            f.write(json_line + "\n")
            f.write(human)
    except Exception:
        pass


def _get_available_card_for_checkout(selected_card_id: int | None = None) -> dict[str, Any] | None:
    """从虚拟卡管理获取一张可用卡用于绑卡"""
    from apps.cards.models import Card

    if selected_card_id:
        card = Card.objects.filter(id=selected_card_id).first()
        if not card or not card.is_available():
            return None
    else:
        card = Card.objects.filter(status="available").order_by("?").first()

    if not card:
        return None
    
    billing = card.billing_address or {}
    expiry = f"{card.expiry_month:02d}/{str(card.expiry_year)[-2:]}" if card.expiry_month and card.expiry_year else ""
    
    return {
        "card_id": card.id,
        "card_number": card.card_number or "",
        "card_expiry": expiry,
        "card_cvc": card.cvv or "",
        "cardholder_name": card.card_holder or "",
        "address_line1": billing.get("street") or billing.get("address_line1") or "",
        "city": billing.get("city") or "",
        "postal_code": billing.get("zip") or billing.get("postal_code") or "",
        "state": billing.get("state") or "",
        "country": billing.get("country") or "US",
    }


def _mark_card_as_used(card_id: int, account_id: str, purpose: str) -> None:
    """标记卡为已使用并记录日志"""
    from apps.cards.models import Card, CardUsageLog
    from django.utils import timezone
    
    try:
        card = Card.objects.get(id=card_id)
        card.status = "in_use"
        card.use_count += 1
        card.last_used_at = timezone.now()
        card.save(update_fields=["status", "use_count", "last_used_at", "updated_at"])
        
        # CardUsageLog 需要 user 字段，但这里没有用户上下文，暂时跳过日志记录
        # 如果需要记录，可以在 card.metadata 中存储
        card.metadata = card.metadata or {}
        card.metadata["last_account_id"] = account_id
        card.metadata["last_purpose"] = purpose
        card.save(update_fields=["metadata"])
        
    except Exception as e:
        logger.warning(f"Failed to mark card as used: {e}")
    except Card.DoesNotExist:
        logger.warning(f"Card {card_id} not found when marking as used")


DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)


class GPTMailClient:
    def __init__(self, api_base: str, api_key: str, *, timeout: int = DEFAULT_TIMEOUT_SECONDS):
        self.api_base = api_base.rstrip("/")
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }
        self.timeout = timeout
        self.session = requests.Session()

    def generate_email(self, *, prefix: str | None = None, domain: str | None = None) -> str:
        url = f"{self.api_base}/api/generate-email"
        if prefix or domain:
            payload: dict[str, Any] = {}
            if prefix:
                payload["prefix"] = prefix
            if domain:
                payload["domain"] = domain
            resp = self.session.post(url, headers=self.headers, json=payload, timeout=self.timeout)
        else:
            resp = self.session.get(url, headers=self.headers, timeout=self.timeout)

        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(str(data.get("error") or "GPTMail generate failed"))

        email = (data.get("data") or {}).get("email")
        if not email:
            raise RuntimeError("GPTMail response missing email")
        return str(email)


class ChatGPTTeamClient:
    def __init__(self, *, timeout: int = DEFAULT_TIMEOUT_SECONDS):
        self.timeout = timeout
        self.session = requests.Session()

    def _normalize_token(self, token: str) -> str:
        token = token.strip()
        if token.startswith("Bearer "):
            return token
        return f"Bearer {token}"

    def fetch_account_id(self, auth_token: str) -> str:
        token = self._normalize_token(auth_token)
        headers = {
            "accept": "*/*",
            "authorization": token,
            "content-type": "application/json",
            "user-agent": DEFAULT_USER_AGENT,
        }

        resp = self.session.get(
            "https://chatgpt.com/backend-api/accounts/check/v4-2023-04-27",
            headers=headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        accounts: dict[str, Any] = data.get("accounts") or {}

        # 优先挑选 plan_type 包含 team 的 account
        for acc_id, acc_info in accounts.items():
            if acc_id == "default":
                continue
            account_data = (acc_info or {}).get("account") or {}
            plan_type = str(account_data.get("plan_type") or "")
            if "team" in plan_type.lower():
                return acc_id

        # fallback: 第一个非 default
        for acc_id in accounts.keys():
            if acc_id != "default":
                return acc_id

        return ""

    def invite_emails(self, *, account_id: str, auth_token: str, emails: list[str]) -> dict[str, Any]:
        token = self._normalize_token(auth_token)
        headers = {
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9",
            "authorization": token,
            "content-type": "application/json",
            "origin": "https://chatgpt.com",
            "referer": "https://chatgpt.com/",
            "user-agent": DEFAULT_USER_AGENT,
            "chatgpt-account-id": account_id,
        }

        payload = {
            "email_addresses": emails,
            "role": "standard-user",
            "resend_emails": True,
        }

        url = f"https://chatgpt.com/backend-api/accounts/{account_id}/invites"
        resp = self.session.post(url, headers=headers, json=payload, timeout=self.timeout)

        # chatgpt 接口通常会返回 200；非 200 直接报错并上抛给任务
        resp.raise_for_status()
        data = resp.json() if resp.content else {}

        success: list[str] = []
        failed: list[dict[str, str]] = []

        for invite in data.get("account_invites") or []:
            invited_email = invite.get("email_address")
            if invited_email:
                success.append(str(invited_email))

        for err in data.get("errored_emails") or []:
            err_email = err.get("email")
            err_msg = err.get("error")
            if err_email:
                failed.append({"email": str(err_email), "error": str(err_msg or "Unknown error")})

        # 没有明确字段时，按成功处理
        if not success and not failed:
            success = emails

        return {
            "success": success,
            "failed": failed,
            "raw": data,
        }


@shared_task(bind=True)
def invite_only_task(self, record_id: str):
    celery_task_id = str(self.request.id or "")
    trace_email = ""
    trace_email = ""
    patch_task(
        record_id,
        {
            "status": "running",
            "started_at": timezone.now().isoformat(),
            "celery_task_id": self.request.id,
        },
    )
    _set_task_progress(record_id, 1, 3, "准备邀请")
    _set_task_progress(record_id, 1, 3, "创建账号")

    try:
        settings = get_settings()
        gptmail_cfg = (settings.get("gptmail") or {})
        teams = settings.get("teams") or []

        task_record = (settings.get("tasks") or [])
        # task_record 可能很大，这里不重复扫描；靠 views 传入的 record_id 已保存 team_name/count

        # 在 settings 中定位任务记录（用于读取参数）
        team_name = None
        count = None
        password = None
        for t in settings.get("tasks") or []:
            if str(t.get("id")) == str(record_id):
                team_name = t.get("team_name")
                count = t.get("count")
                password = t.get("password")
                break

        if not team_name:
            raise RuntimeError("Task record missing team_name")

        team_cfg = next((x for x in teams if x.get("name") == team_name), None)
        if not team_cfg:
            raise RuntimeError(f"Team not found: {team_name}")

        trace_email = str(team_cfg.get("owner_email") or "").strip()

        def _trace(action: str, msg: str, level: str = "info") -> None:
            _append_trace_line(
                celery_task_id,
                trace_email,
                msg,
                step="invite_only",
                action=action,
                level=level,
            )

        api_base = str(gptmail_cfg.get("api_base") or "").strip()
        api_key = str(gptmail_cfg.get("api_key") or "").strip()
        if not api_base or not api_key:
            raise RuntimeError("GPTMail settings missing api_base/api_key")

        domains = gptmail_cfg.get("domains") or []
        prefix = str(gptmail_cfg.get("prefix") or "").strip() or None

        count_int = int(count or 0) if count is not None else 0
        if count_int <= 0:
            count_int = 4

        gptmail = GPTMailClient(api_base, api_key)

        _trace("start", f"invite_only start team_name={team_name} count={count_int}")

        created: list[dict[str, str]] = []
        for _ in range(count_int):
            domain = random.choice(domains) if domains else None
            email = gptmail.generate_email(prefix=prefix, domain=domain)
            created.append({"email": email, "password": str(password or "")})

        team_client = ChatGPTTeamClient()
        account_id = str(team_cfg.get("account_id") or "").strip()
        auth_token = str(team_cfg.get("auth_token") or "").strip()
        if not auth_token:
            raise RuntimeError("Team auth_token missing")

        if not account_id:
            account_id = team_client.fetch_account_id(auth_token)
            if not account_id:
                raise RuntimeError("Failed to fetch account_id")

        invite_result = team_client.invite_emails(
            account_id=account_id,
            auth_token=auth_token,
            emails=[x["email"] for x in created],
        )

        _trace(
            "done",
            f"invite_only done invited={len(invite_result.get('success') or [])} failed={len(invite_result.get('failed') or [])}",
        )

        result = {
            "team_name": team_name,
            "account_id": account_id,
            "created": created,
            "invited": invite_result.get("success") or [],
            "failed": invite_result.get("failed") or [],
        }

        patch_task(
            record_id,
            {
                "status": "completed",
                "finished_at": timezone.now().isoformat(),
                "result": result,
            },
        )
        return result
    except Exception as exc:
        logger.exception("gpt_business invite_only_task failed")
        _append_trace_line(
            celery_task_id,
            trace_email,
            f"invite_only failed: {exc}",
            step="invite_only",
            action="error",
            level="error",
        )
        patch_task(
            record_id,
            {
                "status": "failed",
                "finished_at": timezone.now().isoformat(),
                "error": str(exc),
            },
        )
        raise


def _get_task_record(settings: dict[str, Any], record_id: str) -> dict[str, Any] | None:
    for t in settings.get("tasks") or []:
        if str(t.get("id")) == str(record_id):
            return t
    return None


@shared_task(bind=True)
def legacy_run_task(self, record_id: str):
    celery_task_id = str(self.request.id or "")
    patch_task(
        record_id,
        {
            "status": "running",
            "started_at": timezone.now().isoformat(),
            "celery_task_id": self.request.id,
        },
    )

    err = "legacy_run 已停用：不再支持外部仓库挂载/子进程执行，请使用母号维度的自动开通/自动邀请/自动入池"
    _append_trace_line(
        celery_task_id,
        None,
        f"legacy_run failed: {err}",
        step="legacy_run",
        action="error",
        level="error",
    )
    patch_task(
        record_id,
        {
            "status": "failed",
            "finished_at": timezone.now().isoformat(),
            "error": err,
        },
    )
    raise RuntimeError(err)


def _artifacts_list_from_job_dir(artifacts_dir: Path) -> list[dict[str, Any]]:
    if not artifacts_dir.exists():
        return []
    files: list[dict[str, Any]] = []
    for p in sorted(artifacts_dir.glob("*")):
        if p.is_file():
            files.append({"name": p.name, "path": str(p)})
    return files


def _cloudmail_email_config_from_account(acc: dict[str, Any]) -> dict[str, Any]:
    config_id = int(acc.get("cloudmail_config_id") or 0)
    if config_id <= 0:
        raise RuntimeError("cloudmail_config_id missing")

    from apps.integrations.email.models import CloudMailConfig

    cfg = CloudMailConfig.objects.filter(id=config_id, is_active=True).first()
    if not cfg:
        raise RuntimeError("CloudMailConfig not found")

    # domains 可能被错误保存为: ['["a.com", "b.com", ]']（嵌套 JSON 字符串 + 末尾逗号）
    def _parse_domains(value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, list):
            out: list[str] = []
            for it in value:
                out.extend(_parse_domains(it))
            return out
        if isinstance(value, str):
            raw = value.strip()
            if raw.startswith("["):
                try:
                    fixed = re.sub(r",\s*]", "]", raw)
                    parsed = json.loads(fixed)
                    return _parse_domains(parsed)
                except Exception:
                    return [raw] if raw else []
            return [raw] if raw else []
        return [str(value).strip()]

    domains = [str(x).strip() for x in _parse_domains(cfg.domains) if str(x).strip()]
    if not domains:
        raise RuntimeError("CloudMailConfig domains is empty")

    return {
        "api_base": str(cfg.api_base),
        "api_auth": str(cfg.api_token),
        "domains": domains,
        "role": str(cfg.default_role or "user"),
        "web_url": "",
    }


@shared_task(bind=True)
def self_register_task(self, record_id: str):
    """自助开通任务 - Geekez + Playwright (注册 + 验证码 + 绑卡)"""

    patch_task(
        record_id,
        {
            "status": "running",
            "started_at": timezone.now().isoformat(),
            "celery_task_id": self.request.id,
        },
    )

    celery_task_id = str(self.request.id or "")
    trace_email = ""

    mother_id: str = ""
    job_dir: Path | None = None

    try:
        settings = get_settings()
        task_record = _get_task_record(settings, record_id)
        if not task_record:
            raise RuntimeError("Task record not found")

        mother_id = str(task_record.get("mother_id") or "").strip()
        if not mother_id:
            raise RuntimeError("Task record missing mother_id")

        mother = find_account(settings, mother_id)
        if not isinstance(mother, dict) or str(mother.get("type")) != "mother":
            raise RuntimeError("Mother account not found")

        email = str(mother.get("email") or "").strip()
        password = str(mother.get("account_password") or "").strip()
        if not email or not password:
            raise RuntimeError("Mother account missing email/account_password")

        trace_email = email

        media_root = Path(str(getattr(django_settings, "MEDIA_ROOT", "")))
        if not str(media_root):
            raise RuntimeError("MEDIA_ROOT is not configured")

        job_dir = media_root / "gpt_business" / "jobs" / record_id
        artifacts = prepare_artifacts(job_dir)

        # 状态：入池中
        try:
            patch_account(
                mother_id,
                {
                    "pool_status": "running",
                    "pool_last_task": record_id,
                    "pool_updated_at": timezone.now().isoformat(),
                },
            )
        except Exception:
            pass

        def _log(line: str) -> None:
            ts = timezone.now().isoformat()
            artifacts.log_file.parent.mkdir(parents=True, exist_ok=True)
            with artifacts.log_file.open("a", encoding="utf-8") as fp:
                fp.write(f"[{ts}] {line}\n")
            _append_trace_line(
                celery_task_id,
                trace_email,
                line,
                step="self_register",
                action="log",
            )

        _log(f"self_register start mother_id={mother_id} email={email}")

        # 账号状态：注册中/登录中
        try:
            patch_account(
                mother_id,
                {
                    "register_status": "running",
                    "register_updated_at": timezone.now().isoformat(),
                    "login_status": "running",
                    "login_updated_at": timezone.now().isoformat(),
                },
            )
        except Exception:
            pass

        card_mode_raw = str(task_record.get("card_mode") or "random").strip().lower()
        card_mode = card_mode_raw if card_mode_raw in {"selected", "random", "manual"} else "random"
        selected_card_raw = task_record.get("selected_card_id")
        selected_card_id: int | None = None
        if selected_card_raw not in (None, ""):
            try:
                selected_card_id = int(selected_card_raw)
            except (TypeError, ValueError):
                selected_card_id = None

        card_info = _get_available_card_for_checkout(selected_card_id if card_mode == "selected" else None)
        if not card_info:
            if card_mode == "manual":
                _log("manual card mode: waiting for human card input on checkout")
            elif card_mode == "selected":
                _log(f"selected card unavailable: selected_card_id={selected_card_id}")
            else:
                _log("random card mode found no available card")

        config_id = int(mother.get("cloudmail_config_id") or 0)
        if config_id <= 0:
            raise RuntimeError("cloudmail_config_id missing")

        from apps.integrations.email.models import CloudMailConfig
        from apps.integrations.email.services.client import CloudMailClient
        cfg = CloudMailConfig.objects.filter(id=config_id, is_active=True).first()
        if not cfg:
            raise RuntimeError(f"CloudMailConfig not found: {config_id}")

        email_cfg = _cloudmail_email_config_from_account(mother)
        mail_client = CloudMailClient(
            api_base=str(email_cfg.get("api_base") or ""),
            api_token=str(email_cfg.get("api_auth") or ""),
            domains=list(email_cfg.get("domains") or []),
            default_role=str(email_cfg.get("role") or "user"),
        )

        def _proxy_to_str(proxy_value: Any) -> str | None:
            if not proxy_value:
                return None
            if isinstance(proxy_value, str):
                return proxy_value.strip() or None
            if isinstance(proxy_value, dict):
                t = str(proxy_value.get("type") or "http").strip() or "http"
                host = str(proxy_value.get("host") or "").strip()
                port = str(proxy_value.get("port") or "").strip()
                user = str(proxy_value.get("username") or "").strip()
                pwd = str(proxy_value.get("password") or "").strip()
                if not host or not port:
                    return None
                auth = ""
                if user and pwd:
                    auth = f"{user}:{pwd}@"
                return f"{t}://{auth}{host}:{port}"
            return None

        proxy_str = _proxy_to_str((settings.get("browser") or {}).get("proxy"))
        profile_name = _generate_random_profile_name(email)

        from apps.integrations.geekez.api import GeekezBrowserAPI
        from plugins.gpt_business.services.openai_register import (
            connect_to_browser,
            register_openai_account,
        )

        def _run_sync() -> dict[str, Any]:
            """同步执行注册流程（使用 DrissionPage）"""
            api = GeekezBrowserAPI()
            
            # 创建或获取 profile
            _log(f"creating new random profile: {profile_name}")
            profile = api.create_or_update_profile(name=profile_name, proxy=proxy_str)
            _log(f"profile ready: id={profile.id}, name={profile.name}")
            
            # 启动浏览器
            _log(f"launching profile: {profile.id}")
            launch = api.launch_profile(profile.id)
            if not launch:
                raise RuntimeError(f"launch_profile failed: {profile.id}")
            
            debug_port = launch.debug_port
            _log(f"browser launched, debug_port={debug_port}")
            
            page = None
            try:
                # 用 DrissionPage 连接到 Geekez 浏览器
                page = connect_to_browser(debug_port)
                _log("DrissionPage connected to Geekez browser")
                
                # 截图回调
                def shot_callback(name: str):
                    try:
                        p = job_dir / name
                        page.get_screenshot(path=str(p), full_page=True)
                    except Exception:
                        pass
                
                # 验证码回调
                def get_code_callback(email_addr: str) -> str | None:
                    return mail_client.wait_for_verification_code(email_addr, timeout=120)
                
                # 调用注册函数
                _log("calling register_openai_account...")
                print("[DEBUG] calling register_openai_account...", flush=True)
                
                try:
                    register_ok = register_openai_account(
                        page=page,
                        email=email,
                        password=password,
                        get_verification_code=get_code_callback,
                        log_callback=_log,
                        screenshot_callback=shot_callback,
                    )
                except Exception as reg_err:
                    print(f"[DEBUG] register_openai_account exception: {reg_err}", flush=True)
                    _log(f"register exception: {reg_err}")
                    register_ok = False
                
                print(f"[DEBUG] register_openai_account returned: {register_ok}", flush=True)
                _log(f"register_openai_account returned: {register_ok}")
                
                # Team 开通逻辑
                checkout_ok: bool | None = None
                checkout_err = ""
                session_data = {}
                used_card_id: int | None = None
                
                print(f"[DEBUG] register_ok={register_ok}, starting card check mode={card_mode}...", flush=True)
                _log(f"register_ok={register_ok}, starting team onboarding check...")
                
                if register_ok:
                    print("[DEBUG] starting onboarding...", flush=True)
                    
                    try:
                        _log("start team onboarding flow")
                        
                        from plugins.gpt_business.services.onboarding_flow import (
                            run_onboarding_flow,
                            set_log_callback,
                        )
                        
                        set_log_callback(_log)
                        
                        def get_checkout_card() -> dict[str, Any] | None:
                            nonlocal used_card_id
                            payload = _get_available_card_for_checkout(selected_card_id if card_mode == "selected" else None)
                            if payload:
                                card_id = payload.get("card_id")
                                try:
                                    used_card_id = int(card_id) if card_id is not None else None
                                except (TypeError, ValueError):
                                    used_card_id = None
                            return payload

                        skip_checkout = card_mode == "manual"

                        print(f"[DEBUG] calling run_onboarding_flow mode={card_mode}...", flush=True)
                        success, session_data = run_onboarding_flow(
                            page=page,
                            email=email,
                            skip_checkout=skip_checkout,
                            get_card_callback=None if skip_checkout else get_checkout_card,
                            card_wait_timeout=300,
                        )
                        print(f"[DEBUG] run_onboarding_flow returned: {success}", flush=True)
                        
                        checkout_ok = success
                        if success:
                            _log("team onboarding completed successfully")
                        else:
                            checkout_err = "onboarding flow failed"
                            _log("team onboarding failed")
                        
                        shot_callback("checkout_done.png")
                        
                    except Exception as e:
                        print(f"[DEBUG] checkout exception: {e}", flush=True)
                        checkout_err = str(e)
                        _log(f"checkout error: {e}")
                        shot_callback("checkout_error.png")
                        checkout_ok = False
                
                return {
                    "profile_id": profile.id,
                    "register_ok": register_ok,
                    "checkout_ok": checkout_ok,
                    "checkout_error": checkout_err,
                    "session_data": session_data,
                    "used_card_id": used_card_id,
                }
            finally:
                # 关闭浏览器
                if page:
                    try:
                        page.quit()
                    except Exception:
                        pass
                try:
                    api.close_profile(profile.id)
                    _log(f"closed profile: {profile.id}")
                except Exception as e:
                    _log(f"failed to close profile: {e}")

        flow_result = _run_sync()
        _set_task_progress(record_id, 2, 3, "初始化环境")
        register_ok = bool(flow_result.get("register_ok"))
        checkout_ok = flow_result.get("checkout_ok")
        used_card_id = flow_result.get("used_card_id")
        
        # 开通成功：注册成功且开通成功
        # 未开通：注册成功但开通未进行或失败
        if checkout_ok:
            open_status = "activated"  # 已开通
        elif register_ok:
            open_status = "registered"  # 已注册未开通
        else:
            open_status = "failed"  # 失败
        
        success = register_ok and (checkout_ok in (None, True))

        _log(f"done register_ok={register_ok} checkout_ok={checkout_ok} open_status={open_status}")
        
        now = timezone.now().isoformat()
        patch_account(
            mother_id,
            {
                "open_status": open_status,
                "open_last_task": record_id,
                "open_updated_at": now,
                "register_status": "success" if register_ok else "failed",
                "register_updated_at": now,
                "login_status": "success" if register_ok else "failed",
                "login_updated_at": now,
            },
        )

        if used_card_id:
            _mark_card_as_used(used_card_id, mother_id, "self_register")

        result: dict[str, Any] = {
            "success": success,
            "mother_id": mother_id,
            "email": email,
            "artifacts": _artifacts_list_from_job_dir(job_dir),
            "details": flow_result,
        }

        _set_task_progress(record_id, 3, 3, "完成处理")
        patch_task(
            record_id,
            {
                "status": "completed" if success else "failed",
                "finished_at": timezone.now().isoformat(),
                "result": result,
                **({} if success else {"error": str(flow_result.get("checkout_error") or "self_register failed")}),
            },
        )

        return result
    except Exception as exc:
        logger.exception("gpt_business self_register_task failed")
        _append_trace_line(
            celery_task_id,
            trace_email,
            f"self_register failed: {exc}",
            step="self_register",
            action="error",
            level="error",
        )
        try:
            if mother_id:
                patch_account(
                    mother_id,
                    {
                        "open_status": "failed",
                        "open_last_task": record_id,
                        "open_updated_at": timezone.now().isoformat(),
                        "register_status": "failed",
                        "register_updated_at": timezone.now().isoformat(),
                        "login_status": "failed",
                        "login_updated_at": timezone.now().isoformat(),
                    },
                )
        except Exception:
            pass

        _set_task_progress(record_id, 3, 3, "失败")
        patch_task(
            record_id,
            {
                "status": "failed",
                "finished_at": timezone.now().isoformat(),
                "error": str(exc),
                **(
                    {
                        "result": {
                            "success": False,
                            "mother_id": mother_id,
                            "artifacts": _artifacts_list_from_job_dir(job_dir)
                            if job_dir
                            else [],
                        }
                    }
                    if job_dir
                    else {}
                ),
            },
        )
        raise


def _launch_geekez_for_account(account_id: str) -> dict[str, Any]:
    settings = get_settings()
    acc_raw = find_account(settings, str(account_id))
    if not isinstance(acc_raw, dict):
        raise RuntimeError("Account not found")

    acc: dict[str, Any] = acc_raw
    email = str(acc.get("email") or "").strip()
    if not email:
        raise RuntimeError("Email missing")

    from apps.integrations.browser_base import BrowserType, get_browser_manager

    manager = get_browser_manager()
    api = manager.get_api(BrowserType.GEEKEZ)
    if not api.health_check():
        raise RuntimeError("GeekezBrowser 服务不在线")

    profile_name = _generate_random_profile_name(email)
    created_profile = True

    profile = api.create_or_update_profile(
        name=profile_name,
        proxy=None,
        metadata={"account": {"email": email, "profile_strategy": "random_new"}},
    )

    launch_info = api.launch_profile(profile.id)
    if not launch_info:
        raise RuntimeError("启动 Geekez profile 失败")

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

    saved = patch_account(str(account_id), patch)

    return {
        "success": True,
        "created_profile": created_profile,
        "browser_type": BrowserType.GEEKEZ.value,
        "profile_id": launch_info.profile_id,
        "debug_port": launch_info.debug_port,
        "cdp_endpoint": launch_info.cdp_endpoint,
        "pid": launch_info.pid,
        "saved": bool(saved),
    }


@shared_task(bind=True)
def launch_geekez_task(self, account_id: str):
    return _launch_geekez_for_account(str(account_id))


@shared_task(bind=True)
def auto_invite_task(self, record_id: str):
    celery_task_id = str(self.request.id or "")
    trace_email = ""
    patch_task(
        record_id,
        {
            "status": "running",
            "started_at": timezone.now().isoformat(),
            "celery_task_id": self.request.id,
        },
    )

    try:
        settings = get_settings()
        task_record = _get_task_record(settings, record_id)
        if not task_record:
            raise RuntimeError("Task record not found")

        mother_id = str(task_record.get("mother_id") or "").strip()
        if not mother_id:
            raise RuntimeError("Task record missing mother_id")

        mother = find_account(settings, mother_id)
        if not isinstance(mother, dict) or str(mother.get("type")) != "mother":
            raise RuntimeError("Mother account not found")

        email = str(mother.get("email") or "").strip()
        password = str(mother.get("account_password") or "").strip()
        if not email or not password:
            raise RuntimeError("Mother account missing email/account_password")

        trace_email = email

        media_root = Path(str(getattr(django_settings, "MEDIA_ROOT", "")))
        if not str(media_root):
            raise RuntimeError("MEDIA_ROOT is not configured")

        job_dir = media_root / "gpt_business" / "jobs" / record_id
        artifacts = prepare_artifacts(job_dir)

        def _append_log(msg: str):
            try:
                ts = timezone.now().isoformat()
                artifacts.log_file.parent.mkdir(parents=True, exist_ok=True)
                with artifacts.log_file.open("a", encoding="utf-8") as f:
                    f.write(f"[{ts}] {msg}\n")
                _append_trace_line(
                    celery_task_id,
                    trace_email,
                    msg,
                    step="auto_invite",
                    action="log",
                )
            except Exception:
                pass

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

        # 读取子号；如果 seat_total>0 且子号数量不足，则自动补齐到 seat_total
        children = [
            a
            for a in list_accounts(settings)
            if isinstance(a, dict) and str(a.get("type")) == "child" and str(a.get("parent_id")) == mother_id
        ]
        seat_total = int(mother.get("seat_total") or 0)
        need_fill = 0
        if seat_total > 0 and len(children) < seat_total:
            need_fill = seat_total - len(children)

        if need_fill > 0:
            _append_log(f"auto-fill children by seat_total: seat_total={seat_total} existing={len(children)} fill={need_fill}")

            email_cfg = _cloudmail_email_config_from_account(mother)
            from apps.integrations.email.services.client import CloudMailClient

            mail_client = CloudMailClient(
                api_base=str(email_cfg.get("api_base") or ""),
                api_token=str(email_cfg.get("api_auth") or ""),
                domains=list(email_cfg.get("domains") or []),
                default_role=str(email_cfg.get("role") or "user"),
            )

            preferred_domain = str(mother.get("cloudmail_domain") or "").strip() or None
            if preferred_domain and preferred_domain not in (mail_client.domains or []):
                preferred_domain = None

            now_iso = timezone.now().isoformat()
            created_children: list[dict[str, Any]] = []
            for i in range(need_fill):
                email_child, email_password = mail_client.create_random_user(domain=preferred_domain)
                child_id = uuid.uuid4().hex
                account_password = _generate_account_password()
                actual_domain = email_child.split("@", 1)[1] if "@" in email_child else ""

                record = {
                    "id": child_id,
                    "type": "child",
                    "parent_id": mother_id,
                    "cloudmail_config_id": int(mother.get("cloudmail_config_id") or 0),
                    "cloudmail_domain": actual_domain,
                    "email": email_child,
                    "email_password": email_password,
                    "account_password": account_password,
                    "note": "auto_fill_by_auto_invite",
                    "register_status": "not_started",
                    "register_updated_at": "",
                    "login_status": "not_started",
                    "login_updated_at": "",
                    "pool_status": "not_started",
                    "pool_updated_at": "",
                    "team_join_status": "not_started",
                    "team_join_updated_at": "",
                    "created_at": now_iso,
                    "updated_at": now_iso,
                }
                add_account(record)
                created_children.append(record)
                _append_log(f"auto-filled child {i + 1}/{need_fill}: {email_child}")

            # 重新加载最新 settings/children
            settings = get_settings()
            children = [
                a
                for a in list_accounts(settings)
                if isinstance(a, dict) and str(a.get("type")) == "child" and str(a.get("parent_id")) == mother_id
            ]
            _append_log(f"auto-fill done children_total={len(children)}")

        if not children:
            raise RuntimeError(
                "No child accounts. Set mother.seat_total > 0 to auto-fill, or create children manually before auto_invite"
            )

        # 仅对“未入队”的子号发送邀请；已入队子号会在子号阶段直接 skip。
        child_emails_to_invite: list[str] = []
        for c in children:
            join_status = str(c.get("team_join_status") or "").strip()
            team_account_id_saved = str(c.get("team_account_id") or "").strip()
            if join_status == "success" or team_account_id_saved:
                continue
            ce = str(c.get("email") or "").strip()
            if ce:
                child_emails_to_invite.append(ce)

        _append_log(
            f"auto_invite start mother_id={mother_id} email={email} children_total={len(children)} invite_targets={len(child_emails_to_invite)}"
        )
        _set_task_progress(record_id, 2, 3, "发送邀请")

        # 状态：邀请中
        try:
            patch_account(
                mother_id,
                {
                    "invite_status": "running",
                    "invite_last_task": record_id,
                    "invite_updated_at": timezone.now().isoformat(),
                },
            )
        except Exception:
            pass

        token = str(mother.get("auth_token") or "").strip()
        account_id = str(mother.get("account_id") or "").strip()

        # NOTE: 这里必须走浏览器内的 fetch（见 chatgpt_backend_api.py）
        # 因为 Celery 容器内 requests 可能无法直连 chatgpt.com（例如 Errno 101 Network is unreachable）。
        from .services.browser_service import BrowserService
        from .services.chatgpt_backend_api import browser_fetch_account_id, browser_invite_emails
        from .services.chatgpt_session import ensure_access_token

        def _safe_name(raw: str) -> str:
            s = (raw or "").strip()
            s = re.sub(r"[^a-zA-Z0-9_.-]+", "_", s)
            return s[:80] if len(s) > 80 else s

        def _make_shot(page, prefix: str):
            def _shot(name: str):
                try:
                    p = job_dir / f"{prefix}{name}"
                    page.get_screenshot(path=str(p), full_page=True)
                except Exception:
                    pass

            return _shot

        def _extract_urls(text: str) -> list[str]:
            urls = re.findall(r"https?://[^\s\"<>]+", text or "")
            cleaned: list[str] = []
            for u in urls:
                u2 = u.strip().strip("'\")\n\r\t")
                u2 = u2.rstrip(").,;")
                if u2:
                    cleaned.append(u2)
            return cleaned

        def _pick_invite_url(urls: list[str]) -> str:
            # 尽量挑选 chatgpt/openai 的 join/invite 链接
            for u in urls:
                lu = u.lower()
                if "chatgpt.com" in lu or "openai.com" in lu:
                    if any(k in lu for k in ["invite", "invitation", "join", "workspace"]):
                        return u
            for u in urls:
                lu = u.lower()
                if "chatgpt.com" in lu or "openai.com" in lu:
                    return u
            return urls[0] if urls else ""

        def _wait_invite_link(mail_client, to_email: str, timeout_sec: int = 180) -> str:
            start = timezone.now().timestamp()
            _append_log(f"wait invite email start to={to_email} timeout={timeout_sec}s")
            while timezone.now().timestamp() - start < timeout_sec:
                try:
                    emails = mail_client.list_emails(to_email=to_email, size=10, time_sort="desc")
                    for em in emails:
                        text = f"{em.subject or ''}\n{em.text or ''}\n{em.content or ''}"
                        urls = _extract_urls(text)
                        invite_url = _pick_invite_url(urls)
                        if invite_url:
                            _append_log(f"invite email found subject={em.subject!r} url={invite_url}")
                            return invite_url
                except Exception as e:
                    _append_log(f"wait invite email poll error: {e}")
                time.sleep(5)
            _append_log("wait invite email timeout")
            return ""

        def _try_accept_invite_ui(page, *, log_prefix: str, shot_cb) -> bool:
            # 只做轻量点击：优先按文案点击；避免误点 submit。
            try:
                from .services.openai_register import wait_for_page_stable, wait_for_element, human_delay
            except Exception:
                return False

            def _log(msg: str):
                _append_log(f"{log_prefix}{msg}")

            try:
                wait_for_page_stable(page, timeout=8)
            except Exception:
                pass

            shot_cb("accept_01_before.png")

            candidates = [
                "text:Join workspace",
                "text:Join team",
                "text:Join",
                "text:Accept invite",
                "text:Accept invitation",
                "text:Accept",
                "text:加入工作区",
                "text:加入团队",
                "text:加入",
                "text:接受邀请",
                "text:接受",
            ]

            for sel in candidates:
                try:
                    btn = wait_for_element(page, sel, timeout=2)
                    if btn:
                        _log(f"click {sel}")
                        btn.click()
                        human_delay(0.8, 1.6)
                        shot_cb("accept_02_after_click.png")
                        return True
                except Exception:
                    continue

            return False

        invite_response: dict[str, Any] = {"success": [], "failed": [], "raw": {}}

        if not child_emails_to_invite:
            _append_log("no pending children to invite; skip mother invite stage")
        else:
            with BrowserService(profile_name=f"gpt_{email}") as browser:
                _append_log(f"browser launched profile={getattr(browser, '_launched_profile_id', None)}")
                if not browser.page:
                    raise RuntimeError("Browser page is not available")

                _shot = _make_shot(browser.page, prefix="mother_")

                try:
                    browser.page.get("https://chatgpt.com/")
                except Exception:
                    pass

                if token:
                    _append_log("reuse existing auth_token")
                else:
                    _append_log("auth_token missing, login via Geekez + /api/auth/session")
                    token, _session = ensure_access_token(
                        browser.page,
                        email=email,
                        password=password,
                        timeout=180,
                        log_callback=_append_log,
                        screenshot_callback=_shot,
                    )

                if not token:
                    raise RuntimeError("Failed to get auth_token")

                _append_log(f"auth_token ok len={len(token)}")

                if not account_id:
                    _append_log("account_id missing, fetch via browser /backend-api/accounts/check")
                    try:
                        account_id = browser_fetch_account_id(
                            browser.page,
                            auth_token=token,
                            timeout_sec=20,
                            log_callback=_append_log,
                        )
                    except Exception as e:
                        _append_log(f"fetch account_id failed: {e}; try relogin")
                        token, _session = ensure_access_token(
                            browser.page,
                            email=email,
                            password=password,
                            timeout=180,
                            log_callback=_append_log,
                            screenshot_callback=_shot,
                        )
                        account_id = browser_fetch_account_id(
                            browser.page,
                            auth_token=token,
                            timeout_sec=20,
                            log_callback=_append_log,
                        )

                if account_id:
                    _append_log(f"account_id ok {account_id}")

                if not account_id:
                    raise RuntimeError("Failed to get account_id")

                _append_log(f"invite start count={len(child_emails_to_invite)}")
                invite_response = browser_invite_emails(
                    browser.page,
                    account_id=account_id,
                    auth_token=token,
                    emails=child_emails_to_invite,
                    timeout_sec=40,
                    log_callback=_append_log,
                )

        success_list = invite_response.get("success") or []
        failed_list = invite_response.get("failed") or []
        has_failed = isinstance(failed_list, list) and len(failed_list) > 0

        try:
            _append_log(f"invite done success={len(success_list) if isinstance(success_list, list) else 0} failed={len(failed_list) if isinstance(failed_list, list) else 0}")
            if isinstance(failed_list, list) and failed_list:
                # 失败邮箱可能含原因对象，这里只尽量提取 email 字段
                failed_emails: list[str] = []
                for x in failed_list:
                    if isinstance(x, str):
                        failed_emails.append(x)
                    elif isinstance(x, dict) and x.get("email"):
                        failed_emails.append(str(x.get("email")))
                failed_emails = [e for e in failed_emails if e]
                if failed_emails:
                    _append_log("invite failed_emails=" + ",".join(failed_emails[:50]))
        except Exception:
            pass

        now = timezone.now().isoformat()
        patch: dict[str, Any] = {
            "invite_status": "success" if not has_failed else "failed",
            "invite_last_task": record_id,
            "invite_updated_at": now,
            # 母号 token 属于“已登录”的强信号
            **({"login_status": "success", "login_updated_at": now} if token else {}),
        }
        if token:
            patch["auth_token"] = token
        if account_id:
            patch["account_id"] = account_id
        patch_account(mother_id, patch)

        # ==================== 子号：注册/登录 + 接受邀请 + 验证加入 Team ====================
        from apps.integrations.email.services.client import CloudMailClient
        from plugins.gpt_business.services.openai_register import register_openai_account

        children_results: list[dict[str, Any]] = []
        join_failed: list[str] = []
        _append_log("children accept stage start")

        for idx, child in enumerate(children, start=1):
            child_email = str(child.get("email") or "").strip()
            child_id = str(child.get("id") or "").strip()
            child_pwd = str(child.get("account_password") or "").strip()
            child_join_status = str(child.get("team_join_status") or "").strip()
            child_team_account_id_saved = str(child.get("team_account_id") or "").strip()
            child_login_status = str(child.get("login_status") or "").strip()

            log_prefix = f"[child {idx}/{len(children)} {child_email}] "
            if not child_email:
                continue

            _append_log(log_prefix + "start")

            # 已入队的子号：直接跳过（避免重复登录/重复点邀请）
            if child_join_status == "success" or child_team_account_id_saved:
                children_results.append(
                    {
                        "email": child_email,
                        "id": child_id,
                        "joined": True,
                        "team_account_id": child_team_account_id_saved,
                        "skipped": True,
                        "reason": "already_joined",
                    }
                )
                _append_log(log_prefix + "skip: already joined")
                continue
            if not child_pwd:
                children_results.append({"email": child_email, "joined": False, "error": "missing account_password"})
                join_failed.append(child_email)
                continue

            # 状态：子号入队中
            try:
                patch_account(
                    child_id,
                    {
                        "team_join_status": "running",
                        "team_join_task": record_id,
                        "team_join_updated_at": timezone.now().isoformat(),
                    },
                )
            except Exception:
                pass

            email_cfg_child = _cloudmail_email_config_from_account(child)
            mail_client_child = CloudMailClient(
                api_base=str(email_cfg_child.get("api_base") or ""),
                api_token=str(email_cfg_child.get("api_auth") or ""),
                domains=list(email_cfg_child.get("domains") or []),
                default_role=str(email_cfg_child.get("role") or "user"),
            )

            child_result: dict[str, Any] = {
                "email": child_email,
                "id": child_id,
                "joined": False,
                "invite_url": "",
            }

            try:
                for attempt in range(2):
                    try:
                        with BrowserService(profile_name=f"gpt_{child_email}") as child_browser:
                            if not child_browser.page:
                                raise RuntimeError("child browser page is not available")

                            safe = _safe_name(child_email)
                            child_shot = _make_shot(child_browser.page, prefix=f"child_{safe}_")

                            try:
                                child_browser.page.get("https://chatgpt.com/")
                            except Exception:
                                pass

                            # 1) 登录（若不存在则注册）
                            child_token = ""
                            try:
                                try:
                                    patch_account(
                                        child_id,
                                        {
                                            "login_status": "running",
                                            "login_updated_at": timezone.now().isoformat(),
                                        },
                                    )
                                except Exception:
                                    pass
                                # 如果标记为已登录，则先尝试直接复用 session（避免重复跑完整登录流程）
                                if child_login_status == "success":
                                    _append_log(log_prefix + "skip login: login_status=success, try session")
                                    try:
                                        from .services.chatgpt_session import fetch_auth_session

                                        sess_data = fetch_auth_session(child_browser.page, timeout=7)
                                        sess_user = sess_data.get("user") if isinstance(sess_data, dict) else None
                                        sess_email = (
                                            str(sess_user.get("email") or "").strip()
                                            if isinstance(sess_user, dict)
                                            else ""
                                        )
                                        sess_token = (
                                            str(sess_data.get("accessToken") or "").strip()
                                            if isinstance(sess_data, dict)
                                            else ""
                                        )
                                        if sess_token and sess_email and sess_email.lower() == child_email.lower():
                                            child_token = sess_token
                                    except Exception:
                                        child_token = ""

                                if not child_token:
                                    _append_log(log_prefix + "login via /api/auth/session")
                                    child_token, _sess = ensure_access_token(
                                        child_browser.page,
                                        email=child_email,
                                        password=child_pwd,
                                        timeout=180,
                                        log_callback=lambda m: _append_log(log_prefix + m),
                                        screenshot_callback=child_shot,
                                    )

                                try:
                                    patch_account(
                                        child_id,
                                        {
                                            "login_status": "success",
                                            "login_updated_at": timezone.now().isoformat(),
                                        },
                                    )
                                except Exception:
                                    pass
                            except Exception as e:
                                _append_log(log_prefix + f"login failed: {e}; try register")

                                try:
                                    patch_account(
                                        child_id,
                                        {
                                            "register_status": "running",
                                            "register_updated_at": timezone.now().isoformat(),
                                        },
                                    )
                                except Exception:
                                    pass

                                def _get_code(_email: str) -> str | None:
                                    # 不强依赖 sender_contains，避免不同环境发件人字段差异导致拿不到验证码
                                    _append_log(log_prefix + "wait verification code start")
                                    code = mail_client_child.wait_for_verification_code(
                                        to_email=child_email,
                                        timeout=600,
                                        poll_interval=5,
                                        sender_contains=None,
                                    )
                                    _append_log(log_prefix + ("verification code received" if code else "verification code missing"))
                                    return code

                                register_ok = register_openai_account(
                                    child_browser.page,
                                    email=child_email,
                                    password=child_pwd,
                                    get_verification_code=_get_code,
                                    log_callback=lambda m: _append_log(log_prefix + m),
                                    screenshot_callback=child_shot,
                                )
                                _append_log(log_prefix + f"register result={register_ok}")
                                if not register_ok:
                                    # 可能账号已创建但 session 没落地（会回到未登录首页）。尝试再登录一次兜底。
                                    _append_log(log_prefix + "register returned False, try login anyway")
                                    try:
                                        child_token, _sess = ensure_access_token(
                                            child_browser.page,
                                            email=child_email,
                                            password=child_pwd,
                                            timeout=180,
                                            log_callback=lambda m: _append_log(log_prefix + m),
                                            screenshot_callback=child_shot,
                                        )
                                        register_ok = True
                                    except Exception:
                                        try:
                                            patch_account(
                                                child_id,
                                                {
                                                    "register_status": "failed",
                                                    "register_updated_at": timezone.now().isoformat(),
                                                },
                                            )
                                        except Exception:
                                            pass
                                        raise RuntimeError("register_openai_account failed")

                                try:
                                    patch_account(
                                        child_id,
                                        {
                                            "register_status": "success",
                                            "register_updated_at": timezone.now().isoformat(),
                                        },
                                    )
                                except Exception:
                                    pass

                                # 注册流程结束后，尽量用轻量 session 读取 token（避免再次跑完整登录导致页面断连）
                                from .services.chatgpt_session import fetch_auth_session

                                try:
                                    child_browser.page.get("https://chatgpt.com/")
                                    time.sleep(2)
                                except Exception:
                                    pass

                                sess_data = fetch_auth_session(child_browser.page, timeout=7)
                                sess_user = sess_data.get("user") if isinstance(sess_data, dict) else None
                                sess_email = str(sess_user.get("email") or "").strip() if isinstance(sess_user, dict) else ""
                                sess_token = str(sess_data.get("accessToken") or "").strip() if isinstance(sess_data, dict) else ""
                                if not child_token and sess_token and sess_email and sess_email.lower() == child_email.lower():
                                    child_token = sess_token

                                if not child_token:
                                    child_token, _sess = ensure_access_token(
                                        child_browser.page,
                                        email=child_email,
                                        password=child_pwd,
                                        timeout=180,
                                        log_callback=lambda m: _append_log(log_prefix + m),
                                        screenshot_callback=child_shot,
                                    )

                                try:
                                    patch_account(
                                        child_id,
                                        {
                                            "login_status": "success",
                                            "login_updated_at": timezone.now().isoformat(),
                                        },
                                    )
                                except Exception:
                                    pass

                            child_result["auth"] = "ok"

                            # 2) 检查是否已经加入 Team
                            child_team_account_id = ""
                            try:
                                child_team_account_id = browser_fetch_account_id(
                                    child_browser.page,
                                    auth_token=child_token,
                                    timeout_sec=20,
                                    log_callback=lambda m: _append_log(log_prefix + m),
                                )
                            except Exception as e:
                                _append_log(log_prefix + f"check team account failed: {e}")

                            if child_team_account_id:
                                _append_log(log_prefix + f"already in team account_id={child_team_account_id}")
                                child_result["joined"] = True
                                child_result["team_account_id"] = child_team_account_id
                            else:
                                _append_log(log_prefix + "not in team yet, try accept invite")

                                invite_url = _wait_invite_link(mail_client_child, child_email, timeout_sec=180)
                                if invite_url:
                                    child_result["invite_url"] = invite_url
                                    _append_log(log_prefix + "open invite url")
                                    try:
                                        child_browser.page.get(invite_url)
                                    except Exception as e:
                                        _append_log(log_prefix + f"open invite url failed: {e}")
                                    _try_accept_invite_ui(child_browser.page, log_prefix=log_prefix, shot_cb=child_shot)
                                else:
                                    _append_log(log_prefix + "invite email not found, try in-app prompt")
                                    try:
                                        child_browser.page.get("https://chatgpt.com/")
                                    except Exception:
                                        pass
                                    _try_accept_invite_ui(child_browser.page, log_prefix=log_prefix, shot_cb=child_shot)

                                # 3) 再次校验
                                try:
                                    child_team_account_id = browser_fetch_account_id(
                                        child_browser.page,
                                        auth_token=child_token,
                                        timeout_sec=20,
                                        log_callback=lambda m: _append_log(log_prefix + m),
                                    )
                                except Exception as e:
                                    _append_log(log_prefix + f"re-check team account failed: {e}")
                                    child_team_account_id = ""

                                if child_team_account_id:
                                    _append_log(log_prefix + f"joined team ok account_id={child_team_account_id}")
                                    child_result["joined"] = True
                                    child_result["team_account_id"] = child_team_account_id
                                else:
                                    _append_log(log_prefix + "join team failed")
                                    child_result["joined"] = False
                                    join_failed.append(child_email)

                            # 写回子号状态（不写 token/password）
                            try:
                                patch_account(
                                    child_id,
                                    {
                                        "team_join_status": "success" if child_result.get("joined") else "failed",
                                        "team_join_task": record_id,
                                        "team_join_updated_at": timezone.now().isoformat(),
                                        **(
                                            {"team_account_id": child_result.get("team_account_id")}
                                            if child_result.get("team_account_id")
                                            else {}
                                        ),
                                    },
                                )
                            except Exception:
                                pass

                        break
                    except Exception as e:
                        _append_log(log_prefix + f"attempt {attempt + 1} exception: {e}")
                        if attempt == 0 and "disconnected" in str(e).lower():
                            _append_log(log_prefix + "retry due to disconnected page")
                            time.sleep(2)
                            continue
                        raise

            except Exception as e:
                _append_log(log_prefix + f"child flow exception: {e}")
                child_result["error"] = str(e)
                join_failed.append(child_email)

                # 兜底标记失败（避免长时间卡在 running）
                try:
                    patch_account(
                        child_id,
                        {
                            "team_join_status": "failed",
                            "team_join_task": record_id,
                            "team_join_updated_at": timezone.now().isoformat(),
                            "login_status": "failed",
                            "login_updated_at": timezone.now().isoformat(),
                        },
                    )
                except Exception:
                    pass

            children_results.append(child_result)

        _append_log(f"children accept stage done failed={len(join_failed)}")

        overall_ok = (not has_failed) and (len(join_failed) == 0)

        result: dict[str, Any] = {
            "success": overall_ok,
            "mother_id": mother_id,
            "email": email,
            "invited_count": len(child_emails_to_invite),
            "artifacts": _artifacts_list_from_job_dir(job_dir),
            "details": {
                "failed": invite_response.get("failed") or [],
                "success": invite_response.get("success") or [],
            },
            "children": children_results,
            "children_join_failed": join_failed,
        }

        _set_task_progress(record_id, 3, 3, "完成处理")
        patch_task(
            record_id,
            {
                "status": "completed" if overall_ok else "failed",
                "finished_at": timezone.now().isoformat(),
                "result": result,
                **(
                    {}
                    if overall_ok
                    else {
                        "error": (
                            "auto_invite has failed invites"
                            if has_failed
                            else f"auto_invite child join failed: {','.join(join_failed[:20])}"
                        )
                    }
                ),
            },
        )

        return result
    except Exception as exc:
        logger.exception("gpt_business auto_invite_task failed")
        _append_trace_line(
            celery_task_id,
            trace_email,
            f"auto_invite failed: {exc}",
            step="auto_invite",
            action="error",
            level="error",
        )
        _set_task_progress(record_id, 3, 3, "失败")
        patch_task(
            record_id,
            {
                "status": "failed",
                "finished_at": timezone.now().isoformat(),
                "error": str(exc),
            },
        )
        raise


@shared_task(bind=True)
def sub2api_sink_task(self, record_id: str):
    celery_task_id = str(self.request.id or "")
    trace_email = ""
    patch_task(
        record_id,
        {
            "status": "running",
            "started_at": timezone.now().isoformat(),
            "celery_task_id": self.request.id,
        },
    )
    _set_task_progress(record_id, 1, 3, "准备入池")

    try:
        settings = get_settings()
        task_record = _get_task_record(settings, record_id)
        if not task_record:
            raise RuntimeError("Task record not found")

        mother_id = str(task_record.get("mother_id") or "").strip()
        if not mother_id:
            raise RuntimeError("Task record missing mother_id")

        mother = find_account(settings, mother_id)
        if not isinstance(mother, dict) or str(mother.get("type")) != "mother":
            raise RuntimeError("Mother account not found")

        trace_email = str(mother.get("email") or "").strip()

        s2a_target_key = str(task_record.get("s2a_target_key") or "").strip()
        pool_mode = str(task_record.get("pool_mode") or "").strip() or "crs_sync"
        # Backward/forward compatibility for UI values
        # - "crs"      -> "crs_sync"
        # - "s2a"      -> "s2a_oauth"
        # Keep internal logic normalized.
        if pool_mode in {"crs", "crs_sync"}:
            pool_mode = "crs_sync"
        elif pool_mode in {"s2a", "s2a_oauth"}:
            pool_mode = "s2a_oauth"

        if not trace_email:
            raise RuntimeError("Mother account missing email")

        children_all = [
            a
            for a in list_accounts(settings)
            if isinstance(a, dict) and str(a.get("type")) == "child" and str(a.get("parent_id")) == mother_id
        ]
        accounts_all = [mother, *children_all]

        emails_all = [str(a.get("email") or "").strip() for a in accounts_all]
        emails_all = [e for e in emails_all if e]
        if not emails_all:
            raise RuntimeError("No accounts to pool")

        # 已入池（success）的账号直接跳过：避免重复入池/重复授权
        accounts: list[dict[str, Any]] = []
        already_pooled: dict[str, Any] = {}
        for account in accounts_all:
            aemail = str(account.get("email") or "").strip()
            if not aemail:
                continue
            pool_status = str(account.get("pool_status") or "").strip()
            if pool_status == "success":
                already_pooled[aemail] = {"status": "skipped", "reason": "pool_status_success"}
                continue
            accounts.append(account)

        emails = [str(a.get("email") or "").strip() for a in accounts]
        emails = [e for e in emails if e]

        # 账号状态：入池中（只标记需要处理的账号；已入池 success 的不动）
        now_running = timezone.now().isoformat()
        for account in accounts:
            aid = str(account.get("id") or "").strip()
            aemail = str(account.get("email") or "").strip()
            if not aid or not aemail:
                continue
            try:
                patch_account(
                    aid,
                    {
                        "pool_status": "running",
                        "pool_last_task": record_id,
                        "pool_updated_at": now_running,
                    },
                )
            except Exception:
                pass

        crs = settings.get("crs") or {}

        # Resolve S2A config (support multiple targets)
        s2a_raw = settings.get("s2a")
        s2a: dict[str, Any] = s2a_raw if isinstance(s2a_raw, dict) else {}

        s2a_targets_raw = settings.get("s2a_targets")
        if isinstance(s2a_targets_raw, list):
            default_key = str(settings.get("s2a_default_target") or "").strip()
            chosen_key = s2a_target_key or default_key
            if chosen_key:
                for t in s2a_targets_raw or []:
                    if not isinstance(t, dict):
                        continue
                    if str(t.get("key") or "").strip() != chosen_key:
                        continue
                    cfg = t.get("config")
                    if isinstance(cfg, dict):
                        s2a = cfg
                        break

        crs_api_base = str(crs.get("api_base") or "").strip()
        crs_admin_token = str(crs.get("admin_token") or "").strip()

        sub2api_api_base = str(s2a.get("api_base") or "").strip()
        sub2api_admin_api_key = str(s2a.get("admin_key") or "").strip()
        sub2api_admin_jwt = str(s2a.get("admin_token") or "").strip()

        group_ids = s2a.get("group_ids") or []
        group_ids_str = ",".join([str(int(x)) for x in group_ids if str(x).strip().isdigit()])

        concurrency = int(s2a.get("concurrency") or 3)
        priority = int(s2a.get("priority") or 50)

        media_root = Path(str(getattr(django_settings, "MEDIA_ROOT", "")))
        if not str(media_root):
            raise RuntimeError("MEDIA_ROOT is not configured")

        job_dir = media_root / "gpt_business" / "jobs" / record_id
        artifacts = prepare_artifacts(job_dir)

        # Ensure run.log exists (UI reads it as the task log)
        try:
            artifacts.log_file.parent.mkdir(parents=True, exist_ok=True)
            artifacts.log_file.touch(exist_ok=True)
        except Exception:
            pass

        def _sanitize_url(url: str) -> str:
            s = str(url or "")
            # Prevent leaking oauth code/tokens in run.log
            for key in ["code", "access_token", "refresh_token", "id_token", "token"]:
                try:
                    s = re.sub(rf"([?&]{key}=)[^&]+", r"\\1***", s)
                except Exception:
                    continue
            return s

        def _log_line(msg: str) -> None:
            try:
                ts = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                safe = str(msg).replace("\r", " ").rstrip("\n")
                with artifacts.log_file.open("a", encoding="utf-8") as fp:
                    fp.write(f"[{ts}] {safe}\n")
                _append_trace_line(
                    celery_task_id,
                    trace_email,
                    safe,
                    step="sub2api_sink",
                    action="log",
                )
            except Exception:
                # Never fail the task due to logging
                pass

        _log_line(
            f"sub2api_sink start record_id={record_id} mother_id={mother_id} accounts_total={len(emails_all)} to_process={len(emails)} already_success={len(already_pooled)} pool_mode={pool_mode} s2a_target_key={s2a_target_key or '-'}"
        )
        _log_line(f"s2a_api_base={sub2api_api_base}")

        # 如果全部账号都已入池，直接跳过（不强制校验 S2A/CRS 连通性，也不重复入池动作）
        if not emails:
            sink_result: dict[str, Any] = {
                "ok": 0,
                "skip": len(already_pooled),
                "fail": 0,
                "details": dict(already_pooled),
            }
            _log_line("no accounts to process (all pool_status=success); skip")
        else:
            if not sub2api_api_base:
                raise RuntimeError("S2A settings missing api_base")
            if not sub2api_admin_api_key and not sub2api_admin_jwt:
                raise RuntimeError("S2A settings missing admin_key/admin_token")

            # Test connection early (fail fast)
            from .services.sub2api_sink_service import sub2api_test_connection

            ok, msg = sub2api_test_connection(
                api_base=sub2api_api_base,
                admin_key=sub2api_admin_api_key,
                admin_token=sub2api_admin_jwt,
                timeout=int((settings.get("request") or {}).get("timeout") or 20),
            )
            if not ok:
                _log_line(f"s2a_test_connection failed: {msg}")
                raise RuntimeError(f"S2A connection test failed: {msg}")
            _log_line("s2a_test_connection ok")

            # 生成一个 accounts.csv（只要 email+status=success 即可被 sub2api_sink_run 读取）
            with artifacts.csv_file.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["email", "status"])
                writer.writeheader()
                for e in emails:
                    writer.writerow({"email": e, "status": "success"})

            # 直接走内置逻辑（不再 subprocess 外部 repo）
            from .services.sub2api_sink_service import (
                CrsConfig,
                Sub2ApiConfig,
                sink_openai_oauth_from_crs_to_sub2api,
                sub2api_create_openai_oauth_account,
                sub2api_openai_generate_auth_url,
                sub2api_openai_create_from_oauth,
                sub2api_openai_exchange_code,
                sub2api_find_openai_oauth_account,
            )

            group_ids: list[int] = []
            for x in (s2a.get("group_ids") or []):
                try:
                    group_ids.append(int(x))
                except Exception:
                    continue

            if not group_ids:
                group_names = s2a.get("group_names") or []
                if isinstance(group_names, list) and group_names:
                    try:
                        from .services.sub2api_sink_service import sub2api_resolve_group_ids

                        group_ids = sub2api_resolve_group_ids(
                            api_base=sub2api_api_base,
                            admin_key=sub2api_admin_api_key,
                            admin_token=sub2api_admin_jwt,
                            group_names=[str(x or "").strip() for x in group_names if str(x or "").strip()],
                            timeout=int((settings.get("request") or {}).get("timeout") or 30),
                        )
                    except Exception:
                        group_ids = []

            sub2_cfg = Sub2ApiConfig(
                api_base=sub2api_api_base,
                admin_api_key=sub2api_admin_api_key,
                admin_jwt=sub2api_admin_jwt,
                group_ids=group_ids,
                concurrency=max(1, int(concurrency)),
                priority=max(1, min(int(priority), 100)),
            )

            timeout = int((settings.get("request") or {}).get("timeout") or 30)

            _set_task_progress(record_id, 2, 3, "推送任务")

            if pool_mode == "crs_sync":
                if not crs_api_base or not crs_admin_token:
                    raise RuntimeError(
                        "CRS settings missing api_base/admin_token (source of OAuth tokens). "
                        "Please configure plugin settings: crs.api_base + crs.admin_token"
                    )
                crs_cfg = CrsConfig(api_base=crs_api_base, admin_token=crs_admin_token)
                _log_line(f"crs_sync start: crs_api_base={crs_api_base}")
                sink_result = sink_openai_oauth_from_crs_to_sub2api(
                    emails=emails,
                    crs_cfg=crs_cfg,
                    sub2_cfg=sub2_cfg,
                    timeout=timeout,
                    dry_run=False,
                )
                if already_pooled:
                    sink_result["skip"] = int(sink_result.get("skip") or 0) + len(already_pooled)
                    details = sink_result.get("details")
                    if isinstance(details, dict):
                        details.update(already_pooled)
                try:
                    _log_line(
                        f"crs_sync done: ok={int((sink_result or {}).get('ok') or 0)} skip={int((sink_result or {}).get('skip') or 0)} fail={int((sink_result or {}).get('fail') or 0)}"
                    )
                except Exception:
                    pass
            elif pool_mode == "s2a_oauth":
                # S2A OAuth 模式：不依赖 CRS，直接通过 Sub2API OpenAI OAuth 接口授权入池
                # Flow: generate-auth-url -> browser authorize -> extract code -> create-from-oauth
                from .services.browser_service import BrowserService

                sink_result = {
                    "ok": 0,
                    "skip": len(already_pooled),
                    "fail": 0,
                    "details": dict(already_pooled),
                }

                _log_line("s2a_oauth start")

                for c in accounts:
                    cemail = str(c.get("email") or "").strip()
                    cid = str(c.get("id") or "").strip()
                    cpwd = str(c.get("account_password") or "").strip()
                    if not cemail or not cid:
                        continue

                    try:
                        existing = sub2api_find_openai_oauth_account(sub2_cfg, cemail, timeout=timeout)
                        if existing:
                            sink_result["skip"] += 1
                            sink_result["details"][cemail] = {"status": "skipped", "reason": "already_exists"}
                            _log_line(f"[{cemail}] skipped: already_exists")
                            continue
                    except Exception:
                        pass

                    if not cpwd:
                        sink_result["fail"] += 1
                        sink_result["details"][cemail] = {"status": "failed", "reason": "missing account_password"}
                        _log_line(f"[{cemail}] failed: missing account_password")
                        continue

                    try:
                        safe_email = re.sub(r"[^a-zA-Z0-9]+", "_", cemail).strip("_") or "user"
                        _log_line(f"[{cemail}] oauth start")
                        max_attempts = 2
                        code = ""
                        session_id = ""
                        for attempt in range(1, max_attempts + 1):
                            try:
                                _log_line(f"[{cemail}] oauth attempt {attempt}/{max_attempts} start")

                                auth = sub2api_openai_generate_auth_url(sub2_cfg, email=cemail, timeout=timeout)
                                auth_url = str(auth.get("auth_url") or "").strip()
                                session_id = str(auth.get("session_id") or "").strip()
                                if not auth_url or not session_id:
                                    raise RuntimeError("generate-auth-url returned empty auth_url/session_id")

                                try:
                                    sid_tail = session_id[-8:] if len(session_id) >= 8 else session_id
                                    _log_line(f"[{cemail}] generated auth_url session_id=...{sid_tail}")
                                except Exception:
                                    pass

                                # browser authorize to get code
                                with BrowserService(profile_name=f"gpt_{cemail}") as browser:
                                    page = browser.page
                                    if page is None:
                                        raise RuntimeError("Browser page is not available")
                                    assert page is not None

                                    # NOTE: This is for Codex/OpenAI OAuth authorization.
                                    # Do NOT rely on chatgpt.com session/cookies; open the auth_url and complete
                                    # the auth.openai.com login/consent flow directly.
                                    page.get(auth_url)
                                    time.sleep(2)

                                    try:
                                        _log_line(f"[{cemail}] opened url={_sanitize_url(browser.current_url())}")
                                    except Exception:
                                        pass

                                    from .services.openai_register import (
                                        human_delay,
                                        type_slowly,
                                        wait_for_element,
                                        wait_for_url_change,
                                    )

                                    email_selector = (
                                        'css:input[type="email"], input[name="email"], input[id="email"], '
                                        'input[name="username"], input[id="username"], '
                                        'input[autocomplete="username"], input[autocomplete="email"], input[inputmode="email"]'
                                    )
                                    password_selector = (
                                        'css:input[type="password"], input[name="password"], input[id="password"], '
                                        'input[autocomplete="current-password"], input[autocomplete="new-password"]'
                                    )

                                    def _click_submit_if_any(timeout_sec: int) -> bool:
                                        btn = wait_for_element(page, 'css:button[type="submit"]', timeout=timeout_sec)
                                        if not btn:
                                            return False
                                        old_url = str(browser.current_url() or "")
                                        try:
                                            btn.click()
                                        except Exception:
                                            return False
                                        wait_for_url_change(page, old_url, timeout=20)
                                        human_delay(0.8, 1.6)
                                        return True

                                    # 1) If auth_url redirects to login, fill email/password.
                                    for _ in range(30):
                                        u = str(browser.current_url() or "")
                                        if "code=" in u:
                                            break

                                        email_input = wait_for_element(page, email_selector, timeout=1)
                                        if email_input:
                                            human_delay()
                                            type_slowly(page, email_input, cemail)
                                            _log_line(f"[{cemail}] filled email")
                                            human_delay(0.4, 0.9)
                                            _click_submit_if_any(2)
                                            time.sleep(1)
                                            continue

                                        password_input = wait_for_element(page, password_selector, timeout=1)
                                        if password_input:
                                            human_delay()
                                            type_slowly(page, password_input, str(cpwd))
                                            _log_line(f"[{cemail}] filled password")
                                            human_delay(0.4, 0.9)
                                            _click_submit_if_any(2)
                                            time.sleep(1)
                                            continue

                                        break

                                    # 2) Click consent/authorize (avoid clicking submit when login inputs exist).
                                    for _ in range(30):
                                        u = str(browser.current_url() or "")
                                        if "code=" in u:
                                            break

                                        email_input = wait_for_element(page, email_selector, timeout=1)
                                        if email_input:
                                            human_delay()
                                            type_slowly(page, email_input, cemail)
                                            _log_line(f"[{cemail}] filled email")
                                            human_delay(0.4, 0.9)
                                            _click_submit_if_any(2)
                                            time.sleep(1)
                                            continue

                                        password_input = wait_for_element(page, password_selector, timeout=1)
                                        if password_input:
                                            human_delay()
                                            type_slowly(page, password_input, str(cpwd))
                                            _log_line(f"[{cemail}] filled password")
                                            human_delay(0.4, 0.9)
                                            _click_submit_if_any(2)
                                            time.sleep(1)
                                            continue

                                        btn = None
                                        btn_label = ""
                                        for sel in [
                                            "text:Authorize",
                                            "text:Allow",
                                            "text:Approve",
                                            "text:同意",
                                            "text:授权",
                                            "text:继续",
                                            "text:Continue",
                                        ]:
                                            btn = wait_for_element(page, sel, timeout=1)
                                            if btn:
                                                btn_label = sel
                                                break

                                        if btn:
                                            try:
                                                btn.click()
                                            except Exception:
                                                pass
                                            if btn_label:
                                                _log_line(f"[{cemail}] clicked consent {btn_label}")
                                            human_delay(0.8, 1.6)
                                            time.sleep(1)
                                            continue

                                        # Some consent pages only have a submit button.
                                        # Never click submit on login/identifier pages unless we filled inputs.
                                        if any(
                                            x in u
                                            for x in [
                                                "auth.openai.com/log-in",
                                                "auth.openai.com/log-in-or-create-account",
                                                "auth0.openai.com/u/login",
                                                "/u/login/",
                                                "/login/identifier",
                                                "/login/password",
                                            ]
                                        ):
                                            time.sleep(0.5)
                                            continue

                                        if _click_submit_if_any(1):
                                            _log_line(f"[{cemail}] clicked submit")
                                            time.sleep(1)
                                            continue

                                        time.sleep(0.5)

                                    # wait redirect to callback with code
                                    code = ""
                                    for _ in range(120):
                                        u = str(browser.current_url() or "")
                                        if "code=" in u:
                                            m = re.search(r"[?&]code=([^&]+)", u)
                                            if m:
                                                code = unquote(m.group(1))
                                                _log_line(f"[{cemail}] oauth callback reached")
                                                break
                                        time.sleep(0.5)

                                    if not code:
                                        try:
                                            shot_path = (
                                                artifacts.job_dir
                                                / f"oauth_{safe_email}_{attempt}_{int(time.time())}.png"
                                            )
                                            browser.screenshot(str(shot_path))
                                            _log_line(
                                                f"[{cemail}] oauth callback code not found url={_sanitize_url(browser.current_url())} screenshot={shot_path.name}"
                                            )
                                        except Exception:
                                            pass

                            except Exception as attempt_e:
                                _log_line(f"[{cemail}] oauth attempt {attempt} failed: {attempt_e}")
                                _log_line(traceback.format_exc())
                                if attempt < max_attempts:
                                    time.sleep(2)
                                    continue
                                raise

                            if code:
                                break

                        if not code or not session_id:
                            raise RuntimeError("oauth callback code not found")

                        created = sub2api_openai_create_from_oauth(
                            sub2_cfg,
                            session_id=session_id,
                            code=code,
                            name=cemail,
                            concurrency=max(1, int(concurrency)),
                            priority=max(1, min(int(priority), 999)),
                            group_ids=[int(x) for x in group_ids],
                            timeout=timeout,
                        )

                        if not created:
                            # Fallback for older Sub2API versions:
                            # exchange-code -> create /admin/accounts
                            token_info_raw = sub2api_openai_exchange_code(
                                sub2_cfg,
                                session_id=session_id,
                                code=code,
                                timeout=timeout,
                            )
                            token_info = token_info_raw
                            if isinstance(token_info_raw, dict):
                                if isinstance(token_info_raw.get("tokenInfo"), dict):
                                    token_info = token_info_raw.get("tokenInfo")
                                elif isinstance(token_info_raw.get("token_info"), dict):
                                    token_info = token_info_raw.get("token_info")

                            access_token = ""
                            refresh_token = ""
                            expires_in: int | None = None
                            try:
                                if isinstance(token_info, dict):
                                    access_token = str(
                                        token_info.get("access_token")
                                        or token_info.get("accessToken")
                                        or token_info.get("access")
                                        or ""
                                    ).strip()
                                    refresh_token = str(
                                        token_info.get("refresh_token")
                                        or token_info.get("refreshToken")
                                        or token_info.get("refresh")
                                        or ""
                                    ).strip()

                                    expires_in_val = token_info.get("expires_in") or token_info.get("expiresIn")
                                    expires_at_val = token_info.get("expires_at") or token_info.get("expiresAt")

                                    if isinstance(expires_in_val, int):
                                        expires_in = expires_in_val
                                    elif isinstance(expires_in_val, str) and expires_in_val.strip():
                                        try:
                                            expires_in = int(expires_in_val)
                                        except Exception:
                                            expires_in = None
                                    elif expires_at_val is not None:
                                        try:
                                            expires_at_i = int(expires_at_val)
                                            now_i = int(time.time())
                                            if expires_at_i > now_i:
                                                expires_in = expires_at_i - now_i
                                        except Exception:
                                            expires_in = None
                            except Exception:
                                access_token = ""
                                refresh_token = ""
                                expires_in = None

                            created2, msg2 = sub2api_create_openai_oauth_account(
                                sub2_cfg,
                                email=cemail,
                                access_token=access_token,
                                refresh_token=refresh_token,
                                expires_in=expires_in,
                                timeout=timeout,
                                dry_run=False,
                            )
                            created = bool(created2)
                            if not created and msg2:
                                raise RuntimeError(f"exchange-code/create-account failed: {msg2}")

                        if created:
                            sink_result["ok"] += 1
                            sink_result["details"][cemail] = {"status": "ok"}
                            _log_line(f"[{cemail}] ok")
                        else:
                            sink_result["fail"] += 1
                            sink_result["details"][cemail] = {"status": "failed", "reason": "oauth create failed"}
                            _log_line(f"[{cemail}] failed: oauth create failed")
                    except Exception as e:
                        sink_result["fail"] += 1
                        sink_result["details"][cemail] = {"status": "failed", "reason": str(e)}
                        _log_line(f"[{cemail}] failed: {e}")
                        _log_line(traceback.format_exc())
            else:
                raise RuntimeError(f"unknown pool_mode: {pool_mode}")

        return_code = 0 if int(sink_result.get("fail") or 0) == 0 else 1

        try:
            ok_n = int(sink_result.get("ok") or 0) if isinstance(sink_result, dict) else 0
            skip_n = int(sink_result.get("skip") or 0) if isinstance(sink_result, dict) else 0
            fail_n = int(sink_result.get("fail") or 0) if isinstance(sink_result, dict) else 0
            _log_line(f"sub2api_sink result: ok={ok_n} skip={skip_n} fail={fail_n} return_code={return_code}")

            details_all = sink_result.get("details") if isinstance(sink_result, dict) else None
            details_lc_all: dict[str, Any] = {}
            if isinstance(details_all, dict):
                for k, v in details_all.items():
                    if isinstance(k, str):
                        details_lc_all[k.strip().lower()] = v

            for account in accounts_all:
                aid = str(account.get("id") or "").strip()
                aemail = str(account.get("email") or "").strip()
                role = "mother" if aid == mother_id else "child"
                if not aemail:
                    _log_line(
                        f"sub2api_sink account_result role={role} id={aid or '-'} email=- status=skipped reason=missing_email"
                    )
                    continue
                item = (
                    details_all.get(aemail)
                    if isinstance(details_all, dict)
                    else None
                ) or details_lc_all.get(aemail.lower())
                status = str(item.get("status") or "") if isinstance(item, dict) else ""
                reason = str(item.get("reason") or "") if isinstance(item, dict) else ""
                _log_line(
                    f"sub2api_sink account_result role={role} id={aid or '-'} email={aemail} status={status or 'unknown'} reason={reason or '-'}"
                )
        except Exception:
            pass

        try:
            (artifacts.job_dir / "sub2api_sink_result.json").write_text(
                json.dumps(sink_result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except Exception:
            pass

        now = timezone.now().isoformat()
        patch_account(
            mother_id,
            {
                "pool_status": "success" if return_code == 0 else "failed",
                "pool_last_task": record_id,
                "pool_updated_at": now,
            },
        )
        _log_line(
            f"sub2api_sink writeback role=mother id={mother_id} email={trace_email or '-'} pool_status={'success' if return_code == 0 else 'failed'} source=task_return_code"
        )

        # 子号状态：按邮箱写回入池结果
        details = sink_result.get("details") if isinstance(sink_result, dict) else None
        if isinstance(details, dict):
            details_lc: dict[str, Any] = {}
            for k, v in details.items():
                if isinstance(k, str):
                    details_lc[k.strip().lower()] = v
            for c in accounts:
                cid = str(c.get("id") or "").strip()
                cemail = str(c.get("email") or "").strip()
                if not cid or not cemail:
                    continue

                item = details.get(cemail) or details_lc.get(cemail.lower())
                status = str(item.get("status") or "") if isinstance(item, dict) else ""
                # ok/skipped 都认为“已入池”（skipped=已经存在）
                if status in {"ok", "skipped"}:
                    pool_status = "success"
                elif status == "failed":
                    pool_status = "failed"
                else:
                    pool_status = "failed" if return_code != 0 else "success"

                try:
                    patch_account(
                        cid,
                        {
                            "pool_status": pool_status,
                            "pool_last_task": record_id,
                            "pool_updated_at": now,
                        },
                    )
                    role = "mother" if cid == mother_id else "child"
                    _log_line(
                        f"sub2api_sink writeback role={role} id={cid} email={cemail} pool_status={pool_status} source=detail"
                    )
                except Exception as write_e:
                    _log_line(
                        f"sub2api_sink writeback failed role={'mother' if cid == mother_id else 'child'} id={cid or '-'} email={cemail or '-'} err={write_e}"
                    )

        result: dict[str, Any] = {
            "return_code": return_code,
            "mother_id": mother_id,
            "emails_count": len(emails),
            "s2a_target_key": s2a_target_key,
            "s2a_api_base": sub2api_api_base,
            "pool_mode": pool_mode,
            "artifacts": _artifacts_list_from_job_dir(job_dir),
            "details": sink_result,
        }

        ok_n = int(sink_result.get("ok") or 0) if isinstance(sink_result, dict) else 0
        skip_n = int(sink_result.get("skip") or 0) if isinstance(sink_result, dict) else 0
        fail_n = int(sink_result.get("fail") or 0) if isinstance(sink_result, dict) else 0
        error_msg = f"sub2api_sink failed: ok={ok_n} skip={skip_n} fail={fail_n} (see run.log)"

        _set_task_progress(record_id, 3, 3, "完成处理")
        patch_task(
            record_id,
            {
                "status": "completed" if return_code == 0 else "failed",
                "finished_at": timezone.now().isoformat(),
                "result": result,
                **({} if return_code == 0 else {"error": error_msg}),
            },
        )

        return result
    except Exception as exc:
        logger.exception("gpt_business sub2api_sink_task failed")
        _append_trace_line(
            celery_task_id,
            trace_email,
            f"sub2api_sink failed: {exc}",
            step="sub2api_sink",
            action="error",
            level="error",
        )

        try:
            media_root = Path(str(getattr(django_settings, "MEDIA_ROOT", "")))
            if str(media_root):
                job_dir = media_root / "gpt_business" / "jobs" / record_id
                artifacts = prepare_artifacts(job_dir)
                artifacts.log_file.parent.mkdir(parents=True, exist_ok=True)
                artifacts.log_file.touch(exist_ok=True)
                ts = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                with artifacts.log_file.open("a", encoding="utf-8") as fp:
                    fp.write(f"[{ts}] task failed: {str(exc)}\n")
                    fp.write(traceback.format_exc() + "\n")
        except Exception:
            pass

        _set_task_progress(record_id, 3, 3, "失败")
        patch_task(
            record_id,
            {
                "status": "failed",
                "finished_at": timezone.now().isoformat(),
                "error": str(exc),
            },
        )


@shared_task(name="gpt_business.cleanup_trace")
def cleanup_trace_task():
    settings = get_settings()
    try:
        result = cleanup_trace_files(settings, dry_run=False)
        logger.info(
            "gpt_business trace cleanup finished: deleted=%s freed=%s",
            result.get("deleted_files"),
            result.get("freed_bytes"),
        )
        return {"success": True, **result}
    except Exception as exc:
        logger.exception("gpt_business cleanup_trace_task failed")
        return {"success": False, "error": str(exc)}
        raise


@shared_task(name="gpt_business.team_push", bind=True)
def team_push_task(
    self: Task,
    record_id: str,
    mother_id: str,
    target_url: str,
    admin_password: str,
    is_warranty: bool = True,
    seat_total: int = 5,
    note: str = "",
):
    """
    推送母号 session 到外部兑换系统。

    流程：
    1. 启动浏览器获取 ChatGPT session
    2. 调用外部 API 推送 session
    3. 更新账号状态
    """
    import httpx
    from .services.browser_service import BrowserService
    from .services.chatgpt_session import fetch_auth_session
    from .storage import find_account, patch_account, patch_task

    settings = get_settings()
    result: dict = {"success": False, "record_id": record_id, "mother_id": mother_id}

    # 日志文件
    media_root = Path(str(getattr(django_settings, "MEDIA_ROOT", "")))
    job_dir = media_root / "gpt_business" / "jobs" / record_id
    job_dir.mkdir(parents=True, exist_ok=True)
    log_file = job_dir / "run.log"

    def _log(msg: str):
        ts = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}"
        logger.info("team_push[%s]: %s", record_id[:8], msg)
        try:
            with log_file.open("a", encoding="utf-8") as fp:
                fp.write(line + "\n")
        except Exception:
            pass

    try:
        patch_task(record_id, {"status": "running", "started_at": timezone.now().isoformat()})
        _set_task_progress(record_id, 0, 3, "准备中...")
        _log("任务开始")

        mother = find_account(settings, mother_id)
        if not mother:
            raise ValueError(f"母号不存在: {mother_id}")

        email = mother.get("email", "")

        _log(f"母号: {email}")
        _log(f"座位数: {seat_total}, 备注: {note}")

        if not email:
            raise ValueError("母号邮箱为空")

        _set_task_progress(record_id, 1, 3, "获取 session...")
        _log("启动浏览器获取 session")

        session_data = None
        profile_name = f"gpt_{email}"

        with BrowserService(profile_name=profile_name) as browser:
            page = browser.page
            if page is None:
                raise RuntimeError("Browser page is not available")

            _log("浏览器已启动，导航到 ChatGPT")

            # 导航到 ChatGPT 获取 session
            page.get("https://chatgpt.com/")
            time.sleep(3)

            _log(f"当前 URL: {browser.current_url()}")

            # 获取 session
            session_data = fetch_auth_session(page)

            if not session_data:
                _log("获取 session 失败")
                raise RuntimeError("无法获取 session")

            if not session_data.get("accessToken"):
                _log("accessToken 为空，账号可能未登录")
                raise RuntimeError("无法获取 accessToken，账号可能未登录")

            _log(f"成功获取 session, user: {session_data.get('user', {}).get('email', 'unknown')}")

        if not session_data:
            raise RuntimeError("获取 session 失败")

        _set_task_progress(record_id, 2, 3, "推送到兑换系统...")
        _log(f"推送到: {target_url}")

        # 构造推送请求
        push_payload = {
            "password": admin_password,
            "session": session_data,
            "isWarranty": is_warranty,
            "seatTotal": seat_total,
            "note": note,
        }

        # 发送推送请求
        push_url = target_url.rstrip("/") + "/api/admin/mothers/push"
        _log(f"POST {push_url}")

        with httpx.Client(timeout=60) as client:
            resp = client.post(push_url, json=push_payload)
            _log(f"响应状态: {resp.status_code}")
            resp.raise_for_status()
            push_result = resp.json()

        if not push_result.get("ok"):
            error_msg = push_result.get("error", "unknown")
            _log(f"推送失败: {error_msg}")
            raise RuntimeError(f"推送失败: {error_msg}")

        _log(f"推送成功: action={push_result.get('action')}")
        _set_task_progress(record_id, 3, 3, "完成")

        # 更新账号状态
        patch_account(
            mother_id,
            {
                "team_push_status": "success",
                "team_push_updated_at": timezone.now().isoformat(),
                "team_push_url": target_url,
                "team_account_id": push_result.get("mother", {}).get("id"),
            },
        )

        patch_task(
            record_id,
            {
                "status": "success",
                "finished_at": timezone.now().isoformat(),
            },
        )

        _log("任务完成")
        result["success"] = True
        result["push_result"] = push_result
        return result

    except Exception as exc:
        logger.exception("team_push_task failed: %s", exc)
        _log(f"任务失败: {exc}")

        _set_task_progress(record_id, 3, 3, "失败")
        patch_task(
            record_id,
            {
                "status": "failed",
                "finished_at": timezone.now().isoformat(),
                "error": str(exc),
            },
        )

        # 更新账号状态为失败
        try:
            patch_account(
                mother_id,
                {
                    "team_push_status": "failed",
                    "team_push_updated_at": timezone.now().isoformat(),
                },
            )
        except Exception:
            pass

        result["error"] = str(exc)
        return result

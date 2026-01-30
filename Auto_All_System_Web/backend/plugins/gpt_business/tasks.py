from __future__ import annotations

import logging
import random
import csv
import json
import re
import asyncio
import sys
from pathlib import Path
from typing import Any

import requests
from celery import shared_task
from django.conf import settings as django_settings
from django.utils import timezone

from .legacy_runner import (
    DEFAULT_REPO_PATH,
    build_config_toml,
    build_team_json,
    prepare_artifacts,
    run_legacy,
    run_repo_script,
)
from .storage import find_account, get_settings, list_accounts, patch_account, patch_task


logger = logging.getLogger(__name__)


def _get_available_card_for_checkout() -> dict[str, Any] | None:
    """从虚拟卡管理获取一张可用卡用于绑卡"""
    from apps.cards.models import Card
    
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

        media_root = Path(str(getattr(django_settings, "MEDIA_ROOT", "")))
        if not str(media_root):
            raise RuntimeError("MEDIA_ROOT is not configured")

        job_dir = media_root / "gpt_business" / "jobs" / record_id
        artifacts = prepare_artifacts(job_dir)

        config_toml = build_config_toml(plugin_settings=settings, task_record=task_record, artifacts=artifacts)
        team_json = build_team_json(plugin_settings=settings, task_record=task_record)

        repo_src = str(settings.get("legacy_repo_path") or DEFAULT_REPO_PATH)
        args = task_record.get("legacy_args")
        return_code = run_legacy(
            repo_src,
            artifacts,
            config_toml=config_toml,
            team_json=team_json,
            args=list(args) if isinstance(args, list) and args else None,
        )

        artifacts_list: list[dict[str, Any]] = []
        for p in [artifacts.csv_file, artifacts.tracker_file, artifacts.log_file, artifacts.team_json_file, artifacts.domain_blacklist_file]:
            if p.exists():
                artifacts_list.append(
                    {
                        "name": p.name,
                        "path": str(p),
                    }
                )

        accounts_count = 0
        if artifacts.csv_file.exists():
            try:
                with artifacts.csv_file.open("r", encoding="utf-8", newline="") as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    accounts_count = max(len(rows) - 1, 0)
            except Exception:
                accounts_count = 0

        result: dict[str, Any] = {
            "return_code": return_code,
            "artifacts": artifacts_list,
            "accounts_count": accounts_count,
        }

        if return_code != 0:
            patch_task(
                record_id,
                {
                    "status": "failed",
                    "finished_at": timezone.now().isoformat(),
                    "result": result,
                    "error": f"legacy runner exited with code {return_code}",
                },
            )
            return result

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
        logger.exception("gpt_business legacy_run_task failed")
        patch_task(
            record_id,
            {
                "status": "failed",
                "finished_at": timezone.now().isoformat(),
                "error": str(exc),
            },
        )
        raise


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

        media_root = Path(str(getattr(django_settings, "MEDIA_ROOT", "")))
        if not str(media_root):
            raise RuntimeError("MEDIA_ROOT is not configured")

        job_dir = media_root / "gpt_business" / "jobs" / record_id
        artifacts = prepare_artifacts(job_dir)

        def _log(line: str) -> None:
            ts = timezone.now().isoformat()
            artifacts.log_file.parent.mkdir(parents=True, exist_ok=True)
            with artifacts.log_file.open("a", encoding="utf-8") as fp:
                fp.write(f"[{ts}] {line}\n")

        _log(f"self_register start mother_id={mother_id} email={email}")

        card_info = _get_available_card_for_checkout()
        if not card_info:
            _log("no available card: will still try register, skip checkout")

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
        profile_name = f"gpt_{email}"

        from apps.integrations.geekez.api import GeekezBrowserAPI
        from plugins.gpt_business.services.openai_register import (
            connect_to_browser,
            register_openai_account,
        )

        def _run_sync() -> dict[str, Any]:
            """同步执行注册流程（使用 DrissionPage）"""
            api = GeekezBrowserAPI()
            
            # 创建或获取 profile
            _log(f"creating/updating profile: {profile_name}")
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
                
                print(f"[DEBUG] register_ok={register_ok}, starting card check...", flush=True)
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
                        
                        print("[DEBUG] calling run_onboarding_flow with card callback...", flush=True)
                        success, session_data = run_onboarding_flow(
                            page=page,
                            email=email,
                            skip_checkout=False,
                            get_card_callback=_get_available_card_for_checkout,
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
            },
        )

        if used_card_id:
            pass  # 卡已在 _run_sync 中标记为使用中

        result: dict[str, Any] = {
            "success": success,
            "mother_id": mother_id,
            "email": email,
            "artifacts": _artifacts_list_from_job_dir(job_dir),
            "details": flow_result,
        }

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
        try:
            if mother_id:
                patch_account(
                    mother_id,
                    {
                        "open_status": "failed",
                        "open_last_task": record_id,
                        "open_updated_at": timezone.now().isoformat(),
                    },
                )
        except Exception:
            pass

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


@shared_task(bind=True)
def auto_invite_task(self, record_id: str):
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

        children = [
            a
            for a in list_accounts(settings)
            if isinstance(a, dict) and str(a.get("type")) == "child" and str(a.get("parent_id")) == mother_id
        ]
        child_emails = [str(a.get("email") or "").strip() for a in children]
        child_emails = [e for e in child_emails if e]
        if not child_emails:
            raise RuntimeError("No child accounts")

        media_root = Path(str(getattr(django_settings, "MEDIA_ROOT", "")))
        if not str(media_root):
            raise RuntimeError("MEDIA_ROOT is not configured")

        job_dir = media_root / "gpt_business" / "jobs" / record_id
        artifacts = prepare_artifacts(job_dir)

        email_cfg = _cloudmail_email_config_from_account(mother)
        config_toml = build_config_toml(
            plugin_settings=settings,
            task_record=task_record,
            artifacts=artifacts,
            email_provider="cloudmail",
            email_config=email_cfg,
        )

        script = """
import json
import sys
from pathlib import Path

from browser_automation import init_browser, login_and_get_session
from team_service import batch_invite_to_team


def main() -> int:
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('web_input.json')
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('web_result.json')

    payload = json.loads(input_path.read_text(encoding='utf-8')) if input_path.exists() else {}
    mother = payload.get('mother') if isinstance(payload, dict) else None
    invite_emails = payload.get('invite_emails') if isinstance(payload, dict) else None

    if not isinstance(mother, dict):
        mother = {}
    if not isinstance(invite_emails, list):
        invite_emails = []

    email = str(mother.get('email') or '').strip()
    password = str(mother.get('password') or '').strip()

    page = None
    token = ''
    account_id = ''
    invite_result = {}
    err = ''
    try:
        page = init_browser()
        session = login_and_get_session(page, email, password)
        token = str(session.get('token') or '').strip() if isinstance(session, dict) else ''
        account_id = str(session.get('account_id') or '').strip() if isinstance(session, dict) else ''

        if token and account_id and invite_emails:
            team = {'auth_token': token, 'account_id': account_id}
            invite_result = batch_invite_to_team(invite_emails, team)
    except Exception as e:
        err = str(e)
    finally:
        try:
            if page:
                page.quit()
        except Exception:
            pass

    output = {
        'token': token,
        'account_id': account_id,
        'invite_result': invite_result,
        'error': err,
    }
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    if err:
        return 1
    if not token or not account_id:
        return 2
    # invite_result: { email: {success: bool, error: str} }
    if invite_result and any(isinstance(v, dict) and v.get('success') is False for v in invite_result.values()):
        return 3
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
""".lstrip()

        input_payload = {
            "mother": {"email": email, "password": password},
            "invite_emails": child_emails,
        }

        extra_files = {
            "tools/web_auto_invite.py": script,
            "web_input.json": json.dumps(input_payload, ensure_ascii=False, indent=2) + "\n",
        }

        repo_src = str(settings.get("legacy_repo_path") or DEFAULT_REPO_PATH)
        return_code = run_repo_script(
            repo_src,
            artifacts,
            config_toml=config_toml,
            cmd=[sys.executable, "tools/web_auto_invite.py", "web_input.json", "web_result.json"],
            extra_files=extra_files,
        )

        result_path = artifacts.repo_dir / "web_result.json"
        parsed_result: dict[str, Any] = {}
        if result_path.exists():
            try:
                parsed_result = json.loads(result_path.read_text(encoding="utf-8"))
            except Exception:
                parsed_result = {}

        token = str(parsed_result.get("token") or "").strip()
        account_id = str(parsed_result.get("account_id") or "").strip()

        now = timezone.now().isoformat()
        patch: dict[str, Any] = {
            "invite_status": "success" if return_code == 0 else "failed",
            "invite_last_task": record_id,
            "invite_updated_at": now,
        }
        if token:
            patch["auth_token"] = token
        if account_id:
            patch["account_id"] = account_id
        patch_account(mother_id, patch)

        result: dict[str, Any] = {
            "return_code": return_code,
            "mother_id": mother_id,
            "email": email,
            "invited_count": len(child_emails),
            "artifacts": _artifacts_list_from_job_dir(job_dir),
            "details": parsed_result,
        }

        patch_task(
            record_id,
            {
                "status": "completed" if return_code == 0 else "failed",
                "finished_at": timezone.now().isoformat(),
                "result": result,
                **({} if return_code == 0 else {"error": f"auto_invite exited with code {return_code}"}),
            },
        )

        return result
    except Exception as exc:
        logger.exception("gpt_business auto_invite_task failed")
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

        children = [
            a
            for a in list_accounts(settings)
            if isinstance(a, dict) and str(a.get("type")) == "child" and str(a.get("parent_id")) == mother_id
        ]
        emails = [str(a.get("email") or "").strip() for a in children]
        emails = [e for e in emails if e]
        if not emails:
            raise RuntimeError("No child accounts")

        crs = settings.get("crs") or {}
        s2a = settings.get("s2a") or {}

        crs_api_base = str(crs.get("api_base") or "").strip()
        crs_admin_token = str(crs.get("admin_token") or "").strip()
        if not crs_api_base or not crs_admin_token:
            raise RuntimeError("CRS settings missing api_base/admin_token")

        sub2api_api_base = str(s2a.get("api_base") or "").strip()
        sub2api_admin_api_key = str(s2a.get("admin_key") or "").strip()
        sub2api_admin_jwt = str(s2a.get("admin_token") or "").strip()
        if not sub2api_api_base:
            raise RuntimeError("S2A settings missing api_base")
        if not sub2api_admin_api_key and not sub2api_admin_jwt:
            raise RuntimeError("S2A settings missing admin_key/admin_token")

        group_ids = s2a.get("group_ids") or []
        group_ids_str = ",".join([str(int(x)) for x in group_ids if str(x).strip().isdigit()])

        concurrency = int(s2a.get("concurrency") or 3)
        priority = int(s2a.get("priority") or 50)

        media_root = Path(str(getattr(django_settings, "MEDIA_ROOT", "")))
        if not str(media_root):
            raise RuntimeError("MEDIA_ROOT is not configured")

        job_dir = media_root / "gpt_business" / "jobs" / record_id
        artifacts = prepare_artifacts(job_dir)

        # 生成一个 accounts.csv（只要 email+status=success 即可被 sub2api_sink_run 读取）
        with artifacts.csv_file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["email", "status"])
            writer.writeheader()
            for e in emails:
                writer.writerow({"email": e, "status": "success"})

        repo_src = str(settings.get("legacy_repo_path") or DEFAULT_REPO_PATH)

        # sub2api_sink_run 只吃 CLI 参数，这里不依赖 config.toml，但为了日志与一致性仍写入一个最小 config
        email_cfg = _cloudmail_email_config_from_account(mother)
        config_toml = build_config_toml(
            plugin_settings=settings,
            task_record=task_record,
            artifacts=artifacts,
            email_provider="cloudmail",
            email_config=email_cfg,
        )

        cmd = [
            sys.executable,
            "tools/sub2api_sink_run.py",
            "--crs-api-base",
            crs_api_base,
            "--crs-admin-token",
            crs_admin_token,
            "--sub2api-api-base",
            sub2api_api_base,
        ]

        if sub2api_admin_api_key:
            cmd.extend(["--sub2api-admin-api-key", sub2api_admin_api_key])
        else:
            cmd.extend(["--sub2api-admin-jwt", sub2api_admin_jwt])

        if group_ids_str:
            cmd.extend(["--group-ids", group_ids_str])

        cmd.extend(["--concurrency", str(concurrency), "--priority", str(priority)])
        cmd.extend(["--input-csv", str(artifacts.csv_file)])

        return_code = run_repo_script(
            repo_src,
            artifacts,
            config_toml=config_toml,
            cmd=cmd,
        )

        now = timezone.now().isoformat()
        patch_account(
            mother_id,
            {
                "pool_status": "success" if return_code == 0 else "failed",
                "pool_last_task": record_id,
                "pool_updated_at": now,
            },
        )

        result: dict[str, Any] = {
            "return_code": return_code,
            "mother_id": mother_id,
            "emails_count": len(emails),
            "artifacts": _artifacts_list_from_job_dir(job_dir),
        }

        patch_task(
            record_id,
            {
                "status": "completed" if return_code == 0 else "failed",
                "finished_at": timezone.now().isoformat(),
                "result": result,
                **({} if return_code == 0 else {"error": f"sub2api_sink exited with code {return_code}"}),
            },
        )

        return result
    except Exception as exc:
        logger.exception("gpt_business sub2api_sink_task failed")
        patch_task(
            record_id,
            {
                "status": "failed",
                "finished_at": timezone.now().isoformat(),
                "error": str(exc),
            },
        )
        raise

from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from typing import Any

import requests


logger = logging.getLogger(__name__)


def _now_unix() -> int:
    return int(time.time())


def _normalize_base_url(raw: str) -> str:
    return (raw or "").strip().rstrip("/")


def _unwrap_data(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload.get("data")
    return payload


@dataclass(frozen=True)
class CrsConfig:
    api_base: str
    admin_token: str


@dataclass(frozen=True)
class Sub2ApiConfig:
    api_base: str
    admin_api_key: str
    admin_jwt: str
    group_ids: list[int]
    concurrency: int
    priority: int


def _build_crs_headers(cfg: CrsConfig) -> dict[str, str]:
    api_base = _normalize_base_url(cfg.api_base)
    return {
        "accept": "*/*",
        "authorization": f"Bearer {cfg.admin_token}",
        "content-type": "application/json",
        "origin": api_base,
        "referer": f"{api_base}/admin-next/accounts",
    }


def _build_sub2api_headers(cfg: Sub2ApiConfig) -> dict[str, str]:
    api_base = _normalize_base_url(cfg.api_base)
    headers: dict[str, str] = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": api_base,
        "referer": api_base + "/",
    }

    if cfg.admin_api_key:
        headers["x-api-key"] = cfg.admin_api_key
    elif cfg.admin_jwt:
        headers["authorization"] = f"Bearer {cfg.admin_jwt}"

    return headers


def crs_list_openai_accounts(cfg: CrsConfig, *, timeout: int = 30) -> list[dict[str, Any]]:
    url = _normalize_base_url(cfg.api_base) + "/admin/openai-accounts"

    try:
        resp = requests.get(url, headers=_build_crs_headers(cfg), timeout=timeout)
        if resp.status_code != 200:
            logger.error(f"CRS list failed: HTTP {resp.status_code}")
            return []

        payload = resp.json()
        if isinstance(payload, dict) and payload.get("success") is False:
            logger.error(f"CRS success=false: {payload.get('message') or payload.get('error') or ''}")
            return []

        data = _unwrap_data(payload)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]

        return []

    except Exception as e:
        logger.exception(f"CRS list exception: {e}")
        return []


def crs_find_account_by_email(accounts: list[dict[str, Any]], email: str) -> dict[str, Any] | None:
    email_l = (email or "").strip().lower()
    if not email_l:
        return None

    for acc in accounts:
        name = str(acc.get("name") or "").strip().lower()
        if name == email_l:
            return acc

    return None


def sub2api_find_openai_oauth_account(cfg: Sub2ApiConfig, email: str, *, timeout: int = 30) -> dict[str, Any] | None:
    url = _normalize_base_url(cfg.api_base) + "/api/v1/admin/accounts"
    params = {
        "platform": "openai",
        "type": "oauth",
        "search": (email or "").strip(),
        "page": 1,
        "page_size": 20,
    }

    try:
        resp = requests.get(url, headers=_build_sub2api_headers(cfg), params=params, timeout=timeout)
        if resp.status_code != 200:
            return None

        payload = resp.json()
        data = payload.get("data") if isinstance(payload, dict) else None

        items: list[dict[str, Any]] = []
        if isinstance(data, list):
            items = [x for x in data if isinstance(x, dict)]
        elif isinstance(data, dict):
            inner = data.get("data")
            if isinstance(inner, list):
                items = [x for x in inner if isinstance(x, dict)]

        email_l = (email or "").strip().lower()
        for item in items:
            name = str(item.get("name") or "").strip().lower()
            if name == email_l:
                return item

        return None

    except Exception:
        return None


def sub2api_create_openai_oauth_account(
    cfg: Sub2ApiConfig,
    *,
    email: str,
    access_token: str,
    refresh_token: str,
    expires_in: int | None,
    timeout: int = 30,
    dry_run: bool = False,
) -> tuple[bool, str]:
    if not access_token:
        return False, "missing access_token"

    expires_at = None
    if isinstance(expires_in, int) and expires_in > 0:
        expires_at = _now_unix() + expires_in

    payload: dict[str, Any] = {
        "name": email,
        "platform": "openai",
        "type": "oauth",
        "credentials": {
            "access_token": access_token,
            "refresh_token": refresh_token or "",
            "token_type": "Bearer",
        },
        "concurrency": int(cfg.concurrency),
        "priority": int(cfg.priority),
        "group_ids": cfg.group_ids,
    }
    if expires_at is not None:
        payload["credentials"]["expires_at"] = str(expires_at)

    if dry_run:
        return True, "dry_run"

    url = _normalize_base_url(cfg.api_base) + "/api/v1/admin/accounts"
    try:
        resp = requests.post(url, headers=_build_sub2api_headers(cfg), json=payload, timeout=timeout)
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"

        body = resp.json()
        if isinstance(body, dict) and body.get("success") is False:
            return False, str(body.get("message") or body.get("error") or "success=false")

        return True, "created"
    except Exception as e:
        return False, str(e)


def sink_openai_oauth_from_crs_to_sub2api(
    *,
    emails: list[str],
    crs_cfg: CrsConfig,
    sub2_cfg: Sub2ApiConfig,
    timeout: int = 30,
    dry_run: bool = False,
) -> dict[str, Any]:
    emails = [str(e or "").strip() for e in emails]
    emails = [e for e in emails if e]

    accounts = crs_list_openai_accounts(crs_cfg, timeout=timeout)
    if not accounts:
        raise RuntimeError("CRS accounts list is empty")

    ok = 0
    skip = 0
    fail = 0
    details: dict[str, Any] = {}

    for email in emails:
        existing = sub2api_find_openai_oauth_account(sub2_cfg, email, timeout=timeout)
        if existing:
            skip += 1
            details[email] = {"status": "skipped", "reason": "already_exists"}
            continue

        acc = crs_find_account_by_email(accounts, email)
        if not acc:
            fail += 1
            details[email] = {"status": "failed", "reason": "not_found_in_crs"}
            continue

        oauth = acc.get("openaiOauth")
        if not isinstance(oauth, dict):
            fail += 1
            details[email] = {"status": "failed", "reason": "missing_openaiOauth"}
            continue

        access_token = str(oauth.get("accessToken") or "").strip()
        refresh_token = str(oauth.get("refreshToken") or "").strip()

        expires_in_val = oauth.get("expires_in")
        expires_in: int | None = None
        if isinstance(expires_in_val, int):
            expires_in = expires_in_val
        elif isinstance(expires_in_val, str):
            try:
                expires_in = int(expires_in_val)
            except Exception:
                expires_in = None

        created, msg = sub2api_create_openai_oauth_account(
            sub2_cfg,
            email=email,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            timeout=timeout,
            dry_run=dry_run,
        )

        if created:
            ok += 1
            details[email] = {"status": "ok", "message": msg}
        else:
            fail += 1
            details[email] = {"status": "failed", "reason": msg}

    return {
        "ok": ok,
        "skip": skip,
        "fail": fail,
        "details": details,
    }

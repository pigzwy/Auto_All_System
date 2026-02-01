from __future__ import annotations

import json
import logging
from typing import Any, Callable


logger = logging.getLogger(__name__)


def _normalize_bearer(token: str) -> str:
    token = (token or "").strip()
    if not token:
        return ""
    if token.lower().startswith("bearer "):
        return token
    return f"Bearer {token}"


def browser_fetch_json(
    page,
    *,
    path: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    json_body: Any | None = None,
    timeout_sec: int = 20,
    log_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """在浏览器上下文用 fetch 调用 chatgpt.com 的接口。

    目的：绕过 Celery 容器内对外网的网络限制（requests 无法直连 chatgpt.com）。
    """

    def _log(msg: str):
        try:
            if log_callback:
                log_callback(msg)
        except Exception:
            pass
        logger.info(msg)

    method_u = (method or "GET").upper()
    if not path.startswith("/"):
        raise ValueError("path must start with '/'")

    hdrs = headers or {}
    headers_json = json.dumps(hdrs)
    body_json = "null" if json_body is None else json.dumps(json_body)

    js = f"""
        const url = {json.dumps(path)};
        const method = {json.dumps(method_u)};
        const headers = {headers_json};
        const hasBody = {body_json} !== null;
        const body = hasBody ? JSON.stringify({body_json}) : undefined;
        const controller = new AbortController();
        const t = setTimeout(() => controller.abort(), {int(timeout_sec) * 1000});

        return fetch(url, {{
          method,
          headers,
          body,
          credentials: 'include',
          signal: controller.signal,
        }})
        .then(async (r) => {{
          clearTimeout(t);
          const text = await r.text();
          return JSON.stringify({{ ok: r.ok, status: r.status, text }});
        }})
        .catch((e) => JSON.stringify({{ ok: false, status: 0, text: String(e) }}));
    """.strip()

    raw = page.run_js(js, timeout=timeout_sec + 5)
    if not raw:
        raise RuntimeError("browser_fetch_json empty response")

    outer = json.loads(raw)
    status = int(outer.get("status") or 0)
    text = str(outer.get("text") or "")

    if status == 0 and ("AbortError" in text or "aborted" in text.lower()):
        raise TimeoutError("browser_fetch_json timeout")
    if status and status >= 400:
        _log(f"browser_fetch_json HTTP {status} path={path}")
        raise RuntimeError(f"HTTP {status}: {text[:400]}")

    try:
        data = json.loads(text) if text else {}
    except Exception:
        data = {}

    return data if isinstance(data, dict) else {"data": data}


def browser_fetch_account_id(
    page,
    *,
    auth_token: str,
    timeout_sec: int = 20,
    log_callback: Callable[[str], None] | None = None,
) -> str:
    token = _normalize_bearer(auth_token)
    if not token:
        return ""

    data = browser_fetch_json(
        page,
        path="/backend-api/accounts/check/v4-2023-04-27",
        method="GET",
        headers={
            "accept": "*/*",
            "authorization": token,
            "content-type": "application/json",
        },
        timeout_sec=timeout_sec,
        log_callback=log_callback,
    )

    accounts: dict[str, Any] = data.get("accounts") or {}
    # 优先挑选 plan_type 包含 team 的 account
    for acc_id, acc_info in accounts.items():
        if acc_id == "default":
            continue
        account_data = (acc_info or {}).get("account") or {}
        plan_type = str(account_data.get("plan_type") or "")
        if "team" in plan_type.lower():
            return acc_id

    for acc_id in accounts.keys():
        if acc_id != "default":
            return acc_id

    return ""


def browser_invite_emails(
    page,
    *,
    account_id: str,
    auth_token: str,
    emails: list[str],
    timeout_sec: int = 30,
    log_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    token = _normalize_bearer(auth_token)
    account_id = (account_id or "").strip()
    if not token or not account_id:
        raise ValueError("missing token/account_id")

    payload = {
        "email_addresses": emails,
        "role": "standard-user",
        "resend_emails": True,
    }

    data = browser_fetch_json(
        page,
        path=f"/backend-api/accounts/{account_id}/invites",
        method="POST",
        headers={
            "accept": "*/*",
            "authorization": token,
            "content-type": "application/json",
            "chatgpt-account-id": account_id,
        },
        json_body=payload,
        timeout_sec=timeout_sec,
        log_callback=log_callback,
    )

    success: list[str] = []
    failed: list[dict[str, str]] = []

    for invite in data.get("account_invites") or []:
        if isinstance(invite, dict) and invite.get("email_address"):
            success.append(str(invite.get("email_address")))

    for err in data.get("errored_emails") or []:
        if isinstance(err, dict) and err.get("email"):
            failed.append({"email": str(err.get("email")), "error": str(err.get("error") or "Unknown error")})

    if not success and not failed:
        success = emails

    return {
        "success": success,
        "failed": failed,
        "raw": data,
    }

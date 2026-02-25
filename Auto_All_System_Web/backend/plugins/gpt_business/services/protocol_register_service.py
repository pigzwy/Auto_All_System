from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any, Callable

from . import protocol_keygen as protocol_keygen_module


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    try:
        payload_part = str(token or "").split(".")[1]
        pad = "=" * (-len(payload_part) % 4)
        raw = base64.urlsafe_b64decode((payload_part + pad).encode("ascii"))
        parsed = json.loads(raw.decode("utf-8", errors="ignore"))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _exp_to_iso(exp: Any) -> str:
    try:
        ts = int(exp)
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return ""


class ProtocolRegisterService:
    def __init__(self):
        # 协议注册逻辑已内置到本项目模块，不再依赖外部脚本路径。
        pass

    def _build_token_artifact(
        self,
        *,
        email: str,
        access_token: str,
        refresh_token: str,
        id_token: str,
    ) -> dict[str, Any]:
        payload = _decode_jwt_payload(access_token)
        auth_info = payload.get("https://api.openai.com/auth")
        account_id = ""
        if isinstance(auth_info, dict):
            account_id = str(auth_info.get("chatgpt_account_id") or "").strip()

        exp = payload.get("exp")
        expired_iso = _exp_to_iso(exp)
        now_iso = datetime.now(timezone.utc).isoformat()

        return {
            "type": "codex",
            "email": email,
            "expired": expired_iso,
            "id_token": id_token,
            "account_id": account_id,
            "access_token": access_token,
            "last_refresh": now_iso,
            "refresh_token": refresh_token,
        }

    def register_and_login(
        self,
        *,
        email: str,
        password: str,
        get_verification_code: Callable[[str], str | None],
    ) -> dict[str, Any]:
        module = protocol_keygen_module

        registrar = module.ProtocolRegistrar()
        if not registrar.step0_init_oauth_session(email):
            raise RuntimeError("protocol register failed at step0_init_oauth_session")
        if not registrar.step2_register_user(email, password):
            raise RuntimeError("protocol register failed at step2_register_user")
        if not registrar.step3_send_otp():
            raise RuntimeError("protocol register failed at step3_send_otp")

        code = str(get_verification_code(email) or "").strip()
        if not code:
            raise RuntimeError("protocol register failed: verification code is empty")
        if not registrar.step4_validate_otp(code):
            raise RuntimeError("protocol register failed at step4_validate_otp")

        first_name = "Auto"
        last_name = "System"
        birthday = "1998-08-08"
        try:
            fn, ln = module.generate_random_name()
            bd = module.generate_random_birthday()
            if str(fn or "").strip() and str(ln or "").strip():
                first_name = str(fn).strip()
                last_name = str(ln).strip()
            if str(bd or "").strip():
                birthday = str(bd).strip()
        except Exception:
            pass

        if not registrar.step5_create_account(
            first_name=first_name,
            last_name=last_name,
            birthdate=birthday,
        ):
            raise RuntimeError("protocol register failed at step5_create_account")

        original_fetch_emails = getattr(module, "fetch_emails", None)

        def _fetch_emails_override(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
            otp = str(get_verification_code(email) or "").strip()
            if not otp:
                return []
            return [{"id": "otp-inline", "subject": f"Code: {otp}"}]

        try:
            if callable(original_fetch_emails):
                setattr(module, "fetch_emails", _fetch_emails_override)

            tokens = module.perform_codex_oauth_login_http(
                email,
                password,
            )
        finally:
            if callable(original_fetch_emails):
                setattr(module, "fetch_emails", original_fetch_emails)

        if not isinstance(tokens, dict):
            raise RuntimeError("protocol oauth failed: invalid token payload")

        access_token = str(tokens.get("access_token") or "").strip()
        refresh_token = str(tokens.get("refresh_token") or "").strip()
        id_token = str(tokens.get("id_token") or "").strip()
        if not access_token:
            raise RuntimeError("protocol oauth failed: missing access_token")

        token_artifact = self._build_token_artifact(
            email=email,
            access_token=access_token,
            refresh_token=refresh_token,
            id_token=id_token,
        )
        account_id = str(token_artifact.get("account_id") or "").strip()
        session_data = {
            "accessToken": access_token,
            "user": {
                "email": email,
            },
        }

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "id_token": id_token,
            "account_id": account_id,
            "token_artifact": token_artifact,
            "session_data": session_data,
        }

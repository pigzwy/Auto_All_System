from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_REPO_PATH = str(Path(__file__).resolve().parent.parent.parent / "libs" / "oai_provisioner")


@dataclass(frozen=True)
class LegacyRunArtifacts:
    job_dir: Path
    repo_dir: Path
    log_file: Path
    csv_file: Path
    tracker_file: Path
    team_json_file: Path
    domain_blacklist_file: Path


def _format_toml_str(value: str) -> str:
    value = str(value)
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _format_toml_bool(value: bool) -> str:
    return "true" if bool(value) else "false"


def _format_toml_list(values: list[Any]) -> str:
    parts = []
    for v in values:
        if isinstance(v, bool):
            parts.append(_format_toml_bool(v))
        elif isinstance(v, (int, float)):
            parts.append(str(v))
        else:
            parts.append(_format_toml_str(str(v)))
    return f"[{', '.join(parts)}]"


def build_config_toml(
    *,
    plugin_settings: dict[str, Any],
    task_record: dict[str, Any],
    artifacts: LegacyRunArtifacts,
    email_provider: str | None = None,
    email_config: dict[str, Any] | None = None,
    checkout_card: dict[str, Any] | None = None,
) -> str:
    # 基于 config.toml.example 的 schema，按当前系统 settings 生成。
    # 目标：尽可能保持源项目行为一致，同时保证产物写到 job_dir。
    gptmail = plugin_settings.get("gptmail") or {}
    gptmail_domains = gptmail.get("domains") or []

    proxies = plugin_settings.get("proxies") or []
    proxy_enabled = bool(plugin_settings.get("proxy_enabled", False))

    auth_provider = str(plugin_settings.get("auth_provider") or "crs").strip() or "crs"
    include_team_owners = bool(plugin_settings.get("include_team_owners", False))

    crs = plugin_settings.get("crs") or {}
    cpa = plugin_settings.get("cpa") or {}
    s2a = plugin_settings.get("s2a") or {}

    request_cfg = plugin_settings.get("request") or {}
    verification_cfg = plugin_settings.get("verification") or {}
    browser_cfg = plugin_settings.get("browser") or {}

    default_password = str(task_record.get("password") or plugin_settings.get("default_password") or "")
    if not default_password:
        default_password = "YourSecurePassword@2025"

    accounts_per_team = int(task_record.get("count") or plugin_settings.get("accounts_per_team") or 4)

    resolved_email_provider = str(email_provider or plugin_settings.get("email_provider") or "gptmail").strip() or "gptmail"

    lines: list[str] = []
    lines.append(f"proxy_enabled = {_format_toml_bool(proxy_enabled)}")
    lines.append(f"email_provider = {_format_toml_str(resolved_email_provider)}")
    lines.append("")

    if resolved_email_provider.lower() == "gptmail":
        lines.append("[gptmail]")
        lines.append(f"api_base = {_format_toml_str(str(gptmail.get('api_base') or ''))}")
        lines.append(f"api_key = {_format_toml_str(str(gptmail.get('api_key') or ''))}")
        lines.append(f"prefix = {_format_toml_str(str(gptmail.get('prefix') or ''))}")
        lines.append(f"domains = {_format_toml_list(list(gptmail_domains))}")
        lines.append("")
    else:
        cfg: dict[str, Any] = {}
        if isinstance(email_config, dict):
            cfg = email_config
        else:
            maybe_cfg = plugin_settings.get("email")
            if isinstance(maybe_cfg, dict):
                cfg = maybe_cfg

        lines.append("[email]")
        lines.append(f"api_base = {_format_toml_str(str(cfg.get('api_base') or ''))}")
        lines.append(f"api_auth = {_format_toml_str(str(cfg.get('api_auth') or ''))}")
        lines.append(f"domains = {_format_toml_list(list(cfg.get('domains') or []))}")
        lines.append(f"role = {_format_toml_str(str(cfg.get('role') or 'user'))}")
        lines.append(f"web_url = {_format_toml_str(str(cfg.get('web_url') or ''))}")
        lines.append("")

    lines.append(f"auth_provider = {_format_toml_str(auth_provider)}")
    lines.append(f"include_team_owners = {_format_toml_bool(include_team_owners)}")
    lines.append("")

    lines.append("[crs]")
    lines.append(f"api_base = {_format_toml_str(str(crs.get('api_base') or ''))}")
    lines.append(f"admin_token = {_format_toml_str(str(crs.get('admin_token') or ''))}")
    lines.append("")

    lines.append("[cpa]")
    lines.append(f"api_base = {_format_toml_str(str(cpa.get('api_base') or ''))}")
    lines.append(f"admin_password = {_format_toml_str(str(cpa.get('admin_password') or ''))}")
    lines.append(f"poll_interval = {int(cpa.get('poll_interval') or 2)}")
    lines.append(f"poll_max_retries = {int(cpa.get('poll_max_retries') or 30)}")
    lines.append(f"is_webui = {_format_toml_bool(bool(cpa.get('is_webui', True)))}")
    lines.append("")

    lines.append("[s2a]")
    lines.append(f"api_base = {_format_toml_str(str(s2a.get('api_base') or ''))}")
    lines.append(f"admin_key = {_format_toml_str(str(s2a.get('admin_key') or ''))}")
    lines.append(f"admin_token = {_format_toml_str(str(s2a.get('admin_token') or ''))}")
    lines.append(f"concurrency = {int(s2a.get('concurrency') or 5)}")
    lines.append(f"priority = {int(s2a.get('priority') or 50)}")
    lines.append(f"group_ids = {_format_toml_list(list(s2a.get('group_ids') or []))}")
    lines.append(f"group_names = {_format_toml_list(list(s2a.get('group_names') or []))}")
    lines.append("")

    lines.append("[account]")
    lines.append(f"default_password = {_format_toml_str(default_password)}")
    lines.append(f"accounts_per_team = {accounts_per_team}")
    lines.append("")

    lines.append("[request]")
    lines.append(f"timeout = {int(request_cfg.get('timeout') or 30)}")
    lines.append(f"user_agent = {_format_toml_str(str(request_cfg.get('user_agent') or ''))}")
    lines.append("")

    lines.append("[verification]")
    lines.append(f"timeout = {int(verification_cfg.get('timeout') or 60)}")
    lines.append(f"interval = {int(verification_cfg.get('interval') or 3)}")
    lines.append(f"max_retries = {int(verification_cfg.get('max_retries') or 20)}")
    lines.append("")

    lines.append("[browser]")
    lines.append(f"wait_timeout = {int(browser_cfg.get('wait_timeout') or 60)}")
    lines.append(f"short_wait = {int(browser_cfg.get('short_wait') or 10)}")
    lines.append(f"headless = {_format_toml_bool(bool(browser_cfg.get('headless', False)))}")
    lines.append("")

    # checkout 配置（绑卡信息）- 优先使用传入的 checkout_card，否则使用 settings
    checkout_cfg = checkout_card or plugin_settings.get("checkout") or {}
    lines.append("[checkout]")
    lines.append(f"card_number = {_format_toml_str(str(checkout_cfg.get('card_number') or ''))}")
    lines.append(f"card_expiry = {_format_toml_str(str(checkout_cfg.get('card_expiry') or ''))}")
    lines.append(f"card_cvc = {_format_toml_str(str(checkout_cfg.get('card_cvc') or ''))}")
    lines.append(f"cardholder_name = {_format_toml_str(str(checkout_cfg.get('cardholder_name') or ''))}")
    lines.append(f"address_line1 = {_format_toml_str(str(checkout_cfg.get('address_line1') or ''))}")
    lines.append(f"city = {_format_toml_str(str(checkout_cfg.get('city') or ''))}")
    lines.append(f"postal_code = {_format_toml_str(str(checkout_cfg.get('postal_code') or ''))}")
    lines.append(f"state = {_format_toml_str(str(checkout_cfg.get('state') or ''))}")
    lines.append(f"country = {_format_toml_str(str(checkout_cfg.get('country') or 'US'))}")
    lines.append("")

    lines.append("[files]")
    lines.append(f"csv_file = {_format_toml_str(str(artifacts.csv_file))}")
    lines.append(f"tracker_file = {_format_toml_str(str(artifacts.tracker_file))}")
    lines.append("")

    for proxy in proxies:
        if not isinstance(proxy, dict):
            continue
        lines.append("[[proxies]]")
        lines.append(f"type = {_format_toml_str(str(proxy.get('type') or 'http'))}")
        lines.append(f"host = {_format_toml_str(str(proxy.get('host') or ''))}")
        lines.append(f"port = {int(proxy.get('port') or 0)}")
        lines.append(f"username = {_format_toml_str(str(proxy.get('username') or ''))}")
        lines.append(f"password = {_format_toml_str(str(proxy.get('password') or ''))}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_team_json(*, plugin_settings: dict[str, Any], task_record: dict[str, Any]) -> list[dict[str, Any]]:
    team_name = str(task_record.get("team_name") or "").strip()
    if not team_name:
        raise ValueError("Task record missing team_name")

    teams = plugin_settings.get("teams") or []
    team_cfg = next((x for x in teams if isinstance(x, dict) and x.get("name") == team_name), None)
    if not team_cfg:
        raise ValueError(f"Team not found: {team_name}")

    owner_email = str(team_cfg.get("owner_email") or "").strip()
    owner_password = str(team_cfg.get("owner_password") or "").strip()
    token = str(team_cfg.get("auth_token") or "").strip()
    account_id = str(team_cfg.get("account_id") or "").strip()
    authorized = bool(team_cfg.get("authorized", False))

    if not owner_email or not owner_password:
        raise ValueError("Team missing owner_email/owner_password")

    team_json: dict[str, Any] = {
        "account": owner_email,
        "password": owner_password,
    }
    if token:
        team_json["token"] = token
    if authorized:
        team_json["authorized"] = True
    if account_id:
        team_json["account_id"] = account_id

    return [team_json]


def prepare_artifacts(job_dir: Path) -> LegacyRunArtifacts:
    job_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = job_dir / "repo"
    log_file = job_dir / "run.log"
    csv_file = job_dir / "accounts.csv"
    tracker_file = job_dir / "team_tracker.json"

    # 这两个文件在 repo_dir 内部（源项目固定 BASE_DIR）
    team_json_file = repo_dir / "team.json"
    domain_blacklist_file = repo_dir / "domain_blacklist.json"

    return LegacyRunArtifacts(
        job_dir=job_dir,
        repo_dir=repo_dir,
        log_file=log_file,
        csv_file=csv_file,
        tracker_file=tracker_file,
        team_json_file=team_json_file,
        domain_blacklist_file=domain_blacklist_file,
    )


def copy_repo(repo_src: str, repo_dst: Path):
    src = Path(repo_src)
    if not src.exists():
        raise FileNotFoundError(f"repo not found: {repo_src}")

    if repo_dst.exists():
        shutil.rmtree(repo_dst)

    def ignore(path: str, names: list[str]):
        ignored = {".git", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache"}
        return [n for n in names if n in ignored]

    shutil.copytree(src, repo_dst, ignore=ignore)


def run_legacy(repo_src: str, artifacts: LegacyRunArtifacts, *, config_toml: str, team_json: list[dict[str, Any]], args: list[str] | None = None) -> int:
    copy_repo(repo_src, artifacts.repo_dir)

    # 写入配置（源项目固定读取 repo_dir/config.toml & repo_dir/team.json）
    (artifacts.repo_dir / "config.toml").write_text(config_toml, encoding="utf-8")
    (artifacts.repo_dir / "team.json").write_text(json.dumps(team_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cmd = [sys.executable, "run.py"]
    if args:
        cmd.extend([str(x) for x in args])

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    with artifacts.log_file.open("w", encoding="utf-8") as log_fp:
        proc = subprocess.run(
            cmd,
            cwd=str(artifacts.repo_dir),
            env=env,
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            check=False,
        )
        return int(proc.returncode)


def run_repo_script(
    repo_src: str,
    artifacts: LegacyRunArtifacts,
    *,
    config_toml: str,
    cmd: list[str],
    extra_files: dict[str, str] | None = None,
) -> int:
    """在隔离的 job_dir/repo 内执行任意脚本。

    - 会 copy repo 到 artifacts.repo_dir
    - 会写入 repo_dir/config.toml
    - extra_files 支持写入额外的 repo 内文件（相对 repo_dir）
    - stdout/stderr 会写到 artifacts.log_file
    """

    copy_repo(repo_src, artifacts.repo_dir)
    (artifacts.repo_dir / "config.toml").write_text(config_toml, encoding="utf-8")

    if extra_files:
        for rel_path, content in extra_files.items():
            p = artifacts.repo_dir / rel_path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    with artifacts.log_file.open("w", encoding="utf-8") as log_fp:
        proc = subprocess.run(
            [str(x) for x in cmd],
            cwd=str(artifacts.repo_dir),
            env=env,
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            check=False,
        )
        return int(proc.returncode)

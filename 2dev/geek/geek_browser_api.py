#!/usr/bin/env python3
"""GeekezBrowser local control + profile file helpers.

This project historically uses BitBrowser via HTTP API.
GeekezBrowser differs a bit:

- App health/control: HTTP (e.g. GET /health, POST /profiles/{id}/launch)
- Profiles storage: local JSON files (profiles.json / settings.json)

This module provides a small, testable wrapper so higher-level process/GUI
code can stay close to the existing BitBrowser workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import os
import time

import requests


def _default_data_dir() -> Path:
    # GeekezBrowser template uses Windows APPDATA path.
    # Keep Windows-first behavior, but provide a sane fallback on non-Windows.
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "geekez-browser" / "BrowserProfiles"
    return Path.home() / ".config" / "geekez-browser" / "BrowserProfiles"


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


@dataclass(frozen=True)
class LaunchInfo:
    profile_id: str
    debug_port: int
    # Playwright `connect_over_cdp()` accepts either ws://... or http://host:port
    cdp_endpoint: str


class GeekezBrowserAPI:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 19527,
        data_dir: Optional[Path] = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.timeout_seconds = float(timeout_seconds)

        self.data_dir = data_dir or _default_data_dir()
        self.profiles_file = self.data_dir / "profiles.json"
        self.settings_file = self.data_dir / "settings.json"

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    # ------------------------------
    # App health / remote debugging
    # ------------------------------
    def is_running(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=self.timeout_seconds)
            return resp.status_code == 200
        except Exception:
            return False

    def wait_until_ready(
        self, timeout_seconds: float = 30.0, interval_seconds: float = 1.0
    ) -> bool:
        deadline = time.time() + float(timeout_seconds)
        while time.time() < deadline:
            if self.is_running():
                return True
            time.sleep(float(interval_seconds))
        return False

    def wait_until_down(
        self, timeout_seconds: float = 15.0, interval_seconds: float = 0.5
    ) -> bool:
        deadline = time.time() + float(timeout_seconds)
        while time.time() < deadline:
            if not self.is_running():
                return True
            time.sleep(float(interval_seconds))
        return not self.is_running()

    def enable_remote_debugging(self) -> None:
        settings = _read_json(self.settings_file, {})
        if not isinstance(settings, dict):
            settings = {}
        settings["enableRemoteDebugging"] = True
        _write_json(self.settings_file, settings)

    # ------------------------------
    # Profile file operations
    # ------------------------------
    def load_profiles(self) -> List[Dict[str, Any]]:
        profiles = _read_json(self.profiles_file, [])
        if not isinstance(profiles, list):
            return []
        return [p for p in profiles if isinstance(p, dict)]

    def save_profiles(self, profiles: List[Dict[str, Any]]) -> None:
        _write_json(self.profiles_file, profiles)

    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        for profile in self.load_profiles():
            if profile.get("id") == profile_id:
                return profile
        return None

    def find_profile_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        for profile in self.load_profiles():
            if profile.get("name") == name:
                return profile
        return None

    def upsert_profile(
        self,
        name: str,
        proxy_str: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        width: int = 1280,
        height: int = 800,
    ) -> Dict[str, Any]:
        """Create or update profile by name.

        Geek scripts in this repo treat account(email) as "environment". Using
        profile name as stable key avoids writing an extra mapping file.
        """
        profiles = self.load_profiles()
        existing = None
        for p in profiles:
            if p.get("name") == name:
                existing = p
                break

        if existing is None:
            profile_id = self._new_uuid()
            profile = {
                "id": profile_id,
                "name": name,
                "proxyStr": proxy_str or "",
                "tags": tags or [],
                "fingerprint": {"window": {"width": int(width), "height": int(height)}},
                "preProxyOverride": "default",
                "isSetup": False,
                "debugPort": 0,
                "createdAt": int(time.time() * 1000),
                "metadata": metadata or {},
            }
            profiles.append(profile)
            self.save_profiles(profiles)
            return profile

        # Update in-place
        if proxy_str is not None:
            existing["proxyStr"] = proxy_str
        if tags is not None:
            existing["tags"] = tags
        if metadata:
            if not isinstance(existing.get("metadata"), dict):
                existing["metadata"] = {}
            existing["metadata"].update(metadata)
        # Keep window fingerprint stable unless caller overrides.
        if width or height:
            existing.setdefault("fingerprint", {}).setdefault("window", {})
            existing["fingerprint"]["window"]["width"] = int(width)
            existing["fingerprint"]["window"]["height"] = int(height)

        self.save_profiles(profiles)
        return existing

    def delete_profile(self, profile_id: str) -> bool:
        profiles = self.load_profiles()
        new_profiles = [p for p in profiles if p.get("id") != profile_id]
        if len(new_profiles) == len(profiles):
            return False
        self.save_profiles(new_profiles)
        return True

    # ------------------------------
    # Control API calls
    # ------------------------------
    def launch_profile(
        self, profile_id: str, debug_port: int = 0, enable_remote_debugging: bool = True
    ) -> LaunchInfo:
        url = f"{self.base_url}/profiles/{profile_id}/launch"
        payload = {
            "debugPort": int(debug_port),
            "enableRemoteDebugging": bool(enable_remote_debugging),
        }
        resp = requests.post(url, json=payload, timeout=self.timeout_seconds)
        resp.raise_for_status()
        result = resp.json() if resp.content else {}

        port = int(result.get("debugPort") or 0)
        # Geek scripts sometimes return `wsEndpoint`, but if absent we can use
        # a standard CDP HTTP endpoint and let Playwright resolve WS itself.
        endpoint = result.get("wsEndpoint")
        if not endpoint:
            endpoint = f"http://127.0.0.1:{port}"

        return LaunchInfo(
            profile_id=profile_id, debug_port=port, cdp_endpoint=str(endpoint)
        )

    def close_profile(self, profile_id: str) -> bool:
        try:
            url = f"{self.base_url}/profiles/{profile_id}/close"
            resp = requests.post(url, timeout=self.timeout_seconds)
            return resp.status_code == 200
        except Exception:
            return False

    def shutdown(self) -> bool:
        """Ask GeekezBrowser app to quit via control server."""
        try:
            url = f"{self.base_url}/shutdown"
            resp = requests.post(url, timeout=self.timeout_seconds)
            return resp.status_code == 200
        except Exception:
            return False

    # ------------------------------
    # utils
    # ------------------------------
    @staticmethod
    def _new_uuid() -> str:
        import uuid

        return str(uuid.uuid4())


__all__ = [
    "GeekezBrowserAPI",
    "LaunchInfo",
]

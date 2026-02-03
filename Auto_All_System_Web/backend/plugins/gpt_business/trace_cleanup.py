from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from django.conf import settings as django_settings
from django.utils import timezone


class TraceCleanupConfig(TypedDict):
    max_age_days: int
    max_total_size_mb: int
    max_files: int
    min_keep_files: int
    pattern: str


class TraceFileInfo(TypedDict):
    path: Path
    size: int
    mtime: float


class TraceCleanupResult(TypedDict):
    trace_dir: str
    dry_run: bool
    total_files: int
    total_bytes: int
    deleted_files: int
    freed_bytes: int
    kept_files: int
    settings: TraceCleanupConfig
    deleted_paths: list[str]


DEFAULT_TRACE_CLEANUP: TraceCleanupConfig = {
    "max_age_days": 7,
    "max_total_size_mb": 1024,
    "max_files": 2000,
    "min_keep_files": 20,
    "pattern": "trace_*.log",
}


def get_trace_cleanup_settings(settings: dict[str, object]) -> TraceCleanupConfig:
    raw = settings.get("trace_cleanup")
    if not isinstance(raw, dict):
        raw = {}

    def _get_int(key: str, default: int) -> int:
        val = raw.get(key, default)
        try:
            return int(val)
        except Exception:
            return default

    default_max_age_days = int(DEFAULT_TRACE_CLEANUP["max_age_days"])
    default_max_total_size_mb = int(DEFAULT_TRACE_CLEANUP["max_total_size_mb"])
    default_max_files = int(DEFAULT_TRACE_CLEANUP["max_files"])
    default_min_keep_files = int(DEFAULT_TRACE_CLEANUP["min_keep_files"])
    default_pattern = str(DEFAULT_TRACE_CLEANUP["pattern"])

    return {
        "max_age_days": _get_int("max_age_days", default_max_age_days),
        "max_total_size_mb": _get_int("max_total_size_mb", default_max_total_size_mb),
        "max_files": _get_int("max_files", default_max_files),
        "min_keep_files": _get_int("min_keep_files", default_min_keep_files),
        "pattern": str(raw.get("pattern") or default_pattern),
    }


def _list_trace_files(trace_dir: Path, pattern: str) -> list[TraceFileInfo]:
    items: list[TraceFileInfo] = []
    for path in trace_dir.glob(pattern):
        if not path.is_file():
            continue
        stat = path.stat()
        items.append({"path": path, "size": stat.st_size, "mtime": stat.st_mtime})
    items.sort(key=lambda x: x["mtime"])
    return items


def cleanup_trace_files(
    settings: dict[str, object],
    *,
    dry_run: bool = True,
    overrides: dict[str, int | str] | None = None,
) -> TraceCleanupResult:
    config = get_trace_cleanup_settings(settings)
    if overrides:
        if "max_age_days" in overrides:
            config["max_age_days"] = int(overrides["max_age_days"])
        if "max_total_size_mb" in overrides:
            config["max_total_size_mb"] = int(overrides["max_total_size_mb"])
        if "max_files" in overrides:
            config["max_files"] = int(overrides["max_files"])
        if "min_keep_files" in overrides:
            config["min_keep_files"] = int(overrides["min_keep_files"])
        if "pattern" in overrides:
            config["pattern"] = str(overrides["pattern"])

    base_dir = Path(getattr(django_settings, "BASE_DIR", "."))
    trace_dir = base_dir / "logs" / "trace"
    if not trace_dir.exists():
        return {
            "trace_dir": str(trace_dir),
            "dry_run": dry_run,
            "total_files": 0,
            "total_bytes": 0,
            "deleted_files": 0,
            "freed_bytes": 0,
            "kept_files": 0,
            "settings": config,
            "deleted_paths": [],
        }

    files = _list_trace_files(trace_dir, config["pattern"])
    total_files = len(files)
    total_bytes = sum(x["size"] for x in files)

    to_delete: list[TraceFileInfo] = []
    remaining = list(files)

    max_age_days = int(config["max_age_days"])
    if max_age_days > 0:
        cutoff = timezone.now().timestamp() - max_age_days * 86400
        for item in list(remaining):
            if item["mtime"] < cutoff:
                to_delete.append(item)
                remaining.remove(item)

    min_keep_files = max(int(config["min_keep_files"]), 0)
    max_files = int(config["max_files"])
    if max_files > 0 and len(remaining) > max_files:
        target_keep = max(max_files, min_keep_files)
        delete_count = max(0, len(remaining) - target_keep)
        if delete_count > 0:
            to_delete.extend(remaining[:delete_count])
            remaining = remaining[delete_count:]

    max_total_size_mb = int(config["max_total_size_mb"])
    if max_total_size_mb > 0:
        limit_bytes = max_total_size_mb * 1024 * 1024
        remaining_size = sum(x["size"] for x in remaining)
        while remaining_size > limit_bytes and len(remaining) > min_keep_files:
            oldest = remaining.pop(0)
            to_delete.append(oldest)
            remaining_size -= oldest["size"]

    deleted_paths: list[str] = []
    freed_bytes = 0
    if not dry_run:
        for item in to_delete:
            try:
                item["path"].unlink()
                freed_bytes += item["size"]
                deleted_paths.append(str(item["path"]))
            except Exception:
                continue
    else:
        freed_bytes = sum(x["size"] for x in to_delete)
        deleted_paths = [str(x["path"]) for x in to_delete]

    return {
        "trace_dir": str(trace_dir),
        "dry_run": dry_run,
        "total_files": total_files,
        "total_bytes": total_bytes,
        "deleted_files": len(to_delete),
        "freed_bytes": freed_bytes,
        "kept_files": total_files - len(to_delete),
        "settings": config,
        "deleted_paths": deleted_paths,
    }

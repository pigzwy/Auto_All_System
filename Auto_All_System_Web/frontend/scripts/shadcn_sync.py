#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _curl_json(url: str) -> dict:
    proc = subprocess.run(
        ["curl", "-fsSL", url],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(f"curl failed ({proc.returncode}) for {url}: {stderr}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"invalid JSON from {url}: {e}")


def _dest_for_registry_path(path: str) -> Path:
    # Registry paths are relative to shadcn-vue aliases (ui/lib/etc).
    # In this repo, ui is under src/components/ui, while lib/composables live under src/.
    if path.startswith("ui/"):
        return Path("src/components") / path
    return Path("src") / path


def _write_text_file(dest: Path, content: str, *, overwrite: bool) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        existing = dest.read_text(encoding="utf-8")
        if existing == content:
            return False
        if not overwrite:
            raise RuntimeError(f"refusing to overwrite existing file: {dest}")

    dest.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Sync shadcn-vue registry items into this repo using curl. "
            "Run from the frontend/ directory."
        )
    )
    parser.add_argument("--style", default="new-york", help="Registry style (default: new-york)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Do not write files, only print planned actions",
    )
    parser.add_argument("items", nargs="*", help="Registry item names (e.g. button dialog)")
    args = parser.parse_args()

    initial_items = args.items or [
        # Base registry deps.
        "utils",
        # UI components.
        "button",
        "card",
        "input",
        "label",
        "form",
        "select",
        "table",
        "dropdown-menu",
        "dialog",
        "sheet",
        "avatar",
        "badge",
        "separator",
        "alert",
        "toast",
    ]

    registry_base = f"https://shadcn-vue.com/r/styles/{args.style}".rstrip("/")

    queue: list[str] = ["index", *initial_items]
    seen: set[str] = set()

    runtime_deps: set[str] = set()
    written_files: list[str] = []
    skipped_files: list[str] = []

    while queue:
        name = queue.pop(0)
        if name in seen:
            continue
        seen.add(name)

        url = f"{registry_base}/{name}.json"
        data = _curl_json(url)

        for dep in data.get("dependencies") or []:
            if isinstance(dep, str) and dep:
                runtime_deps.add(dep)

        for dep in data.get("registryDependencies") or []:
            if isinstance(dep, str) and dep and dep not in seen:
                queue.append(dep)

        for file_entry in data.get("files") or []:
            rel = file_entry.get("path")
            content = file_entry.get("content")
            if not isinstance(rel, str) or not rel:
                raise RuntimeError(f"registry item {name} has invalid file path")
            if not isinstance(content, str):
                raise RuntimeError(f"registry item {name} file {rel} missing inline content")

            dest = _dest_for_registry_path(rel)
            if args.no_write:
                written_files.append(str(dest))
                continue

            changed = _write_text_file(dest, content, overwrite=args.overwrite)
            (written_files if changed else skipped_files).append(str(dest))

    print(f"registry items processed: {len(seen)}")
    print(f"files written/updated: {len(written_files)}")
    print(f"files unchanged: {len(skipped_files)}")
    if written_files:
        for p in written_files:
            print(f"- {p}")
    print("dependencies:")
    for dep in sorted(runtime_deps):
        print(f"- {dep}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

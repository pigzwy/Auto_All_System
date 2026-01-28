#!/usr/bin/env bash
set -euo pipefail

# Linux host-network preset:
# - makes backend/celery use host network so Geekez dynamic CDP ports are reachable
# - skips frontend dev server by default

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/开发模式启动.sh" --hostnet --skip-frontend

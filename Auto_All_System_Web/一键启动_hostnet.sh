#!/usr/bin/env bash
set -euo pipefail

# Linux host-network preset for one-click start.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export USE_HOST_NETWORK=1
exec "$SCRIPT_DIR/一键启动.sh"

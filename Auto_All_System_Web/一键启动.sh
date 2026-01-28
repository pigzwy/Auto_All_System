#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ "${USE_HOST_NETWORK:-}" == "1" && -f "docker-compose.linux.hostnet.yml" ]]; then
  export COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml:docker-compose.linux.hostnet.yml}"
elif [[ -f "docker-compose.linux.yml" ]]; then
  export COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml:docker-compose.linux.yml}"
fi

compose() {
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    docker compose "$@"
  fi
}

open_url() {
  local url="$1"
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 || true
  elif command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1 || true
  fi
}

echo "========================================"
echo "  Auto All System - One Click Start"
echo "========================================"
echo

echo "[1/4] Check Docker..."
if ! docker version >/dev/null 2>&1; then
  echo "[ERROR] Docker not running (or no permission)."
  echo "        Try: sudo systemctl start docker"
  echo "        Or add user to docker group."
  exit 1
fi
echo "[OK] Docker is running"

echo
echo "[1.5/4] Prepare runtime env..."
mkdir -p "backend/logs"
if [[ ! -f "backend/.env" ]]; then
  echo "[WARN] backend/.env not found, backend container may fail"
fi

# Linux: provide a default local GeekezBrowser profiles directory
mkdir -p "backend/geekez-browser/BrowserProfiles"
export GEEKEZ_BROWSER_PROFILES_PATH="${GEEKEZ_BROWSER_PROFILES_PATH:-$SCRIPT_DIR/backend/geekez-browser/BrowserProfiles}"

# Clean inherited proxy env to avoid breaking apt/pip during docker build.
unset HTTP_PROXY HTTPS_PROXY NO_PROXY http_proxy https_proxy no_proxy ALL_PROXY all_proxy PIP_PROXY || true

# Speed up pip install during docker build (CN mirror by default)
export PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
export PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST:-pypi.tuna.tsinghua.edu.cn}"

# Optional: use host proxy for pip only (recommended).
# Set USE_HOST_PROXY=1 to enable.
if [[ "${USE_HOST_PROXY:-}" == "1" ]]; then
  export PIP_PROXY="${PIP_PROXY:-http://127.0.0.1:7897}"
fi

# Do NOT force apt to use proxy by default
export HTTP_PROXY=""
export HTTPS_PROXY=""
export NO_PROXY=""
export http_proxy=""
export https_proxy=""
export no_proxy=""
echo "[OK] Runtime env ready"

echo
echo "[2/4] Start all services (build images / install deps)..."
compose up -d --build

# Linux: auto start Geekez forwarders (no manual container management)
if compose config --services 2>/dev/null | grep -qx "geekez-control-forwarder"; then
  compose up -d geekez-control-forwarder geekez-api-forwarder >/dev/null 2>&1 || true
fi

echo
echo "[3/4] Waiting for services..."
sleep 10
echo "[OK] Services should be ready"

echo
echo "[4/4] Service status:"
compose ps

echo
echo "========================================"
echo "  [OK] System Started"
echo "========================================"
echo
echo "URLs:"
echo "  - Frontend:  http://localhost/"
echo "  - Backend:   http://localhost:8000/api/"
echo "  - API Docs:  http://localhost:8000/api/docs/"
echo "  - Admin:     http://localhost:8000/admin/"
echo
echo "Logs: compose logs -f backend"
echo "Stop: compose down"

open_url "http://localhost/"

echo
read -r -p "Press Enter to exit..." _

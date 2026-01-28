#!/usr/bin/env bash
set -euo pipefail

USE_HOST_NETWORK="${USE_HOST_NETWORK:-}"
SKIP_FRONTEND="${SKIP_FRONTEND:-}"

print_help() {
  echo "Usage: $0 [--hostnet] [--skip-frontend]"
  echo
  echo "Options:"
  echo "  --hostnet         Run backend/celery in host network (Linux CDP automation recommended)"
  echo "  --skip-frontend   Skip starting frontend dev server"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --hostnet)
      USE_HOST_NETWORK=1
      shift
      ;;
    --skip-frontend)
      SKIP_FRONTEND=1
      shift
      ;;
    -h|--help)
      print_help
      exit 0
      ;;
    *)
      echo "[ERROR] Unknown argument: $1"
      print_help
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ "${EUID:-$(id -u)}" == "0" ]]; then
  echo "[ERROR] Do not run this script as root/sudo (it breaks npm PATH and file permissions)."
  echo "        Fix docker permission instead: sudo usermod -aG docker $SUDO_USER && newgrp docker"
  exit 1
fi

RUN_USER_HOME="$HOME"
if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
  RUN_USER_HOME="$(getent passwd "${SUDO_USER}" 2>/dev/null | cut -d: -f6)"
  if [[ -z "$RUN_USER_HOME" ]]; then
    RUN_USER_HOME="$HOME"
  fi
fi

if [[ "${USE_HOST_NETWORK}" == "1" && -f "docker-compose.linux.hostnet.yml" ]]; then
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
echo "  Auto All System - Dev Mode"
echo "========================================"
echo

echo "[1/6] Check Docker..."
if ! docker version >/dev/null 2>&1; then
  echo "[ERROR] Docker not running (or no permission)."
  exit 1
fi
echo "[OK] Docker is running"

echo
echo "[2/6] Starting DB and Redis..."
compose up -d db redis
echo "[OK] DB and Redis started"

echo
echo "[3/6] Waiting for DB..."
sleep 5
echo "[OK] DB ready"

echo
echo "[4/6] Prepare backend..."
mkdir -p "backend/logs"
if [[ ! -f "backend/.env" ]]; then
  echo "[WARN] backend/.env not found, backend container may fail"
fi

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

echo "[OK] Backend preparation done"

echo
echo "[5/6] Starting backend (build images / install deps)..."
if [[ "${FORCE_BUILD:-}" == "1" ]]; then
  echo "[INFO] FORCE_BUILD=1, rebuilding backend image (no cache)..."
  compose build --no-cache backend
else
  if ! docker image inspect auto_all_system_web-backend >/dev/null 2>&1; then
    echo "[INFO] Backend image missing, building..."
    compose build backend
  else
    echo "[INFO] Backend image exists, skip build"
  fi
fi

compose up -d backend celery celery-beat
compose restart backend celery celery-beat >/dev/null 2>&1 || true
echo "[OK] Backend started"

# Linux: auto start Geekez forwarders (no manual container management)
if compose config --services 2>/dev/null | grep -qx "geekez-control-forwarder"; then
  compose up -d geekez-control-forwarder geekez-api-forwarder >/dev/null 2>&1 || true
fi

# Stop Docker frontend to avoid port conflict with local dev server
compose stop frontend >/dev/null 2>&1 || true

echo
echo "[6/6] Starting frontend dev server..."

resolve_npm() {
  local npm_bin=""

  npm_bin="$(command -v npm 2>/dev/null || true)"
  if [[ -n "$npm_bin" ]]; then
    echo "$npm_bin"
    return 0
  fi

  # Try load common shell profiles (nvm is often initialized here)
  if [[ -f "$RUN_USER_HOME/.profile" ]]; then
    # shellcheck disable=SC1090
    . "$RUN_USER_HOME/.profile" >/dev/null 2>&1 || true
  fi
  if [[ -f "$RUN_USER_HOME/.bashrc" ]]; then
    # shellcheck disable=SC1090
    . "$RUN_USER_HOME/.bashrc" >/dev/null 2>&1 || true
  fi
  if [[ -f "$RUN_USER_HOME/.bash_profile" ]]; then
    # shellcheck disable=SC1090
    . "$RUN_USER_HOME/.bash_profile" >/dev/null 2>&1 || true
  fi

  npm_bin="$(command -v npm 2>/dev/null || true)"
  if [[ -n "$npm_bin" ]]; then
    echo "$npm_bin"
    return 0
  fi

  # nvm fallback: pick latest installed npm
  if [[ -d "$RUN_USER_HOME/.nvm" ]]; then
    local candidate
    candidate="$(ls -1 "$RUN_USER_HOME/.nvm/versions/node"/*/bin/npm 2>/dev/null | sort -V | tail -n 1 || true)"
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      echo "$candidate"
      return 0
    fi
  fi

  # common installers
  for npm_bin in \
    "$RUN_USER_HOME/.volta/bin/npm" \
    "$RUN_USER_HOME/.asdf/shims/npm" \
    "$RUN_USER_HOME/.npm-global/bin/npm" \
    "$RUN_USER_HOME/.local/share/pnpm/npm" \
    "$RUN_USER_HOME/.local/bin/npm"; do
    if [[ -x "$npm_bin" ]]; then
      echo "$npm_bin"
      return 0
    fi
  done

  return 1
}

NPM_BIN=""
NPM_BIN="$(resolve_npm 2>/dev/null || true)"

NPM_LOGIN_SHELL=""
NPM_LOGIN_OK=""
if command -v zsh >/dev/null 2>&1; then
  NPM_LOGIN_OK="$(zsh -lc 'command -v npm 2>/dev/null || true' 2>/dev/null || true)"
  if [[ -n "$NPM_LOGIN_OK" ]]; then
    NPM_LOGIN_SHELL="zsh"
  fi
fi
if [[ -z "$NPM_LOGIN_OK" ]]; then
  NPM_LOGIN_OK="$(bash -lc 'command -v npm 2>/dev/null || true' 2>/dev/null || true)"
  if [[ -n "$NPM_LOGIN_OK" ]]; then
    NPM_LOGIN_SHELL="bash"
  fi
fi

if [[ -z "$NPM_BIN" ]]; then
  if [[ -n "$NPM_LOGIN_OK" ]]; then
    echo "[WARN] npm not in current PATH, using login shell ($NPM_LOGIN_SHELL) to start frontend"
  else
    echo "[ERROR] npm not found. Frontend dev server cannot start."
    echo "PATH=$PATH"
    echo
    echo "Fix options:"
    echo "  1) Open a new terminal (login shell) and run: cd frontend && npm run dev"
    echo "  2) If you use nvm, ensure it is initialized in ~/.profile or ~/.bashrc"
    echo "  3) Or install Node.js system-wide (apt/snap)"
    exit 1
  fi
fi

if [[ "${SKIP_FRONTEND}" == "1" ]]; then
  echo "[INFO] SKIP_FRONTEND=1, skip starting frontend dev server"
  exit 0
fi

cd frontend

if [[ ! -d node_modules ]]; then
  echo "[INFO] Installing frontend dependencies..."
  if [[ -n "$NPM_BIN" ]]; then
    "$NPM_BIN" install
  else
    if [[ "$NPM_LOGIN_SHELL" == "zsh" ]]; then
      zsh -lc "cd '$SCRIPT_DIR/frontend' && npm install"
    else
      bash -lc "cd '$SCRIPT_DIR/frontend' && npm install"
    fi
  fi
fi

echo
echo "========================================"
echo "  Backend services ready!"
echo "========================================"
echo
echo "Frontend Dev: http://localhost:3000/"
echo "Backend API:  http://localhost:8000/api/"
echo "API Docs:     http://localhost:8000/api/docs/"
echo

open_url "http://localhost:3000/"

if [[ -n "$NPM_BIN" ]]; then
  "$NPM_BIN" run dev
else
  if [[ "$NPM_LOGIN_SHELL" == "zsh" ]]; then
    zsh -lc "cd '$SCRIPT_DIR/frontend' && npm run dev"
  else
    bash -lc "cd '$SCRIPT_DIR/frontend' && npm run dev"
  fi
fi

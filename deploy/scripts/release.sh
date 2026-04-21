#!/usr/bin/env bash
set -euo pipefail

# TM Assistant 发布脚本（模板）
# 用法：
#   bash deploy/scripts/release.sh                # 默认发布当前分支最新提交
#   bash deploy/scripts/release.sh <git-ref>      # 发布指定分支/Tag/Commit

PROJECT_DIR="/opt/tm-assistant-monorepo"
VENV_DIR="${PROJECT_DIR}/.venv"
TARGET_REF="${1:-}"
SERVICES=("api-gateway" "assistant-core" "connector-service" "job-worker")

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

ensure_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

health_check() {
  local retries=20
  local delay=2

  local urls=(
    "http://127.0.0.1:18000/api/v1/tm/health"
    "http://127.0.0.1:18001/health"
    "http://127.0.0.1:18002/health"
  )

  for url in "${urls[@]}"; do
    local ok=0
    for _ in $(seq 1 "${retries}"); do
      if curl -fsS "${url}" >/dev/null; then
        ok=1
        break
      fi
      sleep "${delay}"
    done
    if [[ "${ok}" -ne 1 ]]; then
      echo "Health check failed: ${url}"
      return 1
    fi
  done
}

main() {
  ensure_command git
  ensure_command python3
  ensure_command systemctl
  ensure_command curl

  log "Start release..."
  cd "${PROJECT_DIR}"

  # 记录当前版本，便于回滚
  PREV_COMMIT="$(git rev-parse HEAD)"
  log "Current commit: ${PREV_COMMIT}"

  log "Fetch latest code"
  git fetch --all --tags

  if [[ -n "${TARGET_REF}" ]]; then
    log "Checkout target ref: ${TARGET_REF}"
    git checkout "${TARGET_REF}"
  fi

  log "Pull latest changes"
  git pull --rebase

  NEW_COMMIT="$(git rev-parse HEAD)"
  log "New commit: ${NEW_COMMIT}"

  if [[ ! -d "${VENV_DIR}" ]]; then
    log "Create virtual environment"
    python3 -m venv "${VENV_DIR}"
  fi

  log "Upgrade pip"
  "${VENV_DIR}/bin/pip" install -U pip

  log "Install dependencies"
  for svc in "${SERVICES[@]}"; do
    "${VENV_DIR}/bin/pip" install -r "${PROJECT_DIR}/${svc}/requirements.txt"
  done

  log "Restart services"
  systemctl daemon-reload
  systemctl restart api-gateway assistant-core connector-service job-worker

  log "Run health checks"
  health_check

  log "Release success: ${NEW_COMMIT}"
  log "Previous commit: ${PREV_COMMIT}"
}

main "$@"

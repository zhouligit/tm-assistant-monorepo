#!/usr/bin/env bash
set -euo pipefail

# TM Assistant 回滚脚本（模板）
# 用法：
#   bash deploy/scripts/rollback.sh <git-ref>
# 示例：
#   bash deploy/scripts/rollback.sh HEAD~1
#   bash deploy/scripts/rollback.sh v0.1.2

PROJECT_DIR="/opt/tm-assistant-monorepo"
VENV_DIR="${PROJECT_DIR}/.venv"
TARGET_REF="${1:-}"
SERVICES=("api-gateway" "assistant-core" "connector-service" "job-worker")

if [[ -z "${TARGET_REF}" ]]; then
  echo "Usage: bash deploy/scripts/rollback.sh <git-ref>"
  exit 1
fi

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

health_check() {
  local urls=(
    "http://127.0.0.1:18000/api/v1/tm/health"
    "http://127.0.0.1:18001/health"
    "http://127.0.0.1:18002/health"
  )
  for url in "${urls[@]}"; do
    curl -fsS "${url}" >/dev/null
  done
}

main() {
  log "Rollback to ${TARGET_REF}"
  cd "${PROJECT_DIR}"

  git fetch --all --tags
  git checkout "${TARGET_REF}"

  "${VENV_DIR}/bin/pip" install -U pip
  for svc in "${SERVICES[@]}"; do
    "${VENV_DIR}/bin/pip" install -r "${PROJECT_DIR}/${svc}/requirements.txt"
  done

  systemctl daemon-reload
  systemctl restart api-gateway assistant-core connector-service job-worker

  health_check
  log "Rollback success"
}

main "$@"

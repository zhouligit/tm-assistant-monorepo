#!/usr/bin/env bash
set -euo pipefail

# 教育机构场景演练脚本（MVP）
# 1) 登录
# 2) 创建会话
# 3) 发送高匹配问题（预期自动答疑）
# 4) 发送低匹配问题（预期触发 low_confidence handoff）
# 5) 查看 handoff 队列

BASE_URL="${BASE_URL:-http://127.0.0.1}"
EMAIL="${EMAIL:-admin@demo.com}"
PASSWORD="${PASSWORD:-123456}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

json_field() {
  local payload="$1"
  local expr="$2"
  python3 - "$payload" "$expr" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
expr = sys.argv[2].split(".")
cur = payload
for x in expr:
    if isinstance(cur, dict):
        cur = cur.get(x)
    else:
        cur = None
if cur is None:
    print("")
else:
    print(cur)
PY
}

require_command curl
require_command python3

log "Login as ${EMAIL}"
LOGIN_RES="$(curl -sS -X POST "${BASE_URL}/api/v1/tm/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")"

ACCESS_TOKEN="$(json_field "${LOGIN_RES}" "data.access_token")"
if [[ -z "${ACCESS_TOKEN}" ]]; then
  echo "Login failed: ${LOGIN_RES}"
  exit 1
fi
log "Login success"

log "Create chat session"
CREATE_SESSION_RES="$(curl -sS -X POST "${BASE_URL}/api/v1/tm/chat/sessions" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"channel":"web_widget","visitor_id":"edu_demo_visitor"}')"
SESSION_ID="$(json_field "${CREATE_SESSION_RES}" "data.session_id")"
if [[ -z "${SESSION_ID}" ]]; then
  echo "Create session failed: ${CREATE_SESSION_RES}"
  exit 1
fi
log "Session created: ${SESSION_ID}"

log "Send high-match question"
HIGH_Q_RES="$(curl -sS -X POST "${BASE_URL}/api/v1/tm/chat/sessions/${SESSION_ID}/messages" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"role":"user","content":"课程支持分期吗？学费是多少？"}')"
echo "${HIGH_Q_RES}"

log "Send low-match question"
LOW_Q_RES="$(curl -sS -X POST "${BASE_URL}/api/v1/tm/chat/sessions/${SESSION_ID}/messages" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"role":"user","content":"你们班主任是否会每天晚上直播答疑到23点？"}')"
echo "${LOW_Q_RES}"

log "Check handoff queue"
QUEUE_RES="$(curl -sS "${BASE_URL}/api/v1/tm/handoff/queue" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")"
echo "${QUEUE_RES}"

log "Done"

#!/usr/bin/env bash
#
# Probe gateway / assistant-core / connector health URLs; fail on bad HTTP or slow latency.
# Intended for cron + alerting (non-zero exit).
#
# Env:
#   TM_HEALTH_GATEWAY    default http://127.0.0.1:18000
#   TM_HEALTH_CORE       default http://127.0.0.1:18001
#   TM_HEALTH_CONNECTOR  default http://127.0.0.1:18002
#   TM_HEALTH_MAX_SECONDS  default 3  (max allowed total time per curl)
#
# Usage:
#   bash deploy/scripts/check-critical-endpoints.sh
#   echo $?   # 0 = all ok
#
set -euo pipefail

TM_HEALTH_GATEWAY="${TM_HEALTH_GATEWAY:-http://127.0.0.1:18000}"
TM_HEALTH_CORE="${TM_HEALTH_CORE:-http://127.0.0.1:18001}"
TM_HEALTH_CONNECTOR="${TM_HEALTH_CONNECTOR:-http://127.0.0.1:18002}"
TM_HEALTH_MAX_SECONDS="${TM_HEALTH_MAX_SECONDS:-3}"

urls=(
  "${TM_HEALTH_GATEWAY}/api/v1/tm/health"
  "${TM_HEALTH_CORE}/health"
  "${TM_HEALTH_CONNECTOR}/health"
)

failed=0
max_ms="$(awk -v s="$TM_HEALTH_MAX_SECONDS" 'BEGIN { printf "%.0f", s * 1000 }')"

for url in "${urls[@]}"; do
  if ! out="$(curl -sS -o /dev/null -w "%{http_code} %{time_total}" \
      -f --max-time "$((TM_HEALTH_MAX_SECONDS + 2))" "$url" 2>&1)"; then
    echo "check-critical-endpoints: FAIL $url $out"
    failed=1
    continue
  fi
  code="${out%% *}"
  ttot="${out##* }"
  ms="$(awk -v x="$ttot" 'BEGIN { printf "%.0f", x * 1000 }')"
  if [[ "$code" != "200" ]]; then
    echo "check-critical-endpoints: FAIL $url HTTP $code"
    failed=1
    continue
  fi
  if [[ "$ms" -gt "$max_ms" ]]; then
    echo "check-critical-endpoints: SLOW $url ${ms}ms (max ${max_ms}ms)"
    failed=1
    continue
  fi
  echo "check-critical-endpoints: OK $url ${ms}ms"
done

exit "$failed"

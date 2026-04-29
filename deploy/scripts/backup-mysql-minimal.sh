#!/usr/bin/env bash
#
# Minimal MySQL logical backup: mysqldump | gzip, prune by age.
# Reads MYSQL_DSN from ENV_FILE (same format as app: mysql+pymysql://user:pass@host:port/db).
#
# Usage:
#   ENV_FILE=/opt/tm-assistant-monorepo/.env bash deploy/scripts/backup-mysql-minimal.sh
# Cron (daily 02:15):
#   15 2 * * * ENV_FILE=/opt/tm-assistant-monorepo/.env /opt/tm-assistant-monorepo/deploy/scripts/backup-mysql-minimal.sh >>/var/log/tm-mysql-backup.log 2>&1
#
set -euo pipefail

ENV_FILE="${ENV_FILE:-/opt/tm-assistant-monorepo/.env}"
BACKUP_DIR="${BACKUP_DIR:-/opt/backups/tm-assistant}"
KEEP_DAYS="${KEEP_DAYS:-7}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "backup-mysql-minimal: missing ENV_FILE: $ENV_FILE" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

eval "$(ENV_FILE="$ENV_FILE" python3 <<'PY'
import os, re, sys
from urllib.parse import unquote

path = os.environ["ENV_FILE"]
kv = {}
with open(path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        kv[k.strip()] = v.strip().strip('"').strip("'")

dsn = kv.get("MYSQL_DSN", os.environ.get("MYSQL_DSN", ""))
if not dsn:
    print("backup-mysql-minimal: MYSQL_DSN not set", file=sys.stderr)
    sys.exit(1)

m = re.match(r"mysql\+pymysql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/([^?]+)", dsn)
if not m:
    print("backup-mysql-minimal: could not parse MYSQL_DSN", file=sys.stderr)
    sys.exit(1)

user, pw, host, port, db = m.group(1), unquote(m.group(2)), m.group(3), m.group(4) or "3306", m.group(5)
for name, val in [
    ("MYSQL_USER", user),
    ("MYSQL_PWD", pw),
    ("MYSQL_HOST", host),
    ("MYSQL_PORT", port),
    ("MYSQL_DB", db),
]:
    esc = val.replace("'", "'\"'\"'")
    print(f"{name}='{esc}'")
PY
)"

TS="$(date +%Y%m%d-%H%M%S)"
OUT="${BACKUP_DIR}/tm_assistant-${TS}.sql.gz"

TMP="$(mktemp)"
chmod 600 "$TMP"
trap 'rm -f "$TMP"' EXIT

cat >"$TMP" <<EOF
[client]
user=${MYSQL_USER}
password=${MYSQL_PWD}
host=${MYSQL_HOST}
port=${MYSQL_PORT}
EOF

mysqldump --defaults-extra-file="$TMP" --single-transaction --quick --routines=false \
  "$MYSQL_DB" | gzip -c >"$OUT"

echo "backup-mysql-minimal: wrote $OUT"

find "$BACKUP_DIR" -maxdepth 1 -name 'tm_assistant-*.sql.gz' -mtime "+${KEEP_DAYS}" -delete 2>/dev/null || true

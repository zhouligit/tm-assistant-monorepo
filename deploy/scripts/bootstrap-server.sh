#!/usr/bin/env bash
set -euo pipefail

# One-shot bootstrap for Ubuntu 24.04 (HTTP only).
# It installs dependencies, prepares /opt project, writes .env, installs Python deps,
# creates systemd services, and configures Nginx path routing.
#
# Usage:
#   DOMAIN=example.com REPO_URL=https://github.com/you/tm-assistant-monorepo.git bash deploy/scripts/bootstrap-server.sh

DOMAIN="${DOMAIN:-}"
REPO_URL="${REPO_URL:-}"
APP_DIR="${APP_DIR:-/opt/tm-assistant-monorepo}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-123456}"
REDIS_PASSWORD="${REDIS_PASSWORD:-123456}"
API_GATEWAY_PORT="${API_GATEWAY_PORT:-18000}"
ASSISTANT_CORE_PORT="${ASSISTANT_CORE_PORT:-18001}"
CONNECTOR_SERVICE_PORT="${CONNECTOR_SERVICE_PORT:-18002}"

if [[ -z "${DOMAIN}" || -z "${REPO_URL}" ]]; then
  echo "Missing required env: DOMAIN and REPO_URL"
  echo "Example:"
  echo "  DOMAIN=your-domain.com REPO_URL=https://github.com/yourname/tm-assistant-monorepo.git bash deploy/scripts/bootstrap-server.sh"
  exit 1
fi

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

write_service_file() {
  local service_name="$1"
  local workdir="$2"
  local execstart="$3"

  cat >"/etc/systemd/system/${service_name}.service" <<EOF
[Unit]
Description=${service_name}
After=network.target

[Service]
WorkingDirectory=${workdir}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${execstart}
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF
}

log "Install base packages"
apt update
apt install -y git curl nginx mysql-server redis-server python3.11 python3.11-venv python3-pip
systemctl enable nginx mysql redis
systemctl restart nginx mysql redis

log "Set MySQL and Redis passwords"
mysql -uroot -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${MYSQL_PASSWORD}'; FLUSH PRIVILEGES;"
sed -i "s/^#\? *requirepass .*/requirepass ${REDIS_PASSWORD}/" /etc/redis/redis.conf
systemctl restart redis

log "Prepare project directory"
mkdir -p /opt
if [[ -d "${APP_DIR}/.git" ]]; then
  git -C "${APP_DIR}" fetch --all --tags
  git -C "${APP_DIR}" pull --rebase
else
  git clone "${REPO_URL}" "${APP_DIR}"
fi

log "Write .env from template"
cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
sed -i "s#^MYSQL_DSN=.*#MYSQL_DSN=mysql+pymysql://root:${MYSQL_PASSWORD}@127.0.0.1:3306/tm_assistant#" "${APP_DIR}/.env"
sed -i "s#^REDIS_URL=.*#REDIS_URL=redis://:${REDIS_PASSWORD}@127.0.0.1:6379/0#" "${APP_DIR}/.env"
sed -i "s#^API_GATEWAY_PORT=.*#API_GATEWAY_PORT=${API_GATEWAY_PORT}#" "${APP_DIR}/.env"
sed -i "s#^ASSISTANT_CORE_PORT=.*#ASSISTANT_CORE_PORT=${ASSISTANT_CORE_PORT}#" "${APP_DIR}/.env"
sed -i "s#^CONNECTOR_SERVICE_PORT=.*#CONNECTOR_SERVICE_PORT=${CONNECTOR_SERVICE_PORT}#" "${APP_DIR}/.env"
if grep -q '^JWT_SECRET=' "${APP_DIR}/.env"; then
  sed -i "s#^JWT_SECRET=.*#JWT_SECRET=$(openssl rand -hex 32)#" "${APP_DIR}/.env"
else
  echo "JWT_SECRET=$(openssl rand -hex 32)" >> "${APP_DIR}/.env"
fi

log "Install Python dependencies"
for svc in api-gateway assistant-core connector-service; do
  python3.11 -m venv "${APP_DIR}/${svc}/.venv"
  "${APP_DIR}/${svc}/.venv/bin/pip" install -U pip
  "${APP_DIR}/${svc}/.venv/bin/pip" install -r "${APP_DIR}/${svc}/requirements.txt"
done

log "Create systemd services"
write_service_file \
  "tm-api-gateway" \
  "${APP_DIR}/api-gateway" \
  "${APP_DIR}/api-gateway/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${API_GATEWAY_PORT}"

write_service_file \
  "tm-assistant-core" \
  "${APP_DIR}/assistant-core" \
  "${APP_DIR}/assistant-core/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${ASSISTANT_CORE_PORT}"

write_service_file \
  "tm-connector-service" \
  "${APP_DIR}/connector-service" \
  "${APP_DIR}/connector-service/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${CONNECTOR_SERVICE_PORT}"

systemctl daemon-reload
systemctl enable tm-api-gateway tm-assistant-core tm-connector-service
systemctl restart tm-api-gateway tm-assistant-core tm-connector-service

log "Write Nginx site config"
cat > /etc/nginx/sites-available/tm-assistant.conf <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    location /api/v1/tm/ {
        proxy_pass http://127.0.0.1:${API_GATEWAY_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/tm-assistant.conf /etc/nginx/sites-enabled/tm-assistant.conf
nginx -t
systemctl reload nginx

log "Quick health checks"
curl -fsS "http://127.0.0.1:${API_GATEWAY_PORT}/api/v1/tm/health" >/dev/null
curl -fsS "http://${DOMAIN}/api/v1/tm/health" >/dev/null

log "Bootstrap done."
echo "Next:"
echo "  1) Import SQL migration/seed files on server"
echo "  2) Run Certbot for HTTPS"

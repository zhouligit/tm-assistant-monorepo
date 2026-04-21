# 从0到可访问的最短命令清单（HTTP）

适用场景：Ubuntu 24.04、`root` 用户、部署目录 `/opt/tm-assistant-monorepo`、对外访问使用“域名 + path”。

> 说明：本清单先完成 HTTP 可访问。HTTPS 见 `docs/deploy-https-certbot-shortlist.md`。

## 0) 先设置变量

```bash
export DOMAIN="your-domain.com"
export REPO_URL="https://github.com/yourname/tm-assistant-monorepo.git"
export APP_DIR="/opt/tm-assistant-monorepo"
```

## 1) 安装基础软件

```bash
apt update && apt install -y git curl nginx mysql-server redis-server python3.11 python3.11-venv python3-pip
systemctl enable nginx mysql redis
systemctl start nginx mysql redis
```

## 2) 配置 MySQL / Redis 密码（当前临时值）

```bash
mysql -uroot -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '123456'; FLUSH PRIVILEGES;"
sed -i 's/^#\? *requirepass .*/requirepass 123456/' /etc/redis/redis.conf
systemctl restart redis
```

## 3) 拉代码到 `/opt`

```bash
mkdir -p /opt && cd /opt
git clone "$REPO_URL" tm-assistant-monorepo
cd "$APP_DIR"
```

## 4) 配置环境变量

```bash
cp .env.example .env
sed -i 's#^MYSQL_DSN=.*#MYSQL_DSN=mysql+pymysql://root:123456@127.0.0.1:3306/tm_assistant#' .env
sed -i 's#^REDIS_URL=.*#REDIS_URL=redis://:123456@127.0.0.1:6379/0#' .env
sed -i 's#^API_GATEWAY_PORT=.*#API_GATEWAY_PORT=18000#' .env
sed -i 's#^ASSISTANT_CORE_PORT=.*#ASSISTANT_CORE_PORT=18001#' .env
sed -i 's#^CONNECTOR_SERVICE_PORT=.*#CONNECTOR_SERVICE_PORT=18002#' .env
grep -q '^JWT_SECRET=' .env && sed -i "s#^JWT_SECRET=.*#JWT_SECRET=$(openssl rand -hex 32)#" .env || echo "JWT_SECRET=$(openssl rand -hex 32)" >> .env
```

## 5) 导入数据库

> 建议先把 SQL 上传到服务器（例如 `/opt/sql/`）。

```bash
mkdir -p /opt/sql
# 假设已上传：
# /opt/sql/企业知识助手-mysql-migration-v1.1.sql
# /opt/sql/企业知识助手-mysql-seed-v1.1.sql

mysql -h 127.0.0.1 -P 3306 -u root -p123456 < "/opt/sql/企业知识助手-mysql-migration-v1.1.sql"
mysql -h 127.0.0.1 -P 3306 -u root -p123456 < "/opt/sql/企业知识助手-mysql-seed-v1.1.sql"
```

## 6) 安装后端依赖（3个 HTTP 服务）

```bash
cd "$APP_DIR/api-gateway" && python3.11 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -r requirements.txt
cd "$APP_DIR/assistant-core" && python3.11 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -r requirements.txt
cd "$APP_DIR/connector-service" && python3.11 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -r requirements.txt
```

## 7) 创建 systemd 服务（最小可用）

```bash
cat >/etc/systemd/system/tm-api-gateway.service <<'EOF'
[Unit]
Description=tm api-gateway
After=network.target

[Service]
WorkingDirectory=/opt/tm-assistant-monorepo/api-gateway
EnvironmentFile=/opt/tm-assistant-monorepo/.env
ExecStart=/opt/tm-assistant-monorepo/api-gateway/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 18000
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/tm-assistant-core.service <<'EOF'
[Unit]
Description=tm assistant-core
After=network.target

[Service]
WorkingDirectory=/opt/tm-assistant-monorepo/assistant-core
EnvironmentFile=/opt/tm-assistant-monorepo/.env
ExecStart=/opt/tm-assistant-monorepo/assistant-core/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 18001
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/tm-connector-service.service <<'EOF'
[Unit]
Description=tm connector-service
After=network.target

[Service]
WorkingDirectory=/opt/tm-assistant-monorepo/connector-service
EnvironmentFile=/opt/tm-assistant-monorepo/.env
ExecStart=/opt/tm-assistant-monorepo/connector-service/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 18002
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable tm-api-gateway tm-assistant-core tm-connector-service
systemctl restart tm-api-gateway tm-assistant-core tm-connector-service
```

## 8) 配置 Nginx（域名 + path）

```bash
cat >/etc/nginx/sites-available/tm-assistant.conf <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    location /api/v1/tm/ {
        proxy_pass http://127.0.0.1:18000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/tm-assistant.conf /etc/nginx/sites-enabled/tm-assistant.conf
nginx -t && systemctl reload nginx
```

## 9) 健康检查

```bash
curl -i http://127.0.0.1:18000/health
curl -i "http://${DOMAIN}/api/v1/tm/health"
systemctl --no-pager --full status tm-api-gateway tm-assistant-core tm-connector-service
```

## 10) 前端接入约定
- 前端 API Base URL：`https://<你的域名>/api/v1/tm`（或 HTTP 阶段先 `http://`）
- 不要在前端暴露 `:18000/:18001/:18002` 端口。

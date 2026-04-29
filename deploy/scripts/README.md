# 部署脚本说明

目录：`deploy/scripts`

## 1) 发布脚本
- 文件：`release.sh`
- 功能：
  - 拉取代码
  - （可选）切换到指定 git ref
  - 安装依赖
  - 重启 systemd 服务
  - 健康检查

用法：

```bash
bash deploy/scripts/release.sh
bash deploy/scripts/release.sh <git-ref>
```

## 2) 回滚脚本
- 文件：`rollback.sh`
- 功能：
  - 切换到指定 git ref
  - 安装依赖
  - 重启 systemd 服务
  - 健康检查

用法：

```bash
bash deploy/scripts/rollback.sh <git-ref>
```

## 3) 注意事项
- 脚本默认路径：
  - 项目目录：`/opt/tm-assistant-monorepo`
  - 虚拟环境：`/opt/tm-assistant-monorepo/.venv`
- 依赖服务：
  - `api-gateway`
  - `assistant-core`
  - `connector-service`
  - `job-worker`
- 执行前请确认：
  - systemd unit 已安装并可用
  - `.env` 已配置

## 4) 一键初始化脚本（从0到HTTP可访问）
- 文件：`bootstrap-server.sh`
- 功能：
  - 安装基础软件（Nginx/MySQL/Redis/Python）
  - 拉取项目到 `/opt/tm-assistant-monorepo`
  - 生成 `.env`（含随机 `JWT_SECRET`）
  - 安装后端依赖并创建 systemd 服务
  - 配置 Nginx（`/api/v1/tm/*` 路由到网关）
  - 执行最小健康检查

用法：

```bash
chmod +x deploy/scripts/bootstrap-server.sh
DOMAIN=your-domain.com REPO_URL=https://github.com/yourname/tm-assistant-monorepo.git bash deploy/scripts/bootstrap-server.sh
```

可选环境变量：
- `APP_DIR`（默认 `/opt/tm-assistant-monorepo`）
- `MYSQL_PASSWORD`（默认 `123456`，用于 `tm_app` 数据库用户）
- `REDIS_PASSWORD`（默认 `123456`）
- `PYTHON_BIN`（默认 `python3`）
- `API_GATEWAY_PORT`（默认 `18000`）
- `ASSISTANT_CORE_PORT`（默认 `18001`）
- `CONNECTOR_SERVICE_PORT`（默认 `18002`）

脚本执行后建议继续：
- 导入 MySQL migration + seed
- 按 `docs/deploy-https-certbot-shortlist.md` 启用 HTTPS

## 5) 运维保障（最小）

### MySQL 逻辑备份
- 文件：`backup-mysql-minimal.sh`
- 从 `ENV_FILE` 读取 `MYSQL_DSN`，`mysqldump | gzip` 到 `BACKUP_DIR`，删除超过 `KEEP_DAYS` 天的旧文件。
- 依赖：`mysqldump`（如 `apt install mysql-client`）。

```bash
ENV_FILE=/opt/tm-assistant-monorepo/.env \
BACKUP_DIR=/opt/backups/tm-assistant KEEP_DAYS=7 \
bash deploy/scripts/backup-mysql-minimal.sh
```

### 关键接口延迟 / 可用性
- 文件：`check-critical-endpoints.sh`
- 探测网关 `/api/v1/tm/health`、core `/health`、connector `/health`；任一非 200 或耗时超过 `TM_HEALTH_MAX_SECONDS`（默认 3s）则 **退出码 1**（便于 cron 告警）。

```bash
TM_HEALTH_MAX_SECONDS=3 bash deploy/scripts/check-critical-endpoints.sh
echo $?
```

### 启动时弱口令 / 占位告警
- 实现位置：`api-gateway` 进程启动时（`lifespan`）扫描环境变量：若 `MYSQL_DSN` 密码为已知弱口令、`REDIS_URL` 含默认 redis 密码、`JWT_SECRET` 过短或为占位符，则向日志输出 **WARNING**（便于 `journalctl` / 外部采集）。
- 可选：在 `.env` 中设置 `TM_WEAK_SECRET_MARKERS`（逗号分隔）扩展弱口令名单。
- 本地开发若不想刷屏，可设 `TM_SKIP_WEAK_CONFIG_CHECK=true`（**勿用于生产**）。

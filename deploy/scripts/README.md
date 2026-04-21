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
- `MYSQL_PASSWORD`（默认 `123456`）
- `REDIS_PASSWORD`（默认 `123456`）
- `PYTHON_BIN`（默认 `python3`）
- `API_GATEWAY_PORT`（默认 `18000`）
- `ASSISTANT_CORE_PORT`（默认 `18001`）
- `CONNECTOR_SERVICE_PORT`（默认 `18002`）

脚本执行后建议继续：
- 导入 MySQL migration + seed
- 按 `docs/deploy-https-certbot-shortlist.md` 启用 HTTPS

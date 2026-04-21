# Ubuntu 24.04 部署约定（当前阶段）

## 1) 主机与路径
- OS: Ubuntu 24.04
- User: `root`（临时）
- Project Path: `/opt/tm-assistant-monorepo`

## 2) 端口约束
- 已占用：`8000`, `8001`
- 本项目使用：
  - `api-gateway`: `18000`
  - `assistant-core`: `18001`
  - `connector-service`: `18002`
  - `console-web`: `3000`（可仅内网访问）
  - `chat-widget`: 打包静态资源，不要求常驻端口

## 2.1 外部访问规范（重要）
- 外部（前端/第三方）统一通过：`域名 + path`
- 不直接暴露端口给外部调用
- 建议映射：
  - `/api/v1/tm/*` -> `127.0.0.1:18000`
  - `/api/v1/tm-core/*` -> `127.0.0.1:18001`（建议仅内网）
  - `/api/v1/tm-connector/*` -> `127.0.0.1:18002`（建议仅内网）
- Nginx示例见：`deploy/nginx/tm-assistant.conf.example`

## 2.2 安全收敛建议（推荐）
- 对 `/api/v1/tm-core/*`、`/api/v1/tm-connector/*` 默认拒绝公网访问。
- 仅放行：
  - `127.0.0.1`
  - 私有网段（10/8, 172.16/12, 192.168/16）
  - 必要的办公网出口IP白名单
- 这样可以保证：
  - 外部只经由 `/api/v1/tm/*` 访问
  - 内部服务路径仅用于运维/联调

## 2.3 HTTPS 建议（生产）
- 推荐使用 `443 + TLS`，并将 `80` 全量跳转到 `https`
- 模板文件：
  - HTTP版：`deploy/nginx/tm-assistant.conf.example`
  - HTTPS版：`deploy/nginx/tm-assistant.https.conf.example`
- 证书建议：Let's Encrypt（Certbot）
- 启用步骤（示意）：
  1. 安装 certbot 并申请证书
  2. 将 HTTPS 模板中的 `server_name` 和证书路径替换为实际值
  3. `nginx -t` 校验
  4. `systemctl reload nginx` 热更新

## 3) 默认凭据（仅开发期）
- MySQL
  - user: `root`
  - password: `123456`
- Redis
  - password: `123456`（如果启用 requirepass）

> 说明：你已确认后续会手动修改密码。上线前必须完成。

## 4) 建议环境变量（示例）
```bash
APP_ENV=prod
MYSQL_DSN=mysql+pymysql://root:123456@127.0.0.1:3306/tm_assistant
REDIS_URL=redis://:123456@127.0.0.1:6379/0
JWT_SECRET=replace_me_in_production
OPENAI_API_KEY=replace_me
API_GATEWAY_PORT=18000
ASSISTANT_CORE_PORT=18001
CONNECTOR_SERVICE_PORT=18002
# 前端对外统一走域名，不带端口
VITE_API_BASE_URL=https://your-domain.com
```

## 5) 首次部署建议流程
1. `mkdir -p /opt/tm-assistant-monorepo`
2. 上传代码到 `/opt/tm-assistant-monorepo`
3. 安装 MySQL/Redis 并初始化密码（当前临时 `123456`）
4. 导入 migration 与 seed SQL
5. 启动后端服务（18000/18001/18002）
6. 前端构建并交由 Nginx 托管静态文件
7. 参考 `deploy/ubuntu-nginx-certbot-quickstart.md` 完成 HTTPS 与站点启用
8. 参考 `deploy/systemd/systemd-quickstart.md` 完成后端服务托管与开机自启
9. 参考 `deploy/scripts/README.md` 使用发布与回滚脚本完成日常上线
10. 每次发布前后执行 `deploy/checklist-go-live.md`，确保上线质量


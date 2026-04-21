# TM Assistant Monorepo

企业知识助手（客服/售前）MVP 代码仓目录（单仓多服务）。

## 技术栈约定
- 后端：Python 3.11 + FastAPI
- 前端：TypeScript + React + Vite
- 数据库：MySQL 8.0
- 缓存/队列：Redis

## 目录结构
- `api-gateway`：API统一入口，鉴权、限流、租户注入、路由聚合
- `assistant-core`：核心业务，知识检索、问答编排、会话、转人工
- `connector-service`：飞书/企微/webhook 渠道连接器
- `job-worker`：异步任务（导入、切块、向量化、报表聚合）
- `console-web`：管理后台（知识源、接管队列、看板）
- `chat-widget`：可嵌入客户网站的聊天组件（SDK）

## 端口规划（本地开发）
- `api-gateway`: `:18000`
- `assistant-core`: `:18001`
- `connector-service`: `:18002`
- `job-worker`: worker进程（无固定HTTP端口，可选监控端口）
- `console-web`: `:3000`
- `chat-widget`: `:3001`（本地调试页）

## 环境变量分层
- 根目录统一管理共享变量（后续可用 `.env.example`）
- 每个服务保留自身 `.env.example`
- 关键变量：
  - `MYSQL_DSN`
  - `REDIS_URL`
  - `OPENAI_API_KEY`（或其他模型供应商key）
  - `JWT_SECRET`
  - `APP_ENV`
  - `API_GATEWAY_PORT`
  - `ASSISTANT_CORE_PORT`
  - `CONNECTOR_SERVICE_PORT`

## 本地初始化（脚手架阶段）
0. 基础依赖（Docker）
   - 在仓库根目录执行：`make infra-up`
   - 停止依赖：`make infra-down`
   - MySQL/Redis 默认密码均为 `123456`（开发期）
1. Python 服务
   - 每个后端目录可先创建虚拟环境并安装依赖：
   - `pip install -r requirements.txt`
2. 前端服务
   - 在 `console-web`、`chat-widget` 执行：
   - `npm install`
3. 快速启动
   - `make run-core`
   - `make run-gateway`
   - `make run-connector`
   - `make run-worker`
4. 数据库初始化
   - 执行：
   - `mysql -h 127.0.0.1 -P 3306 -u root -p123456 < "/Users/zhouli/data/code/chuangye/products/企业知识助手-mysql-migration-v1.1.sql"`
   - `mysql -h 127.0.0.1 -P 3306 -u root -p123456 < "/Users/zhouli/data/code/chuangye/products/企业知识助手-mysql-seed-v1.1.sql"`

## 远程部署约定（当前默认）
- 服务器系统：Ubuntu 24.04
- 部署用户：`root`（后续建议切换非root）
- 部署目录：`/opt/tm-assistant-monorepo`
- 端口约定：远程避免使用 `8000`、`8001`，统一使用 `18000`、`18001`、`18002`
- 外部访问约定：统一使用 `域名 + path`，不在前端暴露端口
  - 对外主入口：`/api/v1/tm/*` -> `api-gateway(18000)`
  - 可选内部路径：`/api/v1/tm-core/*` -> `assistant-core(18001)`
  - 可选内部路径：`/api/v1/tm-connector/*` -> `connector-service(18002)`
- 默认密码占位（仅开发阶段）：
  - MySQL: `123456`
  - Redis: 如需密码，暂定 `123456`
- 注意：上线前务必更换密码、收敛防火墙策略并启用最小权限账户。

## 开发顺序建议
1. 启动 MySQL / Redis
2. 跑数据库 migration + seed
3. 起 `assistant-core`（先打通核心链路）
4. 起 `api-gateway`（统一入口）
5. 起 `console-web`（先联调核心页面）
6. 起 `chat-widget`（验证客户端闭环）
7. 补 `connector-service` 和 `job-worker`

## MVP第一阶段目标
- 跑通最短闭环：
  - 知识导入 -> 问答 -> 低置信度转人工 -> 接管回复 -> 回流候选 -> 看板

## 运行与排障
- 详见：`docs/runbook.md`
- Mock/占位实现追踪：`docs/mock-tracker.md`
- 导出后30天路线图：`docs/roadmap-next-30-days.md`

## Nginx 配置模板
- 示例配置：`deploy/nginx/tm-assistant.conf.example`
- HTTPS生产模板：`deploy/nginx/tm-assistant.https.conf.example`
- 默认包含安全收敛策略：
  - `/api/v1/tm-core/*`、`/api/v1/tm-connector/*` 默认拒绝公网，仅允许内网/白名单访问
- Ubuntu 快速部署命令清单：`deploy/ubuntu-nginx-certbot-quickstart.md`

## systemd 服务模板
- `deploy/systemd/api-gateway.service.example`
- `deploy/systemd/assistant-core.service.example`
- `deploy/systemd/connector-service.service.example`
- `deploy/systemd/job-worker.service.example`
- 启用指南：`deploy/systemd/systemd-quickstart.md`

## 发布与回滚脚本
- `deploy/scripts/release.sh`
- `deploy/scripts/rollback.sh`
- 使用说明：`deploy/scripts/README.md`

## 上线检查清单
- `deploy/checklist-go-live.md`

## OpenAPI 导出
- 生成网关与核心服务的 OpenAPI 快照：
- `make export-openapi`
- 导出目录：`docs/openapi`


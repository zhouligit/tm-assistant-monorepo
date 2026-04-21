# 本地启动与排障 Runbook

适用环境：
- 本地开发：macOS（MacBook Pro）
- 远程部署：Ubuntu 24.04（见 `DEPLOYMENT-UBUNTU24.md`）

---

## 1. 一次性准备

在项目根目录执行：

```bash
cd /Users/zhouli/data/code/chuangye/products/tm-assistant-monorepo
```

检查 Docker 是否可用：

```bash
docker info
```

如果提示 `Cannot connect to the Docker daemon`，先启动 Docker Desktop，再重试。

---

## 2. 启动基础依赖（MySQL + Redis）

```bash
make infra-up
```

检查容器状态：

```bash
docker compose ps
```

健康检查（预期返回 `healthy`）：

```bash
docker inspect --format='{{json .State.Health.Status}}' tm-mysql
docker inspect --format='{{json .State.Health.Status}}' tm-redis
```

---

## 3. 初始化数据库

```bash
mysql -h 127.0.0.1 -P 3306 -u root -p123456 < "/Users/zhouli/data/code/chuangye/products/企业知识助手-mysql-migration-v1.1.sql"
mysql -h 127.0.0.1 -P 3306 -u root -p123456 < "/Users/zhouli/data/code/chuangye/products/企业知识助手-mysql-seed-v1.1.sql"
```

快速验证：

```bash
mysql -h 127.0.0.1 -P 3306 -u root -p123456 -e "USE tm_assistant; SHOW TABLES;"
```

---

## 4. 启动后端空服务

分别在不同终端启动：

```bash
make run-core
make run-gateway
make run-connector
make run-worker
```

健康检查：

```bash
curl http://127.0.0.1:18000/api/v1/tm/health
curl http://127.0.0.1:18001/health
curl http://127.0.0.1:18002/health
```

---

## 5. 启动前端空服务

```bash
cd console-web && npm install && npm run dev
cd chat-widget && npm install && npm run dev
```

---

## 6. 常见问题与处理

### 6.1 Docker daemon 未启动
现象：
- `Cannot connect to the Docker daemon at unix:///Users/.../docker.sock`

处理：
1. 启动 Docker Desktop
2. 等待状态变为 Running
3. 再执行 `make infra-up`

### 6.2 端口冲突
现象：
- `address already in use`

说明：
- 当前项目端口：`18000`、`18001`、`18002`，已避开远程 `8000`/`8001`

处理：
1. 查询占用：`lsof -i :18000`
2. 修改 `Makefile` 与 `.env.example` 端口为未占用值

### 6.3 MySQL 初始化失败
常见原因：
- 容器未就绪就执行 SQL
- 密码不一致

处理：
1. 先确认 `docker compose ps` 为 healthy
2. 确认当前默认密码为 `123456`
3. 重试 migration 再 seed

### 6.4 依赖安装失败
处理建议：
- Python：先确认 `python3 --version` 为 3.11+
- Node：建议 20+ 版本
- npm install 如失败，先执行 `npm cache verify`

---

## 7. 关闭环境

```bash
make infra-down
```

如果需要保留数据库数据，不要删除 Docker volumes。

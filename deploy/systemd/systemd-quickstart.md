# systemd 服务启用清单（Ubuntu 24.04）

适用前提：
- 项目目录：`/opt/tm-assistant-monorepo`
- Python 虚拟环境：`/opt/tm-assistant-monorepo/.venv`
- 部署用户：`root`（当前阶段）

---

## 1) 准备 `.env`

```bash
cp /opt/tm-assistant-monorepo/.env.example /opt/tm-assistant-monorepo/.env
nano /opt/tm-assistant-monorepo/.env
```

---

## 2) 安装并准备 Python 依赖（示例）

```bash
apt update
apt install -y python3 python3-venv python3-pip
python3 -m venv /opt/tm-assistant-monorepo/.venv
/opt/tm-assistant-monorepo/.venv/bin/pip install -U pip

/opt/tm-assistant-monorepo/.venv/bin/pip install -r /opt/tm-assistant-monorepo/api-gateway/requirements.txt
/opt/tm-assistant-monorepo/.venv/bin/pip install -r /opt/tm-assistant-monorepo/assistant-core/requirements.txt
/opt/tm-assistant-monorepo/.venv/bin/pip install -r /opt/tm-assistant-monorepo/connector-service/requirements.txt
/opt/tm-assistant-monorepo/.venv/bin/pip install -r /opt/tm-assistant-monorepo/job-worker/requirements.txt
```

---

## 3) 复制 service 文件到 systemd

```bash
cp /opt/tm-assistant-monorepo/deploy/systemd/api-gateway.service.example /etc/systemd/system/api-gateway.service
cp /opt/tm-assistant-monorepo/deploy/systemd/assistant-core.service.example /etc/systemd/system/assistant-core.service
cp /opt/tm-assistant-monorepo/deploy/systemd/connector-service.service.example /etc/systemd/system/connector-service.service
cp /opt/tm-assistant-monorepo/deploy/systemd/job-worker.service.example /etc/systemd/system/job-worker.service
```

---

## 4) 启用并启动

```bash
systemctl daemon-reload
systemctl enable --now api-gateway assistant-core connector-service job-worker
```

---

## 5) 状态检查

```bash
systemctl status api-gateway --no-pager
systemctl status assistant-core --no-pager
systemctl status connector-service --no-pager
systemctl status job-worker --no-pager
```

端口检查：

```bash
ss -lntp | rg "18000|18001|18002"
```

健康检查：

```bash
curl -s http://127.0.0.1:18000/api/v1/tm/health
curl -s http://127.0.0.1:18001/health
curl -s http://127.0.0.1:18002/health
```

---

## 6) 常用运维命令

```bash
systemctl restart api-gateway assistant-core connector-service job-worker
systemctl stop api-gateway assistant-core connector-service job-worker
journalctl -u api-gateway -f
journalctl -u assistant-core -f
journalctl -u connector-service -f
journalctl -u job-worker -f
```

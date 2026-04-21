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

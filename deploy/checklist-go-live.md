# Go Live Checklist（上线检查清单）

适用项目：TM Assistant  
部署环境：Ubuntu 24.04 + Nginx + systemd  
目标：降低上线事故概率，明确观察与回滚标准

---

## 1) 上线前 T-1 天检查

### 1.1 代码与配置
- [ ] 目标发布版本已确认（commit/tag）
- [ ] `.env` 已配置且无占位符（如 `replace_me`）
- [ ] 生产域名配置已确认（`VITE_API_BASE_URL=https://your-domain.com`）
- [ ] Nginx 配置文件已校验：`nginx -t`
- [ ] systemd unit 文件已存在并可用

### 1.2 依赖与资源
- [ ] MySQL 正常，连接参数正确
- [ ] Redis 正常，密码正确
- [ ] 证书有效期充足（建议 >15天）
- [ ] 服务器磁盘空间 > 20%
- [ ] 服务器内存可满足当前并发

### 1.3 安全项
- [ ] `/api/v1/tm-core/*` 与 `/api/v1/tm-connector/*` 已开启白名单/拒绝公网
- [ ] root 账号仅用于当前阶段，已规划后续最小权限迁移
- [ ] 默认密码（123456）已规划替换窗口

---

## 2) 发布窗口执行步骤（T 时刻）

### 2.1 发布前快照
- [ ] 记录当前线上 commit：`git rev-parse HEAD`
- [ ] 记录当前服务状态：
  - `systemctl status api-gateway assistant-core connector-service job-worker --no-pager`

### 2.2 执行发布
- [ ] 执行发布脚本：
  - `bash deploy/scripts/release.sh <git-ref>`
- [ ] 若不指定版本：
  - `bash deploy/scripts/release.sh`

### 2.3 即时验证（5分钟内）
- [ ] 网关健康检查通过：`/api/v1/tm/health`
- [ ] core 健康检查通过：`/health`
- [ ] connector 健康检查通过：`/health`
- [ ] 前端首页可访问（https 域名）
- [ ] 关键路径最小闭环手工跑通：
  - 新增知识源
  - handoff claim/reply/close
  - 候选 approve/reject

---

## 3) 上线后 30 分钟观察项

### 3.1 服务稳定性
- [ ] `systemctl status` 无频繁重启
- [ ] `journalctl` 无持续错误刷屏
- [ ] 5xx 无异常升高（按日志观察）

### 3.2 业务功能
- [ ] API 平均响应无明显劣化
- [ ] 控制台关键页面可用
- [ ] 数据写入正常（MySQL）

### 3.3 安全与流量
- [ ] 非白名单访问 `tm-core` 返回 403（符合预期）
- [ ] Nginx access/error 日志无异常暴增

---

## 4) 回滚触发条件（任一满足即回滚）

- [ ] 健康检查连续失败 > 3 次
- [ ] 核心闭环功能不可用且 10 分钟内无法恢复
- [ ] 5xx 错误率持续异常（相对发布前显著上升）
- [ ] 服务频繁 crash / 自动重启

---

## 5) 回滚执行步骤

1. 确认目标回滚版本（上一个稳定 tag/commit）
2. 执行回滚脚本：
   - `bash deploy/scripts/rollback.sh <git-ref>`
3. 重跑健康检查：
   - `/api/v1/tm/health`
   - `http://127.0.0.1:18001/health`
   - `http://127.0.0.1:18002/health`
4. 验证关键业务闭环
5. 记录事故与根因，形成复盘

---

## 6) 发布后记录模板（建议）

- 发布人：
- 发布时间：
- 发布版本（commit/tag）：
- 回滚版本（如有）：
- 变更范围：
- 结果（成功/失败）：
- 主要问题：
- 后续动作：

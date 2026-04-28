# 教育机构试点场景落地（MVP）

本文把教育机构试点按 4 个步骤落地为可执行方案：
1. 先选一个试点业务线
2. 接咨询入口（MVP 先人工模拟）
3. 喂第一批知识（首批课程 FAQ）
4. 跑“自动答疑 + 人工兜底”闭环

## 1) 先选一个试点业务线

建议先选一条咨询量高、问题重复度高的线：

- 业务线：成人职业教育（数据分析就业班）
- 试点目标：
  - 覆盖前 20 个高频售前问题
  - 将人工重复回答工作量降低
  - 跑通转人工和知识回流闭环

试点用户画像：
- 在职转岗人群
- 关注课程价格、上课方式、就业服务、退费规则

## 2) 接咨询入口（当前 MVP 可先人工模拟）

当前 MVP 未接入真实渠道时，采用 API 人工模拟入口：

- 创建会话：`POST /api/v1/tm/chat/sessions`
- 发送用户问题：`POST /api/v1/tm/chat/sessions/{session_id}/messages`
- 查看会话：`GET /api/v1/tm/chat/sessions/{session_id}`

你可以先用仓库脚本执行模拟流程：

```bash
bash scripts/demo_education_flow.sh
```

## 3) 喂第一批知识（最关键）

本仓库已提供教育机构首批知识 SQL：

- 文件：`sql/init/education-pilot-seed.sql`
- 内容：
  - 新增“数据分析就业班 FAQ”知识源
  - 新增课程相关知识块（价格、排期、分期、试听、退费、就业服务）

执行方式（服务器）：

```bash
mysql -h 127.0.0.1 -P 3306 -u tm_app -p123456 tm_assistant < "/opt/tm-assistant-monorepo/sql/init/education-pilot-seed.sql"
```

## 4) 跑“自动答疑 + 人工兜底”

当前系统已支持：

- 自动答疑：按知识块检索生成回答，返回 `confidence` 与 `citations`
- 自动兜底：低置信度时自动触发 handoff（`reason=low_confidence`）
- 人工处理：在 `Handoff Queue` 认领、回复、关闭
- 知识回流：回复时可勾选候选，进入 `KB Candidates` 审核

建议演练路径：

1. 发送高匹配问题（例如“课程支持分期吗”）  
   - 预期：自动回答，`confidence` 较高
2. 发送低匹配问题（例如“你们班主任会不会直播答疑到深夜”）  
   - 预期：进入 handoff 队列
3. 人工认领并回复，勾选回流候选  
   - 预期：在候选池可见，支持审核通过/驳回

---

## 验收标准（试点通过）

- 自动答疑可覆盖高频问题并返回引用
- 低置信度问题可自动转人工，不丢单
- 人工回复可进入候选并被审核回流
- 前台演示路径可在 `http://<host>/console/` 完整走通

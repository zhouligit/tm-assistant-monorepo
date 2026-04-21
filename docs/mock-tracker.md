# Mock/占位实现清单（待逐项替换）

用于记录当前 MVP 中仍为 mock、占位或演示实现的模块，后续按优先级逐项替换为生产可用实现。

## 说明
- 状态定义：
  - `pending`：尚未开始替换
  - `in_progress`：替换中
  - `done`：已替换完成
- 优先级定义：
  - `P0`：影响核心业务闭环或上线安全
  - `P1`：影响关键体验或运营能力
  - `P2`：次要功能或增强项

## 清单

| 模块 | 位置 | 当前状态 | 影响 | 优先级 | 状态 | 下一步 |
| --- | --- | --- | --- | --- | --- | --- |
| 鉴权用户体系 | `api-gateway/app/auth.py` | 使用 `DEMO_ADMIN_EMAIL/DEMO_ADMIN_PASSWORD` 进行硬编码账号校验 | 无法支持真实多用户登录与权限管理 | P0 | pending | 接入 `users` 表与密码哈希校验 |
| 刷新令牌机制 | `api-gateway/app/routers/auth.py` | `refresh_token` 返回空字符串 | 无法安全续期登录态 | P0 | pending | 增加 refresh token 颁发、存储、轮换与撤销 |
| 聊天回复引擎 | `assistant-core/app/routers/chat.py` | 助手回复为固定文案（非真实检索/模型） | 问答效果不可用，无法承接真实场景 | P0 | pending | 接入检索链路 + LLM 生成 + 引用返回 |
| 检索调试接口 | `assistant-core/app/routers/knowledge.py` | `/chunks`、`/retrieval/debug` 返回 `not_implemented` | 无法排查检索质量 | P1 | pending | 实现 chunk 查询与召回明细输出 |
| 计费能力 | `api-gateway/app/routers/billing.py` | `/plan`、`/usage`、`/quota/check` 返回 `not_implemented` | 无法做配额与商业化闭环 | P1 | pending | 先实现最小配额检查，再补 plan/usage |
| 连接器服务 | `connector-service/app/main.py` | 仅 `health` 接口 | 外部渠道（飞书/企微/webhook）未接通 | P1 | pending | 增加 webhook 接入、签名校验、事件落库 |
| Worker 异步任务 | `job-worker/app/worker.py` | 仅启动打印 | 导入、切块、向量化等后台任务不可用 | P1 | pending | 接 Redis 队列并实现任务消费框架 |
| Analytics 延迟指标 | `assistant-core/app/routers/analytics.py` | `avg_latency_ms = 0` 固定值 | 看板指标不完整 | P2 | pending | 接入埋点并按窗口计算平均耗时 |
| Chat Widget | `chat-widget/src/main.tsx` | 仅 bootstrap 文案页面 | 客户站嵌入端不可用 | P2 | pending | 实现最小可嵌入聊天组件与鉴权参数 |

## 处理顺序建议
1. P0：先保证“可用 + 可上线安全”
2. P1：补齐业务闭环与运营能力
3. P2：增强体验与可观测性

## 备注
- “请求历史导出（JSON）”已记录为后续增强项，当前按你的要求暂不开发。

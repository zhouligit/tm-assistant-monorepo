-- 企业知识助手 MySQL Seed v1.1
-- Execute after migration file

USE tm_assistant;

SET NAMES utf8mb4;

INSERT INTO tenants (id, name, plan_code, status)
VALUES
  (1001, 'Demo Tenant', 'growth', 1)
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  plan_code = VALUES(plan_code),
  status = VALUES(status);

INSERT INTO users (id, tenant_id, email, name, role, password_hash, status, last_login_at)
VALUES
  (2001, 1001, 'owner@demo.com', 'Owner Demo', 'owner', '$2b$12$placeholder_owner_hash', 1, NOW()),
  (2002, 1001, 'admin@demo.com', 'Admin Demo', 'tenant_admin', '$2b$12$placeholder_admin_hash', 1, NOW()),
  (2003, 1001, 'agent@demo.com', 'Agent Demo', 'agent', '$2b$12$placeholder_agent_hash', 1, NOW())
ON DUPLICATE KEY UPDATE
  tenant_id = VALUES(tenant_id),
  name = VALUES(name),
  role = VALUES(role),
  status = VALUES(status),
  last_login_at = VALUES(last_login_at);

INSERT INTO knowledge_sources (
  id, tenant_id, type, name, config_json, status, last_synced_at, created_by
)
VALUES
  (
    3001, 1001, 'faq', '售前FAQ',
    JSON_OBJECT('source', 'manual', 'version', 'v1'),
    'ready', NOW(), 2002
  )
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  config_json = VALUES(config_json),
  status = VALUES(status),
  last_synced_at = VALUES(last_synced_at),
  created_by = VALUES(created_by);

INSERT INTO knowledge_chunks (
  id, tenant_id, source_id, chunk_text, chunk_hash, metadata_json, embedding_ref
)
VALUES
  (
    4001, 1001, 3001,
    '退款预计3-5个工作日到账，具体以支付渠道到账时间为准。',
    SHA2('退款预计3-5个工作日到账，具体以支付渠道到账时间为准。', 256),
    JSON_OBJECT('topic', 'refund', 'lang', 'zh'),
    'vec_demo_4001'
  ),
  (
    4002, 1001, 3001,
    '支持银行卡、对公转账与企业支付。',
    SHA2('支持银行卡、对公转账与企业支付。', 256),
    JSON_OBJECT('topic', 'payment', 'lang', 'zh'),
    'vec_demo_4002'
  )
ON DUPLICATE KEY UPDATE
  chunk_text = VALUES(chunk_text),
  metadata_json = VALUES(metadata_json),
  embedding_ref = VALUES(embedding_ref);

INSERT INTO chat_sessions (
  id, tenant_id, channel, visitor_id, status, started_at
)
VALUES
  (5001, 1001, 'web_widget', 'visitor_001', 'handoff', NOW())
ON DUPLICATE KEY UPDATE
  status = VALUES(status),
  started_at = VALUES(started_at);

INSERT INTO chat_messages (
  id, tenant_id, session_id, role, content, confidence, citations_json, token_usage_json, created_at
)
VALUES
  (
    6001, 1001, 5001, 'user',
    '你们退款多久可以到账？',
    NULL,
    NULL,
    NULL,
    NOW()
  ),
  (
    6002, 1001, 5001, 'assistant',
    '一般在3-5个工作日到账。',
    0.6200,
    JSON_ARRAY(JSON_OBJECT('source_id', 3001, 'chunk_id', 4001)),
    JSON_OBJECT('prompt_tokens', 320, 'completion_tokens', 45, 'total_tokens', 365),
    NOW()
  )
ON DUPLICATE KEY UPDATE
  content = VALUES(content),
  confidence = VALUES(confidence),
  citations_json = VALUES(citations_json),
  token_usage_json = VALUES(token_usage_json),
  created_at = VALUES(created_at);

INSERT INTO handoff_tickets (
  id, tenant_id, session_id, status, reason, assignee_id, claimed_at, created_at
)
VALUES
  (7001, 1001, 5001, 'claimed', 'low_confidence', 2003, NOW(), NOW())
ON DUPLICATE KEY UPDATE
  status = VALUES(status),
  reason = VALUES(reason),
  assignee_id = VALUES(assignee_id),
  claimed_at = VALUES(claimed_at),
  created_at = VALUES(created_at);

INSERT INTO handoff_replies (
  id, tenant_id, ticket_id, agent_id, content, marked_as_kb_candidate, created_at
)
VALUES
  (
    8001, 1001, 7001, 2003,
    '您好，退款通常3-5个工作日到账，节假日顺延。',
    1,
    NOW()
  )
ON DUPLICATE KEY UPDATE
  content = VALUES(content),
  marked_as_kb_candidate = VALUES(marked_as_kb_candidate),
  created_at = VALUES(created_at);

INSERT INTO kb_candidates (
  id, tenant_id, source_reply_id, question, answer, status, reviewed_by, reviewed_at, created_at
)
VALUES
  (
    9001, 1001, 8001,
    '退款多久到账？',
    '退款通常3-5个工作日到账，节假日顺延。',
    'pending',
    NULL,
    NULL,
    NOW()
  )
ON DUPLICATE KEY UPDATE
  question = VALUES(question),
  answer = VALUES(answer),
  status = VALUES(status),
  reviewed_by = VALUES(reviewed_by),
  reviewed_at = VALUES(reviewed_at),
  created_at = VALUES(created_at);

INSERT INTO daily_metrics (
  id, tenant_id, `date`, total_sessions, auto_resolved_sessions, handoff_sessions, avg_latency_ms, total_tokens
)
VALUES
  (10001, 1001, CURRENT_DATE, 42, 18, 12, 2100, 123456)
ON DUPLICATE KEY UPDATE
  total_sessions = VALUES(total_sessions),
  auto_resolved_sessions = VALUES(auto_resolved_sessions),
  handoff_sessions = VALUES(handoff_sessions),
  avg_latency_ms = VALUES(avg_latency_ms),
  total_tokens = VALUES(total_tokens);

INSERT INTO audit_logs (
  id, tenant_id, user_id, action, resource_type, resource_id, detail_json, created_at
)
VALUES
  (
    11001, 1001, 2002,
    'knowledge_source_create', 'knowledge_sources', '3001',
    JSON_OBJECT('name', '售前FAQ', 'type', 'faq'),
    NOW()
  )
ON DUPLICATE KEY UPDATE
  detail_json = VALUES(detail_json),
  created_at = VALUES(created_at);

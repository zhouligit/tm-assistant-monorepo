-- 教育机构试点知识种子数据
-- 作用：注入“数据分析就业班”首批 FAQ 与知识切片

USE tm_assistant;

SET NAMES utf8mb4;

INSERT INTO knowledge_sources (
  id, tenant_id, type, name, config_json, status, last_synced_at, created_by
)
VALUES
  (
    3010, 1001, 'faq', '数据分析就业班 FAQ',
    JSON_OBJECT('source', 'education_pilot', 'version', 'v1'),
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
    4010, 1001, 3010,
    '数据分析就业班标准价为 6980 元，支持 3 期免息分期。',
    SHA2('数据分析就业班标准价为 6980 元，支持 3 期免息分期。', 256),
    JSON_OBJECT('topic', 'pricing', 'line', 'education_pilot'),
    'vec_edu_4010'
  ),
  (
    4011, 1001, 3010,
    '每月 1 号和 15 号开班，支持回放与课后答疑。',
    SHA2('每月 1 号和 15 号开班，支持回放与课后答疑。', 256),
    JSON_OBJECT('topic', 'schedule', 'line', 'education_pilot'),
    'vec_edu_4011'
  ),
  (
    4012, 1001, 3010,
    '报名后 7 天内且未开课可全额退款；开课后按已上课节比例扣费。',
    SHA2('报名后 7 天内且未开课可全额退款；开课后按已上课节比例扣费。', 256),
    JSON_OBJECT('topic', 'refund', 'line', 'education_pilot'),
    'vec_edu_4012'
  ),
  (
    4013, 1001, 3010,
    '课程提供简历优化、模拟面试与内推机会，每周有就业辅导答疑。',
    SHA2('课程提供简历优化、模拟面试与内推机会，每周有就业辅导答疑。', 256),
    JSON_OBJECT('topic', 'career_service', 'line', 'education_pilot'),
    'vec_edu_4013'
  ),
  (
    4014, 1001, 3010,
    '支持 1 节免费试听课，试听后 48 小时内报名可享受 300 元优惠。',
    SHA2('支持 1 节免费试听课，试听后 48 小时内报名可享受 300 元优惠。', 256),
    JSON_OBJECT('topic', 'trial', 'line', 'education_pilot'),
    'vec_edu_4014'
  )
ON DUPLICATE KEY UPDATE
  chunk_text = VALUES(chunk_text),
  metadata_json = VALUES(metadata_json),
  embedding_ref = VALUES(embedding_ref);

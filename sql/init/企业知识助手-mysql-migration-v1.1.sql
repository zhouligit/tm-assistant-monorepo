-- 企业知识助手 MySQL Migration v1.1
-- Engine: MySQL 8.0+
-- Charset: utf8mb4

CREATE DATABASE IF NOT EXISTS tm_assistant
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE tm_assistant;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS tenants (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(128) NOT NULL,
  plan_code VARCHAR(32) NOT NULL DEFAULT 'starter',
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1=active,0=inactive',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_tenants_status (status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  tenant_id BIGINT UNSIGNED NOT NULL,
  email VARCHAR(191) NOT NULL,
  name VARCHAR(64) NOT NULL,
  role ENUM('owner','tenant_admin','agent','viewer') NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  status TINYINT NOT NULL DEFAULT 1 COMMENT '1=active,0=disabled',
  last_login_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_users_email (email),
  KEY idx_users_tenant_role_status (tenant_id, role, status),
  KEY idx_users_tenant_created (tenant_id, created_at),
  CONSTRAINT fk_users_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS knowledge_sources (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  tenant_id BIGINT UNSIGNED NOT NULL,
  type ENUM('feishu_doc','web_url','pdf','faq') NOT NULL,
  name VARCHAR(128) NOT NULL,
  config_json JSON NOT NULL,
  status ENUM('pending','syncing','ready','failed','disabled') NOT NULL DEFAULT 'pending',
  last_synced_at DATETIME NULL,
  last_error VARCHAR(500) NULL,
  created_by BIGINT UNSIGNED NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_ks_tenant_status_type (tenant_id, status, type),
  KEY idx_ks_tenant_updated (tenant_id, updated_at),
  CONSTRAINT fk_ks_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_ks_created_by FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS knowledge_chunks (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  tenant_id BIGINT UNSIGNED NOT NULL,
  source_id BIGINT UNSIGNED NOT NULL,
  chunk_text MEDIUMTEXT NOT NULL,
  chunk_hash CHAR(64) NOT NULL COMMENT 'sha256',
  metadata_json JSON NULL,
  embedding_ref VARCHAR(128) NULL COMMENT '外部向量库引用ID',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_kc_source_hash (source_id, chunk_hash),
  KEY idx_kc_tenant_source (tenant_id, source_id),
  KEY idx_kc_embedding_ref (embedding_ref),
  CONSTRAINT fk_kc_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_kc_source FOREIGN KEY (source_id) REFERENCES knowledge_sources(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS chat_sessions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  tenant_id BIGINT UNSIGNED NOT NULL,
  channel VARCHAR(32) NOT NULL,
  visitor_id VARCHAR(64) NOT NULL,
  status ENUM('open','handoff','closed') NOT NULL DEFAULT 'open',
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  closed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_cs_tenant_status_started (tenant_id, status, started_at),
  KEY idx_cs_tenant_visitor (tenant_id, visitor_id),
  KEY idx_cs_tenant_channel_created (tenant_id, channel, created_at),
  CONSTRAINT fk_cs_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS chat_messages (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  tenant_id BIGINT UNSIGNED NOT NULL,
  session_id BIGINT UNSIGNED NOT NULL,
  role ENUM('user','assistant','agent') NOT NULL,
  content TEXT NOT NULL,
  confidence DECIMAL(5,4) NULL,
  citations_json JSON NULL,
  token_usage_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_cm_tenant_session_created (tenant_id, session_id, created_at),
  KEY idx_cm_session_role_created (session_id, role, created_at),
  CONSTRAINT fk_cm_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_cm_session FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS handoff_tickets (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  tenant_id BIGINT UNSIGNED NOT NULL,
  session_id BIGINT UNSIGNED NOT NULL,
  status ENUM('queued','claimed','resolved') NOT NULL DEFAULT 'queued',
  reason VARCHAR(64) NOT NULL,
  assignee_id BIGINT UNSIGNED NULL,
  claimed_at DATETIME NULL,
  resolved_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_ht_session (session_id),
  KEY idx_ht_tenant_status_created (tenant_id, status, created_at),
  KEY idx_ht_assignee_status (assignee_id, status),
  CONSTRAINT fk_ht_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_ht_session FOREIGN KEY (session_id) REFERENCES chat_sessions(id),
  CONSTRAINT fk_ht_assignee FOREIGN KEY (assignee_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS handoff_replies (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  tenant_id BIGINT UNSIGNED NOT NULL,
  ticket_id BIGINT UNSIGNED NOT NULL,
  agent_id BIGINT UNSIGNED NOT NULL,
  content TEXT NOT NULL,
  marked_as_kb_candidate TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_hr_ticket_created (ticket_id, created_at),
  KEY idx_hr_tenant_agent_created (tenant_id, agent_id, created_at),
  CONSTRAINT fk_hr_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_hr_ticket FOREIGN KEY (ticket_id) REFERENCES handoff_tickets(id),
  CONSTRAINT fk_hr_agent FOREIGN KEY (agent_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS kb_candidates (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  tenant_id BIGINT UNSIGNED NOT NULL,
  source_reply_id BIGINT UNSIGNED NOT NULL,
  question VARCHAR(500) NOT NULL,
  answer TEXT NOT NULL,
  status ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending',
  reviewed_by BIGINT UNSIGNED NULL,
  reviewed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_kbc_source_reply (source_reply_id),
  KEY idx_kbc_tenant_status_created (tenant_id, status, created_at),
  KEY idx_kbc_reviewer (reviewed_by),
  CONSTRAINT fk_kbc_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_kbc_source_reply FOREIGN KEY (source_reply_id) REFERENCES handoff_replies(id),
  CONSTRAINT fk_kbc_reviewer FOREIGN KEY (reviewed_by) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS daily_metrics (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  tenant_id BIGINT UNSIGNED NOT NULL,
  `date` DATE NOT NULL,
  total_sessions INT UNSIGNED NOT NULL DEFAULT 0,
  auto_resolved_sessions INT UNSIGNED NOT NULL DEFAULT 0,
  handoff_sessions INT UNSIGNED NOT NULL DEFAULT 0,
  avg_latency_ms INT UNSIGNED NOT NULL DEFAULT 0,
  total_tokens BIGINT UNSIGNED NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_dm_tenant_date (tenant_id, `date`),
  KEY idx_dm_date (`date`),
  CONSTRAINT fk_dm_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  tenant_id BIGINT UNSIGNED NOT NULL,
  user_id BIGINT UNSIGNED NOT NULL,
  action VARCHAR(64) NOT NULL,
  resource_type VARCHAR(64) NOT NULL,
  resource_id VARCHAR(64) NULL,
  detail_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_al_tenant_created (tenant_id, created_at),
  KEY idx_al_user_created (user_id, created_at),
  KEY idx_al_action_created (action, created_at),
  CONSTRAINT fk_al_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
  CONSTRAINT fk_al_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS = 1;

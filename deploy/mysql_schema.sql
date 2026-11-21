-- GenAI Diagram Studio tables (MySQL database: leadpilot)
-- The leadpilot DB user cannot CREATE DATABASE; tables live in the shared leadpilot DB.

CREATE TABLE IF NOT EXISTS genai_projects (
  id CHAR(36) NOT NULL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT NULL,
  diagram_type VARCHAR(32) NOT NULL DEFAULT 'use_case',
  title VARCHAR(255) NOT NULL DEFAULT 'Untitled Diagram',
  diagram_json JSON NOT NULL,
  external_project_id VARCHAR(255) NULL COMMENT 'Client canvas / LeadPilot project id',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_genai_projects_updated (updated_at),
  INDEX idx_genai_projects_external (external_project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS genai_project_transfers (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  source_project_id CHAR(36) NOT NULL,
  target_project_id CHAR(36) NOT NULL,
  export_payload JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_genai_transfer_source (source_project_id),
  INDEX idx_genai_transfer_target (target_project_id),
  CONSTRAINT fk_genai_transfer_source FOREIGN KEY (source_project_id) REFERENCES genai_projects(id) ON DELETE CASCADE,
  CONSTRAINT fk_genai_transfer_target FOREIGN KEY (target_project_id) REFERENCES genai_projects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS genai_settings (
  `key` VARCHAR(128) NOT NULL PRIMARY KEY,
  `value` JSON NOT NULL,
  `type` VARCHAR(32) NOT NULL DEFAULT 'string',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS genai_prompts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  prompt_key VARCHAR(128) NOT NULL,
  body MEDIUMTEXT NOT NULL,
  version INT NOT NULL DEFAULT 1,
  is_active TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_genai_prompts_key_version (prompt_key, version),
  INDEX idx_genai_prompts_active (prompt_key, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS genai_generation_logs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  diagram_type VARCHAR(32) NOT NULL DEFAULT '',
  edit_mode TINYINT(1) NOT NULL DEFAULT 0,
  status VARCHAR(16) NOT NULL DEFAULT 'ok',
  error_message VARCHAR(512) NULL,
  api_key_last4 VARCHAR(8) NULL,
  models_used VARCHAR(512) NULL,
  call_count INT NOT NULL DEFAULT 0,
  prompt_tokens INT NULL,
  thoughts_tokens INT NULL,
  output_tokens INT NULL,
  total_tokens INT NULL,
  duration_ms INT NULL,
  calls_json JSON NULL,
  INDEX idx_genai_gen_logs_created (created_at),
  INDEX idx_genai_gen_logs_key (api_key_last4),
  INDEX idx_genai_gen_logs_type (diagram_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

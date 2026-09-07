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

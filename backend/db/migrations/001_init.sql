-- ============================================================
-- Google Photos Discovery Engine — Database Schema (SQLite)
-- Migration: 001_init.sql
-- ============================================================

-- ============================================================
-- Table: feedback_records
-- Stores the extracted, structured data from each user complaint
-- ============================================================
CREATE TABLE IF NOT EXISTS feedback_records (
    id                    INTEGER       PRIMARY KEY AUTOINCREMENT,
    source_platform       VARCHAR(20)   NOT NULL,
    source                VARCHAR(30)   DEFAULT NULL,
    url_id                TEXT          NOT NULL UNIQUE,
    raw_text              TEXT          NOT NULL,
    photo_type            VARCHAR(30)   NOT NULL DEFAULT 'other',
    remembered_attributes TEXT          NOT NULL DEFAULT '[]',
    forgotten_attributes  TEXT          NOT NULL DEFAULT '[]',
    search_strategy       VARCHAR(30)   NOT NULL DEFAULT 'other',
    failure_point         TEXT          NOT NULL DEFAULT '',
    workaround            TEXT          DEFAULT '',
    emotional_signal      VARCHAR(20)   NOT NULL DEFAULT 'neutral',
    cluster_id            INTEGER,
    embedding             BLOB,
    created_at            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_cluster_id ON feedback_records (cluster_id);
CREATE INDEX IF NOT EXISTS idx_feedback_source_platform ON feedback_records (source_platform);

-- ============================================================
-- Table: clusters
-- Stores metadata for each identified failure-pattern cluster
-- ============================================================
CREATE TABLE IF NOT EXISTS clusters (
    cluster_id            INTEGER       PRIMARY KEY,
    label                 TEXT          NOT NULL,
    description           TEXT          DEFAULT '',
    record_count          INTEGER       NOT NULL DEFAULT 0,
    source_diversity      TEXT          NOT NULL DEFAULT '{}',
    severity_score        FLOAT         NOT NULL DEFAULT 0.0,
    top_failure_points    TEXT          NOT NULL DEFAULT '[]',
    representative_quotes TEXT          NOT NULL DEFAULT '[]',
    centroid              BLOB,
    created_at            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Table: synthesis_answers
-- Stores the AI-generated answers to the 5 core strategic questions
-- ============================================================
CREATE TABLE IF NOT EXISTS synthesis_answers (
    question_id           INTEGER       PRIMARY KEY AUTOINCREMENT,
    question_text         TEXT          NOT NULL UNIQUE,
    answer_text           TEXT          NOT NULL DEFAULT '',
    evidence              TEXT          NOT NULL DEFAULT '{}',
    generated_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Table: ingestion_log
-- Tracks the progress and status of each scraper batch run
-- ============================================================
CREATE TABLE IF NOT EXISTS ingestion_log (
    id                    INTEGER       PRIMARY KEY AUTOINCREMENT,
    source_platform       VARCHAR(20)   NOT NULL,
    batch_file            TEXT          NOT NULL,
    records_scraped       INTEGER       NOT NULL DEFAULT 0,
    records_valid         INTEGER       NOT NULL DEFAULT 0,
    status                VARCHAR(20)   NOT NULL DEFAULT 'pending',
    error_message         TEXT,
    started_at            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at          DATETIME
);

CREATE INDEX IF NOT EXISTS idx_ingestion_source ON ingestion_log (source_platform, status);

-- ============================================================
-- Table: pipeline_runs
-- Tracks end-to-end pipeline execution status
-- ============================================================
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id                    INTEGER       PRIMARY KEY AUTOINCREMENT,
    phase                 VARCHAR(30)   NOT NULL,
    status                VARCHAR(20)   NOT NULL DEFAULT 'pending',
    records_processed     INTEGER       DEFAULT 0,
    error_message         TEXT,
    started_at            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at          DATETIME
);

-- ============================================================
-- Seed: Pre-insert the 5 core strategic questions
-- ============================================================
INSERT OR IGNORE INTO synthesis_answers (question_text) VALUES
    ('What kinds of old photos do users struggle to retrieve?'),
    ('What information do people actually remember about a photo?'),
    ('What information have they forgotten?'),
    ('How do users formulate searches when their memory is incomplete?'),
    ('Which retrieval failure cluster causes the highest user churn/frustration?');

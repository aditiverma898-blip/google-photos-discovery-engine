-- ============================================================
-- Migration: 003_failure_category.sql
-- Adds failure_category to distinguish vague memory retrieval
-- from engineering data loss & cloud sync bugs.
-- ============================================================

ALTER TABLE feedback_records ADD COLUMN failure_category VARCHAR(30) DEFAULT NULL;
CREATE INDEX IF NOT EXISTS idx_feedback_failure_category ON feedback_records (failure_category);

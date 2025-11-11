-- Migration 009: Add corrected_reasoning field to ai_lessons table
-- This allows users to correct the AI's reasoning, not just annotations

ALTER TABLE ai_lessons ADD COLUMN corrected_reasoning TEXT;


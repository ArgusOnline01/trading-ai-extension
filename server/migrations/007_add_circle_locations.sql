-- Migration 007: Add circle_locations column to annotations table
-- Date: 2025-11-05
-- Phase: Phase 4B - Strategy Documentation

-- Add circle_locations column to annotations table
ALTER TABLE annotations ADD COLUMN circle_locations JSON;

-- Update comment
COMMENT ON COLUMN annotations.circle_locations IS 'Circle annotation locations: [{x, y, radius, color, timestamp}]';


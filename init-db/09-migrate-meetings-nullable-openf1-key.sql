-- Migration: Make silver.meetings.openf1_meeting_key nullable
-- Purpose: Allow future/scheduled meetings to be pre-populated before OpenF1 has data
-- 
-- This migration:
-- 1. Removes the NOT NULL constraint from openf1_meeting_key
-- 2. Adds a partial unique index to ensure uniqueness when the key IS present
--
-- Run this on existing databases to support future meetings

-- Step 1: Remove NOT NULL constraint from openf1_meeting_key
-- This allows future meetings to be inserted without an OpenF1 key
ALTER TABLE silver.meetings 
    ALTER COLUMN openf1_meeting_key DROP NOT NULL;

-- Step 2: Add partial unique index
-- Ensures openf1_meeting_key is unique among non-NULL values
-- This prevents duplicate meeting keys while allowing multiple NULL values
CREATE UNIQUE INDEX IF NOT EXISTS idx_meetings_openf1_meeting_key_unique 
ON silver.meetings(openf1_meeting_key) 
WHERE openf1_meeting_key IS NOT NULL;

-- Verification queries (optional - uncomment to run)
-- SELECT column_name, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_schema = 'silver' 
--   AND table_name = 'meetings' 
--   AND column_name = 'openf1_meeting_key';

-- SELECT indexname, indexdef 
-- FROM pg_indexes 
-- WHERE tablename = 'meetings' 
--   AND schemaname = 'silver'
--   AND indexname = 'idx_meetings_openf1_meeting_key_unique';



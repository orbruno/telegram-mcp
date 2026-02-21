-- Migration: Add media/attachment columns to messages table
-- Run this once to update existing database

-- Add media columns (SQLite allows adding columns one at a time)
ALTER TABLE messages ADD COLUMN has_media BOOLEAN DEFAULT 0;
ALTER TABLE messages ADD COLUMN media_type VARCHAR;
ALTER TABLE messages ADD COLUMN file_id VARCHAR;
ALTER TABLE messages ADD COLUMN file_name VARCHAR;
ALTER TABLE messages ADD COLUMN file_size INTEGER;
ALTER TABLE messages ADD COLUMN mime_type VARCHAR;
ALTER TABLE messages ADD COLUMN local_path VARCHAR;

-- Create index for media queries
CREATE INDEX IF NOT EXISTS idx_messages_has_media ON messages(has_media);

-- ================================================
-- Couple Chat AI - Supabase Database Schema
-- ================================================
-- Run this SQL in your Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ================================================
-- DISABLE ROW LEVEL SECURITY FOR BACKEND ACCESS
-- ================================================
-- The backend uses service connection, so we disable RLS
-- If you want RLS, use the service_role key in SUPABASE_KEY
ALTER TABLE IF EXISTS rooms DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS room_users DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS messages DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS onboarding DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS reactions DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS media_files DISABLE ROW LEVEL SECURITY;

-- ================================================
-- ROOMS TABLE
-- ================================================
CREATE TABLE IF NOT EXISTS rooms (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    secret_hash VARCHAR(64) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deleted')),
    nsfw_mode VARCHAR(20) DEFAULT 'disabled' CHECK (nsfw_mode IN ('disabled', 'pending_consent', 'enabled')),
    
    -- NSFW consent tracking
    partner_a_nsfw_consent BOOLEAN DEFAULT FALSE,
    partner_b_nsfw_consent BOOLEAN DEFAULT FALSE,
    
    -- Onboarding/relationship data
    relationship_type VARCHAR(50),
    anniversary_date TIMESTAMP WITH TIME ZONE,
    partner_a_preferences JSONB,
    partner_b_preferences JSONB,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    last_activity_at TIMESTAMP WITH TIME ZONE
);

-- Index for active rooms lookup
CREATE INDEX IF NOT EXISTS idx_rooms_status ON rooms(status);

-- ================================================
-- ROOM USERS TABLE
-- ================================================
CREATE TABLE IF NOT EXISTS room_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    nickname VARCHAR(50) NOT NULL,
    avatar_url TEXT,
    device_id VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('partner_a', 'partner_b')),
    
    -- Online status
    is_online BOOLEAN DEFAULT FALSE,
    last_seen TIMESTAMP WITH TIME ZONE,
    
    -- NSFW consent
    nsfw_consent BOOLEAN DEFAULT FALSE,
    nsfw_consent_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique device per room
    UNIQUE(room_id, device_id)
);

-- Indexes for user lookups
CREATE INDEX IF NOT EXISTS idx_room_users_room ON room_users(room_id);
CREATE INDEX IF NOT EXISTS idx_room_users_device ON room_users(device_id);

-- ================================================
-- MESSAGES TABLE
-- ================================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    sender_id VARCHAR(100) NOT NULL, -- Can be UUID or 'bot'
    content TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'text' CHECK (message_type IN ('text', 'image', 'audio', 'system', 'bot')),
    
    -- Media fields
    media_url TEXT,
    media_encrypted BOOLEAN DEFAULT FALSE,
    media_nonce VARCHAR(50),
    
    -- View once functionality
    view_once BOOLEAN DEFAULT FALSE,
    view_once_viewed BOOLEAN DEFAULT FALSE,
    view_once_viewed_at TIMESTAMP WITH TIME ZONE,
    
    -- Reply reference
    reply_to_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    
    -- Reactions stored as JSONB: {"heart": ["user1", "user2"], "laugh": ["user3"]}
    reactions JSONB DEFAULT '{}',
    
    -- Memory tracking
    is_remembered BOOLEAN DEFAULT FALSE,
    memory_category VARCHAR(20),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for message queries
CREATE INDEX IF NOT EXISTS idx_messages_room ON messages(room_id);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(room_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(message_type);

-- ================================================
-- REACTIONS TABLE (denormalized for quick access)
-- ================================================
CREATE TABLE IF NOT EXISTS reactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    reaction_type VARCHAR(20) NOT NULL CHECK (reaction_type IN ('heart', 'laugh', 'cry', 'shocked', 'angry')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Prevent duplicate reactions of same type from same user
    UNIQUE(message_id, user_id, reaction_type)
);

-- Index for reaction lookups
CREATE INDEX IF NOT EXISTS idx_reactions_message ON reactions(message_id);

-- ================================================
-- ROW LEVEL SECURITY (RLS)
-- ================================================

-- Enable RLS on all tables
ALTER TABLE rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE room_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE reactions ENABLE ROW LEVEL SECURITY;

-- For MVP/demo, allow all operations with service key
-- In production, add proper RLS policies based on authentication

CREATE POLICY "Allow all for service role" ON rooms
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow all for service role" ON room_users
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow all for service role" ON messages
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow all for service role" ON reactions
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Public read access for anon (needed for API)
CREATE POLICY "Allow anon read" ON rooms
    FOR SELECT
    TO anon
    USING (status = 'active');

CREATE POLICY "Allow anon all" ON room_users
    FOR ALL
    TO anon
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow anon all" ON messages
    FOR ALL
    TO anon
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow anon all" ON reactions
    FOR ALL
    TO anon
    USING (true)
    WITH CHECK (true);

-- ================================================
-- STORAGE BUCKET
-- ================================================
-- Run this in Supabase Dashboard > Storage > Create bucket

-- Bucket name: media
-- Public: false (private bucket)
-- Allowed MIME types: image/jpeg, image/png, image/gif, image/webp, audio/mpeg, audio/wav, audio/ogg, audio/webm
-- File size limit: 5MB

-- Storage policies (add in Supabase Dashboard > Storage > Policies)
-- Policy name: Allow uploads
-- Allowed operation: INSERT
-- Policy: true (for MVP)

-- Policy name: Allow downloads  
-- Allowed operation: SELECT
-- Policy: true (for MVP)

-- Policy name: Allow deletes
-- Allowed operation: DELETE
-- Policy: true (for MVP)

-- ================================================
-- DEMO DATA (Optional)
-- ================================================

-- Insert demo room (room_id=1, secret="12589")
-- Secret hash is SHA-256 of "12589"
INSERT INTO rooms (id, name, secret_hash, status, nsfw_mode, created_at)
VALUES (
    1,
    'Demo Room',
    '5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5',
    'active',
    'disabled',
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- Reset sequence to avoid conflicts
SELECT setval('rooms_id_seq', (SELECT MAX(id) FROM rooms));

-- ================================================
-- FUNCTIONS
-- ================================================

-- Function to update room activity timestamp
CREATE OR REPLACE FUNCTION update_room_activity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE rooms 
    SET last_activity_at = NOW()
    WHERE id = NEW.room_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update room activity on new message
CREATE TRIGGER trigger_update_room_activity
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_room_activity();

-- Function to sync reactions JSONB with reactions table
CREATE OR REPLACE FUNCTION sync_message_reactions()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE messages
        SET reactions = (
            SELECT jsonb_object_agg(
                reaction_type,
                array_agg(user_id::text)
            )
            FROM reactions
            WHERE message_id = NEW.message_id
            GROUP BY message_id
        )
        WHERE id = NEW.message_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE messages
        SET reactions = COALESCE((
            SELECT jsonb_object_agg(
                reaction_type,
                array_agg(user_id::text)
            )
            FROM reactions
            WHERE message_id = OLD.message_id
            GROUP BY message_id
        ), '{}')
        WHERE id = OLD.message_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger to sync reactions
CREATE TRIGGER trigger_sync_reactions
    AFTER INSERT OR DELETE ON reactions
    FOR EACH ROW
    EXECUTE FUNCTION sync_message_reactions();

-- ================================================
-- COMPLETED
-- ================================================
-- Schema setup complete!
-- Remember to:
-- 1. Create the 'media' storage bucket
-- 2. Set up storage policies
-- 3. Copy your Supabase URL and keys to .env

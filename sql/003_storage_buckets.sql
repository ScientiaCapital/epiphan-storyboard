-- =============================================
-- Supabase Storage Buckets for Storyboards
-- Run this in your Supabase SQL Editor
-- =============================================

-- Create storage bucket for storyboard assets
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'coperniq-assets',
    'coperniq-assets',
    true,  -- Public bucket for easy sharing
    52428800,  -- 50MB limit
    ARRAY['image/png', 'image/jpeg', 'image/webp', 'image/gif']
) ON CONFLICT (id) DO NOTHING;

-- Enable RLS on storage.objects (required)
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Policy: Allow public read access to all files
CREATE POLICY "Public read access for coperniq-assets"
ON storage.objects FOR SELECT
USING (bucket_id = 'coperniq-assets');

-- Policy: Allow authenticated users to upload
CREATE POLICY "Authenticated upload for coperniq-assets"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'coperniq-assets');

-- Policy: Allow service role to manage all files
CREATE POLICY "Service role full access for coperniq-assets"
ON storage.objects
USING (bucket_id = 'coperniq-assets' AND auth.role() = 'service_role')
WITH CHECK (bucket_id = 'coperniq-assets' AND auth.role() = 'service_role');

-- =============================================
-- Optional: Create a table to track generated storyboards
-- =============================================

CREATE TABLE IF NOT EXISTS storyboard_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Storage reference
    storage_path TEXT NOT NULL,  -- e.g., 'generated-outputs/2024-12-04/storyboard_abc123.png'
    public_url TEXT,

    -- Metadata
    audience TEXT,  -- 'top_tier_vc', 'field_crew', etc.
    stage TEXT,     -- 'preview', 'demo', 'shipped'
    input_type TEXT, -- 'code', 'image'

    -- Understanding extracted
    headline TEXT,
    understanding JSONB,

    -- Organization (for multi-tenant)
    org_id TEXT DEFAULT 'default'
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_storyboard_assets_org_created
ON storyboard_assets(org_id, created_at DESC);

-- Enable RLS
ALTER TABLE storyboard_assets ENABLE ROW LEVEL SECURITY;

-- Policy: Service role can do everything
CREATE POLICY "Service role full access for storyboard_assets"
ON storyboard_assets
USING (true)
WITH CHECK (true);

COMMENT ON TABLE storyboard_assets IS 'Tracks generated storyboard images with metadata for easy browsing';

-- Demo Pipeline Jobs SQL Migration
-- Run in Supabase SQL Editor
-- Created: 2026-02-19
-- Purpose: Async demo video pipeline (scene extraction + video asset generation)

-- =============================================================================
-- DEMO_PIPELINE_JOBS TABLE
-- Stores async demo pipeline jobs with scene extraction and video asset results
-- =============================================================================

CREATE TABLE IF NOT EXISTS demo_pipeline_jobs (
    -- Identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id TEXT NOT NULL,  -- Multi-tenant organization identifier

    -- Pipeline status
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'extracting_scenes', 'generating_assets', 'completed', 'failed')),

    -- Input
    understanding JSONB NOT NULL DEFAULT '{}'::jsonb,  -- StoryboardUnderstanding dict
    persona TEXT NOT NULL DEFAULT 'av_director',
    vertical TEXT NOT NULL DEFAULT 'higher_ed',
    product_focus TEXT NOT NULL DEFAULT 'pearl_mini',
    skip_video_generation BOOLEAN NOT NULL DEFAULT false,

    -- Output (JSONB — no premature normalization)
    scene_extraction JSONB,  -- SceneExtractionResult: scenes[], persona, vertical, model_used
    video_assets JSONB,  -- VideoAssetBatchResult: assets[], totals, provider
    error_message TEXT,  -- Error details if status = 'failed'

    -- Timing
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    execution_time_ms INTEGER,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Multi-tenant queries (most common access pattern)
CREATE INDEX IF NOT EXISTS idx_demo_pipeline_jobs_org_id
    ON demo_pipeline_jobs(org_id);

-- Status monitoring (find pending/failed jobs)
CREATE INDEX IF NOT EXISTS idx_demo_pipeline_jobs_status
    ON demo_pipeline_jobs(status) WHERE status IN ('pending', 'failed');

-- Recent jobs listing
CREATE INDEX IF NOT EXISTS idx_demo_pipeline_jobs_created
    ON demo_pipeline_jobs(created_at DESC);

-- Composite: org + status (tenant-specific monitoring)
CREATE INDEX IF NOT EXISTS idx_demo_pipeline_jobs_org_status
    ON demo_pipeline_jobs(org_id, status);

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- API-only access via service role
-- =============================================================================

ALTER TABLE demo_pipeline_jobs ENABLE ROW LEVEL SECURITY;

-- Service role has full access (backend bypass RLS)
CREATE POLICY IF NOT EXISTS "Service role full access demo_pipeline_jobs"
    ON demo_pipeline_jobs FOR ALL
    USING (auth.role() = 'service_role');

-- No public access — API-only

-- =============================================================================
-- GRANT PERMISSIONS
-- =============================================================================

GRANT ALL ON demo_pipeline_jobs TO service_role;

-- =============================================================================
-- SUCCESS MESSAGE
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '✓ Demo Pipeline Jobs migration completed successfully!';
    RAISE NOTICE '  - Table: demo_pipeline_jobs';
    RAISE NOTICE '  - Indexes: org_id, status, created_at, org+status';
    RAISE NOTICE '  - RLS: Enabled with service_role-only access';
END $$;

-- Conductor-AI Storyboard Jobs SQL Migration
-- Run in Supabase SQL Editor
-- Created: 2025-12-02
-- Purpose: Async storyboard generation API with Redis hot state + PostgreSQL persistence

-- =============================================================================
-- STORYBOARD_JOBS TABLE
-- Stores async storyboard generation jobs (code_to_storyboard, roadmap_to_storyboard)
-- =============================================================================

CREATE TABLE IF NOT EXISTS storyboard_jobs (
    -- Identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id TEXT NOT NULL,  -- Multi-tenant organization identifier

    -- Job configuration
    job_type TEXT NOT NULL CHECK (job_type IN ('code_to_storyboard', 'roadmap_to_storyboard')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),

    -- Input (flexible JSONB for different job types)
    -- code_to_storyboard: {file_content, file_name, icp_preset, stage, audience, custom_headline}
    -- roadmap_to_storyboard: {image_data, icp_preset, audience, custom_headline, sanitize_ip}
    input_params JSONB NOT NULL,

    -- Output
    result_image TEXT,  -- Base64-encoded PNG (up to 5MB - large text field)
    understanding JSONB,  -- {headline, what_it_does, business_value, who_benefits, differentiator, pain_point_addressed, suggested_icon}
    error_message TEXT,  -- Error details if status = 'failed'

    -- Timing
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,  -- When processing began
    completed_at TIMESTAMPTZ,  -- When job finished (success or failure)
    execution_time_ms INTEGER,  -- Total execution time in milliseconds

    -- Metadata
    model TEXT DEFAULT 'gemini-2.0-flash-preview-image-generation',  -- Model used for generation
    metadata JSONB DEFAULT '{}'::jsonb  -- Additional metadata (stage, audience, icp_preset, etc.)
);

-- =============================================================================
-- INDEXES
-- Optimized for common query patterns
-- =============================================================================

-- Multi-tenant queries (most common access pattern)
CREATE INDEX IF NOT EXISTS idx_storyboard_jobs_org_id ON storyboard_jobs(org_id);

-- Status monitoring (find pending/failed jobs)
CREATE INDEX IF NOT EXISTS idx_storyboard_jobs_status ON storyboard_jobs(status) WHERE status IN ('pending', 'failed');

-- Recent jobs listing (sorted by created_at DESC)
CREATE INDEX IF NOT EXISTS idx_storyboard_jobs_created ON storyboard_jobs(created_at DESC);

-- Job type analytics
CREATE INDEX IF NOT EXISTS idx_storyboard_jobs_type ON storyboard_jobs(job_type);

-- Composite index for org + status queries (efficient tenant-specific monitoring)
CREATE INDEX IF NOT EXISTS idx_storyboard_jobs_org_status ON storyboard_jobs(org_id, status);

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- API-only access via service role
-- =============================================================================

ALTER TABLE storyboard_jobs ENABLE ROW LEVEL SECURITY;

-- Service role has full access (backend bypass RLS)
CREATE POLICY IF NOT EXISTS "Service role full access storyboard_jobs"
    ON storyboard_jobs FOR ALL
    USING (auth.role() = 'service_role');

-- No public access - API-only
-- (No policies for anon/authenticated users means they get zero access)

-- =============================================================================
-- UPDATED_AT TRIGGER (optional but useful)
-- Auto-update completion timestamp on status changes
-- =============================================================================

-- Note: We don't need updated_at since we have completed_at for tracking changes
-- Jobs are immutable after completion (no updates after status = 'completed' or 'failed')

-- =============================================================================
-- HELPER VIEWS
-- Convenient views for monitoring and analytics
-- =============================================================================

-- Recent jobs: Last 100 jobs with key fields
CREATE OR REPLACE VIEW recent_storyboard_jobs AS
SELECT
    id,
    org_id,
    job_type,
    status,
    created_at,
    completed_at,
    execution_time_ms,
    CASE
        WHEN result_image IS NOT NULL THEN true
        ELSE false
    END as has_result,
    CASE
        WHEN error_message IS NOT NULL THEN SUBSTRING(error_message, 1, 100)
        ELSE NULL
    END as error_preview,
    metadata->>'stage' as stage,
    metadata->>'audience' as audience,
    metadata->>'icp_preset' as icp_preset
FROM storyboard_jobs
ORDER BY created_at DESC
LIMIT 100;

-- Job stats: Aggregated success/failure rates by job_type
CREATE OR REPLACE VIEW storyboard_job_stats AS
SELECT
    job_type,
    COUNT(*) as total_jobs,
    COUNT(*) FILTER (WHERE status = 'completed') as completed,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    COUNT(*) FILTER (WHERE status = 'pending') as pending,
    COUNT(*) FILTER (WHERE status = 'processing') as processing,
    ROUND(
        (COUNT(*) FILTER (WHERE status = 'completed')::NUMERIC / NULLIF(COUNT(*), 0)) * 100,
        2
    ) as success_rate_pct,
    ROUND(AVG(execution_time_ms) FILTER (WHERE status = 'completed'), 0) as avg_execution_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY execution_time_ms) FILTER (WHERE status = 'completed') as median_execution_ms,
    MAX(execution_time_ms) FILTER (WHERE status = 'completed') as max_execution_ms
FROM storyboard_jobs
WHERE created_at > NOW() - INTERVAL '30 days'  -- Last 30 days only
GROUP BY job_type
ORDER BY total_jobs DESC;

-- Organization usage: Jobs per org (for billing/quota monitoring)
CREATE OR REPLACE VIEW storyboard_org_usage AS
SELECT
    org_id,
    COUNT(*) as total_jobs,
    COUNT(*) FILTER (WHERE status = 'completed') as successful_jobs,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_jobs,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as jobs_last_24h,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') as jobs_last_7d,
    MAX(created_at) as last_job_at
FROM storyboard_jobs
GROUP BY org_id
ORDER BY total_jobs DESC;

-- Failed jobs: Recent failures for debugging
CREATE OR REPLACE VIEW storyboard_failures AS
SELECT
    id,
    org_id,
    job_type,
    created_at,
    started_at,
    completed_at,
    execution_time_ms,
    error_message,
    input_params,
    metadata
FROM storyboard_jobs
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 50;

-- =============================================================================
-- GRANT PERMISSIONS
-- =============================================================================

GRANT ALL ON storyboard_jobs TO service_role;
GRANT SELECT ON recent_storyboard_jobs TO service_role;
GRANT SELECT ON storyboard_job_stats TO service_role;
GRANT SELECT ON storyboard_org_usage TO service_role;
GRANT SELECT ON storyboard_failures TO service_role;

-- =============================================================================
-- SUCCESS MESSAGE
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '✓ Storyboard Jobs SQL migration completed successfully!';
    RAISE NOTICE '  - Table created: storyboard_jobs';
    RAISE NOTICE '  - Indexes: 5 indexes for org_id, status, created_at, job_type, composite';
    RAISE NOTICE '  - Views: recent_storyboard_jobs, storyboard_job_stats, storyboard_org_usage, storyboard_failures';
    RAISE NOTICE '  - RLS: Enabled with service_role-only access (API-only)';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Verify table: SELECT * FROM storyboard_jobs LIMIT 1;';
    RAISE NOTICE '  2. Test insert: INSERT INTO storyboard_jobs (org_id, job_type, input_params) VALUES (''test-org'', ''code_to_storyboard'', ''{}''::jsonb);';
    RAISE NOTICE '  3. Check views: SELECT * FROM storyboard_job_stats;';
END $$;

-- ============================================================================
-- Enterprise Data Connectors Schema
-- ============================================================================
-- This migration adds support for multi-tenant data connector infrastructure
-- - Connector instance management (Gong, Fireflies, Linear, Notion, etc.)
-- - Sync run tracking with cursor-based incremental updates
-- - Multi-tenant isolation via org_id
-- ============================================================================

-- ============================================================================
-- CONNECTOR INSTANCES TABLE
-- ============================================================================
-- Tracks one connector instance per connector type per organization
-- Example: org_123 might have one Gong instance, one Linear instance, etc.

CREATE TABLE IF NOT EXISTS connector_instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id TEXT NOT NULL,
    connector_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending' NOT NULL,
    oauth_tokens JSONB,  -- Encrypted: {access_token, refresh_token, expires_at}
    config JSONB DEFAULT '{}'::jsonb,  -- Connector-specific config
    last_sync_at TIMESTAMPTZ,
    next_sync_at TIMESTAMPTZ,
    sync_cursor TEXT,  -- For incremental sync (e.g., "2025-12-09T00:00:00Z")
    items_synced INT DEFAULT 0,
    error_message TEXT,
    error_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT connector_instances_type_check CHECK (
        connector_type IN (
            'gong',
            'fireflies',
            'linear',
            'notion',
            'google_docs',
            'loom',
            'miro',
            'close'
        )
    ),
    CONSTRAINT connector_instances_status_check CHECK (
        status IN ('pending', 'connected', 'syncing', 'error', 'disabled')
    ),
    CONSTRAINT connector_instances_unique_org_type UNIQUE (org_id, connector_type)
);

COMMENT ON TABLE connector_instances IS 'Tracks data connector instances per organization';
COMMENT ON COLUMN connector_instances.org_id IS 'Multi-tenant isolation key';
COMMENT ON COLUMN connector_instances.connector_type IS 'Type of connector: gong, fireflies, linear, etc.';
COMMENT ON COLUMN connector_instances.status IS 'Current status: pending, connected, syncing, error, disabled';
COMMENT ON COLUMN connector_instances.oauth_tokens IS 'Encrypted OAuth tokens (access_token, refresh_token, expires_at)';
COMMENT ON COLUMN connector_instances.config IS 'Connector-specific configuration (e.g., {"team_id": "linear_team_xyz"})';
COMMENT ON COLUMN connector_instances.sync_cursor IS 'Cursor for incremental sync (timestamp, page token, etc.)';
COMMENT ON COLUMN connector_instances.items_synced IS 'Total items successfully synced from this connector';
COMMENT ON COLUMN connector_instances.error_count IS 'Consecutive error count (reset on success)';

-- ============================================================================
-- SYNC RUNS TABLE
-- ============================================================================
-- Tracks each sync run with detailed metrics and error logging

CREATE TABLE IF NOT EXISTS sync_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connector_instance_id UUID NOT NULL REFERENCES connector_instances(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',
    items_fetched INT DEFAULT 0,  -- Items retrieved from external API
    items_extracted INT DEFAULT 0,  -- Items processed by LLM extraction
    items_created INT DEFAULT 0,  -- Items successfully stored in knowledge base
    items_skipped INT DEFAULT 0,  -- Items skipped (duplicates, filtered, etc.)
    error_log JSONB,  -- Structured error details
    cursor_before TEXT,  -- Sync cursor at start of run
    cursor_after TEXT,  -- Sync cursor after run (for next incremental sync)

    -- Constraints
    CONSTRAINT sync_runs_status_check CHECK (
        status IN ('running', 'success', 'failed', 'cancelled')
    )
);

COMMENT ON TABLE sync_runs IS 'Audit trail of all connector sync runs';
COMMENT ON COLUMN sync_runs.items_fetched IS 'Number of items retrieved from external API';
COMMENT ON COLUMN sync_runs.items_extracted IS 'Number of items processed by LLM extraction';
COMMENT ON COLUMN sync_runs.items_created IS 'Number of knowledge entries created';
COMMENT ON COLUMN sync_runs.items_skipped IS 'Number of items skipped (duplicates, filtered out)';
COMMENT ON COLUMN sync_runs.error_log IS 'Structured error details: {"errors": [{"item_id": "x", "error": "..."}]}';
COMMENT ON COLUMN sync_runs.cursor_before IS 'Sync cursor at start (for debugging)';
COMMENT ON COLUMN sync_runs.cursor_after IS 'Sync cursor to use for next incremental sync';

-- ============================================================================
-- MULTI-TENANT ISOLATION - ALTER EXISTING TABLES
-- ============================================================================
-- Add org_id to existing knowledge tables for multi-tenant support

ALTER TABLE knowledge_sources
    ADD COLUMN IF NOT EXISTS org_id TEXT;

ALTER TABLE knowledge
    ADD COLUMN IF NOT EXISTS org_id TEXT;

COMMENT ON COLUMN knowledge_sources.org_id IS 'Multi-tenant isolation key (NULL for legacy/shared data)';
COMMENT ON COLUMN knowledge.org_id IS 'Multi-tenant isolation key (NULL for legacy/shared data)';

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Connector instances
CREATE INDEX IF NOT EXISTS idx_connector_instances_org
    ON connector_instances(org_id);

CREATE INDEX IF NOT EXISTS idx_connector_instances_status
    ON connector_instances(status);

CREATE INDEX IF NOT EXISTS idx_connector_instances_next_sync
    ON connector_instances(next_sync_at)
    WHERE status = 'connected';

-- Sync runs
CREATE INDEX IF NOT EXISTS idx_sync_runs_instance
    ON sync_runs(connector_instance_id);

CREATE INDEX IF NOT EXISTS idx_sync_runs_status
    ON sync_runs(status);

CREATE INDEX IF NOT EXISTS idx_sync_runs_started
    ON sync_runs(started_at DESC);

-- Multi-tenant knowledge tables
CREATE INDEX IF NOT EXISTS idx_knowledge_sources_org
    ON knowledge_sources(org_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_org
    ON knowledge(org_id);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on new tables
ALTER TABLE connector_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_runs ENABLE ROW LEVEL SECURITY;

-- Service role full access (for backend processes)
CREATE POLICY connector_instances_service_role
    ON connector_instances
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY sync_runs_service_role
    ON sync_runs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp on connector_instances
CREATE OR REPLACE FUNCTION update_connector_instances_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER connector_instances_updated_at_trigger
    BEFORE UPDATE ON connector_instances
    FOR EACH ROW
    EXECUTE FUNCTION update_connector_instances_updated_at();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Get active connectors ready for sync
CREATE OR REPLACE FUNCTION get_connectors_ready_for_sync()
RETURNS TABLE (
    id UUID,
    org_id TEXT,
    connector_type TEXT,
    sync_cursor TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ci.id,
        ci.org_id,
        ci.connector_type,
        ci.sync_cursor
    FROM connector_instances ci
    WHERE ci.status = 'connected'
        AND (ci.next_sync_at IS NULL OR ci.next_sync_at <= NOW())
    ORDER BY ci.next_sync_at NULLS FIRST;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_connectors_ready_for_sync IS 'Returns connectors that are ready for their next sync run';

-- Get sync stats for a connector
CREATE OR REPLACE FUNCTION get_connector_sync_stats(p_connector_id UUID)
RETURNS TABLE (
    total_runs BIGINT,
    successful_runs BIGINT,
    failed_runs BIGINT,
    total_items_synced BIGINT,
    last_success_at TIMESTAMPTZ,
    last_error TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as total_runs,
        COUNT(*) FILTER (WHERE status = 'success')::BIGINT as successful_runs,
        COUNT(*) FILTER (WHERE status = 'failed')::BIGINT as failed_runs,
        COALESCE(SUM(items_created) FILTER (WHERE status = 'success'), 0)::BIGINT as total_items_synced,
        MAX(completed_at) FILTER (WHERE status = 'success') as last_success_at,
        (
            SELECT error_log->>'message'
            FROM sync_runs
            WHERE connector_instance_id = p_connector_id
                AND status = 'failed'
            ORDER BY started_at DESC
            LIMIT 1
        ) as last_error
    FROM sync_runs
    WHERE connector_instance_id = p_connector_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_connector_sync_stats IS 'Returns aggregated sync statistics for a connector instance';

-- ============================================================================
-- SAMPLE DATA (for development/testing)
-- ============================================================================
-- Uncomment to populate test data

/*
-- Example connector instance
INSERT INTO connector_instances (org_id, connector_type, status, config) VALUES
('epiphan-dev', 'gong', 'connected', '{"workspace_id": "gong_ws_123"}'::jsonb);

-- Example sync run
INSERT INTO sync_runs (
    connector_instance_id,
    status,
    items_fetched,
    items_extracted,
    items_created,
    completed_at
) VALUES (
    (SELECT id FROM connector_instances WHERE connector_type = 'gong' LIMIT 1),
    'success',
    50,
    50,
    45,
    NOW()
);
*/

-- ============================================================================
-- MIGRATION VERIFICATION
-- ============================================================================
-- Run these queries after migration to verify

-- Check table creation
SELECT
    tablename,
    tableowner
FROM pg_tables
WHERE tablename IN ('connector_instances', 'sync_runs');

-- Check RLS policies
SELECT
    schemaname,
    tablename,
    policyname
FROM pg_policies
WHERE tablename IN ('connector_instances', 'sync_runs');

-- Check indexes
SELECT
    tablename,
    indexname
FROM pg_indexes
WHERE tablename IN ('connector_instances', 'sync_runs', 'knowledge_sources', 'knowledge')
ORDER BY tablename, indexname;

-- Check triggers
SELECT
    trigger_name,
    event_object_table,
    action_statement
FROM information_schema.triggers
WHERE event_object_table = 'connector_instances';

-- Conductor-AI Plugin System SQL Migration
-- Run in Supabase SQL Editor
-- Created: 2025-11-27

-- =============================================================================
-- AUDIT LOGS TABLE
-- Captures all tool executions across projects for full observability
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_id TEXT,  -- Links to agent session if applicable
    org_id TEXT NOT NULL,  -- Organization identifier
    action TEXT NOT NULL,  -- 'tool_call', 'scrape', 'enrich', 'outreach'
    tool_name TEXT NOT NULL,  -- Which tool was executed
    input_params JSONB,  -- Input arguments (sanitized)
    output_summary TEXT,  -- Brief result description
    target_entity TEXT,  -- 'lead:123', 'contractor:456'
    source_project TEXT,  -- 'dealer-scraper-mvp', 'sales-agent', 'conductor-ai'
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    duration_ms INTEGER,
    cost_usd DECIMAL(10, 6)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_audit_logs_org ON audit_logs(org_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tool ON audit_logs(tool_name);
CREATE INDEX IF NOT EXISTS idx_audit_logs_session ON audit_logs(session_id) WHERE session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_logs_success ON audit_logs(success) WHERE success = FALSE;

-- =============================================================================
-- TOOL EXECUTIONS TABLE
-- Detailed execution records with full input/output
-- =============================================================================

CREATE TABLE IF NOT EXISTS tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_log_id UUID REFERENCES audit_logs(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    input_json JSONB NOT NULL,
    output_json JSONB,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    retry_count INTEGER DEFAULT 0,
    tokens_used INTEGER,
    api_calls_made INTEGER DEFAULT 1
);

-- Index for audit log lookups
CREATE INDEX IF NOT EXISTS idx_tool_executions_audit ON tool_executions(audit_log_id);

-- =============================================================================
-- LEADS TABLE
-- Central lead storage shared between dealer-scraper-mvp and sales-agent
-- =============================================================================

CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT UNIQUE,  -- Deduplication key (e.g., 'generac:53202:ABC Solar')
    source_project TEXT NOT NULL,  -- 'dealer-scraper-mvp', 'sales-agent'

    -- Basic company info from scraping
    company_name TEXT NOT NULL,
    domain TEXT,
    phone TEXT,
    email TEXT,
    address JSONB,  -- {street, city, state, zip, lat, lng}

    -- Enrichment data
    enriched_at TIMESTAMPTZ,
    employee_count INTEGER,
    revenue_range TEXT,
    linkedin_url TEXT,
    contacts JSONB,  -- [{name, title, email, phone, linkedin}]

    -- License validation
    license_validated_at TIMESTAMPTZ,
    license_status TEXT,  -- 'valid', 'expired', 'revoked', 'unknown'
    license_number TEXT,
    license_expiry DATE,

    -- Qualification
    stage TEXT DEFAULT 'scraped',  -- 'scraped', 'enriched', 'qualified', 'contacted', 'converted'
    qualified_at TIMESTAMPTZ,
    qualification_score INTEGER,  -- 0-100
    qualification_reasons JSONB,  -- ['Has valid license', 'Revenue > $1M']

    -- Outreach
    contacted_at TIMESTAMPTZ,
    last_outreach_channel TEXT,  -- 'email', 'sms', 'linkedin'
    outreach_count INTEGER DEFAULT 0,

    -- CRM sync
    crm_synced_at TIMESTAMPTZ,
    crm_type TEXT,  -- 'close', 'hubspot', 'apollo'
    crm_id TEXT,  -- External CRM record ID

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    oem_brand TEXT,  -- 'generac', 'tesla', 'enphase', etc.
    zip_code TEXT
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_leads_external ON leads(external_id);
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source_project);
CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(stage);
CREATE INDEX IF NOT EXISTS idx_leads_qualified ON leads(qualification_score DESC) WHERE stage = 'qualified';
CREATE INDEX IF NOT EXISTS idx_leads_oem ON leads(oem_brand);
CREATE INDEX IF NOT EXISTS idx_leads_zip ON leads(zip_code);

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- Enable RLS for all tables
-- =============================================================================

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;

-- Policy for service role (full access)
-- Drop existing policies first (PostgreSQL doesn't support IF NOT EXISTS for policies)
DROP POLICY IF EXISTS "Service role full access audit_logs" ON audit_logs;
DROP POLICY IF EXISTS "Service role full access tool_executions" ON tool_executions;
DROP POLICY IF EXISTS "Service role full access leads" ON leads;

CREATE POLICY "Service role full access audit_logs"
    ON audit_logs FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access tool_executions"
    ON tool_executions FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access leads"
    ON leads FOR ALL
    USING (auth.role() = 'service_role');

-- =============================================================================
-- UPDATED_AT TRIGGER
-- Auto-update updated_at timestamp on leads
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_leads_updated_at ON leads;
CREATE TRIGGER update_leads_updated_at
    BEFORE UPDATE ON leads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- HELPFUL VIEWS
-- =============================================================================

-- Recent failures across all tools
CREATE OR REPLACE VIEW recent_failures AS
SELECT
    timestamp,
    tool_name,
    source_project,
    error_message,
    input_params
FROM audit_logs
WHERE success = FALSE
ORDER BY timestamp DESC
LIMIT 100;

-- Lead pipeline summary
CREATE OR REPLACE VIEW lead_pipeline AS
SELECT
    stage,
    COUNT(*) as count,
    AVG(qualification_score) as avg_score,
    COUNT(DISTINCT oem_brand) as unique_oems
FROM leads
GROUP BY stage
ORDER BY
    CASE stage
        WHEN 'scraped' THEN 1
        WHEN 'enriched' THEN 2
        WHEN 'qualified' THEN 3
        WHEN 'contacted' THEN 4
        WHEN 'converted' THEN 5
        ELSE 6
    END;

-- Tool usage stats
CREATE OR REPLACE VIEW tool_usage_stats AS
SELECT
    tool_name,
    source_project,
    COUNT(*) as total_calls,
    COUNT(*) FILTER (WHERE success = TRUE) as successful,
    COUNT(*) FILTER (WHERE success = FALSE) as failed,
    AVG(duration_ms) as avg_duration_ms,
    SUM(cost_usd) as total_cost
FROM audit_logs
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY tool_name, source_project
ORDER BY total_calls DESC;

-- =============================================================================
-- GRANT PERMISSIONS
-- =============================================================================

GRANT ALL ON audit_logs TO service_role;
GRANT ALL ON tool_executions TO service_role;
GRANT ALL ON leads TO service_role;
GRANT SELECT ON recent_failures TO service_role;
GRANT SELECT ON lead_pipeline TO service_role;
GRANT SELECT ON tool_usage_stats TO service_role;

-- Print success message
DO $$
BEGIN
    RAISE NOTICE 'Conductor-AI Plugin System SQL migration completed successfully!';
    RAISE NOTICE 'Tables created: audit_logs, tool_executions, leads';
    RAISE NOTICE 'Views created: recent_failures, lead_pipeline, tool_usage_stats';
END $$;

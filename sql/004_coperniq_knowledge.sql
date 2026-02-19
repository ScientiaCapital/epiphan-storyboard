-- Conductor-AI Coperniq Knowledge Base SQL Migration
-- Run in Supabase SQL Editor
-- Created: 2025-12-04
-- Purpose: Learning pipeline for intelligent storyboard generation

-- =============================================================================
-- KNOWLEDGE SOURCES TABLE
-- Tracks where knowledge comes from (Miro, Loom, Close CRM, Code)
-- =============================================================================

CREATE TABLE IF NOT EXISTS knowledge_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Source identification
    source_type TEXT NOT NULL CHECK (source_type IN (
        'close_crm_call',    -- Close CRM call recordings
        'close_crm_note',    -- Close CRM notes
        'loom_transcript',   -- Loom video transcripts
        'miro_board',        -- Miro board screenshots
        'engineer_code',     -- Code from engineers
        'gong_transcript',   -- Gong call transcripts (future)
        'manual_entry'       -- Manually added knowledge
    )),

    -- External references
    external_id TEXT,             -- ID in source system (Close call ID, Loom video ID, etc.)
    external_url TEXT,            -- URL to source (Loom share link, Miro board URL)
    file_path TEXT,               -- Local file path for code files

    -- Source metadata
    source_title TEXT,            -- Title/name of the source
    source_date TIMESTAMPTZ,      -- When the source was created (call date, etc.)
    duration_seconds INTEGER,     -- For calls/videos: duration
    participant_names TEXT[],     -- People involved (call participants, code author)

    -- Raw content storage
    raw_content TEXT,             -- Full transcript/code/notes (for re-extraction)
    content_hash TEXT,            -- SHA256 hash to detect duplicates

    -- Processing status
    extraction_status TEXT DEFAULT 'pending' CHECK (extraction_status IN (
        'pending',     -- Not yet processed
        'processing',  -- Currently extracting
        'completed',   -- Extraction done
        'failed'       -- Extraction failed
    )),
    extraction_error TEXT,        -- Error message if failed
    last_extracted_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- COPERNIQ KNOWLEDGE TABLE
-- Core knowledge entries extracted from sources
-- =============================================================================

CREATE TABLE IF NOT EXISTS coperniq_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to source
    source_id UUID REFERENCES knowledge_sources(id) ON DELETE SET NULL,

    -- Knowledge classification
    knowledge_type TEXT NOT NULL CHECK (knowledge_type IN (
        'feature',         -- Product feature (e.g., "Receptionist AI", "Document Engine")
        'pain_point',      -- Customer pain point (e.g., "PM lives in Excel", "Losing $3K/job")
        'metric',          -- Specific numbers (e.g., "$3K/job", "5 hours/week", "65% faster")
        'quote',           -- Verbatim customer quote worth reusing
        'approved_term',   -- Language that resonates (e.g., "Save time", "Get paid faster")
        'banned_term',     -- Language to avoid (e.g., "marketing campaign", "API")
        'objection',       -- Common sales objections
        'competitor',      -- Competitor mentions and context
        'success_story',   -- Customer win/testimonial
        'use_case',        -- Specific use case (e.g., "solar permit tracking")
        'persona'          -- ICP persona insight
    )),

    -- The knowledge itself
    content TEXT NOT NULL,              -- The actual knowledge content
    context TEXT,                       -- Surrounding context (what was being discussed)
    verbatim BOOLEAN DEFAULT false,     -- Is this an exact quote vs paraphrased?

    -- Relevance metadata
    audience TEXT[] DEFAULT '{}',       -- Which audiences this applies to (c_suite, field_crew, etc.)
    industries TEXT[] DEFAULT '{}',     -- Which industries (solar, hvac, electrical, etc.)
    product_areas TEXT[] DEFAULT '{}',  -- Product areas (Intelligence, Sales Cloud, PM Cloud, etc.)

    -- Quality signals
    confidence_score FLOAT DEFAULT 0.8 CHECK (confidence_score >= 0 AND confidence_score <= 1),
    usage_count INTEGER DEFAULT 0,      -- How many times used in storyboards
    last_used_at TIMESTAMPTZ,           -- When last used
    effectiveness_score FLOAT,          -- If tracked: did storyboard perform well?

    -- Source attribution
    speaker_name TEXT,                  -- Who said it (for quotes)
    speaker_role TEXT,                  -- Their role (CEO, PM, etc.)
    company_name TEXT,                  -- Which company (for anonymization)

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- KNOWLEDGE TAGS TABLE
-- Flexible tagging for knowledge items
-- =============================================================================

CREATE TABLE IF NOT EXISTS knowledge_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_id UUID NOT NULL REFERENCES coperniq_knowledge(id) ON DELETE CASCADE,

    tag_type TEXT NOT NULL CHECK (tag_type IN (
        'topic',           -- Topic tag (e.g., "invoicing", "scheduling")
        'sentiment',       -- Sentiment (positive, negative, neutral)
        'priority',        -- Priority level (high, medium, low)
        'status',          -- Status (active, deprecated, review_needed)
        'source_quality',  -- Source quality (verified, unverified)
        'custom'           -- Custom tags
    )),
    tag_value TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(knowledge_id, tag_type, tag_value)
);

-- =============================================================================
-- EXTRACTION LOGS TABLE
-- Audit trail for extraction runs
-- =============================================================================

CREATE TABLE IF NOT EXISTS knowledge_extraction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What was extracted
    source_id UUID NOT NULL REFERENCES knowledge_sources(id) ON DELETE CASCADE,

    -- Extraction details
    extraction_model TEXT,            -- Model used (deepseek-v3, qwen-vl, etc.)
    extraction_prompt_version TEXT,   -- Prompt version for reproducibility

    -- Results
    items_extracted INTEGER DEFAULT 0,
    items_created INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,
    items_skipped INTEGER DEFAULT 0,  -- Duplicates/low-quality

    -- Raw extraction output (for debugging)
    raw_extraction_output JSONB,

    -- Timing
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    execution_time_ms INTEGER,

    -- Status
    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    error_message TEXT
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Knowledge sources
CREATE INDEX IF NOT EXISTS idx_knowledge_sources_type ON knowledge_sources(source_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_sources_status ON knowledge_sources(extraction_status);
CREATE INDEX IF NOT EXISTS idx_knowledge_sources_external_id ON knowledge_sources(source_type, external_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_sources_hash ON knowledge_sources(content_hash);

-- Coperniq knowledge
CREATE INDEX IF NOT EXISTS idx_coperniq_knowledge_type ON coperniq_knowledge(knowledge_type);
CREATE INDEX IF NOT EXISTS idx_coperniq_knowledge_source ON coperniq_knowledge(source_id);
CREATE INDEX IF NOT EXISTS idx_coperniq_knowledge_audience ON coperniq_knowledge USING GIN(audience);
CREATE INDEX IF NOT EXISTS idx_coperniq_knowledge_industries ON coperniq_knowledge USING GIN(industries);
CREATE INDEX IF NOT EXISTS idx_coperniq_knowledge_product_areas ON coperniq_knowledge USING GIN(product_areas);
CREATE INDEX IF NOT EXISTS idx_coperniq_knowledge_confidence ON coperniq_knowledge(confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_coperniq_knowledge_usage ON coperniq_knowledge(usage_count DESC);

-- Full-text search on knowledge content
CREATE INDEX IF NOT EXISTS idx_coperniq_knowledge_content_search
ON coperniq_knowledge USING GIN(to_tsvector('english', content || ' ' || COALESCE(context, '')));

-- Knowledge tags
CREATE INDEX IF NOT EXISTS idx_knowledge_tags_knowledge ON knowledge_tags(knowledge_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_tags_type_value ON knowledge_tags(tag_type, tag_value);

-- Extraction logs
CREATE INDEX IF NOT EXISTS idx_extraction_logs_source ON knowledge_extraction_logs(source_id);
CREATE INDEX IF NOT EXISTS idx_extraction_logs_status ON knowledge_extraction_logs(status);

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================================================

ALTER TABLE knowledge_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE coperniq_knowledge ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_extraction_logs ENABLE ROW LEVEL SECURITY;

-- Service role has full access
CREATE POLICY "Service role full access knowledge_sources"
    ON knowledge_sources FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access coperniq_knowledge"
    ON coperniq_knowledge FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access knowledge_tags"
    ON knowledge_tags FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access knowledge_extraction_logs"
    ON knowledge_extraction_logs FOR ALL
    USING (auth.role() = 'service_role');

-- =============================================================================
-- UPDATED_AT TRIGGERS
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_knowledge_sources_updated_at
    BEFORE UPDATE ON knowledge_sources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_coperniq_knowledge_updated_at
    BEFORE UPDATE ON coperniq_knowledge
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- HELPER VIEWS
-- =============================================================================

-- Active knowledge by type: Most useful knowledge items
CREATE OR REPLACE VIEW active_knowledge AS
SELECT
    ck.id,
    ck.knowledge_type,
    ck.content,
    ck.context,
    ck.verbatim,
    ck.audience,
    ck.industries,
    ck.product_areas,
    ck.confidence_score,
    ck.usage_count,
    ck.speaker_name,
    ck.company_name,
    ks.source_type,
    ks.source_title,
    ks.source_date
FROM coperniq_knowledge ck
LEFT JOIN knowledge_sources ks ON ck.source_id = ks.id
WHERE ck.confidence_score >= 0.7
ORDER BY ck.usage_count DESC, ck.confidence_score DESC;

-- Knowledge by type summary
CREATE OR REPLACE VIEW knowledge_type_summary AS
SELECT
    knowledge_type,
    COUNT(*) as total_items,
    ROUND(AVG(confidence_score)::NUMERIC, 2) as avg_confidence,
    SUM(usage_count) as total_usage,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') as added_last_7d
FROM coperniq_knowledge
GROUP BY knowledge_type
ORDER BY total_items DESC;

-- Source ingestion status
CREATE OR REPLACE VIEW source_ingestion_status AS
SELECT
    source_type,
    extraction_status,
    COUNT(*) as source_count,
    MAX(last_extracted_at) as latest_extraction
FROM knowledge_sources
GROUP BY source_type, extraction_status
ORDER BY source_type, extraction_status;

-- Pain points for storyboards (most useful for marketing)
CREATE OR REPLACE VIEW pain_points_for_storyboards AS
SELECT
    content as pain_point,
    context,
    speaker_role,
    company_name,
    industries,
    confidence_score,
    usage_count
FROM coperniq_knowledge
WHERE knowledge_type = 'pain_point'
  AND confidence_score >= 0.7
ORDER BY usage_count DESC, confidence_score DESC
LIMIT 100;

-- Approved terms for copy
CREATE OR REPLACE VIEW approved_terms AS
SELECT
    content as term,
    context as usage_context,
    audience,
    usage_count,
    confidence_score
FROM coperniq_knowledge
WHERE knowledge_type = 'approved_term'
  AND confidence_score >= 0.8
ORDER BY usage_count DESC;

-- Banned terms to avoid
CREATE OR REPLACE VIEW banned_terms AS
SELECT
    content as term,
    context as reason,
    created_at
FROM coperniq_knowledge
WHERE knowledge_type = 'banned_term'
ORDER BY created_at DESC;

-- Feature catalog
CREATE OR REPLACE VIEW feature_catalog AS
SELECT
    content as feature_name,
    context as description,
    product_areas,
    audience,
    usage_count
FROM coperniq_knowledge
WHERE knowledge_type = 'feature'
ORDER BY usage_count DESC;

-- =============================================================================
-- SEARCH FUNCTIONS
-- =============================================================================

-- Full-text search for knowledge
CREATE OR REPLACE FUNCTION search_knowledge(
    search_query TEXT,
    knowledge_types TEXT[] DEFAULT NULL,
    min_confidence FLOAT DEFAULT 0.5,
    max_results INTEGER DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    knowledge_type TEXT,
    content TEXT,
    context TEXT,
    confidence_score FLOAT,
    usage_count INTEGER,
    source_type TEXT,
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ck.id,
        ck.knowledge_type,
        ck.content,
        ck.context,
        ck.confidence_score,
        ck.usage_count,
        ks.source_type,
        ts_rank(
            to_tsvector('english', ck.content || ' ' || COALESCE(ck.context, '')),
            plainto_tsquery('english', search_query)
        ) as rank
    FROM coperniq_knowledge ck
    LEFT JOIN knowledge_sources ks ON ck.source_id = ks.id
    WHERE
        to_tsvector('english', ck.content || ' ' || COALESCE(ck.context, ''))
        @@ plainto_tsquery('english', search_query)
        AND ck.confidence_score >= min_confidence
        AND (knowledge_types IS NULL OR ck.knowledge_type = ANY(knowledge_types))
    ORDER BY rank DESC, ck.usage_count DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Get knowledge for storyboard generation
CREATE OR REPLACE FUNCTION get_knowledge_for_storyboard(
    target_audience TEXT DEFAULT 'c_suite',
    target_industry TEXT DEFAULT NULL,
    knowledge_types TEXT[] DEFAULT ARRAY['pain_point', 'metric', 'approved_term', 'feature']
)
RETURNS TABLE (
    knowledge_type TEXT,
    content TEXT,
    context TEXT,
    confidence_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ck.knowledge_type,
        ck.content,
        ck.context,
        ck.confidence_score
    FROM coperniq_knowledge ck
    WHERE
        ck.knowledge_type = ANY(knowledge_types)
        AND ck.confidence_score >= 0.7
        AND (
            target_audience = ANY(ck.audience)
            OR array_length(ck.audience, 1) IS NULL
            OR array_length(ck.audience, 1) = 0
        )
        AND (
            target_industry IS NULL
            OR target_industry = ANY(ck.industries)
            OR array_length(ck.industries, 1) IS NULL
            OR array_length(ck.industries, 1) = 0
        )
    ORDER BY ck.confidence_score DESC, ck.usage_count DESC
    LIMIT 50;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- GRANT PERMISSIONS
-- =============================================================================

GRANT ALL ON knowledge_sources TO service_role;
GRANT ALL ON coperniq_knowledge TO service_role;
GRANT ALL ON knowledge_tags TO service_role;
GRANT ALL ON knowledge_extraction_logs TO service_role;

GRANT SELECT ON active_knowledge TO service_role;
GRANT SELECT ON knowledge_type_summary TO service_role;
GRANT SELECT ON source_ingestion_status TO service_role;
GRANT SELECT ON pain_points_for_storyboards TO service_role;
GRANT SELECT ON approved_terms TO service_role;
GRANT SELECT ON banned_terms TO service_role;
GRANT SELECT ON feature_catalog TO service_role;

-- =============================================================================
-- SEED DATA: Initial banned terms (from coperniq_presets.py)
-- =============================================================================

INSERT INTO coperniq_knowledge (knowledge_type, content, context, confidence_score) VALUES
-- Technical jargon to avoid
('banned_term', 'API', 'Technical term - contractors don''t use this language', 1.0),
('banned_term', 'microservices', 'Technical architecture term', 1.0),
('banned_term', 'backend', 'Technical term', 1.0),
('banned_term', 'frontend', 'Technical term', 1.0),
('banned_term', 'async', 'Technical programming term', 1.0),
('banned_term', 'database schema', 'Technical database term', 1.0),

-- Marketing fluff to avoid
('banned_term', 'revolutionary', 'Marketing fluff - sounds salesy', 1.0),
('banned_term', 'disruptive', 'Marketing fluff', 1.0),
('banned_term', 'game-changing', 'Marketing fluff', 1.0),
('banned_term', 'best-in-class', 'Marketing fluff', 1.0),
('banned_term', 'synergy', 'Corporate jargon', 1.0),
('banned_term', 'paradigm', 'Corporate jargon', 1.0),
('banned_term', 'holistic', 'Corporate jargon', 1.0),

-- Marketing language (internal GTM - not for external content)
('banned_term', 'marketing campaign', 'Internal GTM language - not for ICP/VC content', 1.0),
('banned_term', 'marketing strategy', 'Internal GTM language', 1.0),
('banned_term', 'brand awareness', 'Internal GTM language', 1.0),
('banned_term', 'promotional', 'Internal GTM language', 1.0),
('banned_term', 'advertising', 'Internal GTM language', 1.0),
('banned_term', 'drive engagement', 'Internal GTM language', 1.0),
('banned_term', 'target audience', 'Internal GTM language', 1.0),
('banned_term', 'buyer persona', 'Internal GTM language', 1.0),
('banned_term', 'customer journey', 'Internal GTM language', 1.0),
('banned_term', 'content marketing', 'Internal GTM language', 1.0),
('banned_term', 'lead generation campaign', 'Internal GTM language', 1.0)
ON CONFLICT DO NOTHING;

-- Seed approved terms (from coperniq_presets.py)
INSERT INTO coperniq_knowledge (knowledge_type, content, context, audience, confidence_score) VALUES
('approved_term', 'saves you time', 'Direct benefit language contractors understand', ARRAY['business_owner', 'c_suite', 'btl_champion'], 1.0),
('approved_term', 'gets you paid faster', 'Cash flow focus - critical for contractors', ARRAY['business_owner', 'c_suite'], 1.0),
('approved_term', 'one less headache', 'Relatable pain reduction', ARRAY['business_owner', 'btl_champion'], 1.0),
('approved_term', 'works on your phone in the field', 'Mobile-first messaging for field workers', ARRAY['field_crew', 'btl_champion'], 1.0),
('approved_term', 'no more spreadsheets', 'Anti-Excel positioning', ARRAY['business_owner', 'c_suite', 'btl_champion'], 1.0),
('approved_term', 'see everything in one place', 'Consolidation value prop', ARRAY['c_suite', 'btl_champion'], 1.0)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- SUCCESS MESSAGE
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=================================================================';
    RAISE NOTICE '  COPERNIQ KNOWLEDGE BASE - Migration Complete';
    RAISE NOTICE '=================================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - knowledge_sources: Track ingestion sources (Close CRM, Loom, Miro, Code)';
    RAISE NOTICE '  - coperniq_knowledge: Core knowledge entries (features, pain points, metrics)';
    RAISE NOTICE '  - knowledge_tags: Flexible tagging system';
    RAISE NOTICE '  - knowledge_extraction_logs: Audit trail for extractions';
    RAISE NOTICE '';
    RAISE NOTICE 'Views created:';
    RAISE NOTICE '  - active_knowledge: High-confidence knowledge items';
    RAISE NOTICE '  - knowledge_type_summary: Stats by knowledge type';
    RAISE NOTICE '  - pain_points_for_storyboards: Ready-to-use pain points';
    RAISE NOTICE '  - approved_terms / banned_terms: Language guidelines';
    RAISE NOTICE '  - feature_catalog: Product features';
    RAISE NOTICE '';
    RAISE NOTICE 'Functions created:';
    RAISE NOTICE '  - search_knowledge(): Full-text search across knowledge';
    RAISE NOTICE '  - get_knowledge_for_storyboard(): Get relevant knowledge for generation';
    RAISE NOTICE '';
    RAISE NOTICE 'Seed data:';
    RAISE NOTICE '  - 22 banned terms (technical jargon, marketing fluff, GTM language)';
    RAISE NOTICE '  - 6 approved terms (contractor-friendly language)';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Build Close CRM ingestion pipeline';
    RAISE NOTICE '  2. Build Loom transcript ingestion';
    RAISE NOTICE '  3. Build Miro board screenshot extraction';
    RAISE NOTICE '  4. Update storyboard generator to query knowledge base';
    RAISE NOTICE '';
END $$;

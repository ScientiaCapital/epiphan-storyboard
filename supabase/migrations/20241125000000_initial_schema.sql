-- Conductor-AI Initial Schema
-- Organizations, Users, API Keys, Agent Sessions, Usage Tracking

-- ===========================================
-- 1. ORGANIZATIONS (Tenants)
-- ===========================================
CREATE TABLE public.organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    tier TEXT DEFAULT 'free' CHECK (tier IN ('free', 'basic', 'pro', 'enterprise')),
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_organizations_slug ON public.organizations(slug);

-- ===========================================
-- 2. USER PROFILES (extends auth.users)
-- ===========================================
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    organization_id UUID REFERENCES public.organizations(id),
    role TEXT DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_profiles_org ON public.profiles(organization_id);

-- ===========================================
-- 3. API KEYS
-- ===========================================
CREATE TABLE public.api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    created_by UUID REFERENCES auth.users(id),
    name TEXT NOT NULL DEFAULT 'Default',
    key_hash TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    rate_limit_rpm INTEGER DEFAULT 60,
    rate_limit_tpd INTEGER DEFAULT 100000,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_api_keys_hash ON public.api_keys(key_hash);
CREATE INDEX idx_api_keys_org ON public.api_keys(organization_id);
CREATE INDEX idx_api_keys_prefix ON public.api_keys(key_prefix);

-- ===========================================
-- 4. AGENT SESSIONS
-- ===========================================
CREATE TABLE public.agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    api_key_id UUID REFERENCES public.api_keys(id),

    -- Configuration
    agent_type TEXT NOT NULL DEFAULT 'react' CHECK (agent_type IN ('react', 'plan_execute', 'custom')),
    model TEXT NOT NULL,
    system_prompt TEXT,
    max_steps INTEGER DEFAULT 20,

    -- Status
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    error_message TEXT,

    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Usage
    total_steps INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost_cents NUMERIC(10, 4) DEFAULT 0,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_sessions_org ON public.agent_sessions(organization_id);
CREATE INDEX idx_sessions_status ON public.agent_sessions(status);
CREATE INDEX idx_sessions_created ON public.agent_sessions(created_at DESC);

-- ===========================================
-- 5. AGENT STEPS (Message History)
-- ===========================================
CREATE TABLE public.agent_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.agent_sessions(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,

    -- Content
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool', 'system')),
    content TEXT,

    -- Tool interactions
    tool_calls JSONB,
    tool_results JSONB,

    -- Metrics
    tokens_used INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,

    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(session_id, step_number)
);

CREATE INDEX idx_steps_session ON public.agent_steps(session_id);

-- ===========================================
-- 6. TOOL EXECUTIONS
-- ===========================================
CREATE TABLE public.tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.agent_sessions(id) ON DELETE CASCADE,
    step_id UUID REFERENCES public.agent_steps(id),

    -- Tool info
    tool_name TEXT NOT NULL,
    tool_category TEXT,

    -- Execution
    arguments JSONB NOT NULL,
    result JSONB,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    error_message TEXT,

    -- Metrics
    execution_time_ms INTEGER,

    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_tool_exec_session ON public.tool_executions(session_id);

-- ===========================================
-- 7. USAGE RECORDS
-- ===========================================
CREATE TABLE public.usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id),
    api_key_id UUID REFERENCES public.api_keys(id),
    session_id UUID REFERENCES public.agent_sessions(id),
    request_id TEXT,

    -- Request details
    model TEXT NOT NULL,
    provider TEXT NOT NULL,

    -- Token usage
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,

    -- Cost
    cost_cents NUMERIC(10, 4) DEFAULT 0,

    -- Performance
    latency_ms INTEGER,

    -- Status
    success BOOLEAN DEFAULT true,
    error_code TEXT,

    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_usage_org_time ON public.usage_records(organization_id, created_at);
CREATE INDEX idx_usage_api_key ON public.usage_records(api_key_id);

-- ===========================================
-- 8. AUDIT LOGS
-- ===========================================
CREATE TABLE public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES public.organizations(id),
    user_id UUID REFERENCES auth.users(id),
    api_key_id UUID REFERENCES public.api_keys(id),

    -- Event
    event_type TEXT NOT NULL,
    severity TEXT DEFAULT 'info' CHECK (severity IN ('info', 'warning', 'error', 'critical')),

    -- Context
    request_id TEXT,
    session_id UUID,
    ip_address INET,

    -- Details
    details JSONB DEFAULT '{}'::jsonb,

    -- Integrity
    previous_hash TEXT,
    event_hash TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_org_time ON public.audit_logs(organization_id, created_at);
CREATE INDEX idx_audit_event_type ON public.audit_logs(event_type);

-- ===========================================
-- 9. ROW LEVEL SECURITY
-- ===========================================

ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tool_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- Function to get user's organization IDs
CREATE OR REPLACE FUNCTION public.get_user_org_ids()
RETURNS SETOF UUID AS $$
BEGIN
    RETURN QUERY
    SELECT organization_id FROM public.profiles
    WHERE id = auth.uid() AND organization_id IS NOT NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Organizations: users see their own orgs
CREATE POLICY "Users can view own organizations" ON public.organizations
    FOR SELECT USING (id IN (SELECT public.get_user_org_ids()));

CREATE POLICY "Users can update own organizations" ON public.organizations
    FOR UPDATE USING (id IN (SELECT public.get_user_org_ids()));

-- Profiles: users see their own profile and org members
CREATE POLICY "Users can view own profile" ON public.profiles
    FOR SELECT USING (id = auth.uid() OR organization_id IN (SELECT public.get_user_org_ids()));

CREATE POLICY "Users can update own profile" ON public.profiles
    FOR UPDATE USING (id = auth.uid());

-- API Keys: users see keys from their orgs
CREATE POLICY "Users can view org api keys" ON public.api_keys
    FOR SELECT USING (organization_id IN (SELECT public.get_user_org_ids()));

CREATE POLICY "Users can create org api keys" ON public.api_keys
    FOR INSERT WITH CHECK (organization_id IN (SELECT public.get_user_org_ids()));

CREATE POLICY "Users can update org api keys" ON public.api_keys
    FOR UPDATE USING (organization_id IN (SELECT public.get_user_org_ids()));

CREATE POLICY "Users can delete org api keys" ON public.api_keys
    FOR DELETE USING (organization_id IN (SELECT public.get_user_org_ids()));

-- Agent Sessions: users see sessions from their orgs
CREATE POLICY "Users can view org sessions" ON public.agent_sessions
    FOR SELECT USING (organization_id IN (SELECT public.get_user_org_ids()));

CREATE POLICY "Users can create org sessions" ON public.agent_sessions
    FOR INSERT WITH CHECK (organization_id IN (SELECT public.get_user_org_ids()));

-- Agent Steps: users see steps from their sessions
CREATE POLICY "Users can view org steps" ON public.agent_steps
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM public.agent_sessions WHERE id = session_id AND organization_id IN (SELECT public.get_user_org_ids()))
    );

-- Tool Executions: users see executions from their sessions
CREATE POLICY "Users can view org tool executions" ON public.tool_executions
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM public.agent_sessions WHERE id = session_id AND organization_id IN (SELECT public.get_user_org_ids()))
    );

-- Usage Records: users see usage from their orgs
CREATE POLICY "Users can view org usage" ON public.usage_records
    FOR SELECT USING (organization_id IN (SELECT public.get_user_org_ids()));

-- Audit Logs: users see audit logs from their orgs
CREATE POLICY "Users can view org audit logs" ON public.audit_logs
    FOR SELECT USING (organization_id IN (SELECT public.get_user_org_ids()));

-- ===========================================
-- 10. TRIGGERS
-- ===========================================

-- Auto-create profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
    new_org_id UUID;
BEGIN
    -- Create a personal organization for the user
    INSERT INTO public.organizations (name, slug, tier)
    VALUES (
        COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)) || '''s Workspace',
        LOWER(REPLACE(split_part(NEW.email, '@', 1), '.', '-')) || '-' || SUBSTR(gen_random_uuid()::TEXT, 1, 8),
        'free'
    )
    RETURNING id INTO new_org_id;

    -- Create the user profile
    INSERT INTO public.profiles (id, email, full_name, organization_id, role)
    VALUES (
        NEW.id,
        NEW.email,
        NEW.raw_user_meta_data->>'full_name',
        new_org_id,
        'owner'
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Update timestamps
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_organizations_updated_at
    BEFORE UPDATE ON public.organizations
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- ===========================================
-- 11. SERVICE ROLE POLICIES (for backend)
-- ===========================================
-- These allow the service role to bypass RLS for backend operations

CREATE POLICY "Service role can do anything on organizations" ON public.organizations
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can do anything on profiles" ON public.profiles
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can do anything on api_keys" ON public.api_keys
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can do anything on agent_sessions" ON public.agent_sessions
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can do anything on agent_steps" ON public.agent_steps
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can do anything on tool_executions" ON public.tool_executions
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can do anything on usage_records" ON public.usage_records
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can do anything on audit_logs" ON public.audit_logs
    FOR ALL USING (auth.role() = 'service_role');

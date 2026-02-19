-- ============================================================================
-- Billing Schema Migration
-- ============================================================================
-- Adds Stripe billing columns to organizations table and creates
-- billing_events table for audit trail.
--
-- Prerequisites:
--   - organizations table must exist (from 001_audit_and_leads.sql)
--
-- Run this migration in Supabase SQL Editor or via CLI.
-- ============================================================================

-- Add billing columns to organizations table
ALTER TABLE public.organizations
ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT UNIQUE,
ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT,
ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'free',
ADD COLUMN IF NOT EXISTS current_period_end TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS cancel_at_period_end BOOLEAN DEFAULT FALSE;

-- Create index for customer lookup (faster webhook handling)
CREATE INDEX IF NOT EXISTS idx_organizations_stripe_customer
ON public.organizations(stripe_customer_id)
WHERE stripe_customer_id IS NOT NULL;

-- Create index for subscription lookup
CREATE INDEX IF NOT EXISTS idx_organizations_stripe_subscription
ON public.organizations(stripe_subscription_id)
WHERE stripe_subscription_id IS NOT NULL;

-- ============================================================================
-- Billing Events Table (Audit Trail)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.billing_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES public.organizations(id) ON DELETE CASCADE,
    stripe_event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_billing_events_org
ON public.billing_events(organization_id);

CREATE INDEX IF NOT EXISTS idx_billing_events_type
ON public.billing_events(event_type);

CREATE INDEX IF NOT EXISTS idx_billing_events_created
ON public.billing_events(created_at DESC);

-- ============================================================================
-- Row Level Security
-- ============================================================================

ALTER TABLE public.billing_events ENABLE ROW LEVEL SECURITY;

-- Service role has full access (for webhook processing)
CREATE POLICY IF NOT EXISTS "Service role full access billing_events"
ON public.billing_events
FOR ALL
USING (auth.role() = 'service_role');

-- Organizations can read their own billing events
CREATE POLICY IF NOT EXISTS "Orgs can read own billing_events"
ON public.billing_events
FOR SELECT
USING (
    organization_id IN (
        SELECT id FROM public.organizations
        WHERE id = organization_id
    )
);

-- ============================================================================
-- Billing Analytics View
-- ============================================================================

CREATE OR REPLACE VIEW public.billing_summary AS
SELECT
    o.id AS org_id,
    o.name AS org_name,
    o.tier,
    o.subscription_status,
    o.stripe_customer_id,
    o.stripe_subscription_id,
    o.current_period_end,
    o.cancel_at_period_end,
    COUNT(be.id) AS total_billing_events,
    MAX(be.created_at) AS last_billing_event
FROM public.organizations o
LEFT JOIN public.billing_events be ON o.id = be.organization_id
GROUP BY o.id, o.name, o.tier, o.subscription_status,
         o.stripe_customer_id, o.stripe_subscription_id,
         o.current_period_end, o.cancel_at_period_end;

-- ============================================================================
-- Grant Permissions
-- ============================================================================

GRANT SELECT ON public.billing_summary TO authenticated;
GRANT SELECT, INSERT ON public.billing_events TO service_role;
GRANT UPDATE (tier, stripe_customer_id, stripe_subscription_id,
              subscription_status, current_period_end, cancel_at_period_end)
ON public.organizations TO service_role;

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON COLUMN public.organizations.stripe_customer_id IS 'Stripe customer ID (cus_xxx)';
COMMENT ON COLUMN public.organizations.stripe_subscription_id IS 'Active Stripe subscription ID (sub_xxx)';
COMMENT ON COLUMN public.organizations.subscription_status IS 'Subscription status: free, active, canceled, past_due, etc.';
COMMENT ON COLUMN public.organizations.current_period_end IS 'When current billing period ends';
COMMENT ON COLUMN public.organizations.cancel_at_period_end IS 'Whether subscription will cancel at period end';

COMMENT ON TABLE public.billing_events IS 'Audit trail of Stripe webhook events for each organization';

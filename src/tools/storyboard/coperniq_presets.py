"""
Coperniq ICP Presets and Sanitization Rules
============================================

Defines Ideal Customer Profile (ICP) configurations and content
sanitization rules for executive storyboard generation.

Target: Multi-trade contractors (MEP+energy) with $5M+ revenue
Golden Rule: If a competitor could use the info to copy us, strip it.
             If a 5th grader couldn't understand it, simplify it.
"""

from typing import Any
from enum import Enum


# =============================================
# Coperniq Brand Identity (Scraped 2025-12-04)
# =============================================

COPERNIQ_BRAND = {
    "company": "Coperniq",
    "tagline": "One platform to run every trade: build, dispatch, service",
    "website": "https://coperniq.io",

    # Visual Identity (extracted from coperniq.io 2025-12-04)
    "colors": {
        "primary": "#23433E",        # Dark teal/forest green (CTA buttons, primary actions)
        "accent": "#2D9688",         # Teal (accent text like "$5M+ Contractors")
        "text": "#333333",           # Dark gray (body text, logo)
        "background": "#FDFDFC",     # Off-white (body background)
        "hero_bg": "#DDEDEB",        # Light mint/sage (hero section background)
        "light_gray": "#F7F6F3",     # Warm gray (alternate sections)
    },
    "typography": {
        "primary": "Albert Sans",
        "weights": [400, 500, 600],
        "style": "Clean, geometric sans-serif",
    },
    "visual_aesthetic": "Modern, professional, enterprise. Minimal grid patterns, photography-heavy with field workers. Corporate but approachable.",

    # Key Headlines from Landing Pages
    "headlines": [
        "Built for Complex Operations. Designed for $5M+ Contractors",
        "Quote, Book, Pay, Dispatch, and Grow",
        "One platform for your entire operation",
        "AI for the Trades—Not just call answering",
        "Construction CRM that runs the work — not just the contacts",
        "Plan the job, schedule the crews, collect the cash",
    ],

    # Proven Results (for storyboards)
    "proof_points": {
        "completion_rate": "99% first-time completion rate",
        "time_to_completion": "45 days faster to project completion",
        "payment_speed": "65% faster payment collection",
        "cost_savings": "$3,000 soft-cost savings per install",
        "dso_improvement": "24/7 faster DSO (cash collection)",
        "scale_story": "Scaled from 20 to 100+ installs/month without adding staff",
    },

    # AI Capabilities (for VC/innovation focus)
    "ai_features": [
        "AI Receptionist - Answers calls, books work orders 24/7",
        "Smart Forms - Converts paper inspections to digital via AI",
        "Nameplate Scanning - Capture make, model, serial in one shot",
        "Project Copilot - Ask questions within job records",
        "Ask AI Views - Describe data slice you want to see",
        "Quote Generation - Good/better/best options auto-generated",
    ],

    # Product Categories
    "feature_categories": {
        "sales": ["CRM", "Quotes/Proposals", "E-signatures", "Lead conversion"],
        "operations": ["Field service", "Dispatch", "Scheduling", "Mobile app (offline)"],
        "admin": ["Document management", "Payment processing", "Accounting sync"],
        "integrations": ["QuickBooks", "Xero", "NetSuite", "Design tools", "Hardware APIs"],
    },
}


class AudiencePersona(str, Enum):
    """Target audience personas for storyboard content."""

    BUSINESS_OWNER = "business_owner"
    C_SUITE = "c_suite"
    BTL_CHAMPION = "btl_champion"
    TOP_TIER_VC = "top_tier_vc"
    FIELD_CREW = "field_crew"


class StoryboardStage(str, Enum):
    """Storyboard stage for 3-wave BDR cadence."""

    PREVIEW = "preview"  # Wave 1: "Here's what we're building"
    DEMO = "demo"  # Wave 2: "Here it is working"
    SHIPPED = "shipped"  # Wave 3: "It's live + what's next"


# =============================================
# Coperniq Ideal Customer Profile (ICP)
# =============================================

COPERNIQ_ICP = {
    "name": "coperniq_mep",
    "target": "Multi-trade contractors (MEP+energy)",
    "characteristics": {
        "revenue": "$5M+",
        "style": "Asset-centric, self-perform",
        "trades": ["mechanical", "electrical", "plumbing", "energy", "solar", "hvac"],
        "pain_points": [
            "Spreadsheet chaos across multiple jobs",
            "Missed deadlines and change orders",
            "Crew coordination nightmares",
            "Getting paid takes forever",
            "No visibility into job profitability",
        ],
    },
    "audience_personas": {
        AudiencePersona.BUSINESS_OWNER: {
            "title": "Business Owner / Founder",
            "cares_about": ["profit", "growth", "less headaches", "family time"],
            "tone": "Direct, bottom-line focused, respect their time",
            # COI: Loss aversion hits harder - "what you're losing every day"
            "value_angle": "COI",  # Cost of Inaction - emphasize what they LOSE by not acting
            "value_framing": "Every day without this = money walking out the door. Your competitors already figured this out.",
            "hooks": [
                "Stop losing money on jobs you thought were profitable",
                "Your competition is already using this",
                "What if you could leave the office at 5pm?",
            ],
            # PERSONA POLISH - Voice & Style
            "voice_tone": "Founder anxiety meets pragmatic hope. Speak to the weight on their shoulders.",
            "vocabulary": [
                "bleeding money",
                "my guys",
                "cash flow",
                "keeping the lights on",
                "I built this",
                "sleepless nights",
                "finally get control",
                "my baby",
                "skin in the game",
                "make payroll",
            ],
            "forbidden_phrases": [
                "stakeholders",
                "enterprise solution",
                "synergize",
                "leverage",
                "robust platform",
                "digital transformation",
            ],
            "default_visual_style": "isometric",  # Modern SaaS feel, Stripe/Linear quality
        },
        AudiencePersona.C_SUITE: {
            "title": "CEO / CFO / COO",
            "cares_about": ["ROI", "competitive edge", "scalability", "data-driven decisions"],
            "tone": "Strategic, numbers-focused, executive-level",
            # ROI: They need numbers for the board, spreadsheet justification
            "value_angle": "ROI",  # Return on Investment - show the math
            "value_framing": "Here's the math: X invested → Y returned. Payback in Z months.",
            "hooks": [
                "See your entire operation at a glance",
                "Make decisions based on real data, not gut feelings",
                "Scale without adding overhead",
            ],
            # PERSONA POLISH - Voice & Style
            "voice_tone": "Boardroom brevity. Every word earns its place. Numbers speak louder than adjectives.",
            "vocabulary": [
                "margin improvement",
                "operational leverage",
                "unit economics",
                "payback period",
                "scale efficiently",
                "competitive moat",
                "data-driven",
                "visibility",
                "reduce overhead",
                "strategic advantage",
            ],
            "forbidden_phrases": [
                "game-changing",
                "revolutionary",
                "best-in-class",
                "cutting-edge",
                "paradigm shift",
                "synergy",
            ],
            "default_visual_style": "data_viz",  # McKinsey deck style, numbers prominent
        },
        AudiencePersona.BTL_CHAMPION: {
            "title": "Project Manager / Operations Manager",
            "cares_about": ["easier day-to-day", "team coordination", "less fire-fighting"],
            "tone": "Empathetic, practical, day-in-the-life focused",
            "value_angle": "COI",  # Cost of Inaction - the daily cost of not having this
            "value_framing": "Every fire you're fighting today? There's a tool that prevents it. Finally get ahead instead of always catching up.",
            "hooks": [
                "Your crews will actually use this",
                "No more chasing down updates",
                "Finally get the coordination problem under control",
            ],
            # PERSONA POLISH - Voice & Style
            "voice_tone": "Internal advocate energy. Speak to the daily grind and real frustrations.",
            "vocabulary": [
                "fires to put out",
                "chasing updates",
                "prove it works",
                "the team will actually use this",
                "less headaches",
                "one less thing",
                "finally under control",
                "save time",
                "reduce frustration",
            ],
            "forbidden_phrases": [
                "enterprise-grade",
                "holistic solution",
                "comprehensive platform",
                "end-to-end",
                "industry-leading",
                "world-class",
            ],
            "default_visual_style": "clean",  # Professional infographic, shareable internally
        },
        AudiencePersona.TOP_TIER_VC: {
            "title": "Investor / VC / Angel",
            "cares_about": ["big market opportunity", "why this team wins", "what's defensible", "momentum signals"],
            "tone": "Confident founder energy. Data backs up the vision. No fluff, no sales pitch.",
            # ROI: Unit economics, market size, return potential
            "value_angle": "ROI",  # Return on Investment - show the opportunity
            "value_framing": "Here's the market. Here's why we win. Here's the return profile.",
            "hooks": [
                # These are starting points - Gemini should riff on the actual content
                "Here's what contractors deal with every day",
                "This is why the old tools don't work anymore",
                "The market is shifting - here's how we're positioned",
            ],
            # NO rigid structure - let Gemini be creative for LinkedIn/GTM
            # The prompt gives guidance, not templates
            "avoid": [
                "Book a demo",
                "Get started",
                "Contact sales",
                "Free trial",
                "revolutionary",
                "game-changing",
                "best-in-class",
            ],
            # PERSONA POLISH - Voice & Style
            "voice_tone": "Pattern-matching investor brain. Show the moat. Prove the momentum. No fluff.",
            "vocabulary": [
                "defensible moat",
                "network effects",
                "land and expand",
                "negative churn",
                "CAC payback",
                "LTV/CAC ratio",
                "gross margin",
                "market timing",
                "founder-market fit",
                "category creation",
            ],
            "forbidden_phrases": [
                "disruptive",
                "revolutionary",
                "game-changing",
                "Uber for X",
                "best-in-class",
                "world-class team",
            ],
            "default_visual_style": "bold",  # Bauhaus-inspired, memorable pitch deck slide
        },
        AudiencePersona.FIELD_CREW: {
            "title": "Field Crew / Technicians / Blue Collar Workers",
            "cares_about": ["making my job easier", "clear instructions", "getting home on time", "less paperwork"],
            "tone": "Super simple, friendly, visual-first - explain like I'm 10",
            # EASE: They don't control the budget - just show it makes life easier
            "value_angle": "EASE",  # Not ROI or COI - just "this makes your day better"
            "value_framing": "Less hassle. Less paperwork. Get home on time.",
            "hooks": [
                "This makes your job way easier",
                "No more paperwork headaches",
                "Works even when you don't have signal",
                "Everything in one place",
            ],
            "infographic_style": {
                "design": "Simple icons, big text, minimal words",
                "colors": "Bold primary colors, high contrast",
                "format": "Step-by-step visual flow, numbered steps",
                "language_rules": [
                    "Use 5th grade vocabulary ONLY",
                    "Replace technical words with everyday analogies",
                    "Use pictures/icons instead of text when possible",
                    "Maximum 6 words per bullet point",
                    "Compare to things they already know (phone, truck, tools)",
                ],
                "analogies": {
                    "API": "like a waiter taking your order",
                    "database": "like a filing cabinet",
                    "sync": "like copying to your other phone",
                    "cloud": "like saving to the internet",
                    "automation": "like setting a coffee maker timer",
                    "workflow": "like following a recipe",
                    "integration": "like plugging in an extension cord",
                    "real-time": "instant, like a text message",
                },
            },
            # PERSONA POLISH - Voice & Style
            "voice_tone": "Buddy on the jobsite. No corporate BS. Just show me it works.",
            "vocabulary": [
                "get it done",
                "no BS",
                "works offline",
                "one tap",
                "no training needed",
                "my truck",
                "the job",
                "clock out on time",
                "less paperwork",
                "just works",
            ],
            "forbidden_phrases": [
                "optimize",
                "leverage",
                "utilize",
                "streamline",
                "enhance",
                "stakeholder",
                "implementation",
                "enterprise",
                "scalable",
                "robust",
            ],
            "default_visual_style": "sketch",  # Hand-drawn whiteboard feel, approachable
        },
    },
    "language_style": {
        "avoid": [
            # Technical jargon (confuses blue collar workers)
            "API",
            "microservices",
            "async",
            "database schema",
            "backend",
            "frontend",
            "deployment",
            "infrastructure",
            "algorithm",
            "neural network",
            "deep learning",
            # Proprietary terms (actual IP exposure)
            "proprietary algorithm",
            "patent-pending",
            "trade secret",
            "secret sauce",
            # Marketing fluff (sounds salesy/fake)
            "revolutionary",
            "disruptive",
            "game-changing",
            "best-in-class",
            "cutting-edge",
            "synergy",
            "paradigm",
            "holistic",
            # Internal marketing/sales language (NEVER use for external content)
            "marketing campaign",
            "marketing strategy",
            "brand awareness",
            "promotional",
            "advertising",
            "drive engagement",
            "target audience",
            "buyer persona",
            "customer journey",
            "content marketing",
            "lead generation campaign",
            "go-to-market",
            # NOTE: These are OK and should NOT be avoided:
            # - "AI" (we have Receptionist AI, AI features)
            # - "competitive advantage" (valid business language)
            # - "scalable" / "robust" (valid descriptors)
            # - "machine learning" when appropriate for technical audience
        ],
        "use": [
            # Simple, benefit-focused language
            "saves you time",
            "gets you paid faster",
            "one place for everything",
            "no more spreadsheets",
            "your crews will love this",
            "works like magic",
            "see everything at a glance",
            "never miss a beat",
            "stop the chaos",
            "know where every dollar goes",
            "finally get home for dinner",
            "your guys can actually use it",
            "works even in the field",
            "no training required",
        ],
    },
    "tone": "Friendly expert friend, not salesy vendor. Like a contractor buddy who found something awesome.",
    "proof_points": {
        "metrics": [
            "hours saved per week",
            "% fewer errors",
            "days faster to payment",
            "% increase in job profitability",
        ],
        "social": [
            "contractors like you",
            "trusted by MEP firms",
            "built for self-performers",
            "designed by people who get it",
        ],
    },
    # Value props for transcript extraction (maps to Coperniq features)
    "value_props": {
        "core": [
            "Projects - track every job from start to finish",
            "Dispatch - send the right crew to the right job",
            "Scheduling - fill your calendar without the chaos",
            "CRM - know your customers, win more work",
            "Quotes - create professional proposals in minutes",
            "Mobile - your crews can access everything on-site",
        ],
        "ai": [
            "Receptionist AI - never miss a call, book 24/7",
            "Project Copilot - ask questions about any job",
            "Smart Forms - digitize inspections instantly",
            "Quote Generation - good/better/best options automatically",
        ],
        "outcomes": [
            "Get paid faster - 65% improvement in payment collection",
            "Save time - hours back every week",
            "Scale operations - grow without adding overhead",
            "Know your numbers - see exactly where every dollar goes",
            "Go home on time - stop the after-hours chaos",
        ],
    },
    "visual_style": {
        "colors": ["#23433E", "#2D9688", "#DDEDEB", "#333333", "#FDFDFC"],  # Coperniq: dark teal, teal accent, mint bg, text, off-white
        "primary_color": "#23433E",  # Dark teal/forest green for CTAs and headers
        "accent_color": "#2D9688",   # Teal for accent text and highlights
        "hero_bg": "#DDEDEB",        # Light mint/sage for hero backgrounds
        "text_color": "#333333",     # Dark gray for body text
        "icons": "Simple, construction-related metaphors (tools, buildings, workers)",
        "layout": "Clean, scannable, executive-friendly. Subtle mint backgrounds.",
        "font_style": "Albert Sans or similar. Large, readable, no fine print feel.",
        "aesthetic": "Modern, professional, teal/green palette. Corporate but approachable.",
    },
}


# =============================================
# Content Sanitization Rules
# =============================================

SANITIZE_RULES = {
    "remove": [
        # Code internals (IP PROTECTION)
        "class names",
        "function names",
        "variable names",
        "method signatures",
        "import statements",
        "package names",
        # System architecture (IP PROTECTION)
        "API endpoints",
        "database tables",
        "database columns",
        "internal URLs",
        "service names",
        "queue names",
        "cache keys",
        # Business secrets (IP PROTECTION)
        "employee names",
        "customer names",
        "pricing details",
        "margin information",
        "vendor names",
        "partnership details",
        # Security (CRITICAL)
        "API keys",
        "tokens",
        "passwords",
        "secrets",
        "credentials",
        "authentication details",
    ],
    "keep": [
        # Business value (SAFE TO SHARE)
        "business outcome",
        "user benefit",
        "time saved",
        "problem solved",
        "workflow improvement",
        "pain point addressed",
        # General concepts (SAFE TO SHARE)
        "general workflow description",
        "high-level process",
        "user experience improvement",
        "efficiency gain",
    ],
    "transform": {
        # Technical → Simple mappings
        "technical_process": "simple analogy or metaphor",
        "code_logic": "plain english benefit",
        "system_architecture": "visual workflow icon",
        "database operation": "data management",
        "API call": "automatic sync",
        "async processing": "works in the background",
        "machine learning": "smart automation",
        "algorithm": "smart system",
        "real-time sync": "instant updates",
        "webhook": "automatic notification",
        "microservice": "specialized helper",
        "containerization": "runs anywhere",
    },
}


# =============================================
# Stage-Specific Templates
# =============================================

STAGE_TEMPLATES = {
    StoryboardStage.PREVIEW: {
        "header_prefix": "Introducing",
        "tone_modifier": "confident, benefit-focused, this solves real problems",
        "cta": "See how it works for your team.",
        "visual_style": "Clean, professional, polished",
        "badge": "",  # No badge - clean marketing
    },
    StoryboardStage.DEMO: {
        "header_prefix": "See How",
        "tone_modifier": "confident, proven, real results",
        "cta": "Let's talk about your operation.",
        "visual_style": "Screenshot-based, real interface glimpses",
        "badge": "",  # No badge - clean marketing
    },
    StoryboardStage.SHIPPED: {
        "header_prefix": "Transform Your",
        "tone_modifier": "ready-to-use, immediate value, proven results",
        "cta": "Start seeing results this week.",
        "visual_style": "Polished, professional, ready-to-use",
        "badge": "",  # No badge - clean marketing
    },
}


# =============================================
# Helper Functions
# =============================================


def get_icp_preset(preset_name: str = "coperniq_mep") -> dict[str, Any]:
    """
    Get ICP preset configuration by name.

    Args:
        preset_name: Name of the ICP preset (default: coperniq_mep)

    Returns:
        ICP configuration dictionary

    Raises:
        ValueError: If preset_name is not found
    """
    presets = {
        "coperniq_mep": COPERNIQ_ICP,
        # Future: Add more ICP presets here
        # "solar_residential": SOLAR_ICP,
        # "general_contractor": GC_ICP,
    }

    if preset_name not in presets:
        available = ", ".join(presets.keys())
        raise ValueError(f"Unknown ICP preset: {preset_name}. Available: {available}")

    return presets[preset_name]


def get_audience_persona(
    persona: AudiencePersona | str, icp_preset: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Get audience persona configuration.

    Args:
        persona: AudiencePersona enum or string value
        icp_preset: Optional ICP preset (defaults to COPERNIQ_ICP)

    Returns:
        Audience persona configuration dictionary
    """
    if icp_preset is None:
        icp_preset = COPERNIQ_ICP

    # Convert string to enum if needed
    if isinstance(persona, str):
        persona = AudiencePersona(persona)

    return icp_preset["audience_personas"].get(persona, icp_preset["audience_personas"][AudiencePersona.C_SUITE])


def get_stage_template(stage: StoryboardStage | str) -> dict[str, Any]:
    """
    Get stage-specific template configuration.

    Args:
        stage: StoryboardStage enum or string value

    Returns:
        Stage template configuration dictionary
    """
    # Convert string to enum if needed
    if isinstance(stage, str):
        stage = StoryboardStage(stage)

    return STAGE_TEMPLATES.get(stage, STAGE_TEMPLATES[StoryboardStage.PREVIEW])


def sanitize_content(content: str, rules: dict[str, Any] | None = None) -> str:
    """
    Sanitize content according to IP protection rules.

    This is a lightweight sanitizer - the heavy lifting is done by Gemini
    during the understanding phase. This catches obvious patterns.

    Args:
        content: Raw content to sanitize
        rules: Optional custom rules (defaults to SANITIZE_RULES)

    Returns:
        Sanitized content string
    """
    if rules is None:
        rules = SANITIZE_RULES

    sanitized = content

    # Remove obvious code patterns
    import re

    # Remove import statements
    sanitized = re.sub(r"^import\s+.*$", "", sanitized, flags=re.MULTILINE)
    sanitized = re.sub(r"^from\s+.*import.*$", "", sanitized, flags=re.MULTILINE)

    # Remove class/function definitions (keep generic description)
    sanitized = re.sub(r"^class\s+\w+.*:$", "[Feature Component]", sanitized, flags=re.MULTILINE)
    sanitized = re.sub(r"^def\s+\w+\(.*\):$", "[Process Step]", sanitized, flags=re.MULTILINE)
    sanitized = re.sub(r"^async\s+def\s+\w+\(.*\):$", "[Automated Process]", sanitized, flags=re.MULTILINE)

    # Remove API keys and secrets
    sanitized = re.sub(r'["\']?[A-Za-z_]*(?:KEY|SECRET|TOKEN|PASSWORD)["\']?\s*[=:]\s*["\'][^"\']+["\']', "[REDACTED]", sanitized, flags=re.IGNORECASE)

    # Remove URLs with internal paths
    sanitized = re.sub(r"https?://[^\s]+(?:internal|staging|dev|api\.)[^\s]*", "[Internal URL]", sanitized)

    # Remove email addresses
    sanitized = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[email]", sanitized)

    return sanitized


def build_language_guidelines(icp_preset: dict[str, Any] | None = None) -> str:
    """
    Build language guidelines string for Gemini prompts.

    Args:
        icp_preset: Optional ICP preset (defaults to COPERNIQ_ICP)

    Returns:
        Formatted language guidelines string
    """
    if icp_preset is None:
        icp_preset = COPERNIQ_ICP

    avoid = icp_preset["language_style"]["avoid"]
    use = icp_preset["language_style"]["use"]
    tone = icp_preset["tone"]

    return f"""LANGUAGE GUIDELINES:
- Tone: {tone}
- AVOID these words/phrases: {', '.join(avoid[:10])}...
- USE these words/phrases: {', '.join(use[:10])}...
- Write for a 5th grader - if they can't understand it, simplify it
- NO technical jargon - translate everything to business benefits
- NO proprietary details - if a competitor could copy it, remove it"""

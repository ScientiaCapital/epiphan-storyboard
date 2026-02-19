"""
Epiphan ICP Presets and Sanitization Rules
==========================================

Defines Ideal Customer Profile (ICP) configurations and content
sanitization rules for executive storyboard generation.

Target: AV integrators, IT departments, and organizations needing professional video
Golden Rule: If a competitor could use the info to copy us, strip it.
             If a 5th grader couldn't understand it, simplify it.
"""

from typing import Any
from enum import Enum


# =============================================
# Epiphan Brand Identity
# =============================================

EPIPHAN_BRAND = {
    "company": "Epiphan Video",
    "tagline": "Professional video solutions for capture, streaming, and collaboration",
    "website": "https://www.epiphan.com",

    "colors": {
        "primary": "#1D2B51",        # Dark navy (headers, CTAs)
        "accent": "#8CBE3F",         # Lime green (Epiphan signature green)
        "secondary": "#3E67D2",      # Blue (interactive elements, links)
        "text": "#202329",           # Near-black (body text)
        "background": "#FFFFFF",     # White (main background)
        "hero_bg": "#f6f7f9",        # Light gray (section backgrounds)
        "light_gray": "#dfe3e9",     # Medium gray (borders, dividers)
        "green_dark": "#2F5117",     # Dark green (hover states)
        "green_light": "#A8D72E",    # Light green (highlights)
    },
    "typography": {
        "primary": "System sans-serif stack",
        "weights": [400, 500, 600, 700],
        "style": "Modern, clean, technical. 1.6rem base, generous line height.",
    },
    "visual_aesthetic": "Technical, professional, reliable. Clean product photography, AV integration visuals.",

    "headlines": [
        "Professional Video Capture and Streaming Solutions",
        "Simplify Your AV Workflow",
        "Reliable Video Processing for Every Environment",
        "From Lecture Halls to Boardrooms — Epiphan Delivers",
        "The Hardware-Software Combination That Just Works",
        "Trusted by Universities, Enterprises, and Houses of Worship Worldwide",
    ],

    "proof_points": {
        "market_position": "20+ years in professional AV",
        "customer_base": "Thousands of installations worldwide",
        "reliability": "Enterprise-grade reliability and support",
        "integration": "Works with any video source and platform",
        "use_cases": "Lecture capture, live streaming, hybrid meetings, worship services",
    },

    "product_lines": [
        "Pearl Mini — All-in-one video encoder, recorder, and streamer",
        "Pearl Nano — Ultra-compact live production system",
        "Pearl Nexus — Cloud-managed video gateway",
        "Epiphan Connect (EC20 PTZ) — PoE-powered PTZ camera",
        "Webcaster X2 — Simple live streaming encoder",
    ],

    "feature_categories": {
        "capture": ["Multi-source recording", "NDI/SRT/RTMP input", "4K recording", "Hardware encoding"],
        "streaming": ["Multi-platform streaming", "SRT/RTMP output", "Simulcast", "Cloud management"],
        "collaboration": ["MS Teams Rooms", "Zoom Rooms", "Hybrid meetings", "BYOD"],
        "management": ["Epiphan Cloud", "Remote management", "Fleet monitoring", "API access"],
    },
}


class AudiencePersona(str, Enum):
    """Target audience personas for storyboard content."""

    AV_INTEGRATOR = "av_integrator"
    IT_DIRECTOR = "it_director"
    CTO = "cto"
    RESELLER = "reseller"
    BDR = "bdr"


class StoryboardStage(str, Enum):
    """Storyboard stage for 3-wave BDR cadence."""

    PREVIEW = "preview"  # Wave 1: "Here's what we're building"
    DEMO = "demo"  # Wave 2: "Here it is working"
    SHIPPED = "shipped"  # Wave 3: "It's live + what's next"


# =============================================
# Epiphan Ideal Customer Profile (ICP)
# =============================================

EPIPHAN_ICP = {
    "name": "epiphan_av",
    "target": "AV integrators, IT departments, and organizations needing professional video",
    "characteristics": {
        "verticals": ["higher_education", "k12", "corporate", "houses_of_worship", "healthcare", "government"],
        "style": "Hardware-first, reliability-focused, enterprise AV",
        "pain_points": [
            "Managing multiple video sources from different vendors",
            "Unreliable streaming causing missed or failed broadcasts",
            "Complex AV setups that require constant on-site support",
            "Scaling video infrastructure across campuses or facilities",
            "Integrating hardware with platforms like Zoom, Teams, and LMS",
        ],
    },
    "audience_personas": {
        AudiencePersona.AV_INTEGRATOR: {
            "title": "AV System Integrator",
            "cares_about": ["reliable installs", "margin on hardware", "easy deployment", "vendor support"],
            "tone": "Peer-level, technical respect, show you understand the job site",
            "value_angle": "ROI",
            "value_framing": "Equipment that installs cleanly, runs without babysitting, and keeps clients happy for years.",
            "hooks": [
                "Spec it once, forget about it",
                "Your clients won't call you back with issues",
                "Margins you can actually build a business on",
            ],
            "voice_tone": "Tradesperson respect. Speak to the pressure of commissioning day and keeping clients happy.",
            "vocabulary": [
                "rack-mount",
                "commission",
                "signal chain",
                "endpoints",
                "spec sheet",
                "zero-config",
                "plug-and-play",
                "firmware",
                "PoE",
                "NDI",
            ],
            "forbidden_phrases": [
                "synergize",
                "digital transformation",
                "enterprise journey",
                "stakeholder alignment",
                "paradigm shift",
                "robust platform",
            ],
            "default_visual_style": "clean",
        },
        AudiencePersona.IT_DIRECTOR: {
            "title": "IT Director / AV Manager",
            "cares_about": ["centralized management", "security", "uptime SLAs", "reducing support tickets"],
            "tone": "Practical, security-conscious, show you respect their infrastructure",
            "value_angle": "COI",
            "value_framing": "Every unmanaged video device is a support ticket waiting to happen. Here's how to get ahead of it.",
            "hooks": [
                "Manage your entire fleet from one dashboard",
                "No more campus-wide AV support calls",
                "Works inside your existing network policies",
            ],
            "voice_tone": "IT pragmatist. Less downtime, fewer tickets, cleaner network. That's the win.",
            "vocabulary": [
                "fleet management",
                "zero-touch provisioning",
                "network policy",
                "VLAN",
                "remote monitoring",
                "API integration",
                "LDAP/SSO",
                "audit trail",
                "uptime",
                "ticketing",
            ],
            "forbidden_phrases": [
                "game-changing",
                "revolutionary",
                "world-class",
                "best-in-class",
                "cutting-edge",
                "paradigm",
            ],
            "default_visual_style": "data_viz",
        },
        AudiencePersona.CTO: {
            "title": "CTO / VP of Technology",
            "cares_about": ["strategic infrastructure", "vendor consolidation", "total cost of ownership", "future-proofing"],
            "tone": "Strategic, TCO-focused, executive-level brevity",
            "value_angle": "ROI",
            "value_framing": "Here's the math: fewer vendors, less complexity, lower TCO. Payback in one budget cycle.",
            "hooks": [
                "Consolidate your video infrastructure under one vendor",
                "Hardware built to last — not to be replaced every 3 years",
                "The platform your team can actually standardize on",
            ],
            "voice_tone": "Boardroom brevity. TCO, standardization, and strategic fit. Numbers over adjectives.",
            "vocabulary": [
                "total cost of ownership",
                "vendor consolidation",
                "standards-based",
                "interoperability",
                "future-proof",
                "API-first",
                "SLA",
                "capital expense",
                "operational leverage",
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
            "default_visual_style": "isometric",
        },
        AudiencePersona.RESELLER: {
            "title": "AV Reseller / Distributor",
            "cares_about": ["margin", "deal registration", "product training", "competitive differentiation"],
            "tone": "Partner-first, margin-aware, help them win deals",
            "value_angle": "ROI",
            "value_framing": "Better margin, easier sell, happier end customers — the combination that keeps deals coming back.",
            "hooks": [
                "Products your customers keep reordering",
                "Deal registration that protects your margin",
                "Technical support that backs you in the field",
            ],
            "voice_tone": "Channel partner energy. Protect the margin, simplify the sell, win together.",
            "vocabulary": [
                "deal registration",
                "MDF",
                "channel margin",
                "demo units",
                "end-user pricing",
                "competitive displacement",
                "pipeline",
                "VAR",
                "distributor pricing",
                "co-sell",
            ],
            "forbidden_phrases": [
                "enterprise-grade",
                "holistic solution",
                "comprehensive platform",
                "end-to-end",
                "industry-leading",
                "world-class",
            ],
            "default_visual_style": "bold",
        },
        AudiencePersona.BDR: {
            "title": "Business Development Rep",
            "cares_about": ["opening conversations", "quick value hooks", "qualifying fast", "booking meetings"],
            "tone": "Punchy, benefit-first, respect their time — get to the point in 10 seconds",
            "value_angle": "COI",
            "value_framing": "Every week without reliable video is a problem your prospect is living with. Here's the hook.",
            "hooks": [
                "Is your video setup giving you headaches?",
                "What if your AV just worked — every time?",
                "20 years of installs that don't come back for support calls",
            ],
            "voice_tone": "Conversational opener. Lead with the pain, follow with the proof. No jargon.",
            "vocabulary": [
                "quick question",
                "worth a look",
                "five minutes",
                "fix the problem",
                "works out of the box",
                "no maintenance headaches",
                "trusted by",
                "happy to show you",
                "makes sense to chat",
                "simple setup",
            ],
            "forbidden_phrases": [
                "leverage",
                "synergize",
                "utilize",
                "streamline",
                "enhance",
                "stakeholder",
                "implementation",
                "enterprise",
                "scalable solution",
                "robust",
            ],
            "default_visual_style": "sketch",
        },
    },
    "language_style": {
        "avoid": [
            # Technical jargon (confuses non-AV buyers)
            "bitrate optimization",
            "codec pipeline",
            "FPGA",
            "firmware stack",
            "hardware abstraction",
            "kernel driver",
            "latency buffer",
            "multiplexing",
            "transcoding pipeline",
            "encoding matrix",
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
        ],
        "use": [
            "just works",
            "set it and forget it",
            "works with any video source",
            "manage from anywhere",
            "no IT headaches",
            "reliable every time",
            "trusted by universities",
            "built for the real world",
            "hardware that lasts",
            "support when you need it",
            "stream to any platform",
            "one device, every use case",
            "zero-touch deployment",
            "works with your existing setup",
        ],
    },
    "tone": "Trusted technical expert, not pushy vendor. Like an AV engineer who's done thousands of installs.",
    "proof_points": {
        "metrics": [
            "uptime percentage",
            "hours of reliable operation",
            "number of simultaneous streams",
            "setup time in minutes",
        ],
        "social": [
            "trusted by top universities",
            "deployed in Fortune 500 boardrooms",
            "houses of worship rely on Epiphan",
            "20+ years of AV hardware expertise",
        ],
    },
    "value_props": {
        "core": [
            "Pearl Mini — all-in-one capture, record, and stream from one device",
            "Pearl Nano — ultra-compact for tight spaces and portable setups",
            "Pearl Nexus — cloud-managed gateway for distributed deployments",
            "EC20 PTZ — PoE camera that integrates with any Pearl system",
            "Epiphan Cloud — manage your entire fleet remotely",
            "Webcaster X2 — plug-and-play streaming for simple use cases",
        ],
        "integrations": [
            "Microsoft Teams Rooms — certified integration",
            "Zoom Rooms — native support",
            "NDI — full native support",
            "SRT/RTMP — multi-platform streaming out of the box",
            "LMS integration — Kaltura, Panopto, Brightcove",
        ],
        "outcomes": [
            "Reliable uptime — no more failed recordings or dropped streams",
            "Simplified management — control everything from Epiphan Cloud",
            "Future-proof — firmware updates extend hardware life",
            "Support you can count on — real engineers, not just a ticketing system",
            "Works with what you have — any camera, any source, any platform",
        ],
    },
    "visual_style": {
        "colors": ["#1D2B51", "#8CBE3F", "#3E67D2", "#202329", "#f6f7f9"],  # Epiphan: navy, green, blue, text, light bg
        "primary_color": "#1D2B51",   # Dark navy for CTAs and headers
        "accent_color": "#8CBE3F",    # Lime green for accent highlights (Epiphan signature)
        "hero_bg": "#f6f7f9",         # Light gray for hero/section backgrounds
        "text_color": "#202329",      # Near-black for body text
        "icons": "AV equipment metaphors (cameras, racks, streaming icons, signal flow)",
        "layout": "Clean, technical, enterprise-friendly. Green accents on navy backgrounds.",
        "font_style": "System sans-serif. Large, readable, technical-clean aesthetic.",
        "aesthetic": "Professional, navy/green palette. Technical but approachable. High contrast.",
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


def get_icp_preset(preset_name: str = "epiphan_av") -> dict[str, Any]:
    """
    Get ICP preset configuration by name.

    Args:
        preset_name: Name of the ICP preset (default: epiphan_av)

    Returns:
        ICP configuration dictionary

    Raises:
        ValueError: If preset_name is not found
    """
    presets = {
        "epiphan_av": EPIPHAN_ICP,
        # Future: Add more ICP presets here
        # "higher_ed": HIGHER_ED_ICP,
        # "corporate": CORPORATE_ICP,
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
        icp_preset: Optional ICP preset (defaults to EPIPHAN_ICP)

    Returns:
        Audience persona configuration dictionary
    """
    if icp_preset is None:
        icp_preset = EPIPHAN_ICP

    # Convert string to enum if needed
    if isinstance(persona, str):
        persona = AudiencePersona(persona)

    return icp_preset["audience_personas"].get(persona, icp_preset["audience_personas"][AudiencePersona.CTO])


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
        icp_preset: Optional ICP preset (defaults to EPIPHAN_ICP)

    Returns:
        Formatted language guidelines string
    """
    if icp_preset is None:
        icp_preset = EPIPHAN_ICP

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

"""
Epiphan ICP Presets and Sanitization Rules
==========================================

Defines Ideal Customer Profile (ICP) configurations and content
sanitization rules for executive storyboard generation.

Target: ATL decision-makers and BTL operators across 10 verticals.
Source of truth: epiphan-bdr-playbook/study-app data.

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
}


# =============================================
# Product Catalog (with pricing)
# =============================================

EPIPHAN_PRODUCTS = {
    "pearl_mini": {
        "name": "Pearl Mini",
        "price": "$3,750",
        "tagline": "All-in-one video encoder, recorder, and streamer",
        "form_factor": "Half-rack, rack-mountable",
        "key_specs": ["6 video sources", "4K recording", "dual streaming", "hardware encoding"],
        "best_for": ["Lecture capture", "Boardrooms", "Hybrid meetings", "Multi-camera production"],
        "verticals": ["higher_ed", "corporate", "healthcare", "government"],
    },
    "pearl_nano": {
        "name": "Pearl Nano",
        "price": "$1,999",
        "tagline": "Ultra-compact live production system",
        "form_factor": "Ultra-compact, portable",
        "key_specs": ["2 video sources", "1080p60", "SRT/RTMP", "NDI input"],
        "best_for": ["Small classrooms", "Portable events", "Houses of worship", "Simple setups"],
        "verticals": ["k12", "houses_of_worship", "corporate", "live_events"],
    },
    "pearl_nexus": {
        "name": "Pearl Nexus",
        "price": "$3,299",
        "tagline": "Cloud-managed video gateway for distributed teams",
        "form_factor": "Compact, network-first",
        "key_specs": ["Cloud management", "Multi-site", "SRT gateway", "Zero-touch provisioning"],
        "best_for": ["Distributed campuses", "Multi-site enterprise", "Remote production", "IT-managed deployments"],
        "verticals": ["higher_ed", "corporate", "government", "healthcare"],
    },
    "pearl_2": {
        "name": "Pearl-2",
        "price": "$7,999",
        "tagline": "Flagship all-in-one video production system",
        "form_factor": "Full-rack, rack-mountable",
        "key_specs": ["12+ video sources", "4K recording", "6 encoding channels", "custom layouts"],
        "best_for": ["Large lecture halls", "Simulation centers", "Multi-camera production", "Live events"],
        "verticals": ["higher_ed", "healthcare", "live_events", "corporate"],
    },
    "ec20_ptz": {
        "name": "Epiphan Connect (EC20 PTZ)",
        "price": "$1,899",
        "tagline": "PoE-powered PTZ camera that integrates with any Pearl",
        "form_factor": "Ceiling/wall mount PTZ",
        "key_specs": ["20x optical zoom", "PoE powered", "NDI|HX", "HDMI output"],
        "best_for": ["Classrooms", "Boardrooms", "Houses of worship", "Courtrooms"],
        "verticals": ["higher_ed", "corporate", "houses_of_worship", "legal"],
    },
    "avio_4k": {
        "name": "AV.io 4K",
        "price": "$579.95",
        "tagline": "4K HDMI to USB capture card",
        "form_factor": "Grab-and-go dongle",
        "key_specs": ["4K capture", "HDMI input", "USB 3.0", "UVC compliant"],
        "best_for": ["Software-based capture", "Portability", "Telemedicine", "UX research"],
        "verticals": ["healthcare", "corporate", "ux_research"],
    },
    "avio_hd_plus": {
        "name": "AV.io HD+",
        "price": "$449.95",
        "tagline": "Universal video capture card (HDMI, DVI, VGA)",
        "form_factor": "Grab-and-go dongle",
        "key_specs": ["1080p60", "HDMI/DVI/VGA input", "USB 3.0", "UVC compliant"],
        "best_for": ["Legacy equipment", "Portable capture", "Budget-friendly"],
        "verticals": ["corporate", "government", "healthcare"],
    },
    "avio_sdi_plus": {
        "name": "AV.io SDI+",
        "price": "$579.95",
        "tagline": "SDI to USB capture card for broadcast sources",
        "form_factor": "Grab-and-go dongle",
        "key_specs": ["3G-SDI input", "1080p60", "USB 3.0", "broadcast-grade"],
        "best_for": ["Broadcast integration", "Professional cameras", "Live events"],
        "verticals": ["live_events", "corporate", "healthcare"],
    },
}


# =============================================
# Verticals (10 from study app)
# =============================================

EPIPHAN_VERTICALS = {
    "higher_ed": {
        "name": "Higher Education",
        "atl_buyers": ["av_director", "ld_director"],
        "btl_users": ["technical_director"],
        "use_cases": ["Lecture capture", "Hybrid classrooms", "Campus-wide streaming", "Event recording"],
        "reference_stories": [
            "NC State — 300+ Pearl units across campus",
            "UNLV — 215 rooms with automated lecture capture",
            "MTSU — 428 rooms centrally managed via Epiphan Cloud",
        ],
        "pain_points": [
            "Faculty won't use complex AV — needs to be one-button",
            "Managing hundreds of rooms across campus with small AV staff",
            "Students expect recorded lectures as baseline",
            "Budget cycles mean 3-5 year TCO matters more than sticker price",
        ],
        "recommended_products": ["pearl_mini", "pearl_nano", "pearl_nexus", "ec20_ptz"],
    },
    "corporate": {
        "name": "Corporate / Enterprise",
        "atl_buyers": ["av_director", "corp_comms"],
        "btl_users": ["technical_director"],
        "use_cases": ["Boardroom meetings", "Town halls", "Training recordings", "Hybrid events"],
        "reference_stories": [
            "OpenAI — Pearl systems for internal production",
            "Fortune 500 boardrooms — standardized on Pearl Mini",
        ],
        "pain_points": [
            "Every meeting room has different AV — no standardization",
            "IT gets 50 support tickets a week for 'the video doesn't work'",
            "Executives expect broadcast-quality from every room",
            "Remote employees feel like second-class citizens in hybrid meetings",
        ],
        "recommended_products": ["pearl_mini", "pearl_nexus", "ec20_ptz"],
    },
    "live_events": {
        "name": "Live Events / Production",
        "atl_buyers": ["av_director", "technical_director"],
        "btl_users": ["technical_director"],
        "use_cases": ["Multi-camera production", "Live streaming", "IMAG", "Event recording"],
        "reference_stories": [],
        "pain_points": [
            "Software encoders crash mid-show — hardware reliability is non-negotiable",
            "Need to ingest 6+ sources and switch live with zero latency",
            "Client expects broadcast quality from a portable rig",
            "Rental houses need gear that any operator can run without training",
        ],
        "recommended_products": ["pearl_2", "pearl_mini", "ec20_ptz"],
    },
    "government": {
        "name": "Government / Municipal",
        "atl_buyers": ["court_admin", "av_director"],
        "btl_users": ["technical_director"],
        "use_cases": ["Council meetings", "Courtroom recording", "Public access streaming", "Training"],
        "reference_stories": [],
        "pain_points": [
            "Public transparency mandates require reliable recording/streaming",
            "Strict procurement processes — need clear TCO justification",
            "Security compliance — FISMA/FedRAMP considerations",
            "Staff turnover means AV must be foolproof",
        ],
        "recommended_products": ["pearl_mini", "pearl_nexus", "ec20_ptz"],
    },
    "houses_of_worship": {
        "name": "Houses of Worship",
        "atl_buyers": ["av_director"],
        "btl_users": ["technical_director"],
        "use_cases": ["Service streaming", "Multi-campus distribution", "Sermon recording", "Event production"],
        "reference_stories": [],
        "pain_points": [
            "Volunteer operators — can't require AV expertise",
            "Budget-sensitive — every dollar is a donation",
            "Congregation expects professional-quality stream",
            "Multi-campus needs synchronized content distribution",
        ],
        "recommended_products": ["pearl_nano", "pearl_mini", "ec20_ptz"],
    },
    "healthcare": {
        "name": "Healthcare / Medical Simulation",
        "atl_buyers": ["sim_center_director", "ld_director"],
        "btl_users": ["technical_director"],
        "use_cases": ["Simulation recording", "Surgical capture", "Telemedicine", "Grand rounds"],
        "reference_stories": [],
        "pain_points": [
            "HIPAA compliance — video data must stay secure and controlled",
            "Simulation debriefs require multi-angle synchronized playback",
            "Medical equipment outputs non-standard video signals",
            "Staff doesn't have time to learn complex AV — it must just work",
        ],
        "recommended_products": ["pearl_2", "pearl_mini", "avio_4k", "ec20_ptz"],
    },
    "industrial": {
        "name": "Industrial / Manufacturing",
        "atl_buyers": ["ehs_manager", "ld_director"],
        "btl_users": ["technical_director"],
        "use_cases": ["Safety training capture", "Process documentation", "Remote inspections", "Compliance recording"],
        "reference_stories": [],
        "pain_points": [
            "Training content is tribal knowledge in senior workers' heads",
            "OSHA compliance requires documented training procedures",
            "Harsh environments — equipment needs to be robust and reliable",
            "Distributed plants need centralized training content management",
        ],
        "recommended_products": ["pearl_mini", "pearl_nano", "avio_4k"],
    },
    "legal": {
        "name": "Legal",
        "atl_buyers": ["court_admin", "law_firm_it"],
        "btl_users": ["technical_director"],
        "use_cases": ["Deposition recording", "Courtroom proceedings", "Remote testimony", "Training"],
        "reference_stories": [],
        "pain_points": [
            "Chain of custody for video evidence — must be tamper-proof",
            "Remote depositions are now standard — quality and reliability matter",
            "Judges and attorneys have zero tolerance for technical failures",
            "Transcription services need clean audio from video recordings",
        ],
        "recommended_products": ["pearl_mini", "ec20_ptz", "avio_4k"],
    },
    "ux_research": {
        "name": "UX Research",
        "atl_buyers": ["ld_director", "corp_comms"],
        "btl_users": ["technical_director"],
        "use_cases": ["Usability testing", "Focus groups", "Eye tracking capture", "Screen + face recording"],
        "reference_stories": [],
        "pain_points": [
            "Need synchronized multi-source capture (screen + face + room)",
            "Researchers aren't AV technicians — setup must be simple",
            "Data stays on-premises for privacy/NDA compliance",
            "Quick turnaround — can't wait hours for video processing",
        ],
        "recommended_products": ["pearl_mini", "avio_4k", "ec20_ptz"],
    },
    "k12": {
        "name": "K-12 Education",
        "atl_buyers": ["av_director", "ld_director"],
        "btl_users": ["technical_director"],
        "use_cases": ["Classroom recording", "Board meetings", "Event streaming", "Distance learning"],
        "reference_stories": [],
        "pain_points": [
            "Teachers won't use it if it's not one-button simple",
            "Extremely budget-constrained — need lowest TCO option",
            "Limited IT staff — can't have equipment that needs babysitting",
            "CIPA/COPPA compliance for student privacy",
        ],
        "recommended_products": ["pearl_nano", "ec20_ptz"],
    },
}


# =============================================
# ATL / BTL Persona Definitions
# =============================================

class AudiencePersona(str, Enum):
    """Target audience personas for storyboard content.

    ATL (Above The Line) = Decision makers who sign the PO.
    BTL (Below The Line) = Operators/users who use the product daily.
    Channel = Sales intermediaries (integrators, resellers, internal BDRs).
    """

    # ATL — Decision Makers (7 from study app)
    AV_DIRECTOR = "av_director"
    LD_DIRECTOR = "ld_director"
    SIM_CENTER_DIRECTOR = "sim_center_director"
    COURT_ADMIN = "court_admin"
    CORP_COMMS = "corp_comms"
    EHS_MANAGER = "ehs_manager"
    LAW_FIRM_IT = "law_firm_it"

    # BTL — Operators (1 from study app)
    TECHNICAL_DIRECTOR = "technical_director"


class StoryboardStage(str, Enum):
    """Storyboard stage for 3-wave BDR cadence."""

    PREVIEW = "preview"  # Wave 1: "Here's what we're building"
    DEMO = "demo"  # Wave 2: "Here it is working"
    SHIPPED = "shipped"  # Wave 3: "It's live + what's next"


# =============================================
# Competitive Positioning
# =============================================

COMPETITIVE_INTEL = {
    "crestron": {
        "name": "Crestron",
        "position": "Enterprise control systems giant",
        "weakness": "Proprietary ecosystem lock-in, requires certified programmers, expensive ongoing support",
        "epiphan_advantage": "Open standards (NDI, SRT, RTMP), no proprietary lock-in, works with any platform",
    },
    "extron": {
        "name": "Extron",
        "position": "AV signal management and distribution",
        "weakness": "Hardware-heavy approach, limited cloud management, complex configuration",
        "epiphan_advantage": "Cloud-managed via Epiphan Cloud, zero-touch provisioning, simpler deployment",
    },
    "vaddio": {
        "name": "Vaddio (Legrand AV)",
        "position": "PTZ cameras and AV bridges",
        "weakness": "Camera-focused, limited all-in-one production capability",
        "epiphan_advantage": "Pearl is a complete production system — camera + encoder + recorder + streamer in one",
    },
    "matrox": {
        "name": "Matrox Video",
        "position": "Encoding and streaming hardware",
        "weakness": "Encoder-only, no integrated recording or camera control",
        "epiphan_advantage": "All-in-one: encode + record + stream + switch from one device",
    },
    "magewell": {
        "name": "Magewell",
        "position": "Capture cards and encoders",
        "weakness": "Low-cost capture cards, limited enterprise management, no all-in-one solution",
        "epiphan_advantage": "Enterprise fleet management, integrated recording, professional support",
    },
    "panopto": {
        "name": "Panopto",
        "position": "Video management software (lecture capture)",
        "weakness": "Software-only — relies on unreliable PC/Mac capture, no hardware encoding",
        "epiphan_advantage": "Hardware encoding is always reliable — no PC crashes, no driver issues, no OS updates breaking capture",
    },
}


# =============================================
# Reference Stories (proof points)
# =============================================

REFERENCE_STORIES = {
    "nc_state": {
        "customer": "NC State University",
        "metric": "300+ Pearl units deployed campus-wide",
        "vertical": "higher_ed",
        "quote_theme": "Standardized on Epiphan for reliability across 300+ rooms",
    },
    "unlv": {
        "customer": "UNLV",
        "metric": "215 rooms with automated lecture capture",
        "vertical": "higher_ed",
        "quote_theme": "Automated capture in 215 classrooms — faculty just teach",
    },
    "mtsu": {
        "customer": "Middle Tennessee State University",
        "metric": "428 rooms centrally managed",
        "vertical": "higher_ed",
        "quote_theme": "One AV team manages 428 rooms via Epiphan Cloud",
    },
    "openai": {
        "customer": "OpenAI",
        "metric": "Pearl systems for internal video production",
        "vertical": "corporate",
        "quote_theme": "The world's leading AI company trusts Epiphan for their video infrastructure",
    },
}


# =============================================
# Epiphan Ideal Customer Profile (ICP)
# =============================================

EPIPHAN_ICP = {
    "name": "epiphan_av",
    "target": "ATL decision-makers and BTL operators across Higher Ed, Corporate, Healthcare, Government, Legal, Industrial, Live Events, Houses of Worship, UX Research, and K-12",
    "characteristics": {
        "verticals": list(EPIPHAN_VERTICALS.keys()),
        "style": "Hardware-first, reliability-focused, enterprise AV",
        "pain_points": [
            "Managing multiple video sources from different vendors",
            "Unreliable streaming causing missed or failed broadcasts",
            "Complex AV setups that require constant on-site support",
            "Scaling video infrastructure across campuses or facilities",
            "Integrating hardware with platforms like Zoom, Teams, and LMS",
            "Volunteer or non-technical operators need one-button simplicity",
            "Compliance requirements (HIPAA, FERPA, chain of custody)",
        ],
    },
    "audience_personas": {
        # ── ATL: Decision Makers ──────────────────────────────────

        AudiencePersona.AV_DIRECTOR: {
            "title": "AV Director",
            "persona_type": "ATL",
            "verticals": ["higher_ed", "corporate", "live_events", "houses_of_worship"],
            "cares_about": ["system reliability", "fleet standardization", "ease of management", "vendor support quality"],
            "tone": "Peer-level AV professional. Speak to the pressure of managing hundreds of rooms.",
            "value_angle": "COI",
            "value_framing": "Every room with unreliable AV is a support ticket and a frustrated user. Standardize and forget about it.",
            "hooks": [
                "NC State runs 300+ Pearls — one AV team, zero headaches",
                "What if every room just worked the same way?",
                "Stop babysitting AV. Start managing it.",
            ],
            "voice_tone": "AV peer. You've both done the 6AM setup and the midnight troubleshooting call.",
            "vocabulary": [
                "fleet management", "standardize", "rack-mount", "signal chain",
                "commissioning", "punchlist", "as-built", "AV-over-IP",
                "NDI", "SRT", "RTMP", "Dante", "PoE",
            ],
            "forbidden_phrases": [
                "digital transformation", "synergize", "paradigm shift",
                "enterprise journey", "holistic solution", "leverage",
            ],
            "default_visual_style": "clean",
        },

        AudiencePersona.LD_DIRECTOR: {
            "title": "L&D Director",
            "persona_type": "ATL",
            "verticals": ["corporate", "healthcare", "industrial"],
            "cares_about": ["training content quality", "scalable delivery", "compliance documentation", "measurement"],
            "tone": "Training professional. Show you understand the learning outcomes, not just the tech.",
            "value_angle": "ROI",
            "value_framing": "Your best trainer's knowledge walks out the door when they retire. Capture it once, deliver it forever.",
            "hooks": [
                "Turn your best trainers into content libraries",
                "OSHA says document it. Epiphan makes it effortless.",
                "One recording. Every new hire. Every location. Forever.",
            ],
            "voice_tone": "Learning professional empathy. You care about outcomes, not AV specs.",
            "vocabulary": [
                "learning outcomes", "content library", "compliance training",
                "onboarding", "knowledge capture", "LMS integration",
                "Panopto", "Kaltura", "SCORM", "blended learning",
            ],
            "forbidden_phrases": [
                "cutting-edge", "revolutionary", "game-changing",
                "best-in-class", "enterprise-grade", "robust platform",
            ],
            "default_visual_style": "polished",
        },

        AudiencePersona.SIM_CENTER_DIRECTOR: {
            "title": "Simulation Center Director",
            "persona_type": "ATL",
            "verticals": ["healthcare"],
            "cares_about": ["multi-angle recording", "debrief quality", "HIPAA compliance", "SimCapture/CAE integration"],
            "tone": "Clinical educator. Show you understand simulation pedagogy and debriefing.",
            "value_angle": "COI",
            "value_framing": "Every simulation without proper recording is a missed learning opportunity. Students deserve better debriefs.",
            "hooks": [
                "6 angles. One device. Perfect debriefs every time.",
                "HIPAA-compliant recording that stays on your network",
                "Your manikin is $100K — the recording shouldn't be an afterthought",
            ],
            "voice_tone": "Clinical simulation peer. You speak manikin brands, INACSL standards, and debrief methodology.",
            "vocabulary": [
                "debrief", "simulation", "standardized patient", "manikin",
                "INACSL", "SimCapture", "CAE", "high-fidelity sim",
                "multi-angle", "synchronized playback", "HIPAA",
            ],
            "forbidden_phrases": [
                "game-changing", "synergy", "leverage", "paradigm",
                "revolutionary", "disruptive", "best-in-class",
            ],
            "default_visual_style": "data_viz",
        },

        AudiencePersona.COURT_ADMIN: {
            "title": "Court Administrator",
            "persona_type": "ATL",
            "verticals": ["legal", "government"],
            "cares_about": ["record integrity", "chain of custody", "reliability", "public access compliance"],
            "tone": "Judicial professional. Reliability and record integrity are non-negotiable.",
            "value_angle": "COI",
            "value_framing": "A failed recording of court proceedings isn't an inconvenience — it's a legal crisis. Don't risk it.",
            "hooks": [
                "Court recording that never fails, never loses footage",
                "Tamper-proof records for chain of custody",
                "Public access streaming that actually works for every hearing",
            ],
            "voice_tone": "Judicial gravity. Every word matters. Reliability is the only feature that counts.",
            "vocabulary": [
                "record of proceedings", "chain of custody", "public access",
                "remote testimony", "court reporter", "transcript",
                "tamper-proof", "archival", "retention policy",
            ],
            "forbidden_phrases": [
                "game-changing", "revolutionary", "cutting-edge",
                "disruptive", "exciting", "innovative",
            ],
            "default_visual_style": "clean",
        },

        AudiencePersona.CORP_COMMS: {
            "title": "Corporate Communications Director",
            "persona_type": "ATL",
            "verticals": ["corporate"],
            "cares_about": ["broadcast quality", "executive presence", "brand consistency", "multi-platform distribution"],
            "tone": "Communications professional. Production quality reflects company brand.",
            "value_angle": "ROI",
            "value_framing": "Your CEO's town hall shouldn't look like a bad Zoom call. Broadcast quality from every room, every time.",
            "hooks": [
                "Town halls that look like they were produced by a network",
                "One device turns any room into a broadcast studio",
                "Stream to Teams, YouTube, and your intranet simultaneously",
            ],
            "voice_tone": "Brand-conscious communicator. Quality is non-negotiable when leadership is on camera.",
            "vocabulary": [
                "town hall", "all-hands", "executive communication",
                "brand standards", "simulcast", "multi-platform",
                "production value", "B-roll", "lower thirds",
            ],
            "forbidden_phrases": [
                "synergize", "leverage", "paradigm shift",
                "holistic", "enterprise journey", "robust",
            ],
            "default_visual_style": "polished",
        },

        AudiencePersona.EHS_MANAGER: {
            "title": "EHS Manager",
            "persona_type": "ATL",
            "verticals": ["industrial"],
            "cares_about": ["OSHA compliance", "safety training documentation", "incident recording", "audit readiness"],
            "tone": "Safety professional. Compliance isn't optional — it's life or death.",
            "value_angle": "COI",
            "value_framing": "OSHA doesn't accept 'the recording failed' as an excuse. One incident without documentation can cost millions.",
            "hooks": [
                "OSHA-ready training documentation from day one",
                "Record every safety procedure. Prove every training session.",
                "Your most experienced operator retires next year. Capture everything now.",
            ],
            "voice_tone": "Safety-first pragmatist. Compliance, documentation, zero tolerance for 'it didn't record.'",
            "vocabulary": [
                "OSHA", "compliance", "incident report", "safety training",
                "lockout/tagout", "JSA", "SOP documentation",
                "audit trail", "recordkeeping", "toolbox talk",
            ],
            "forbidden_phrases": [
                "game-changing", "revolutionary", "cutting-edge",
                "best-in-class", "synergy", "paradigm",
            ],
            "default_visual_style": "bold",
        },

        AudiencePersona.LAW_FIRM_IT: {
            "title": "Law Firm IT Director",
            "persona_type": "ATL",
            "verticals": ["legal"],
            "cares_about": ["data security", "on-premises control", "remote deposition quality", "partner satisfaction"],
            "tone": "IT professional in a high-stakes environment. Security and reliability above all.",
            "value_angle": "COI",
            "value_framing": "When a deposition recording fails, the billable hour count doesn't stop. Neither does the partner's frustration.",
            "hooks": [
                "Deposition recording that stays on your network — not someone else's cloud",
                "Partners don't call IT to complain about working AV",
                "Remote depositions in 4K, every time, with no IT involvement",
            ],
            "voice_tone": "IT professional serving demanding attorneys. Security, reliability, and zero complaints.",
            "vocabulary": [
                "on-premises", "data sovereignty", "encryption at rest",
                "deposition", "remote testimony", "e-discovery",
                "network segmentation", "compliance", "partner satisfaction",
            ],
            "forbidden_phrases": [
                "cloud-first", "SaaS", "disruptive", "game-changing",
                "revolutionary", "best-in-class", "cutting-edge",
            ],
            "default_visual_style": "clean",
        },

        # ── BTL: Operators ────────────────────────────────────────

        AudiencePersona.TECHNICAL_DIRECTOR: {
            "title": "Technical Director / AV Operator",
            "persona_type": "BTL",
            "verticals": ["higher_ed", "corporate", "live_events", "houses_of_worship", "healthcare"],
            "cares_about": ["ease of use", "reliability under pressure", "quick setup", "real-time monitoring"],
            "tone": "Fellow operator. You've both been in the back of the room making live TV happen.",
            "value_angle": "EASE",
            "value_framing": "When the president walks on stage, the switcher better work. No excuses, no reboots, no 'give me a minute.'",
            "hooks": [
                "One-button start. Every source. Every time.",
                "Built for the operator who can't afford a crash during the show",
                "The gear that works when the pressure is highest",
            ],
            "voice_tone": "Operator empathy. You understand the stress of live production and the joy of a clean show.",
            "vocabulary": [
                "cue", "cut", "fade", "PGM/PVW", "tally",
                "multiview", "ISO record", "confidence monitor",
                "return feed", "comms", "rundown", "show flow",
            ],
            "forbidden_phrases": [
                "leverage", "synergize", "enterprise", "stakeholder",
                "paradigm", "holistic", "best-in-class",
            ],
            "default_visual_style": "sketch",
        },

    },
    "language_style": {
        "avoid": [
            # Technical jargon (confuses non-AV buyers)
            "bitrate optimization", "codec pipeline", "FPGA",
            "firmware stack", "hardware abstraction", "kernel driver",
            "latency buffer", "multiplexing", "transcoding pipeline",
            "encoding matrix",
            # Proprietary terms (actual IP exposure)
            "proprietary algorithm", "patent-pending", "trade secret", "secret sauce",
            # Marketing fluff (sounds salesy/fake)
            "revolutionary", "disruptive", "game-changing", "best-in-class",
            "cutting-edge", "synergy", "paradigm", "holistic",
            # Internal marketing/sales language
            "marketing campaign", "marketing strategy", "brand awareness",
            "promotional", "advertising", "drive engagement",
            "target audience", "buyer persona", "customer journey",
            "content marketing", "lead generation campaign", "go-to-market",
        ],
        "use": [
            "just works", "set it and forget it",
            "works with any video source", "manage from anywhere",
            "no IT headaches", "reliable every time",
            "trusted by universities", "built for the real world",
            "hardware that lasts", "support when you need it",
            "stream to any platform", "one device, every use case",
            "zero-touch deployment", "works with your existing setup",
            "300+ rooms at NC State", "428 rooms at MTSU",
        ],
    },
    "tone": "Trusted technical expert, not pushy vendor. Like an AV engineer who's done thousands of installs.",
    "proof_points": {
        "metrics": [
            "NC State — 300+ Pearl units campus-wide",
            "UNLV — 215 rooms automated lecture capture",
            "MTSU — 428 rooms centrally managed",
            "OpenAI — Pearl systems for internal production",
            "20+ years of professional AV hardware",
        ],
        "social": [
            "trusted by top-tier universities (NC State, UNLV, MTSU)",
            "deployed in Fortune 500 boardrooms",
            "OpenAI chose Epiphan for their video infrastructure",
            "houses of worship rely on Pearl for Sunday services",
            "20+ years of AV hardware expertise",
        ],
    },
    "value_props": {
        "core": [
            "Pearl-2 ($7,999) — flagship 12+ source production system",
            "Pearl Mini ($3,750) — all-in-one capture, record, and stream",
            "Pearl Nexus ($3,299) — cloud-managed gateway for distributed sites",
            "Pearl Nano ($1,999) — ultra-compact for tight spaces and portability",
            "EC20 PTZ ($1,899) — PoE camera that integrates with any Pearl",
            "AV.io 4K ($579.95) — grab-and-go 4K capture card",
            "Epiphan Cloud — manage your entire fleet remotely",
        ],
        "integrations": [
            "Microsoft Teams Rooms — certified integration",
            "Zoom Rooms — native support",
            "NDI — full native support for AV-over-IP",
            "SRT/RTMP — multi-platform streaming out of the box",
            "LMS integration — Kaltura, Panopto, Brightcove",
        ],
        "outcomes": [
            "Reliable uptime — no more failed recordings or dropped streams",
            "Simplified management — control everything from Epiphan Cloud",
            "Future-proof — firmware updates extend hardware life for years",
            "Support you can count on — real engineers, not a ticketing system",
            "Works with what you have — any camera, any source, any platform",
        ],
    },
    "visual_style": {
        "colors": ["#1D2B51", "#8CBE3F", "#3E67D2", "#202329", "#f6f7f9"],
        "primary_color": "#1D2B51",
        "accent_color": "#8CBE3F",
        "hero_bg": "#f6f7f9",
        "text_color": "#202329",
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
        "class names", "function names", "variable names",
        "method signatures", "import statements", "package names",
        # System architecture (IP PROTECTION)
        "API endpoints", "database tables", "database columns",
        "internal URLs", "service names", "queue names", "cache keys",
        # Business secrets (IP PROTECTION)
        "employee names", "customer names", "pricing details",
        "margin information", "vendor names", "partnership details",
        # Security (CRITICAL)
        "API keys", "tokens", "passwords", "secrets",
        "credentials", "authentication details",
    ],
    "keep": [
        # Business value (SAFE TO SHARE)
        "business outcome", "user benefit", "time saved",
        "problem solved", "workflow improvement", "pain point addressed",
        # General concepts (SAFE TO SHARE)
        "general workflow description", "high-level process",
        "user experience improvement", "efficiency gain",
    ],
    "transform": {
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
        "badge": "",
    },
    StoryboardStage.DEMO: {
        "header_prefix": "See How",
        "tone_modifier": "confident, proven, real results",
        "cta": "Let's talk about your operation.",
        "visual_style": "Screenshot-based, real interface glimpses",
        "badge": "",
    },
    StoryboardStage.SHIPPED: {
        "header_prefix": "Transform Your",
        "tone_modifier": "ready-to-use, immediate value, proven results",
        "cta": "Start seeing results this week.",
        "visual_style": "Polished, professional, ready-to-use",
        "badge": "",
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

    if isinstance(persona, str):
        try:
            persona = AudiencePersona(persona)
        except ValueError:
            # Fallback to av_director for unknown personas
            persona = AudiencePersona.AV_DIRECTOR

    return icp_preset["audience_personas"].get(persona, icp_preset["audience_personas"][AudiencePersona.AV_DIRECTOR])


def get_stage_template(stage: StoryboardStage | str) -> dict[str, Any]:
    """
    Get stage-specific template configuration.

    Args:
        stage: StoryboardStage enum or string value

    Returns:
        Stage template configuration dictionary
    """
    if isinstance(stage, str):
        stage = StoryboardStage(stage)

    return STAGE_TEMPLATES.get(stage, STAGE_TEMPLATES[StoryboardStage.PREVIEW])


def get_vertical(vertical_name: str) -> dict[str, Any]:
    """
    Get vertical configuration by name.

    Args:
        vertical_name: Vertical identifier (e.g., "higher_ed", "healthcare")

    Returns:
        Vertical configuration dictionary

    Raises:
        ValueError: If vertical_name is not found
    """
    if vertical_name not in EPIPHAN_VERTICALS:
        available = ", ".join(EPIPHAN_VERTICALS.keys())
        raise ValueError(f"Unknown vertical: {vertical_name}. Available: {available}")

    return EPIPHAN_VERTICALS[vertical_name]


def get_product(product_id: str) -> dict[str, Any]:
    """
    Get product configuration by ID.

    Args:
        product_id: Product identifier (e.g., "pearl_mini", "ec20_ptz")

    Returns:
        Product configuration dictionary

    Raises:
        ValueError: If product_id is not found
    """
    if product_id not in EPIPHAN_PRODUCTS:
        available = ", ".join(EPIPHAN_PRODUCTS.keys())
        raise ValueError(f"Unknown product: {product_id}. Available: {available}")

    return EPIPHAN_PRODUCTS[product_id]


def get_reference_stories(vertical: str | None = None) -> list[dict[str, Any]]:
    """
    Get reference stories, optionally filtered by vertical.

    Args:
        vertical: Optional vertical filter

    Returns:
        List of reference story dictionaries
    """
    stories = list(REFERENCE_STORIES.values())
    if vertical:
        stories = [s for s in stories if s["vertical"] == vertical]
    return stories


def get_competitive_positioning(competitor: str | None = None) -> dict[str, Any] | list[dict[str, Any]]:
    """
    Get competitive positioning data.

    Args:
        competitor: Optional specific competitor name

    Returns:
        Single competitor dict or list of all competitors
    """
    if competitor:
        comp = COMPETITIVE_INTEL.get(competitor.lower())
        if not comp:
            available = ", ".join(COMPETITIVE_INTEL.keys())
            raise ValueError(f"Unknown competitor: {competitor}. Available: {available}")
        return comp
    return list(COMPETITIVE_INTEL.values())


def sanitize_content(content: str, rules: dict[str, Any] | None = None) -> str:
    """
    Sanitize content according to IP protection rules.

    Args:
        content: Raw content to sanitize
        rules: Optional custom rules (defaults to SANITIZE_RULES)

    Returns:
        Sanitized content string
    """
    if rules is None:
        rules = SANITIZE_RULES

    sanitized = content

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

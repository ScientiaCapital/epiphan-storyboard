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

from enum import Enum
from typing import Any

# =============================================
# Epiphan Brand Identity
# =============================================

EPIPHAN_BRAND = {
    "company": "Epiphan Video",
    "tagline": "Professional video solutions for capture, streaming, and collaboration",
    "website": "https://www.epiphan.com",
    "colors": {
        "primary": "#1D2B51",  # Dark navy (headers, CTAs)
        "accent": "#8CBE3F",  # Lime green (Epiphan signature green)
        "secondary": "#3E67D2",  # Blue (interactive elements, links)
        "text": "#202329",  # Near-black (body text)
        "background": "#FFFFFF",  # White (main background)
        "hero_bg": "#f6f7f9",  # Light gray (section backgrounds)
        "light_gray": "#dfe3e9",  # Medium gray (borders, dividers)
        "green_dark": "#2F5117",  # Dark green (hover states)
        "green_light": "#A8D72E",  # Light green (highlights)
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
        "key_specs": [
            "6 video sources",
            "4K recording",
            "dual streaming",
            "hardware encoding",
        ],
        "best_for": [
            "Lecture capture",
            "Boardrooms",
            "Hybrid meetings",
            "Multi-camera production",
        ],
        "verticals": ["higher_ed", "corporate", "healthcare", "government"],
    },
    "pearl_nano": {
        "name": "Pearl Nano",
        "price": "$1,999",
        "tagline": "Ultra-compact live production system",
        "form_factor": "Ultra-compact, portable",
        "key_specs": ["2 video sources", "1080p60", "SRT/RTMP", "NDI input"],
        "best_for": [
            "Small classrooms",
            "Portable events",
            "Houses of worship",
            "Simple setups",
        ],
        "verticals": ["k12", "houses_of_worship", "corporate", "live_events"],
    },
    "pearl_nexus": {
        "name": "Pearl Nexus",
        "price": "$3,299",
        "tagline": "Cloud-managed video gateway for distributed teams",
        "form_factor": "Compact, network-first",
        "key_specs": [
            "Cloud management",
            "Multi-site",
            "SRT gateway",
            "Zero-touch provisioning",
        ],
        "best_for": [
            "Distributed campuses",
            "Multi-site enterprise",
            "Remote production",
            "IT-managed deployments",
        ],
        "verticals": ["higher_ed", "corporate", "government", "healthcare"],
    },
    "pearl_2": {
        "name": "Pearl-2",
        "price": "$7,999",
        "tagline": "Flagship all-in-one video production system",
        "form_factor": "Full-rack, rack-mountable",
        "key_specs": [
            "12+ video sources",
            "4K recording",
            "6 encoding channels",
            "custom layouts",
        ],
        "best_for": [
            "Large lecture halls",
            "Simulation centers",
            "Multi-camera production",
            "Live events",
        ],
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
        "best_for": [
            "Software-based capture",
            "Portability",
            "Telemedicine",
            "UX research",
        ],
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
        "atl_buyers": ["av_director", "ld_director", "provost", "university_president", "university_finance", "edtech_manager"],
        "btl_users": ["technical_director"],
        "channel_partners": ["dealer_dave", "system_engineer"],
        "use_cases": [
            "Lecture capture",
            "Hybrid classrooms",
            "Campus-wide streaming",
            "Event recording",
        ],
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
        "use_cases": [
            "Boardroom meetings",
            "Town halls",
            "Training recordings",
            "Hybrid events",
        ],
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
        "atl_buyers": ["av_director", "venue_manager", "production_director"],
        "btl_users": ["technical_director"],
        "channel_partners": ["dealer_dave", "system_engineer"],
        "use_cases": [
            "Multi-camera production",
            "Live streaming",
            "IMAG",
            "Event recording",
        ],
        "reference_stories": [
            "Freeman — Pearl fleet for world's largest events",
            "MSAVi — Disney, Imagine Dragons — 'Haven't failed us once'",
            "Talon AV — 30+ unstaffed rooms via Epiphan Cloud",
            "Oslo Opera — 300+ shows/year, minimal staff",
            "The Volume — Shannon Sharpe show production",
        ],
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
        "use_cases": [
            "Council meetings",
            "Courtroom recording",
            "Public access streaming",
            "Training",
        ],
        "reference_stories": [
            "Hawaii Senate — 6 Pearl-2 units, NDI, 'Any user can operate with confidence'",
            "Redfish Technologies — 60+ Pearl installations across WA state",
        ],
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
        "use_cases": [
            "Service streaming",
            "Multi-campus distribution",
            "Sermon recording",
            "Event production",
        ],
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
        "use_cases": [
            "Simulation recording",
            "Surgical capture",
            "Telemedicine",
            "Grand rounds",
        ],
        "reference_stories": [
            "BabyFlix — Multi-clinic ultrasound streaming, 'By far the best'",
            "Charles Sturt — 6 sim labs, 'Intuitive enough, rarely explain'",
        ],
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
        "use_cases": [
            "Safety training capture",
            "Process documentation",
            "Remote inspections",
            "Compliance recording",
        ],
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
        "use_cases": [
            "Deposition recording",
            "Courtroom proceedings",
            "Remote testimony",
            "Training",
        ],
        "reference_stories": [
            "UCLA Law — Classrooms + courtrooms, 'Edge has been a lifesaver'",
            "Anchor Point — Mock trial capture, 'Super simple, no complex computer'",
            "Benchmark Legal — Multi-venue mock trials, 'Flexibility and versatility'",
            "Verdict Advantage — 6-channel mock trial recording",
        ],
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
        "use_cases": [
            "Usability testing",
            "Focus groups",
            "Eye tracking capture",
            "Screen + face recording",
        ],
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
        "atl_buyers": ["av_director", "ld_director", "edtech_manager"],
        "btl_users": ["technical_director"],
        "channel_partners": ["dealer_dave", "system_engineer"],
        "use_cases": [
            "Classroom recording",
            "Board meetings",
            "Event streaming",
            "Distance learning",
        ],
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

    # ATL — Higher Ed Executive Buyers (3 new)
    PROVOST = "provost"
    UNIVERSITY_PRESIDENT = "university_president"
    UNIVERSITY_FINANCE = "university_finance"

    # ATL — Edtech & Live Events (3 new from PDF research)
    EDTECH_MANAGER = "edtech_manager"
    VENUE_MANAGER = "venue_manager"
    PRODUCTION_DIRECTOR = "production_director"

    # BTL — Operators (1 from study app)
    TECHNICAL_DIRECTOR = "technical_director"

    # CHANNEL — Sales Intermediaries (2 new from PDF research)
    DEALER_DAVE = "dealer_dave"
    SYSTEM_ENGINEER = "system_engineer"


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


# Product-specific competitive comparisons (from collateral CSVs)
PRODUCT_COMPARISONS = {
    "pearl_mini": {
        "vs_extron_smp352": {
            "competitor": "Extron SMP 352",
            "key_diff": "Multi-source vs single-source, integrated recording vs external",
            "epiphan_wins": "6 video sources, built-in recording, cloud management",
        },
        "vs_mediasite": {
            "competitor": "Mediasite Recorders",
            "key_diff": "Hardware encoding vs software, fleet management",
            "epiphan_wins": "No PC dependency, Epiphan Cloud fleet management",
        },
    },
    "pearl_nexus": {
        "vs_extron_smp352": {
            "competitor": "Extron SMP 352",
            "key_diff": "Cloud-native vs local-only management",
            "epiphan_wins": "Zero-touch provisioning, cloud management, SRT gateway",
        },
        "vs_mediasite": {
            "competitor": "Mediasite Recorders",
            "key_diff": "Cloud-first architecture vs legacy software capture",
            "epiphan_wins": "No PC required, multi-site cloud management",
        },
        "vs_maevex_6020": {
            "competitor": "Matrox Maevex 6020",
            "key_diff": "All-in-one vs encode-only",
            "epiphan_wins": "Recording + streaming + switching in one device",
        },
    },
    "pearl_nano": {
        "vs_extron_smp111": {
            "competitor": "Extron SMP 111",
            "key_diff": "Multi-source vs single-source at similar price",
            "epiphan_wins": "2 video sources, SRT/RTMP, NDI input, portable",
        },
        "vs_monarch_hdx": {
            "competitor": "Matrox Monarch HDX",
            "key_diff": "Production features vs encode-only",
            "epiphan_wins": "Built-in switching, layouts, and scheduling",
        },
    },
    "pearl_2": {
        "vs_newtek_capturecast": {
            "competitor": "NewTek CaptureCast",
            "key_diff": "All-in-one production vs switcher-only",
            "epiphan_wins": "12+ sources, recording, streaming, switching in single rack unit",
        },
    },
}


# =============================================
# Reference Stories (proof points)
# =============================================

REFERENCE_STORIES = {
    # ── Higher Ed ────────────────────────────────────────────────
    "ntnu": {
        "customer": "NTNU (Norwegian University)",
        "metric": "100+ rooms",
        "vertical": "higher_ed",
        "products": ["pearl_mini"],
        "quote": "Pearls and Panopto are a perfect fit",
        "quote_theme": "Seamless Panopto integration across 100+ lecture halls",
    },
    "mtsu": {
        "customer": "Middle Tennessee State University",
        "metric": "428 classrooms",
        "vertical": "higher_ed",
        "products": ["pearl_mini"],
        "quote": "Do more with less — 2-person team, 400+ rooms",
        "quote_theme": "One AV team manages 428 rooms via Epiphan Cloud",
    },
    "nc_state": {
        "customer": "NC State University",
        "metric": "300+ rooms",
        "vertical": "higher_ed",
        "products": ["pearl_mini"],
        "quote": "It just works flawlessly",
        "quote_theme": "Standardized on Epiphan for reliability across 300+ rooms",
    },
    "unlv": {
        "customer": "UNLV",
        "metric": "200+ rooms",
        "vertical": "higher_ed",
        "products": ["pearl_nexus"],
        "quote": "Super fast to install and pair",
        "quote_theme": "Automated capture in 200+ classrooms — faculty just teach",
    },
    "vanderbilt": {
        "customer": "Vanderbilt University",
        "metric": "One-button studios",
        "vertical": "higher_ed",
        "products": ["pearl_mini"],
        "quote": "Swiss army knife for us",
        "quote_theme": "Pearl Mini as versatile self-service recording studio",
    },
    "ub": {
        "customer": "University at Buffalo",
        "metric": "Campus-wide deployment",
        "vertical": "higher_ed",
        "products": ["pearl_nexus"],
        "quote": "Eliminated 4-5 devices",
        "quote_theme": "Consolidated AV stack to single Pearl device per room",
    },
    # ── Legal ────────────────────────────────────────────────────
    "ucla_law": {
        "customer": "UCLA School of Law",
        "metric": "Classrooms + courtrooms",
        "vertical": "legal",
        "products": ["pearl_2", "pearl_nexus"],
        "quote": "Edge has been a lifesaver",
        "quote_theme": "Multi-use: classrooms, moot court, and event capture",
    },
    "anchor_point": {
        "customer": "Anchor Point Litigation Support",
        "metric": "Mock trials, mobile",
        "vertical": "legal",
        "products": ["pearl_2"],
        "quote": "Super simple, no complex computer",
        "quote_theme": "Simplified mock trial capture — portable and reliable",
    },
    "benchmark_legal": {
        "customer": "Benchmark Legal Video",
        "metric": "Multi-venue mock trials",
        "vertical": "legal",
        "products": ["pearl_2"],
        "quote": "Flexibility and versatility",
        "quote_theme": "Flexible multi-venue mock trial video capture",
    },
    "verdict_advantage": {
        "customer": "Verdict Advantage",
        "metric": "Mock trials, 6 channels",
        "vertical": "legal",
        "products": ["pearl_2"],
        "quote": "Delivered exactly what we needed",
        "quote_theme": "6-channel mock trial recording for jury analysis",
    },
    # ── Government ───────────────────────────────────────────────
    "hawaii_senate": {
        "customer": "Hawaii State Senate",
        "metric": "6 units, NDI",
        "vertical": "government",
        "products": ["pearl_2"],
        "quote": "Any user can operate with confidence",
        "quote_theme": "Simple enough for any staff member to operate reliably",
    },
    "redfish": {
        "customer": "Redfish Technologies",
        "metric": "60+ installations",
        "vertical": "government",
        "products": ["pearl_mini", "pearl_2"],
        "quote": "Confident in every single Pearl",
        "quote_theme": "60+ Pearl systems across WA state courts and councils",
    },
    # ── Corporate ────────────────────────────────────────────────
    "openai": {
        "customer": "OpenAI",
        "metric": "12 Days livestream",
        "vertical": "corporate",
        "products": ["pearl_2"],
        "quote": "The workhorse of our streams",
        "quote_theme": "The world's leading AI company trusts Pearl for livestream production",
    },
    "crestron_hq": {
        "customer": "Crestron",
        "metric": "HQ webcasts",
        "vertical": "corporate",
        "products": ["pearl_2"],
        "quote": "Changed the game for us",
        "quote_theme": "Even AV industry leaders choose Pearl for their own HQ",
    },
    # ── Live Events ──────────────────────────────────────────────
    "freeman": {
        "customer": "Freeman",
        "metric": "World's largest events",
        "vertical": "live_events",
        "products": ["pearl_2", "pearl_mini"],
        "quote": "Game-changer in customer offering",
        "quote_theme": "Global event production company trusts Pearl fleet for largest events",
    },
    "msavi": {
        "customer": "MSAVi",
        "metric": "Disney, Imagine Dragons",
        "vertical": "live_events",
        "products": ["pearl_2"],
        "quote": "Haven't failed us once",
        "quote_theme": "High-profile events — Disney, Imagine Dragons — zero failures",
    },
    "talon_av": {
        "customer": "Talon AV",
        "metric": "30+ unstaffed rooms",
        "vertical": "live_events",
        "products": ["pearl_nano"],
        "quote": "Swiss Army knife",
        "quote_theme": "30+ unstaffed rooms managed remotely via Epiphan Cloud",
    },
    "oslo_opera": {
        "customer": "Oslo Opera House",
        "metric": "300+ shows/year",
        "vertical": "live_events",
        "products": ["pearl_nano", "pearl_2"],
        "quote": "As easy as their phone",
        "quote_theme": "300+ annual productions captured with minimal staff",
    },
    "the_volume": {
        "customer": "The Volume",
        "metric": "Shannon Sharpe shows",
        "vertical": "live_events",
        "products": ["pearl_2"],
        "quote": "Biggest game changer",
        "quote_theme": "Celebrity podcast/show production powered by Pearl",
    },
    # ── Healthcare ───────────────────────────────────────────────
    "babyflix": {
        "customer": "BabyFlix",
        "metric": "Multi-clinic ultrasound",
        "vertical": "healthcare",
        "products": ["pearl_nano", "avio_4k"],
        "quote": "By far the best",
        "quote_theme": "Multi-clinic ultrasound streaming for expecting parents",
    },
    "charles_sturt": {
        "customer": "Charles Sturt University",
        "metric": "6 sim labs",
        "vertical": "healthcare",
        "products": ["pearl_2"],
        "quote": "Intuitive enough, rarely explain",
        "quote_theme": "Simulation lab recording so intuitive it needs no training",
    },
}


# =============================================
# Sales Collateral Metadata
# =============================================

SALES_COLLATERAL = {
    # Product pages — direct links for each Pearl model
    "product_pages": {
        "pearl_2": {
            "name": "Pearl-2",
            "url": "https://www.epiphan.com/products/pearl-2/",
            "tagline": "Flagship 12+ source all-in-one production system",
        },
        "pearl_mini": {
            "name": "Pearl Mini",
            "url": "https://www.epiphan.com/products/pearl-mini/",
            "tagline": "All-in-one video encoder, recorder, and streamer",
        },
        "pearl_nexus": {
            "name": "Pearl Nexus",
            "url": "https://www.epiphan.com/products/pearl-nexus/",
            "tagline": "Cloud-managed video gateway for distributed teams",
        },
        "pearl_nano": {
            "name": "Pearl Nano",
            "url": "https://www.epiphan.com/products/pearl-nano/",
            "tagline": "Ultra-compact live production system",
        },
        "ec20_ptz": {
            "name": "EC20 PTZ Camera",
            "url": "https://www.epiphan.com/products/ec20/",
            "tagline": "PoE PTZ camera designed for Pearl integration",
        },
        "epiphan_cloud": {
            "name": "Epiphan Cloud",
            "url": "https://www.epiphan.com/products/epiphan-cloud/",
            "tagline": "Fleet management — manage all your Pearls from one dashboard",
        },
    },
    # Case studies with URLs — curated proof points by vertical
    "case_studies": {
        "ntnu": {
            "title": "NTNU — 100+ Rooms with Panopto Integration",
            "url": "https://www.epiphan.com/customers/ntnu/",
            "vertical": "higher_ed",
            "products": ["pearl_mini"],
        },
        "mtsu": {
            "title": "MTSU — 428 Classrooms, 2-Person Team",
            "url": "https://www.epiphan.com/customers/mtsu/",
            "vertical": "higher_ed",
            "products": ["pearl_mini"],
        },
        "nc_state": {
            "title": "NC State — 300+ Pearl Units Campus-Wide",
            "url": "https://www.epiphan.com/customers/nc-state/",
            "vertical": "higher_ed",
            "products": ["pearl_mini"],
        },
        "unlv": {
            "title": "UNLV — 200+ Rooms with Pearl Nexus",
            "url": "https://www.epiphan.com/customers/unlv/",
            "vertical": "higher_ed",
            "products": ["pearl_nexus"],
        },
        "freeman": {
            "title": "Freeman — World's Largest Events on Pearl",
            "url": "https://www.epiphan.com/customers/freeman/",
            "vertical": "live_events",
            "products": ["pearl_2", "pearl_mini"],
        },
        "msavi": {
            "title": "MSAVi — Disney and Imagine Dragons Events",
            "url": "https://www.epiphan.com/customers/msavi/",
            "vertical": "live_events",
            "products": ["pearl_2"],
        },
        "openai": {
            "title": "OpenAI — 12 Days Livestream Production",
            "url": "https://www.epiphan.com/customers/openai/",
            "vertical": "corporate",
            "products": ["pearl_2"],
        },
        "hawaii_senate": {
            "title": "Hawaii Senate — 6 NDI-Enabled Units",
            "url": "https://www.epiphan.com/customers/hawaii-state-senate/",
            "vertical": "government",
            "products": ["pearl_2"],
        },
        "ucla_law": {
            "title": "UCLA Law — Classrooms and Courtrooms",
            "url": "https://www.epiphan.com/customers/ucla-law/",
            "vertical": "legal",
            "products": ["pearl_2", "pearl_nexus"],
        },
        "babyflix": {
            "title": "BabyFlix — Multi-Clinic Ultrasound Streaming",
            "url": "https://www.epiphan.com/customers/babyflix/",
            "vertical": "healthcare",
            "products": ["pearl_nano", "avio_4k"],
        },
        "oslo_opera": {
            "title": "Oslo Opera House — 300+ Shows/Year",
            "url": "https://www.epiphan.com/customers/oslo-opera/",
            "vertical": "live_events",
            "products": ["pearl_nano", "pearl_2"],
        },
        "the_volume": {
            "title": "The Volume — Shannon Sharpe Show Production",
            "url": "https://www.epiphan.com/customers/the-volume/",
            "vertical": "live_events",
            "products": ["pearl_2"],
        },
    },
    # Webinars
    "webinars": [
        {
            "title": "Lecture Capture at Scale",
            "vertical": "higher_ed",
            "products": ["pearl_mini", "pearl_nexus"],
            "url": "https://www.epiphan.com/resources/webinars/",
            "description": "How universities deploy 100+ rooms with 2-person AV teams",
        },
        {
            "title": "Live Event Production with Pearl",
            "vertical": "live_events",
            "products": ["pearl_2", "pearl_mini"],
            "url": "https://www.epiphan.com/resources/webinars/",
            "description": "Multi-camera production for concerts, conferences, and broadcasts",
        },
        {
            "title": "Courtroom & Government Recording",
            "vertical": "government",
            "products": ["pearl_2", "pearl_mini"],
            "url": "https://www.epiphan.com/resources/webinars/",
            "description": "Reliable recording for transparency mandates and public access",
        },
    ],
    # Competitive comparisons (metadata only — no URLs for competitor content)
    "competitive": {
        "pearl_mini": {
            "vs_extron": "Pearl Mini vs Extron SMP 352 — multi-source vs single-source",
            "vs_mediasite": "Pearl Mini vs Mediasite — hardware encoding vs software dependency",
        },
        "pearl_nexus": {
            "vs_extron": "Pearl Nexus vs Extron SMP 352 — cloud-native vs local-only",
            "vs_maevex": "Pearl Nexus vs Matrox Maevex 6020 — all-in-one vs encode-only",
        },
        "pearl_nano": {
            "vs_extron": "Pearl Nano vs Extron SMP 111 — multi-source vs single-source",
            "vs_monarch": "Pearl Nano vs Matrox Monarch HDX — production features vs encode-only",
        },
        "pearl_2": {
            "vs_newtek": "Pearl-2 vs NewTek CaptureCast — all-in-one vs switcher-only",
        },
    },
    # Key resource pages
    "resources": {
        "all_customers": "https://www.epiphan.com/customers/",
        "all_products": "https://www.epiphan.com/products/",
        "support": "https://www.epiphan.com/support/",
        "contact_sales": "https://www.epiphan.com/contact/",
        "partner_program": "https://www.epiphan.com/partners/",
        "request_demo": "https://www.epiphan.com/request-demo/",
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
            "cares_about": [
                "system reliability",
                "fleet standardization",
                "ease of management",
                "vendor support quality",
                "peer recognition",
                "end-of-lifecycle planning",
            ],
            "tone": "Peer-level AV professional. Speak to the pressure of managing hundreds of rooms.",
            "value_angle": "COI",
            "value_framing": "Every room with unreliable AV is a support ticket and a frustrated user. Standardize and forget about it.",
            "hooks": [
                "NC State runs 300+ Pearls — one AV team, zero headaches",
                "What if every room just worked the same way?",
                "Stop babysitting AV. Start managing it.",
                "You're not alone — 300+ universities standardized on Pearl",
                "Embrace end of lifecycle — replace aging gear before it fails you",
            ],
            "voice_tone": "AV peer. You've both done the 6AM setup and the midnight troubleshooting call. AV nerd who loves technology — trusts his peers, doesn't like being sold to.",
            "vocabulary": [
                "fleet management",
                "standardize",
                "rack-mount",
                "signal chain",
                "commissioning",
                "punchlist",
                "as-built",
                "AV-over-IP",
                "NDI",
                "SRT",
                "RTMP",
                "Dante",
                "PoE",
                "end of lifecycle",
                "AVIXA",
                "InfoComm",
                "peer network",
            ],
            "forbidden_phrases": [
                "digital transformation",
                "synergize",
                "paradigm shift",
                "enterprise journey",
                "holistic solution",
                "leverage",
            ],
            "default_visual_style": "clean",
            "pdf_source": "AV Andy",
            "measured_by": ["functionality", "uptime", "adoption", "satisfaction", "peer recognition"],
            "key_messages": ["You're not alone", "There's a better way", "Embrace end of lifecycle", "Advocate for yourself"],
        },
        AudiencePersona.LD_DIRECTOR: {
            "title": "L&D Director",
            "persona_type": "ATL",
            "verticals": ["corporate", "healthcare", "industrial"],
            "cares_about": [
                "training content quality",
                "scalable delivery",
                "compliance documentation",
                "measurement",
            ],
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
                "learning outcomes",
                "content library",
                "compliance training",
                "onboarding",
                "knowledge capture",
                "LMS integration",
                "Panopto",
                "Kaltura",
                "SCORM",
                "blended learning",
            ],
            "forbidden_phrases": [
                "cutting-edge",
                "revolutionary",
                "game-changing",
                "best-in-class",
                "enterprise-grade",
                "robust platform",
            ],
            "default_visual_style": "polished",
        },
        AudiencePersona.SIM_CENTER_DIRECTOR: {
            "title": "Simulation Center Director",
            "persona_type": "ATL",
            "verticals": ["healthcare"],
            "cares_about": [
                "multi-angle recording",
                "debrief quality",
                "HIPAA compliance",
                "SimCapture/CAE integration",
            ],
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
                "debrief",
                "simulation",
                "standardized patient",
                "manikin",
                "INACSL",
                "SimCapture",
                "CAE",
                "high-fidelity sim",
                "multi-angle",
                "synchronized playback",
                "HIPAA",
            ],
            "forbidden_phrases": [
                "game-changing",
                "synergy",
                "leverage",
                "paradigm",
                "revolutionary",
                "disruptive",
                "best-in-class",
            ],
            "default_visual_style": "data_viz",
        },
        AudiencePersona.COURT_ADMIN: {
            "title": "Court Administrator",
            "persona_type": "ATL",
            "verticals": ["legal", "government"],
            "cares_about": [
                "record integrity",
                "chain of custody",
                "reliability",
                "public access compliance",
                "compliance",
                "redundancy",
                "evidence integrity",
            ],
            "tone": "Judicial professional. Reliability and record integrity are non-negotiable. Failure isn't an option.",
            "value_angle": "COI",
            "value_framing": "A failed recording of court proceedings isn't an inconvenience — it's a legal crisis. Don't risk it.",
            "hooks": [
                "Court recording that never fails, never loses footage",
                "Tamper-proof records for chain of custody",
                "Public access streaming that actually works for every hearing",
                "Foolproof, compliant, simple — because failure isn't an option",
            ],
            "voice_tone": "Judicial gravity. Every word matters. Reliability is the only feature that counts. Needs tools that are foolproof, compliant, simple.",
            "vocabulary": [
                "record of proceedings",
                "chain of custody",
                "public access",
                "remote testimony",
                "court reporter",
                "transcript",
                "tamper-proof",
                "archival",
                "retention policy",
                "redundancy",
                "compliance",
                "evidence integrity",
            ],
            "forbidden_phrases": [
                "game-changing",
                "revolutionary",
                "cutting-edge",
                "disruptive",
                "exciting",
                "innovative",
            ],
            "default_visual_style": "clean",
            "pdf_source": "Courtroom Carl",
            "bdr_tip": "Emphasize redundancy, simplicity, peace of mind",
        },
        AudiencePersona.CORP_COMMS: {
            "title": "Corporate Communications Director",
            "persona_type": "ATL",
            "verticals": ["corporate"],
            "cares_about": [
                "broadcast quality",
                "executive presence",
                "brand consistency",
                "multi-platform distribution",
            ],
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
                "town hall",
                "all-hands",
                "executive communication",
                "brand standards",
                "simulcast",
                "multi-platform",
                "production value",
                "B-roll",
                "lower thirds",
            ],
            "forbidden_phrases": [
                "synergize",
                "leverage",
                "paradigm shift",
                "holistic",
                "enterprise journey",
                "robust",
            ],
            "default_visual_style": "polished",
        },
        AudiencePersona.EHS_MANAGER: {
            "title": "EHS Manager",
            "persona_type": "ATL",
            "verticals": ["industrial"],
            "cares_about": [
                "OSHA compliance",
                "safety training documentation",
                "incident recording",
                "audit readiness",
            ],
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
                "OSHA",
                "compliance",
                "incident report",
                "safety training",
                "lockout/tagout",
                "JSA",
                "SOP documentation",
                "audit trail",
                "recordkeeping",
                "toolbox talk",
            ],
            "forbidden_phrases": [
                "game-changing",
                "revolutionary",
                "cutting-edge",
                "best-in-class",
                "synergy",
                "paradigm",
            ],
            "default_visual_style": "bold",
        },
        AudiencePersona.LAW_FIRM_IT: {
            "title": "Law Firm IT Director",
            "persona_type": "ATL",
            "verticals": ["legal"],
            "cares_about": [
                "data security",
                "on-premises control",
                "remote deposition quality",
                "partner satisfaction",
            ],
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
                "on-premises",
                "data sovereignty",
                "encryption at rest",
                "deposition",
                "remote testimony",
                "e-discovery",
                "network segmentation",
                "compliance",
                "partner satisfaction",
            ],
            "forbidden_phrases": [
                "cloud-first",
                "SaaS",
                "disruptive",
                "game-changing",
                "revolutionary",
                "best-in-class",
                "cutting-edge",
            ],
            "default_visual_style": "clean",
        },
        # ── ATL: Higher Ed Executive Buyers ────────────────────────
        AudiencePersona.PROVOST: {
            "title": "Provost / VP Academic Affairs",
            "persona_type": "ATL",
            "verticals": ["higher_ed"],
            "cares_about": [
                "student outcomes",
                "faculty satisfaction",
                "accreditation readiness",
                "digital learning strategy",
            ],
            "tone": "Academic executive. Speak to strategic impact on teaching and learning mission.",
            "value_angle": "ROI",
            "value_framing": "Every classroom without reliable lecture capture is a missed opportunity for student success and retention.",
            "hooks": [
                "UNLV saw measurable retention gains after deploying lecture capture in 215 rooms",
                "Faculty adoption rates soar when recording is one-button simple",
                "Hybrid learning isn't optional — your accreditor expects it",
            ],
            "voice_tone": "Strategic academic leader. You think in terms of student outcomes, faculty workload, and institutional mission.",
            "vocabulary": [
                "student outcomes",
                "retention",
                "accreditation",
                "faculty satisfaction",
                "digital learning",
                "hybrid pedagogy",
                "strategic plan",
                "provost council",
                "academic technology",
                "institutional effectiveness",
            ],
            "forbidden_phrases": [
                "synergize",
                "paradigm shift",
                "cutting-edge",
                "game-changing",
                "disruptive",
                "best-in-class",
                "robust platform",
            ],
            "default_visual_style": "polished",
        },
        AudiencePersona.UNIVERSITY_PRESIDENT: {
            "title": "University President",
            "persona_type": "ATL",
            "verticals": ["higher_ed"],
            "cares_about": [
                "institutional reputation",
                "innovation narrative",
                "student experience",
                "board of trustees visibility",
            ],
            "tone": "Institutional leader. Speak to vision, reputation, and competitive positioning.",
            "value_angle": "ROI",
            "value_framing": "Campus-wide AV infrastructure is a strategic investment in institutional reputation and the student experience that drives enrollment.",
            "hooks": [
                "NC State's 300+ room deployment became a recruiting differentiator",
                "Your board wants to see innovation — show them a campus that just works",
                "Students choose universities that invest in their learning experience",
            ],
            "voice_tone": "Presidential gravitas. Vision, legacy, and institutional excellence.",
            "vocabulary": [
                "strategic vision",
                "board of trustees",
                "institutional excellence",
                "student experience",
                "campus innovation",
                "enrollment",
                "accreditation",
                "capital investment",
                "institutional reputation",
                "competitive positioning",
            ],
            "forbidden_phrases": [
                "synergize",
                "leverage",
                "paradigm shift",
                "disruptive",
                "game-changing",
                "best-in-class",
                "cutting-edge",
            ],
            "default_visual_style": "polished",
        },
        AudiencePersona.UNIVERSITY_FINANCE: {
            "title": "VP Finance / CFO",
            "persona_type": "ATL",
            "verticals": ["higher_ed"],
            "cares_about": [
                "total cost of ownership",
                "capital vs operating budget",
                "procurement compliance",
                "vendor stability",
            ],
            "tone": "Finance executive. Speak to TCO, lifecycle cost, and fiscal responsibility.",
            "value_angle": "ROI",
            "value_framing": "Hardware-based AV is a capital asset that depreciates predictably — no surprise SaaS renewals, no per-seat fees eating your operating budget.",
            "hooks": [
                "Pearl hardware lasts 7+ years — compare that to annual SaaS renewals",
                "Capital expenditure today vs. recurring OpEx forever — the math is clear",
                "MTSU manages 428 rooms with the same small AV team — that's TCO efficiency",
            ],
            "voice_tone": "Fiscally disciplined. Every dollar must be justified with lifecycle math.",
            "vocabulary": [
                "TCO",
                "capital expenditure",
                "depreciation",
                "bond cycle",
                "procurement",
                "RFP",
                "operating budget",
                "lifecycle cost",
                "vendor stability",
                "fiscal year",
            ],
            "forbidden_phrases": [
                "game-changing",
                "revolutionary",
                "cutting-edge",
                "disruptive",
                "synergy",
                "paradigm",
                "best-in-class",
            ],
            "default_visual_style": "data_viz",
        },
        # ── BTL: Operators ────────────────────────────────────────
        AudiencePersona.TECHNICAL_DIRECTOR: {
            "title": "Technical Director / AV Operator",
            "persona_type": "BTL",
            "verticals": [
                "higher_ed",
                "corporate",
                "live_events",
                "houses_of_worship",
                "healthcare",
            ],
            "cares_about": [
                "ease of use",
                "reliability under pressure",
                "quick setup",
                "real-time monitoring",
                "competitive edge",
                "standing out from competitors",
            ],
            "tone": "Fellow operator. You've both been in the back of the room making live TV happen.",
            "value_angle": "EASE",
            "value_framing": "When the president walks on stage, the switcher better work. No excuses, no reboots, no 'give me a minute.'",
            "hooks": [
                "One-button start. Every source. Every time.",
                "Built for the operator who can't afford a crash during the show",
                "The gear that works when the pressure is highest",
                "Stand out from competitors with production quality they can't match",
            ],
            "voice_tone": "Operator empathy. You understand the stress of live production and the joy of a clean show. Open to trying new solutions to stand out.",
            "vocabulary": [
                "cue",
                "cut",
                "fade",
                "PGM/PVW",
                "tally",
                "multiview",
                "ISO record",
                "confidence monitor",
                "return feed",
                "comms",
                "rundown",
                "show flow",
            ],
            "forbidden_phrases": [
                "leverage",
                "synergize",
                "enterprise",
                "stakeholder",
                "paradigm",
                "holistic",
                "best-in-class",
            ],
            "default_visual_style": "sketch",
            "pdf_source": "Expert Edward",
            "challenges": ["competitive pressure", "limited resources", "budget constraints"],
        },
        # ── CHANNEL: Sales Intermediaries (from PDF research) ────────
        AudiencePersona.DEALER_DAVE: {
            "title": "Channel Account Manager / Regional Sales Manager",
            "persona_type": "CHANNEL",
            "verticals": [
                "higher_ed", "corporate", "live_events", "government",
                "houses_of_worship", "healthcare", "industrial", "legal",
                "ux_research", "k12",
            ],
            "cares_about": [
                "deal support",
                "demo assets",
                "competitive differentiators",
                "margin",
                "vendor reliability",
                "minimal support calls",
            ],
            "tone": "Fellow sales professional; peer-to-peer, not vendor-to-buyer.",
            "value_angle": "ENABLEMENT",
            "value_framing": "Arm your team with assets that close deals. Products that install cleanly and generate zero support calls.",
            "hooks": [
                "Your customer's AV Director will forward this to their VP",
                "Pre-built battlecard, ready for your next demo",
                "Products that install cleanly and generate zero support calls",
                "Arm him with one-pagers, spec sheets, competitive differentiators he can copy/paste to clients",
            ],
            "voice_tone": "Fellow sales professional. You understand deal cycles, margin pressure, and the importance of vendor reliability.",
            "vocabulary": [
                "deal reg", "margin", "demo", "proof of concept", "RFP", "bid",
                "distribution", "rep", "territory", "install base", "upsell",
                "attach rate", "ASP", "one-pager", "spec sheet", "copy/paste to client",
            ],
            "forbidden_phrases": [
                "corporate jargon",
                "synergize",
                "paradigm shift",
                "holistic",
                "enterprise journey",
                "leverage",
            ],
            "default_visual_style": "polished",
            "pdf_source": "Dealer Dave",
            "org_size": "10-250 employees (AVI-SPL, Diversified, Ford AV)",
            "titles": ["Regional Sales Manager", "Sales Engineer", "Account Executive", "VP Sales"],
            "buys_based_on": ["reliability track record", "margin", "vendor support", "ease of quoting"],
            "fears": ["recommending something that fails at client site", "losing a customer relationship"],
            "bdr_tip": "Arm him with one-pagers, spec sheets, competitive differentiators he can copy/paste to clients",
        },
        AudiencePersona.SYSTEM_ENGINEER: {
            "title": "AV Systems Designer / Pre-sales Engineer",
            "persona_type": "CHANNEL",
            "verticals": [
                "higher_ed", "corporate", "live_events", "government",
                "houses_of_worship", "healthcare", "industrial", "legal",
                "ux_research", "k12",
            ],
            "cares_about": [
                "API quality",
                "integration specs",
                "partner ecosystem compatibility",
                "installation simplicity",
                "post-install support burden",
            ],
            "tone": "Technical peer; speak to specs, integration, and real-world deployment.",
            "value_angle": "TECHNICAL",
            "value_framing": "Designed to integrate cleanly with your stack. Open API, native NDI/SRT, works with Q-SYS and Kaltura out of the box.",
            "hooks": [
                "Open API, native NDI/SRT, integrates with Q-SYS and Kaltura out of the box",
                "Case studies from integrators who've deployed 60+ units",
                "Sharp and self-sufficient — clear API access and configuration guides",
            ],
            "voice_tone": "Technical peer. Sharp and self-sufficient. Speak to specs, integration, and real-world deployment challenges.",
            "vocabulary": [
                "API", "Q-SYS", "Crestron", "AMX", "Dante", "NDI", "AV-over-IP",
                "signal flow", "as-built", "rack unit", "PoE budget", "network topology",
                "VLAN", "multicast",
            ],
            "forbidden_phrases": [
                "marketing fluff",
                "game-changing",
                "revolutionary",
                "best-in-class",
                "cutting-edge",
                "synergy",
            ],
            "default_visual_style": "sketch",
            "pdf_source": "System Engineer Sam",
            "org_size": "10-100 employees (integrators)",
            "titles": ["AV Systems Designer", "Technical Consultant", "Design Engineer", "Pre-sales Engineer"],
            "buys_based_on": ["technical specs", "API quality", "integration flexibility", "peer validation"],
            "fears": ["specifying a product that doesn't integrate cleanly", "having to support it post-install"],
            "bdr_tip": "Show case studies, connect him with product champions, highlight partner ecosystem (Q-SYS, Kaltura, Panopto)",
        },
        # ── ATL: Edtech & Live Events (from PDF research) ───────────
        AudiencePersona.EDTECH_MANAGER: {
            "title": "Educational Technology Manager",
            "persona_type": "ATL",
            "verticals": ["higher_ed", "k12"],
            "cares_about": [
                "LMS/CMS integration",
                "faculty adoption rates",
                "student accessibility",
                "platform compatibility",
                "seamless edtech experience",
            ],
            "tone": "Edtech peer; you understand faculty resistance and the adoption challenge.",
            "value_angle": "ADOPTION",
            "value_framing": "Faculty actually use it because it just works with their LMS. Capture happens automatically — adoption isn't an issue when there's nothing to adopt.",
            "hooks": [
                "Native Panopto and Kaltura integration — faculty don't change their workflow",
                "Capture happens automatically — adoption isn't an issue when there's nothing to adopt",
                "Align with her vision for seamless edtech",
            ],
            "voice_tone": "Edtech peer. Visionary who wants seamless edtech experience. Understands faculty resistance to change.",
            "vocabulary": [
                "LMS", "CMS", "Panopto", "Kaltura", "SCORM", "accessibility",
                "universal design", "faculty adoption", "student engagement",
                "lecture capture", "content management", "platform integration",
            ],
            "forbidden_phrases": [
                "pure AV jargon",
                "hardware specs without learning context",
                "game-changing",
                "revolutionary",
                "best-in-class",
                "cutting-edge",
            ],
            "default_visual_style": "polished",
            "pdf_source": "Software Sophie",
            "titles": ["Educational Technology Manager", "Learning Technology Coordinator"],
            "key_challenge": "Faculty resistance to change, driving adoption",
            "bdr_tip": "Align with her vision for seamless edtech. Show Panopto/Kaltura integration stories.",
        },
        AudiencePersona.VENUE_MANAGER: {
            "title": "Head of AV / Venue AV Manager",
            "persona_type": "ATL",
            "verticals": ["live_events", "houses_of_worship"],
            "cares_about": [
                "multi-event flexibility",
                "client satisfaction",
                "budget constraints",
                "equipment reliability",
                "staff that can operate without extensive training",
            ],
            "tone": "Venue operations professional; you understand the pressure of back-to-back events with different requirements.",
            "value_angle": "VERSATILITY",
            "value_framing": "One system, every event type. Orchestra on Monday, corporate keynote on Tuesday — same Pearl, different layout.",
            "hooks": [
                "Orchestra on Monday, corporate keynote on Tuesday — same Pearl, different layout",
                "Oslo Opera runs 300+ shows/year on Pearl",
                "One system, every event type",
            ],
            "voice_tone": "Venue operations professional. You understand back-to-back events with different requirements and the pressure of client satisfaction.",
            "vocabulary": [
                "green room", "load-in", "strike", "house system", "venue tech",
                "event manager", "client specs", "AV rider", "house camera", "IMAG",
                "program feed", "webcast", "multi-camera",
            ],
            "forbidden_phrases": [
                "enterprise software language",
                "cloud-first",
                "synergize",
                "paradigm",
                "holistic",
                "best-in-class",
            ],
            "default_visual_style": "clean",
            "pdf_source": "Venue Vernon",
            "titles": ["Head of AV", "AV Manager", "Technical Director"],
            "project_types": ["Orchestra Houses", "Conference Centers", "Arts Centers", "Theaters"],
            "challenges": ["budget", "equipment limitations", "client retention", "unexpected hurdles"],
        },
        AudiencePersona.PRODUCTION_DIRECTOR: {
            "title": "Senior Video Engineer / Director of Event Technology",
            "persona_type": "ATL",
            "verticals": ["live_events"],
            "cares_about": [
                "fleet management at scale",
                "reliability and uptime",
                "inventory lifecycle",
                "standardization across venues",
                "enterprise support SLA",
            ],
            "tone": "Enterprise production executive; you think in fleets, not individual boxes.",
            "value_angle": "SCALE",
            "value_framing": "Manage 100 units like 1. Fleet management, standardization, enterprise support.",
            "hooks": [
                "Freeman trusts Pearl for the world's largest events",
                "MSAVi runs Disney events — 'Haven't failed us once'",
                "Epiphan Cloud manages your entire fleet from one dashboard",
            ],
            "voice_tone": "Enterprise production executive. You think in fleets, not individual boxes. Values reliability, low-risk solutions that ensure uptime.",
            "vocabulary": [
                "fleet management", "inventory", "lifecycle", "uptime SLA", "redundancy",
                "failover", "standardization", "deployment template", "enterprise support",
                "spare pool", "RMA",
            ],
            "forbidden_phrases": [
                "affordable",
                "compact",
                "portable",
                "small-scale",
                "game-changing",
                "best-in-class",
            ],
            "default_visual_style": "data_viz",
            "pdf_source": "Solution Steve",
            "org_size": "1K-10K employees (Freeman, Encore, AVI-SPL, GPJ)",
            "titles": ["Senior Video Engineer", "Director Event Technology"],
            "key_concern": "Management at Scale: Inventory, uptime, lifecycle, reliability",
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
            # Internal marketing/sales language
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
            "300+ rooms at NC State",
            "428 rooms at MTSU",
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

    return icp_preset["audience_personas"].get(
        persona, icp_preset["audience_personas"][AudiencePersona.AV_DIRECTOR]
    )


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


def get_competitive_positioning(
    competitor: str | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
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
            raise ValueError(
                f"Unknown competitor: {competitor}. Available: {available}"
            )
        return comp
    return list(COMPETITIVE_INTEL.values())


def get_product_comparisons(product_id: str | None = None) -> dict[str, Any]:
    """
    Get product-specific competitive comparisons.

    Args:
        product_id: Optional product ID (e.g., "pearl_mini"). Returns all if None.

    Returns:
        Product comparison dict for one product, or all comparisons.
    """
    if product_id:
        return PRODUCT_COMPARISONS.get(product_id, {})
    return PRODUCT_COMPARISONS


def get_sales_collateral(
    category: str | None = None, vertical: str | None = None
) -> dict[str, Any]:
    """
    Get sales collateral metadata, optionally filtered.

    Args:
        category: Optional category filter ("webinars", "competitive", "brochures", "case_studies")
        vertical: Optional vertical filter (only applies to webinars and case_studies)

    Returns:
        Filtered collateral dict or full SALES_COLLATERAL.
    """
    if category:
        data = SALES_COLLATERAL.get(category, {})
        if vertical and isinstance(data, list):
            return [item for item in data if item.get("vertical") == vertical]
        if category == "case_studies" and vertical and isinstance(data, dict):
            return {k: v for k, v in data.items() if v.get("vertical") == vertical}
        return data
    return SALES_COLLATERAL


def get_collateral_links(
    audience: str | None = None,
    vertical: str | None = None,
    products: list[str] | None = None,
) -> dict[str, Any]:
    """
    Build a curated set of collateral links for a storyboard download.

    Returns links to relevant product pages, case studies, and resources
    based on the audience persona, vertical, and products mentioned.
    The BDR can share these alongside the storyboard PDF.

    Args:
        audience: Audience persona string (e.g., "av_director")
        vertical: Vertical string (e.g., "higher_ed")
        products: Optional list of product IDs mentioned in the storyboard

    Returns:
        Dict with "product_links", "case_study_links", "resource_links" keys.
    """
    result: dict[str, Any] = {
        "product_links": [],
        "case_study_links": [],
        "resource_links": {},
    }

    collateral = SALES_COLLATERAL

    # Product links — from products mentioned or persona's recommended products
    product_ids = set(products or [])
    if not product_ids and vertical and vertical in EPIPHAN_VERTICALS:
        product_ids = set(EPIPHAN_VERTICALS[vertical].get("recommended_products", []))

    product_pages = collateral.get("product_pages", {})
    for pid in product_ids:
        if pid in product_pages:
            result["product_links"].append(product_pages[pid])
    # Always include Epiphan Cloud
    if "epiphan_cloud" in product_pages:
        result["product_links"].append(product_pages["epiphan_cloud"])

    # Case study links — filtered by vertical
    case_studies = collateral.get("case_studies", {})
    for _key, study in case_studies.items():
        if isinstance(study, dict):
            if vertical and study.get("vertical") == vertical:
                result["case_study_links"].append(study)
            elif not vertical:
                result["case_study_links"].append(study)

    # Limit to top 3 most relevant case studies
    result["case_study_links"] = result["case_study_links"][:3]

    # Resource links — always include key pages
    resources = collateral.get("resources", {})
    # Channel personas get partner program link prominently
    persona_config = None
    if audience:
        try:
            persona_config = get_audience_persona(audience)
        except Exception:
            pass

    result["resource_links"] = {
        "request_demo": resources.get("request_demo", ""),
        "contact_sales": resources.get("contact_sales", ""),
        "all_customers": resources.get("all_customers", ""),
    }
    if persona_config and persona_config.get("persona_type") == "CHANNEL":
        result["resource_links"]["partner_program"] = resources.get("partner_program", "")

    return result


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
    sanitized = re.sub(
        r"^class\s+\w+.*:$", "[Feature Component]", sanitized, flags=re.MULTILINE
    )
    sanitized = re.sub(
        r"^def\s+\w+\(.*\):$", "[Process Step]", sanitized, flags=re.MULTILINE
    )
    sanitized = re.sub(
        r"^async\s+def\s+\w+\(.*\):$",
        "[Automated Process]",
        sanitized,
        flags=re.MULTILINE,
    )

    # Remove API keys and secrets
    sanitized = re.sub(
        r'["\']?[A-Za-z_]*(?:KEY|SECRET|TOKEN|PASSWORD)["\']?\s*[=:]\s*["\'][^"\']+["\']',
        "[REDACTED]",
        sanitized,
        flags=re.IGNORECASE,
    )

    # Remove URLs with internal paths
    sanitized = re.sub(
        r"https?://[^\s]+(?:internal|staging|dev|api\.)[^\s]*",
        "[Internal URL]",
        sanitized,
    )

    # Remove email addresses
    sanitized = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[email]", sanitized
    )

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
- AVOID these words/phrases: {", ".join(avoid[:10])}...
- USE these words/phrases: {", ".join(use[:10])}...
- Write for a 5th grader - if they can't understand it, simplify it
- NO technical jargon - translate everything to business benefits
- NO proprietary details - if a competitor could copy it, remove it"""

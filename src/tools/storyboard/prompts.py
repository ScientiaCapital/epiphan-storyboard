"""
Storyboard Prompts
==================

Static persona dictionaries and style instructions for the storyboard pipeline.

These are pure functions (no class state) extracted from GeminiStoryboardClient.
Each function takes an audience/style string and returns a prompt fragment.
"""


def get_value_angle_instruction(audience: str) -> str:
    """
    Get value angle framing instruction for extraction based on audience.

    This ensures the extraction phase knows HOW to frame value:
    - COI (Cost of Inaction): What they LOSE by not acting
    - ROI (Return on Investment): What they GAIN by acting
    - EASE: How much simpler their life becomes
    - URGENCY: Why they need to act NOW
    """
    value_angles = {
        # ── ATL: Decision Makers ──────────────────────────────────
        "av_director": """VALUE FRAMING: COI (Cost of Inaction) - AMPLIFIED

SPEAK TO THE AV DIRECTOR'S FLEET BURDEN:
- Every room with different AV is a support ticket and a frustrated user.
- Standardize once. Manage from anywhere. Forget about it.
- NC State runs 300+ Pearls with one AV team.
- "Stop babysitting AV. Start managing it."

VOCABULARY THAT RESONATES:
- "fleet management", "standardize", "rack-mount", "signal chain"
- "commissioning", "as-built", "NDI", "SRT", "PoE"
- "zero headaches", "one team, hundreds of rooms"

FORBIDDEN (sounds like marketing):
- "digital transformation", "synergize", "paradigm shift", "holistic"

EMOTIONAL CORE: Professional pride. Managing hundreds of rooms without losing sleep.
""",
        "ld_director": """VALUE FRAMING: ROI (Knowledge Capture) - AMPLIFIED

SPEAK TO THE L&D LEADER'S MISSION:
- Your best trainer retires next year. Their knowledge walks out the door.
- Capture once, deliver forever, to every location.
- LMS integration means content goes where learners are.
- "OSHA says document it. Epiphan makes it effortless."

VOCABULARY THAT RESONATES:
- "knowledge capture", "learning outcomes", "compliance training"
- "onboarding at scale", "LMS integration", "content library"
- "blended learning", "one recording, every new hire"

FORBIDDEN (sounds like tech marketing):
- "cutting-edge", "revolutionary", "game-changing", "enterprise-grade"

EMOTIONAL CORE: Protecting institutional knowledge. Measurable training ROI.
""",
        "sim_center_director": """VALUE FRAMING: COI (Missed Learning) - AMPLIFIED

SPEAK TO THE SIM CENTER EDUCATOR:
- Every simulation without proper recording is a missed learning opportunity.
- Students deserve better debriefs — multi-angle, synchronized, reviewable.
- HIPAA-compliant recording that stays on YOUR network.
- "Your manikin is $100K — the recording shouldn't be an afterthought."

VOCABULARY THAT RESONATES:
- "debrief", "simulation", "standardized patient", "manikin"
- "INACSL", "SimCapture", "multi-angle", "synchronized playback"
- "high-fidelity sim", "HIPAA", "local recording"

FORBIDDEN (sounds like AV marketing):
- "game-changing", "synergy", "leverage", "paradigm", "disruptive"

EMOTIONAL CORE: Clinical education excellence. Every sim recorded, every debrief better.
""",
        "court_admin": """VALUE FRAMING: COI (Legal Risk) - AMPLIFIED

SPEAK WITH JUDICIAL GRAVITY:
- A failed recording of court proceedings isn't an inconvenience — it's a legal crisis.
- Tamper-proof records. Chain of custody. Public access compliance.
- Court reporters are scarce. Reliable video recording fills the gap.
- "The record must be complete. Every time. No exceptions."

VOCABULARY THAT RESONATES:
- "record of proceedings", "chain of custody", "public access"
- "remote testimony", "tamper-proof", "archival", "retention policy"
- "unattended recording", "court reporter shortage"

FORBIDDEN (sounds flippant):
- "game-changing", "revolutionary", "exciting", "innovative"

EMOTIONAL CORE: Judicial integrity. The record is everything. Zero tolerance for failure.
""",
        "corp_comms": """VALUE FRAMING: ROI (Brand Quality) - AMPLIFIED

SPEAK TO THE COMMUNICATIONS PROFESSIONAL:
- Your CEO's town hall shouldn't look like a bad Zoom call.
- Broadcast quality from every room, every time, without a production crew.
- Stream to Teams, YouTube, and your intranet simultaneously.
- "One device turns any room into a broadcast studio."

VOCABULARY THAT RESONATES:
- "town hall", "all-hands", "executive communication"
- "brand standards", "simulcast", "production value"
- "multi-platform", "broadcast quality", "professional presence"

FORBIDDEN (sounds like internal jargon):
- "synergize", "leverage", "paradigm shift", "holistic"

EMOTIONAL CORE: Brand protection. When leadership is on camera, quality is non-negotiable.
""",
        "ehs_manager": """VALUE FRAMING: COI (Compliance Risk) - AMPLIFIED

SPEAK TO THE SAFETY PROFESSIONAL:
- OSHA doesn't accept "the recording failed" as an excuse.
- One incident without documentation can cost millions.
- Your most experienced operator retires next year. Capture everything now.
- "Record every safety procedure. Prove every training session."

VOCABULARY THAT RESONATES:
- "OSHA", "compliance", "incident report", "safety training"
- "lockout/tagout", "JSA", "SOP documentation"
- "audit trail", "recordkeeping", "toolbox talk"

FORBIDDEN (sounds trivial):
- "game-changing", "revolutionary", "cutting-edge", "best-in-class"

EMOTIONAL CORE: Safety-first pragmatism. Documentation saves lives and lawsuits.
""",
        "law_firm_it": """VALUE FRAMING: COI (Partner Frustration + Risk) - AMPLIFIED

SPEAK TO THE LAW FIRM IT PROFESSIONAL:
- When a deposition recording fails, billable hours don't stop. Neither does the partner's frustration.
- Data stays on YOUR network — not someone else's cloud.
- Remote depositions in 4K, every time, with no IT involvement.
- "Partners don't call IT to complain about working AV."

VOCABULARY THAT RESONATES:
- "on-premises", "data sovereignty", "encryption at rest"
- "deposition", "remote testimony", "e-discovery"
- "network segmentation", "compliance", "partner satisfaction"

FORBIDDEN (sounds risky):
- "cloud-first", "SaaS", "disruptive", "game-changing"

EMOTIONAL CORE: Security, reliability, and zero complaints from demanding attorneys.
""",
        # ── BTL: Operators ────────────────────────────────────────
        "technical_director": """VALUE FRAMING: EASE (Operator Reliability) - AMPLIFIED

SPEAK TO THE OPERATOR'S REALITY:
- When the president walks on stage, the switcher better work. No excuses.
- One-button start. Every source. Every time.
- Built for the operator who can't afford a crash during the show.
- "The gear that works when the pressure is highest."
- Open to trying new solutions to stand out from competitors.

VOCABULARY THAT RESONATES:
- "cue", "cut", "fade", "PGM/PVW", "tally"
- "multiview", "ISO record", "confidence monitor"
- "one-touch", "reliable under pressure", "field-proven"

FORBIDDEN (sounds corporate):
- "leverage", "synergize", "enterprise", "stakeholder", "paradigm"

EMOTIONAL CORE: Operator pride. Clean shows. Gear you can trust when it matters most.
""",
        # ── CHANNEL: Sales Intermediaries (from PDF research) ────────
        "dealer_dave": """VALUE FRAMING: ENABLEMENT (Channel Sales Support) - AMPLIFIED

SPEAK AS A FELLOW SALES PROFESSIONAL (peer-to-peer, NOT vendor-to-buyer):
- "#1 is building long-term relationships through customer satisfaction."
- "Arm your team with assets that close deals."
- "Products that install cleanly, work reliably, generate minimal support calls."
- "One-pagers, spec sheets, competitive differentiators he can copy/paste to clients."

VOCABULARY THAT RESONATES:
- "deal reg", "margin", "demo", "proof of concept", "RFP", "bid"
- "territory", "install base", "upsell", "attach rate", "ASP"
- "one-pager", "spec sheet", "copy/paste to client"

FORBIDDEN (sounds like internal corporate):
- "corporate jargon", "synergize", "paradigm shift", "holistic"

EMOTIONAL CORE: Sales enablement. Arm the channel with assets that close deals and build relationships.
""",
        "system_engineer": """VALUE FRAMING: TECHNICAL (Integration-First) - AMPLIFIED

SPEAK AS A TECHNICAL PEER:
- "Sharp and self-sufficient, does own testing, needs clear API access and configuration guides."
- "Open API, native NDI/SRT, integrates with Q-SYS and Kaltura out of the box."
- "Case studies from integrators who've deployed 60+ units."
- "Highlight partner ecosystem (Q-SYS, Kaltura, Panopto)."

VOCABULARY THAT RESONATES:
- "API", "Q-SYS", "Crestron", "AMX", "Dante", "NDI", "AV-over-IP"
- "signal flow", "as-built", "rack unit", "PoE budget", "VLAN", "multicast"
- "integration flexibility", "peer validation"

FORBIDDEN (sounds like marketing):
- "marketing fluff", "vague claims without specs", "game-changing"

EMOTIONAL CORE: Technical credibility. Specs, integration stories, and peer validation from fellow integrators.
""",
        # ── ATL: Edtech & Live Events (from PDF research) ───────────
        "edtech_manager": """VALUE FRAMING: ADOPTION (Faculty Actually Use It) - AMPLIFIED

SPEAK AS AN EDTECH PEER:
- "Visionary, wants seamless edtech experience."
- "Faculty don't change their workflow — native Panopto and Kaltura integration."
- "Capture happens automatically — adoption isn't an issue when there's nothing to adopt."
- "Works alongside AV Director but focuses on CMS/LMS."

VOCABULARY THAT RESONATES:
- "LMS", "CMS", "Panopto", "Kaltura", "SCORM", "accessibility"
- "faculty adoption", "student engagement", "lecture capture"
- "universal design", "platform integration"

FORBIDDEN (leave pure AV to AV Andy):
- "pure AV jargon", "hardware specs without learning context"

EMOTIONAL CORE: Seamless edtech vision. Faculty resistance disappears when technology is invisible.
""",
        "venue_manager": """VALUE FRAMING: VERSATILITY (One System, Every Event) - AMPLIFIED

SPEAK AS A VENUE OPERATIONS PROFESSIONAL:
- "Orchestra on Monday, corporate keynote on Tuesday — same Pearl, different layout."
- "Oslo Opera runs 300+ shows/year on Pearl."
- "Budget constraints, equipment limitations, client retention — you juggle all three."
- "Staff can operate without extensive training."

VOCABULARY THAT RESONATES:
- "green room", "load-in", "strike", "house system", "venue tech"
- "client specs", "AV rider", "house camera", "IMAG", "program feed"
- "multi-camera", "webcast"

FORBIDDEN (sounds like enterprise software):
- "enterprise software language", "cloud-first", "synergize"

EMOTIONAL CORE: Venue versatility. One reliable system for every event type, operable by any staff.
""",
        "production_director": """VALUE FRAMING: SCALE (Manage 100 Units Like 1) - AMPLIFIED

SPEAK AS AN ENTERPRISE PRODUCTION EXECUTIVE:
- "Values reliability, low-risk solutions that ensure uptime."
- "Management at Scale: Inventory, uptime, lifecycle, reliability."
- "Freeman trusts Pearl for the world's largest events."
- "MSAVi runs Disney events — 'Haven't failed us once.'"

VOCABULARY THAT RESONATES:
- "fleet management", "inventory", "lifecycle", "uptime SLA"
- "redundancy", "failover", "standardization", "deployment template"
- "enterprise support", "spare pool", "RMA"

FORBIDDEN (sounds small-scale):
- "affordable", "compact", "portable", "small-scale"

EMOTIONAL CORE: Enterprise scale confidence. Fleet management, reliability SLAs, and zero tolerance for downtime.
""",
    }
    return value_angles.get(audience, value_angles["av_director"])


def get_persona_extraction_focus(audience: str, audience_info: dict) -> str:
    """Get persona-specific extraction instructions for 8 BDR Playbook personas."""
    extractions = {
        # ── ATL: Decision Makers ──────────────────────────────────
        "av_director": """FOCUS FOR AV DIRECTOR:
- What FLEET MANAGEMENT or STANDARDIZATION was discussed?
- What UPTIME and RELIABILITY across multiple rooms/venues?
- How does this REDUCE TRUCK ROLLS and vendor dependency?
- What VENDOR CONSOLIDATION or simplified support?""",
        "ld_director": """FOCUS FOR L&D DIRECTOR:
- What KNOWLEDGE CAPTURE or TRAINING SCALABILITY was discussed?
- What LMS INTEGRATION or content library capabilities?
- How does this help COMPLIANCE DOCUMENTATION (OSHA, accreditation)?
- What measurable LEARNING OUTCOMES or training ROI?""",
        "sim_center_director": """FOCUS FOR SIMULATION CENTER DIRECTOR:
- What MULTI-ANGLE RECORDING or DEBRIEF quality improvements?
- What HIPAA COMPLIANCE or data security for patient recordings?
- How does this integrate with SIMCAPTURE or CAE systems?
- What LOCAL RECORDING capabilities (no cloud dependency)?""",
        "court_admin": """FOCUS FOR COURT ADMINISTRATOR:
- What RECORD INTEGRITY or CHAIN OF CUSTODY features?
- What UNATTENDED RECORDING reliability for proceedings?
- How does this address COURT REPORTER SHORTAGE?
- What PUBLIC ACCESS STREAMING compliance?""",
        "corp_comms": """FOCUS FOR CORPORATE COMMUNICATIONS DIRECTOR:
- What BROADCAST QUALITY from any room?
- How does this prevent PRODUCTION FAILURES in town halls?
- What MULTI-PLATFORM DISTRIBUTION (Teams + YouTube + intranet)?
- What EXECUTIVE PRESENCE and brand consistency?""",
        "ehs_manager": """FOCUS FOR EHS MANAGER:
- What OSHA COMPLIANCE documentation capabilities?
- What SAFETY TRAINING CAPTURE for SOPs and procedures?
- How does this capture TRIBAL KNOWLEDGE from retiring workers?
- What AUDIT READINESS for safety procedures?""",
        "law_firm_it": """FOCUS FOR LAW FIRM IT DIRECTOR:
- What ON-PREMISES RECORDING (no cloud risk)?
- What DEPOSITION QUALITY and reliability?
- How does this address E-DISCOVERY and privilege concerns?
- What PARTNER SATISFACTION through zero-complaint AV?""",
        # ── BTL: Operators ────────────────────────────────────────
        "technical_director": """FOCUS FOR TECHNICAL DIRECTOR / AV OPERATOR:
- What EASE OF USE or ONE-BUTTON operation?
- What RELIABILITY UNDER PRESSURE during live events?
- How does this simplify QUICK SETUP and teardown?
- What REAL-TIME MONITORING and confidence monitoring?""",
        # ── CHANNEL: Sales Intermediaries ────────────────────────────
        "dealer_dave": """FOCUS FOR CHANNEL ACCOUNT MANAGER (Dealer/Reseller):
- What DEAL SUPPORT or DEMO ASSETS were discussed?
- What COMPETITIVE DIFFERENTIATORS vs other vendors?
- What MARGIN or VENDOR RELIABILITY benefits?
- What INSTALL SIMPLICITY minimizes post-sale support calls?""",
        "system_engineer": """FOCUS FOR AV SYSTEMS DESIGNER (Integrator Technical):
- What API QUALITY or INTEGRATION SPECS were discussed?
- What PARTNER ECOSYSTEM compatibility (Q-SYS, Crestron, Kaltura)?
- What INSTALLATION SIMPLICITY or deployment guides?
- What PEER VALIDATION from other integrators?""",
        # ── ATL: Edtech & Live Events ────────────────────────────────
        "edtech_manager": """FOCUS FOR EDUCATIONAL TECHNOLOGY MANAGER:
- What LMS/CMS INTEGRATION (Panopto, Kaltura, Brightcove) was discussed?
- What FACULTY ADOPTION improvements or barriers addressed?
- What STUDENT ACCESSIBILITY or platform compatibility?
- How does this create a SEAMLESS EDTECH EXPERIENCE?""",
        "venue_manager": """FOCUS FOR VENUE AV MANAGER:
- What MULTI-EVENT FLEXIBILITY across different event types?
- What CLIENT SATISFACTION or venue reputation benefits?
- How does this work with LIMITED STAFF and minimal training?
- What EQUIPMENT RELIABILITY for back-to-back events?""",
        "production_director": """FOCUS FOR DIRECTOR OF EVENT TECHNOLOGY:
- What FLEET MANAGEMENT AT SCALE (50-500+ units)?
- What RELIABILITY/UPTIME SLA and redundancy features?
- What STANDARDIZATION across multiple venues?
- What ENTERPRISE SUPPORT or lifecycle management?""",
    }
    return extractions.get(audience, extractions["av_director"])


def get_persona_generation_context(audience: str, persona: dict) -> str:
    """
    Build persona-specific context for image generation.

    CRITICAL: Only provides high-level GUIDANCE, not literal content.
    - Value angle (COI/ROI/EASE) tells HOW to frame
    - Visual style tells WHAT to design
    - Forbidden phrases are guardrails only
    - NO vocabulary or cares_about - these caused literal rendering

    The EXTRACTION phase already outputs persona-appropriate content.
    This method just guides the VISUAL treatment.
    """
    title = persona.get("title", audience)
    voice_tone = persona.get("voice_tone", "")
    forbidden = persona.get("forbidden_phrases", [])
    default_style = persona.get("default_visual_style", "polished")

    # Persona-specific generation context (8 BDR Playbook personas)
    persona_contexts = {
        # ── ATL: Decision Makers ──────────────────────────────────
        "av_director": f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: COI - fleet standardization, fewer truck rolls, managed from anywhere
VISUAL STYLE: {default_style} (fleet dashboard, multi-room management aesthetic)
DESIGN: Before/after fleet comparison, reference stories (NC State 300+), campus map
AVOID WORDS: {", ".join(forbidden[:5])}""",
        "ld_director": f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: ROI - knowledge capture, training scalability, compliance documentation
VISUAL STYLE: {default_style} (learning platform aesthetic, content library view)
DESIGN: Training workflow, knowledge capture funnel, LMS integration diagram
AVOID WORDS: {", ".join(forbidden[:5])}""",
        "sim_center_director": f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: COI - every sim without recording is a missed learning opportunity
VISUAL STYLE: {default_style} (clinical simulation, multi-angle debrief view)
DESIGN: Multi-camera sim layout, debrief comparison, HIPAA compliance badge
AVOID WORDS: {", ".join(forbidden[:5])}""",
        "court_admin": f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: COI - legal risk from failed recordings, chain of custody
VISUAL STYLE: {default_style} (judicial gravity, clean institutional aesthetic)
DESIGN: Courtroom recording layout, chain of custody flow, public access streaming
AVOID WORDS: {", ".join(forbidden[:5])}""",
        "corp_comms": f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: ROI - broadcast quality from any room, zero production failures
VISUAL STYLE: {default_style} (broadcast studio aesthetic, executive communications)
DESIGN: Town hall setup, multi-platform distribution, before/after quality comparison
AVOID WORDS: {", ".join(forbidden[:5])}""",
        "ehs_manager": f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: COI - OSHA compliance risk, knowledge loss from retiring workers
VISUAL STYLE: {default_style} (safety-first, industrial, compliance documentation)
DESIGN: Training capture workflow, OSHA compliance checklist, audit trail view
AVOID WORDS: {", ".join(forbidden[:5])}""",
        "law_firm_it": f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: COI - data security risk, partner frustration from failed depositions
VISUAL STYLE: {default_style} (secure, on-premises, professional law firm aesthetic)
DESIGN: Network security diagram, deposition setup, data sovereignty flow
AVOID WORDS: {", ".join(forbidden[:5])}""",
        # ── BTL: Operators ────────────────────────────────────────
        "technical_director": f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: EASE - one-button operation, reliability under pressure
VISUAL STYLE: {default_style} (operator's view, control room aesthetic, multiview)
DESIGN: Show flow layout, one-touch control panel, confidence monitoring view
AVOID WORDS: {", ".join(forbidden[:5])}""",
        # ── CHANNEL: Sales Intermediaries ────────────────────────────
        "dealer_dave": f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: ENABLEMENT - deal support assets, competitive differentiators, channel enablement
VISUAL STYLE: {default_style} (sales battlecard aesthetic, clean product comparison)
DESIGN: Competitive comparison table, product one-pager, deal support assets
AVOID WORDS: {", ".join(forbidden[:5])}""",
        "system_engineer": f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: TECHNICAL - API quality, integration specs, partner ecosystem
VISUAL STYLE: {default_style} (technical diagram, signal flow, rack layout)
DESIGN: Integration architecture, signal flow diagram, partner ecosystem map
AVOID WORDS: {", ".join(forbidden[:5])}""",
        # ── ATL: Edtech & Live Events ────────────────────────────────
        "edtech_manager": f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: ADOPTION - faculty use it because it works with their LMS, invisible technology
VISUAL STYLE: {default_style} (edtech platform aesthetic, LMS integration view)
DESIGN: LMS integration flow, faculty adoption journey, platform compatibility grid
AVOID WORDS: {", ".join(forbidden[:5])}""",
        "venue_manager": f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: VERSATILITY - one system for every event type, multi-use flexibility
VISUAL STYLE: {default_style} (venue operations aesthetic, event type grid)
DESIGN: Multi-event layout comparison, venue tech setup, client satisfaction flow
AVOID WORDS: {", ".join(forbidden[:5])}""",
        "production_director": f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: SCALE - fleet management, 100 units managed as one, enterprise reliability
VISUAL STYLE: {default_style} (fleet dashboard, enterprise management aesthetic)
DESIGN: Fleet management dashboard, uptime metrics, multi-venue deployment map
AVOID WORDS: {", ".join(forbidden[:5])}""",
    }

    return persona_contexts.get(
        audience,
        f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: Show clear business value
VISUAL STYLE: {default_style}
DESIGN: Professional and polished""",
    )


def get_visual_style_instructions(visual_style: str) -> str:
    """Get visual style instructions based on style preference."""
    styles = {
        "clean": """VISUAL STYLE: CLEAN
- Simple flat icons and shapes
- Minimal decoration, maximum clarity
- Bold typography, lots of whitespace
- No gradients or shadows
- Think: Apple keynote slides""",
        "polished": """VISUAL STYLE: POLISHED PROFESSIONAL
- Refined, corporate-quality graphics
- Subtle gradients and modern touches
- Professional iconography
- Balanced composition with visual hierarchy
- Think: McKinsey or BCG presentation""",
        "photo_realistic": """VISUAL STYLE: PHOTO-REALISTIC
- Include realistic imagery and photos
- High-quality stock photo aesthetic
- Blend photos with text overlays
- Modern editorial feel
- Think: LinkedIn featured image or magazine layout""",
        "minimalist": """VISUAL STYLE: MINIMALIST
- Extreme simplicity, sparse elements
- Maximum whitespace
- Only essential text and icons
- Single accent color usage
- Think: Japanese design or Dieter Rams""",
        # NEW STYLES FOR PERSONA RESONANCE
        "isometric": """VISUAL STYLE: ISOMETRIC 3D
- Clean 3D isometric icons and illustrations
- Soft shadows, subtle depth
- Modern SaaS aesthetic (Stripe, Linear, Notion)
- Precise geometric shapes
- Light, airy backgrounds with floating elements
- Think: Stripe's marketing illustrations""",
        "sketch": """VISUAL STYLE: HAND-DRAWN SKETCH
- Whiteboard/napkin sketch aesthetic
- Imperfect, hand-drawn lines
- Marker or pencil texture
- Casual, approachable feel
- Doodle-style icons
- Think: Quick sketch explaining an idea to a coworker""",
        "data_viz": """VISUAL STYLE: DATA VISUALIZATION
- Charts, graphs, and numbers prominent
- McKinsey/BCG consulting deck aesthetic
- Clean data tables and metrics
- Waterfall charts, bar graphs, trend lines
- Numbers are heroes, not supporting cast
- Think: Board presentation with hard data""",
        "bold": """VISUAL STYLE: BOLD GEOMETRIC
- Bauhaus-inspired strong shapes
- High contrast, vibrant colors
- Geometric patterns and forms
- Memorable, stand-out aesthetic
- Think: Pitch deck slide that demands attention""",
    }
    return styles.get(visual_style, styles["polished"])


def get_artist_style_instructions(artist_style: str | None) -> str:
    """Get artist style instructions for fun variations."""
    if not artist_style:
        return ""

    artists = {
        "salvador_dali": """ARTIST STYLE: SALVADOR DALI
- Surrealist elements and dreamlike quality
- Melting or distorted shapes (but keep text readable!)
- Unexpected juxtapositions
- Rich, warm colors with dramatic lighting
- Imaginative, thought-provoking visuals
- Think: The Persistence of Memory meets corporate presentation""",
        "monet": """ARTIST STYLE: CLAUDE MONET
- Impressionist brushstroke texture
- Soft, diffused lighting
- Pastel and natural color palette
- Dreamy, atmospheric quality
- Nature-inspired elements (water lilies, gardens)
- Think: Water Lilies meets executive summary""",
        "diego_rivera": """ARTIST STYLE: DIEGO RIVERA
- Bold muralist style
- Strong, blocky shapes and forms
- Workers and industry themes
- Rich earth tones and vibrant accents
- Social realism aesthetic
- Think: Detroit Industry Murals meets tech infographic""",
        "warhol": """ARTIST STYLE: ANDY WARHOL
- Pop art boldness
- High contrast, vibrant colors
- Repetition and pattern elements
- Commercial art aesthetic
- Bold outlines and flat colors
- Think: Campbell's Soup meets business presentation""",
        "van_gogh": """ARTIST STYLE: VAN GOGH
- Expressive brushstroke texture
- Swirling, dynamic movement
- Bold, emotional color choices
- Starry Night energy
- Intense yellows, blues, and greens
- Think: Starry Night meets executive dashboard""",
        "picasso": """ARTIST STYLE: PICASSO (CUBIST)
- Geometric, fragmented forms
- Multiple perspectives simultaneously
- Bold, angular shapes
- Strong black outlines
- Analytical cubism meets business graphics
- Think: Three Musicians meets corporate storyboard""",
        # NEW ARTIST STYLE
        "giger": """ARTIST STYLE: H.R. GIGER (BIOMECHANICAL)
- Dark, intricate biomechanical aesthetic
- Organic forms merged with mechanical elements
- Alien/xenomorph design language
- Textured, layered surfaces
- Haunting, otherworldly atmosphere
- Bold choice for disruption/transformation messaging
- Think: Alien movie meets tech transformation story""",
    }
    return artists.get(artist_style, "")


def get_format_layout_instructions(output_format: str) -> str:
    """Get layout instructions based on output format."""
    if output_format == "storyboard":
        return """LAYOUT (VERTICAL STORYBOARD):
- PORTRAIT orientation - tall, scrollable format
- Visual flow from TOP TO BOTTOM (vertical reading)
- Multiple sections stacked vertically
- Each section tells part of the story
- Good for detailed explanations and step-by-step narratives
- Think: LinkedIn article header or presentation slide deck feel"""
    else:  # infographic (default)
        return """LAYOUT (HORIZONTAL INFOGRAPHIC):
- LANDSCAPE orientation - wide, single-view format
- Visual flow from LEFT TO RIGHT (horizontal reading)
- Clean, scannable, executive-friendly
- Key points visible at a glance
- Good for quick value communication
- Think: LinkedIn post image or email header"""


def get_format_output_instructions(output_format: str) -> str:
    """Get output specifications based on format."""
    if output_format == "storyboard":
        return """OUTPUT:
- Single image, PORTRAIT 9:16 aspect ratio (vertical)
- 1080x1920 resolution (mobile/story format)
- PNG format"""
    else:  # infographic (default)
        return """OUTPUT:
- Single image, LANDSCAPE 16:9 aspect ratio (widescreen horizontal)
- 1920x1080 resolution (HD widescreen)
- PNG format"""


def get_vertical_generation_context(vertical: str | None) -> str:
    """
    Get vertical-specific context for storyboard generation.

    Injects vertical pain points, reference stories, and recommended products
    into the generation prompt so the storyboard is contextually relevant.

    Args:
        vertical: Vertical identifier (e.g., "higher_ed", "live_events")

    Returns:
        Prompt fragment with vertical context, or empty string if no vertical.
    """
    if not vertical:
        return ""

    from src.tools.storyboard.epiphan_presets import EPIPHAN_VERTICALS, get_reference_stories

    vert_data = EPIPHAN_VERTICALS.get(vertical)
    if not vert_data:
        return ""

    sections = [f"\nVERTICAL CONTEXT: {vert_data['name']}"]

    # Pain points specific to this vertical
    pain_points = vert_data.get("pain_points", [])
    if pain_points:
        sections.append(f"INDUSTRY PAIN POINTS: {'; '.join(pain_points[:3])}")

    # Reference stories filtered by vertical
    stories = get_reference_stories(vertical)
    if stories:
        story_lines = []
        for s in stories[:3]:
            quote = s.get("quote", "")
            story_lines.append(f"- {s['customer']}: {s['metric']} — \"{quote}\"")
        sections.append("PROOF POINTS:\n" + "\n".join(story_lines))

    # Use cases
    use_cases = vert_data.get("use_cases", [])
    if use_cases:
        sections.append(f"USE CASES: {', '.join(use_cases)}")

    # Recommended products (names only, no pricing per user request)
    from src.tools.storyboard.epiphan_presets import EPIPHAN_PRODUCTS

    rec_products = vert_data.get("recommended_products", [])
    if rec_products:
        product_names = [
            EPIPHAN_PRODUCTS[pid]["name"]
            for pid in rec_products
            if pid in EPIPHAN_PRODUCTS
        ]
        sections.append(f"RECOMMENDED PRODUCTS: {', '.join(product_names)}")

    return "\n".join(sections)

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

CHALLENGER REFRAME: Most AV directors think they can't afford lecture capture in
every room because traditional setups cost $5,700-$8,500/room. But EC20 at $1,899
records direct to your CMS/LMS with one Ethernet cable — no encoder, no electrician,
no audio interface. Those 160 rooms that were "out of reach"? Now capturable.

SPEAK TO THE AV DIRECTOR'S FLEET BURDEN:
- Every room with different AV is a support ticket and a frustrated user.
- Standardize once. Manage from anywhere. Forget about it.
- NC State runs 300+ Pearls with one AV team.
- "Stop babysitting AV. Start managing it."
- EC20 at $1,899 vs traditional $5,700-$8,500/room — save up to $6,600/room.
- Dante audio on the same Ethernet cable — no separate audio runs.
- Direct CMS/LMS publish — no middleware, no encoder, brand agnostic.
- Pearl bundles: complete HyFlex room (Nano + EC20) under $3,500.

VOCABULARY THAT RESONATES:
- "fleet management", "standardize", "rack-mount", "signal chain"
- "commissioning", "as-built", "NDI", "SRT", "PoE", "Dante"
- "zero headaches", "one team, hundreds of rooms"
- "rooms out of reach", "direct to CMS/LMS", "one cable"

FORBIDDEN (sounds like marketing):
- "digital transformation", "synergize", "paradigm shift", "holistic"

EMOTIONAL CORE: Professional pride. Managing hundreds of rooms without losing sleep.
The EC20 cost story changes the budget conversation from "which rooms can we afford"
to "why aren't ALL rooms captured."
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
        "av_integrator": """VALUE FRAMING: PARTNERSHIP (Margin + Install Efficiency) - AMPLIFIED

CHALLENGER REFRAME: Most integrators think their biggest cost is hardware.
But what we hear from firms managing 50+ client sites is the real cost is
truck rolls and support calls for gear that doesn't self-manage.
At $150/truck roll × 3 calls/site/month × 50 sites = $270K/year in margin erosion.

SPEAK AS A FELLOW AV PROFESSIONAL (peer-to-peer):
- "Your field techs install Pearl in 20 minutes. Try that with the other guys."
- "Fleet management across 50 client sites from one Epiphan Edge dashboard."
- "Open API means your Crestron/Q-SYS programmer isn't fighting the hardware."
- "Zero post-install support calls. Your margin stays on the project, not the service desk."

VOCABULARY THAT RESONATES:
- "rack-mount", "install base", "field tech", "commissioning"
- "Crestron", "Q-SYS", "AMX", "Dante", "NDI", "AV-over-IP"
- "deal registration", "margin", "RFP", "spec sheet"
- "fleet management", "Epiphan Edge", "remote monitoring"
- "truck roll", "as-built", "PoE budget"

FORBIDDEN (sounds like vendor marketing):
- "game-changing", "revolutionary", "paradigm shift", "disruptive"

EMOTIONAL CORE: Business partnership. Products that make integrators look good,
keep margins healthy, and generate zero callbacks. Your field techs are the ones
getting the 7 AM call when an encoder crashes — Epiphan means that call never comes.
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
        "av_integrator": """FOCUS FOR AV INTEGRATOR (Solutions Architect):
- What INSTALL COMPLEXITY or COMMISSIONING TIME was discussed?
- What FLEET MANAGEMENT across multiple client sites?
- What CONTROL SYSTEM INTEGRATION (Crestron, Q-SYS, AMX)?
- What MARGIN IMPACT — support calls, truck rolls, warranty returns?
- What FRANKENSTACK — mismatched vendor gear across client sites?
- What RFP REQUIREMENTS or spec compliance needs?""",
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
        "av_integrator": f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: PARTNERSHIP - margin protection, install efficiency, fleet management, zero truck rolls
VISUAL STYLE: {default_style} (before/after: frankenstack vs clean Epiphan deployment)
DESIGN: Multi-site fleet dashboard, install comparison (20-min Pearl vs hours for competitor),
truck roll cost calculator, Epiphan Edge management view across client sites
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
        "blueprint": """VISUAL STYLE: BLUEPRINT / TECHNICAL DRAWING
- Dark navy background (#1a2744) with white or light green line drawings
- Architectural drawing aesthetic — clean lines, precise geometry
- Signal flow diagrams, rack elevations, cable routing paths
- Technical callouts with dotted leader lines and measurements
- Subtle grid overlay for engineering precision
- Equipment labels in clean sans-serif, wire-frame style icons
- Think: AV system design drawing, control room layout blueprint
- Perfect for integrators, system engineers, and technical directors""",
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
        # MX/LATAM ARTIST STYLES
        "frida_kahlo": """ARTIST STYLE: FRIDA KAHLO
- Vibrant, saturated colors — deep reds, warm yellows, lush greens
- Folk art elements merged with surrealist symbolism
- Floral crowns, botanical elements, Mexican textile patterns
- Intimate, personal, emotionally direct
- Bold composition with cultural identity at center
- Rich textures and decorative borders
- Warm earth tones grounded with vivid accents
- Think: The Two Fridas meets professional infographic""",
        "siqueiros": """ARTIST STYLE: DAVID ALFARO SIQUEIROS
- Dynamic, angular muralist style with dramatic perspective
- Industrial and technological themes — machines, progress, labor
- Strong diagonal composition with foreshortening
- Bold, almost aggressive colors — deep blues, fiery oranges, steel grays
- Sculptural volume and movement (unlike Rivera's flat mural blocks)
- Forward-looking energy channeled into visuals of transformation
- Dramatic lighting with deep shadows
- Think: March of Humanity meets technology transformation story""",
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

    from src.tools.storyboard.epiphan_presets import (
        EPIPHAN_VERTICALS,
        get_reference_stories,
    )

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
            story_lines.append(f'- {s["customer"]}: {s["metric"]} — "{quote}"')
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


# ── JTBD (Jobs To Be Done) Framework ────────────────────────────────────────


def get_persona_job_statement(audience: str) -> str:
    """
    Core JTBD job statement for each persona.

    Format: When [circumstance], I want to [job], so I can [outcome].
    Solution-agnostic — no product names, technologies, or methods.
    """
    jobs = {
        # ── ATL: Decision Makers ──────────────────────────────────
        "av_director": (
            "When managing AV across dozens of rooms with different equipment, "
            "I want to standardize on reliable hardware I can manage remotely, "
            "so I can stop babysitting AV and start managing it."
        ),
        "ld_director": (
            "When institutional knowledge walks out the door with retiring experts, "
            "I want to capture and distribute training content at scale, "
            "so I can prove training ROI and maintain compliance."
        ),
        "sim_center_director": (
            "When running high-fidelity simulations, "
            "I want multi-angle synchronized recording that stays on our network, "
            "so I can deliver better debriefs without HIPAA risk."
        ),
        "court_admin": (
            "When proceedings must be recorded without exception, "
            "I want tamper-proof recording that works unattended, "
            "so I can maintain the integrity of the judicial record."
        ),
        "corp_comms": (
            "When leadership goes on camera for town halls and all-hands, "
            "I want broadcast-quality production from any room without a production crew, "
            "so I can protect the brand every time the CEO speaks."
        ),
        "ehs_manager": (
            "When safety procedures must be documented and auditable, "
            "I want to capture every training session and process demonstration, "
            "so I can prove compliance and preserve tribal knowledge before it retires."
        ),
        "law_firm_it": (
            "When depositions and client meetings must be recorded securely, "
            "I want on-premises recording that partners never have to think about, "
            "so I can eliminate AV complaints and protect privileged data."
        ),
        # ── ATL: Higher Ed Executive ──────────────────────────────
        "provost": (
            "When enrollment depends on student experience quality, "
            "I want consistent lecture delivery across all modalities, "
            "so I can compete for students and satisfy accreditation."
        ),
        "university_president": (
            "When campus technology defines institutional reputation, "
            "I want scalable infrastructure that demonstrates innovation, "
            "so I can attract enrollment and position the university competitively."
        ),
        "university_finance": (
            "When AV budgets compete with every other campus priority, "
            "I want predictable total cost of ownership across all rooms, "
            "so I can justify the investment with measurable ROI."
        ),
        # ── ATL: Edtech & Live Events ─────────────────────────────
        "edtech_manager": (
            "When faculty resistance is the biggest barrier to edtech adoption, "
            "I want technology that integrates invisibly with the LMS, "
            "so I can achieve adoption without changing faculty workflow."
        ),
        "venue_manager": (
            "When every event has different requirements and limited staff, "
            "I want one system that handles any event type with minimal training, "
            "so I can deliver consistent client satisfaction regardless of the show."
        ),
        "production_director": (
            "When managing AV fleets across multiple venues and events, "
            "I want standardized equipment with centralized monitoring, "
            "so I can guarantee uptime at enterprise scale."
        ),
        # ── BTL: Operators ────────────────────────────────────────
        "technical_director": (
            "When the show is live and there's no second take, "
            "I want gear that works under pressure with one-button simplicity, "
            "so I can deliver clean shows without worrying about crashes."
        ),
        # ── CHANNEL: Sales Intermediaries ─────────────────────────
        "dealer_dave": (
            "When my customers need AV solutions and I need to close deals, "
            "I want vendor-provided sales assets and competitive proof points, "
            "so I can win the deal and build a long-term customer relationship."
        ),
        "system_engineer": (
            "When designing AV systems for client projects, "
            "I want products with clean APIs and documented integration paths, "
            "so I can spec with confidence and avoid post-install headaches."
        ),
        "av_integrator": (
            "When specifying AV for client projects across verticals, "
            "I want products that install clean, manage remotely, and generate zero support calls, "
            "so I can protect my margin and my reputation."
        ),
    }
    return jobs.get(audience, jobs["av_director"])


def get_jtbd_extraction_instructions(audience: str) -> str:
    """
    JTBD-specific extraction instructions to add to any content prompt.

    Extracts Forces of Progress (push/pull/anxiety/habit),
    the frankenstack (current hired solutions + workarounds),
    and maps content to the persona's core job.
    """
    job_statement = get_persona_job_statement(audience)
    return f"""JOBS TO BE DONE ANALYSIS:
The target persona's core job: "{job_statement}"

Map the content to this job. Extract:
- JOB ALIGNMENT: How does this content relate to the persona's core job?
- FORCES OF PROGRESS:
  * PUSH: What current pain is driving them to change? What's broken today?
  * PULL: What new capability or outcome is attracting them?
  * ANXIETY: What fears about switching? Risk, timeline, IT burden?
  * HABIT: What's comfortable about the current state? "We've always done X"
- FRANKENSTACK: Describe their current messy setup — mismatched vendors,
  laptop-on-a-cart solutions, manual workarounds, multiple platforms.
  This becomes the "before" in the storyboard.
- HIRING/FIRING: What solution are they currently "hiring" for this job?
  Why might they "fire" it? What workarounds reveal unmet needs?
"""


# ── Challenger Sale Framework ────────────────────────────────────────────────


def get_challenger_choreography(audience: str) -> str:
    """
    Challenger 6-step teaching narrative for storyboard generation.

    The storyboard should tell a TEACHING STORY, not list features.
    Each panel maps to a Challenger step.
    """
    return f"""STORYBOARD NARRATIVE — CHALLENGER TEACHING STORY:

PANEL 1 — THE WARMER (show you understand their world):
Visual: Their current reality — the frankenstack of mismatched gear,
the frustration, the complexity. Make it feel REAL, not abstract.
Text: Acknowledge their situation without selling.

PANEL 2 — THE REFRAME (the insight they don't know):
Visual: Data point or comparison that challenges their assumption.
Text: "Most {audience}s believe [assumption]. But [evidence] shows [surprise]."
This is the most important panel — it's WHY they should care.

PANEL 3 — RATIONAL DROWNING (stack the evidence):
Visual: Numbers, metrics, cost comparison. Make the problem UNDENIABLE.
Text: Quantified impact — hours lost, dollars wasted, incidents per year.
Include bundle pricing where relevant (EC20 at $1,899 vs $7-8K Sony/Panasonic).

PANEL 4 — EMOTIONAL IMPACT (make it personal):
Visual: The personal consequence — their team getting the call at 8 PM,
the failed recording during the board meeting, the judge's frustration.
Text: Connect to THEIR career, THEIR stress, THEIR reputation.

PANEL 5 — THE NEW WAY (the approach, not the product yet):
Visual: Clean architecture diagram — hardware-based, appliance model,
fleet-managed, no software layer. Contrast with the frankenstack.
Text: "What leading [peers] are doing is [approach]..."

PANEL 6 — YOUR SOLUTION (NOW introduce Epiphan):
Visual: Epiphan product in context — rack-mounted, in the room, on the
Epiphan Edge dashboard. Show it solving the exact problem from Panel 1.
Text: Product name + one-line capability + validated CTA link.
Include bundle options where the savings story is compelling.
"""


# ── NSTTD (Never Split the Difference) Framework ────────────────────────────


def get_nsttd_email_framework(audience: str) -> str:
    """
    Chris Voss tactical empathy framework for follow-up email drafts.

    Applies: accusation audit, labels, calibrated questions, no-oriented CTA.
    """
    return """EMAIL FRAMEWORK — TACTICAL EMPATHY (NSTTD):

STRUCTURE:
1. ACCUSATION AUDIT (first line): Front-run their likely objection.
   "You're probably thinking [worst thing they'd think about this follow-up]."
   Example: "You're probably thinking this is just another vendor follow-up."

2. LABEL (second line): Name what you heard in the conversation.
   "It seems like [specific pain/concern from the call]..."
   Must reference something SPECIFIC from the call — not generic.

3. REFERENCE SPECIFIC CALL MOMENTS: Quote or paraphrase 1-2 things
   THEY said (roles only, no names). This proves you listened.

4. NO-ORIENTED CTA (closing): Make it safe to say no.
   "Would it be out of the question to..." or "Would it be a terrible
   idea to..." — NOT "Would you like to schedule a call?"

RULES:
- Under 100 words total
- No "I" in the first sentence — lead with THEM
- No features list — reference the JOB they described
- Use calibrated questions (How/What, never Why)
- FM DJ tone: calm, confident, no urgency or desperation

CALIBRATED QUESTIONS FOR NEXT CALL:
Generate 3-5 questions using only "How" or "What" — NEVER "Why":
- "What does success look like for your team?"
- "How does this fit into your broader priorities?"
- "What would need to be true for you to feel confident moving forward?"
- "How do you typically evaluate solutions like this?"

"THAT'S RIGHT" SUMMARY:
Write a summary of their position designed to get them to say "That's right"
(not "You're right" — that's a brush-off). Summarize their pain, their
constraints, and what they're looking for. When they confirm it, you've
earned the right to propose.
"""

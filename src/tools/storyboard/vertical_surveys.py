"""Vertical workflow surveys — Phase 1: Higher Ed, Courts/Legal, Live Events.

Each survey follows the JTBD job-map structure (Define → Locate → Prepare →
Confirm → Execute → Monitor → Modify → Conclude) so answers can be aggregated
into a ``BuyerProfile`` and fed back into the prompt-builder grounding flow.

Source-of-truth for Live Events: ``US_2026_Live_Events_Workflow_Survey.docx``
(48 questions ported verbatim with internal-note tags preserved).

Higher Ed and Courts/Legal surveys are constructed by adapting the same
job-map structure to vertical-specific personas mined from the April-2026
BDR playbook (``Problem Statements Per Persona by Vertical.docx``).

This module is data + thin helpers. The orchestration layer (router + brief
generator) lives elsewhere; this file should never import a network or LLM
client.
"""

from __future__ import annotations

from src.storyboard.schemas import (
    BuyerProfile,
    SurveyQuestion,
    WorkflowSurvey,
)

# =============================================================================
# Live Events / Production — 48 questions ported verbatim from the docx
# =============================================================================

_LIVE_EVENTS_QUESTIONS: list[SurveyQuestion] = [
    # Section 1: About You ────────────────────────────────────────────────────
    SurveyQuestion(
        id="le_q1",
        section="About You",
        text="Which best describes your role in live event production?",
        type="single",
        options=[
            "Owner / Founder",
            "Producer / Executive Producer",
            "Technical Director",
            "Production Manager",
            "Video Engineer",
            "Streaming Engineer / Broadcast Engineer",
            "Audio Engineer / A1",
            "Event Technology Manager (Venue, Hotel, Convention Center)",
            "AV Technician / A2",
            "Solutions Engineer / Systems Integrator",
            "Design Engineer / Design Consultant",
            "AV Reseller / Account Development Manager",
            "Freelancer / Independent Specialist",
            "Marketing / Communications",
            "Other",
        ],
        job_map_step="define",
    ),
    SurveyQuestion(
        id="le_q2",
        section="About You",
        text="What type of organization do you work for?",
        type="single",
        options=[
            "AV / live event production company",
            "Event agency",
            "Venue (hotel, convention center, ballroom, performing arts center)",
            "Corporate / enterprise events team",
            "Government / municipal events team",
            "Higher education / campus events",
            "House of worship",
            "Broadcast / media production company",
            "Sports media / league production",
            "Independent freelancer / specialist",
            "Systems integrator / reseller",
            "Other",
        ],
        job_map_step="define",
    ),
    SurveyQuestion(
        id="le_q3",
        section="About You",
        text="Where are you primarily based?",
        type="single",
        options=[
            "United States",
            "Canada",
            "Mexico / Central America",
            "United Kingdom / Europe",
            "Australia / New Zealand",
            "Latin America (other)",
            "Asia-Pacific",
            "Middle East / Africa",
            "Other",
        ],
        job_map_step="define",
    ),
    SurveyQuestion(
        id="le_q4",
        section="About You",
        text="How many live events does your team produce per year?",
        type="single",
        options=[
            "Fewer than 25",
            "25 to 99",
            "100 to 249",
            "250 to 499",
            "500 or more",
            "Not sure",
        ],
        job_map_step="define",
        internal_intent=(
            "Volume tier — separates boutique shops from venue/national-"
            "integrator scale. Useful for sizing fly-kit fleet recs."
        ),
    ),
    SurveyQuestion(
        id="le_q5",
        section="About You",
        text="What types of live events do you support? Select all that apply.",
        type="multi",
        options=[
            "Corporate meetings / town halls",
            "Conferences / conventions / trade shows",
            "Training and education events",
            "Government and public meetings",
            "Worship services",
            "Live music and performance",
            "Sports (pro, college, high school)",
            "Esports",
            "Product launches",
            "Hybrid events",
            "Webinars and virtual events",
            "Broadcast and media production",
            "Awards / galas",
            "Theater and performing arts",
            "Other",
        ],
        job_map_step="define",
    ),
    # Section 2: Streaming and Recording Workflows ────────────────────────────
    SurveyQuestion(
        id="le_q6",
        section="Streaming and Recording Workflows",
        text="What do you deliver most often for live events?",
        type="single",
        options=[
            "Live stream only",
            "Recording only",
            "Both live stream and recording",
            "It varies by event",
            "We mostly provide production support, not final delivery",
        ],
        job_map_step="execute",
    ),
    SurveyQuestion(
        id="le_q7",
        section="Streaming and Recording Workflows",
        text="When you both stream and record, how do you usually handle it?",
        type="single",
        options=[
            "One system handles streaming and recording",
            "Separate boxes for streaming and recording",
            "Software handles streaming, hardware handles recording",
            "Hardware handles streaming, software handles recording",
            "Cloud platform handles one or both",
            "It varies by event",
            "Not applicable",
        ],
        job_map_step="execute",
        force_signal="habit",
        internal_intent=(
            "Direct read on consolidation appetite. Sets up the all-in-one "
            "narrative for Pearl Nexus and the upcoming hardware refresh."
        ),
    ),
    SurveyQuestion(
        id="le_q8",
        section="Streaming and Recording Workflows",
        text="In your typical event, what is mission-critical?",
        type="single",
        options=[
            "The live stream",
            "The recording",
            "Both equally",
            "It depends on the event",
            "Neither is usually mission-critical",
        ],
        job_map_step="define",
    ),
    SurveyQuestion(
        id="le_q9",
        section="Streaming and Recording Workflows",
        text=(
            "How often do you run a fully redundant signal path "
            "(primary plus backup encoder, dual record, or stream failover)?"
        ),
        type="single",
        options=[
            "Every event",
            "Most events",
            "About half of events",
            "Some events",
            "Rarely",
            "Never — we run single-path",
            "Not sure",
        ],
        job_map_step="prepare",
        force_signal="anxiety",
        internal_intent="Failover maturity — pairs with the failure-mode question.",
    ),
    SurveyQuestion(
        id="le_q10",
        section="Streaming and Recording Workflows",
        text=(
            "When something goes wrong mid-show, what is your most common "
            "point of failure? Select up to two."
        ),
        type="multi",
        limit=2,
        options=[
            "Internet / bandwidth",
            "Encoder hardware",
            "Switcher / production software (vMix, OBS, ATEM)",
            "Audio chain / sync",
            "Camera / source signal",
            "Network / NDI / SRT delivery",
            "Recording media (drive full, file corruption, missed start)",
            "Operator error / config",
            "Client platform or stream key issue",
            "Power",
            "We rarely have failures",
            "Other",
        ],
        job_map_step="monitor",
        force_signal="push",
        internal_intent="Maps to persona pain language — drives Challenger reframes.",
    ),
    # Section 3: Fly Kits / Mobile Production ─────────────────────────────────
    SurveyQuestion(
        id="le_q11",
        section="Fly Kits and Mobile Production",
        text=(
            "Do you build and travel with mobile production kits — "
            "fly packs, road cases, or flyaway rigs?"
        ),
        type="single",
        options=[
            "Yes, multiple standardized kits we deploy continuously",
            "Yes, one or two kits we share across events",
            "We build custom kits per event",
            "We mostly use venue-installed gear",
            "No, we work from a fixed studio or control room",
            "Other",
        ],
        job_map_step="prepare",
    ),
    SurveyQuestion(
        id="le_q12",
        section="Fly Kits and Mobile Production",
        text="How many distinct fly-kit configurations does your team maintain today?",
        type="single",
        options=[
            "1 — single standardized kit",
            "2 to 3 kits, sized to event tier",
            "4 to 6 kits",
            "More than 6",
            "We don't standardize — every kit is one-off",
            "Not applicable",
        ],
        job_map_step="prepare",
    ),
    SurveyQuestion(
        id="le_q13",
        section="Fly Kits and Mobile Production",
        text="What is in your typical fly kit? Select all that apply.",
        type="multi",
        options=[
            "Hardware encoder / streamer / recorder",
            "Hardware video switcher (ATEM, TriCaster, etc.)",
            "Software switcher on a laptop or workstation (vMix, OBS, Wirecast)",
            "PTZ cameras",
            "Cinema or broadcast cameras",
            "Audio mixer / digital console",
            "Wireless mic system",
            "Dante audio network gear",
            "Comms / intercom",
            "NDI converters or NDI bridge",
            "Fiber or SDI distribution",
            "Network switch with PoE",
            "Cellular bonding device",
            "Confidence monitors",
            "Cloud production gateway",
            "Multiviewer",
            "UPS / power conditioning",
            "Other",
        ],
        job_map_step="prepare",
        internal_intent="Signal-chain complexity — feeds 'fewer boxes' narrative.",
    ),
    SurveyQuestion(
        id="le_q14",
        section="Fly Kits and Mobile Production",
        text=(
            "How long does it typically take one technician to set up a fly "
            "kit and be show-ready at a venue?"
        ),
        type="single",
        options=[
            "Under 30 minutes",
            "30 to 60 minutes",
            "1 to 2 hours",
            "2 to 4 hours",
            "More than 4 hours",
            "It varies wildly by event",
        ],
        job_map_step="prepare",
        force_signal="push",
    ),
    SurveyQuestion(
        id="le_q15",
        section="Fly Kits and Mobile Production",
        text=(
            "How often do you re-use the same kit configuration from one "
            "event to the next without reconfiguring?"
        ),
        type="single",
        options=[
            "Always — presets and templates carry over",
            "Often",
            "Sometimes",
            "Rarely — most events need a custom config",
            "Never",
            "Not applicable",
        ],
        job_map_step="prepare",
        force_signal="push",
    ),
    SurveyQuestion(
        id="le_q16",
        section="Fly Kits and Mobile Production",
        text="What is the biggest pain in your fly-kit workflow today? Select up to two.",
        type="multi",
        limit=2,
        options=[
            "Setup time on-site",
            "Re-cabling and rerouting between events",
            "Reconfiguring encoders and stream destinations every time",
            "Audio routing and Dante / network audio config",
            "Network and IP setup at unfamiliar venues",
            "Weight, size, and rack density",
            "Power requirements",
            "Client- or venue-supplied internet reliability",
            "Training the next tech to operate the kit",
            "Gear surviving the road",
            "Cost of maintaining multiple kits",
            "Other",
        ],
        job_map_step="prepare",
        force_signal="push",
    ),
    # Section 4: Audio over IP / NDI / Transport ──────────────────────────────
    SurveyQuestion(
        id="le_q18",
        section="Audio over IP, NDI, and Signal Transport",
        text=(
            "Which video and audio transport protocols are part of your live "
            "event workflows today? Select all that apply."
        ),
        type="multi",
        options=[
            "SDI (3G, 6G, 12G)",
            "HDMI",
            "NDI (full bandwidth NDI 5)",
            "NDI|HX",
            "SRT",
            "RTMP / RTMPS",
            "HLS",
            "WebRTC",
            "ST 2110",
            "Dante audio",
            "AES67 audio",
            "AVB / Milan audio",
            "Analog audio (XLR, line)",
            "Other",
            "Not sure",
        ],
        job_map_step="execute",
        internal_intent="Surfaces Dante adoption directly.",
    ),
    SurveyQuestion(
        id="le_q19",
        section="Audio over IP, NDI, and Signal Transport",
        text="Is Dante audio used anywhere in your typical event setup?",
        type="single",
        options=[
            "Yes — Dante is our standard audio transport",
            "Yes — on most events with a mixed audio team",
            "Sometimes — when the venue or client requires it",
            "Rarely — we use it only on specific shows",
            "No — but we expect to add it in the next 12 to 24 months",
            "No — we have no plans to adopt it",
            "Not sure",
        ],
        job_map_step="execute",
        force_signal="pull",
    ),
    SurveyQuestion(
        id="le_q20",
        section="Audio over IP, NDI, and Signal Transport",
        text=(
            "If your encoder or streamer accepted Dante audio directly "
            "(no separate Dante-to-analog converter), how valuable would "
            "that be?"
        ),
        type="single",
        options=[
            "Extremely valuable — it would change our buying decision",
            "Very valuable",
            "Somewhat valuable",
            "Nice to have",
            "Not valuable — we don't use Dante",
            "Not sure",
        ],
        job_map_step="execute",
        force_signal="pull",
    ),
    SurveyQuestion(
        id="le_q21",
        section="Audio over IP, NDI, and Signal Transport",
        text=(
            "What is the biggest pain you have today routing audio into your "
            "stream and recording chain?"
        ),
        type="open",
        job_map_step="execute",
        force_signal="push",
    ),
    # Section 5: Automation and Control ───────────────────────────────────────
    SurveyQuestion(
        id="le_q23",
        section="Automation and Control",
        text=(
            "Which of these workflow automations are part of your live event "
            "operation today? Select all that apply."
        ),
        type="multi",
        options=[
            "Scheduled stream and record start / stop",
            "Preset recall (encoder, switcher, audio)",
            "Templated event configuration loaded per show",
            "Auto-publish to client or media platform",
            "Auto-upload of recordings after event",
            "Stream destination management via API",
            "Control system integration",
            "Multi-room dashboard / fleet view",
            "Alerting on signal, stream, or recording failure",
            "Automated transcription / captioning",
            "None — we run everything manually",
            "Other",
        ],
        job_map_step="modify",
        force_signal="habit",
    ),
    SurveyQuestion(
        id="le_q24",
        section="Automation and Control",
        text="How many simultaneous events / rooms can one technician realistically run today?",
        type="single",
        options=[
            "1 room",
            "2 rooms",
            "3 to 4 rooms",
            "5 or more rooms",
            "Not applicable",
        ],
        job_map_step="modify",
        internal_intent="Operator leverage benchmark.",
    ),
    SurveyQuestion(
        id="le_q25",
        section="Automation and Control",
        text=(
            "What would it take for one technician to cover an additional room "
            "without adding risk? Select up to two."
        ),
        type="multi",
        limit=2,
        options=[
            "Reliable remote monitoring across rooms",
            "Centralized fleet dashboard",
            "Better presets and templating",
            "Stream and record schedule automation",
            "Alerts when signal or stream drops",
            "Lower-skill operator interface for on-site staff",
            "API or control-system integration with venue automation",
            "Better recording confidence — we trust it without watching",
            "Nothing — the bottleneck is the room, not the gear",
            "Other",
        ],
        job_map_step="modify",
        force_signal="pull",
    ),
    SurveyQuestion(
        id="le_q26",
        section="Automation and Control",
        text="How do you remotely manage encoders or production gear today?",
        type="single",
        options=[
            "Vendor cloud platform",
            "VPN into the venue or production network",
            "Dedicated control system",
            "Custom in-house tooling or API integration",
            "We run on-prem only — no remote management",
            "Other",
        ],
        job_map_step="monitor",
    ),
    # Section 6: Current Tools ────────────────────────────────────────────────
    SurveyQuestion(
        id="le_q27",
        section="Current Tools and Competitive Landscape",
        text="Which encoders or streaming systems do you currently use? Select all that apply.",
        type="multi",
        options=[
            "Epiphan Pearl-2 / Pearl Mini / Pearl Nano / Pearl Nexus",
            "AJA HELO / HELO Plus",
            "Magewell Ultra Encode",
            "Kiloview encoder",
            "Teradek encoder / bonding",
            "LiveU bonding encoder",
            "Roland streaming/switching system",
            "Blackmagic Design system",
            "Matrox Monarch (legacy)",
            "OBS",
            "vMix",
            "Wirecast",
            "TriCaster / NDI Studio",
            "Web conferencing platform",
            "Cloud production platform",
            "Custom-built system",
            "Other",
            "Not sure",
        ],
        job_map_step="execute",
        force_signal="habit",
    ),
    SurveyQuestion(
        id="le_q29",
        section="Current Tools and Competitive Landscape",
        text="How satisfied are you with your current production gear?",
        type="matrix",
        options=[
            "Reliability under load",
            "Setup speed at a new venue",
            "Confidence monitoring",
            "Multi-destination streaming",
            "Recording quality and trust",
            "Remote management",
            "Audio integration (analog plus IP)",
            "Integration with switchers and control systems",
            "Survives the road",
            "Overall value",
        ],
        job_map_step="monitor",
    ),
    SurveyQuestion(
        id="le_q30",
        section="Current Tools and Competitive Landscape",
        text=(
            "What would most likely cause you to replace or add to your "
            "current production gear in the next 12 to 18 months? Select up to three."
        ),
        type="multi",
        limit=3,
        options=[
            "More reliable performance under load",
            "Direct Dante audio input",
            "4K production and recording",
            "HEVC / more efficient codecs",
            "Native NDI plus SRT plus RTMP without extra boxes",
            "Single-box encode plus stream plus record",
            "Better confidence monitoring",
            "Better redundancy and failover",
            "Better remote management",
            "Better fleet management across rooms or venues",
            "Smaller or more portable form factor",
            "Better rack density for fixed installs",
            "Lower total cost of ownership",
            "Current equipment is aging out",
            "Other",
        ],
        job_map_step="modify",
        force_signal="pull",
        internal_intent="Buying-trigger inventory — direct map to roadmap conversations.",
    ),
    # Section 7: Sources, Streams, Delivery ───────────────────────────────────
    SurveyQuestion(
        id="le_q31",
        section="Sources, Streams, and Delivery",
        text="How many video sources do you typically bring into your encoder?",
        type="single",
        options=["1", "2", "3 to 4", "5 to 6", "More than 6", "It varies by event"],
        job_map_step="locate",
    ),
    SurveyQuestion(
        id="le_q32",
        section="Sources, Streams, and Delivery",
        text="How many separate streams or recordings do you typically create from a single event?",
        type="single",
        options=["1", "2", "3 to 4", "5 or more", "It varies by event"],
        job_map_step="execute",
    ),
    SurveyQuestion(
        id="le_q33",
        section="Sources, Streams, and Delivery",
        text="What do you typically record? Select all that apply.",
        type="multi",
        options=[
            "Final program only",
            "Program plus backup recording",
            "Individual camera or source ISO recordings",
            "Program plus ISOs (multitrack)",
            "Slides / content feed",
            "Audio-only backup",
            "Proxy files for review",
            "We do not usually record",
            "Other",
        ],
        job_map_step="execute",
    ),
    SurveyQuestion(
        id="le_q34",
        section="Sources, Streams, and Delivery",
        text="How often do you stream the same event to multiple destinations?",
        type="single",
        options=["Always", "Often", "Sometimes", "Rarely", "Never", "Not applicable"],
        job_map_step="execute",
    ),
    SurveyQuestion(
        id="le_q36",
        section="Sources, Streams, and Delivery",
        text="Which video resolutions are important to your live event workflows today?",
        type="multi",
        options=[
            "720p",
            "1080p",
            "1080p60 / high frame rate",
            "4K",
            "4K with HD outputs and recordings",
            "HDR",
            "Not sure",
        ],
        job_map_step="execute",
    ),
    SurveyQuestion(
        id="le_q37",
        section="Sources, Streams, and Delivery",
        text="Which resolutions do you expect to become more important in the next 12 to 24 months?",
        type="multi",
        options=[
            "720p",
            "1080p",
            "1080p60 / high frame rate",
            "4K",
            "4K with HD outputs and recordings",
            "HDR",
            "Not sure",
        ],
        job_map_step="modify",
        force_signal="pull",
    ),
    SurveyQuestion(
        id="le_q38",
        section="Sources, Streams, and Delivery",
        text="Which recording formats or codecs are important to your workflows?",
        type="multi",
        options=[
            "H.264",
            "HEVC / H.265",
            "ProRes",
            "DNxHD / DNxHR",
            "AV1",
            "MP4",
            "MOV",
            "Other",
        ],
        job_map_step="execute",
    ),
    # Section 8: File Handoff / Delivery ──────────────────────────────────────
    SurveyQuestion(
        id="le_q39",
        section="File Handoff and Delivery",
        text="How quickly do clients expect recorded files after an event?",
        type="single",
        options=[
            "Immediately or during the event",
            "Within a few hours",
            "Same day",
            "Within 24 hours",
            "Within a few days",
            "Within a week",
            "No standard expectation",
            "Not applicable",
        ],
        job_map_step="conclude",
    ),
    SurveyQuestion(
        id="le_q40",
        section="File Handoff and Delivery",
        text="How do you usually deliver recorded files? Select all that apply.",
        type="multi",
        options=[
            "USB drive or physical media",
            "Cloud storage link",
            "Direct upload to client platform",
            "FTP / SFTP",
            "Internal media asset system",
            "Hand off to editor or post-production team",
            "Automatic upload from device after event",
            "We do not usually deliver files",
            "Other",
        ],
        job_map_step="conclude",
    ),
    # Section 9: Industry direction / open ────────────────────────────────────
    SurveyQuestion(
        id="le_q41",
        section="Where the Industry is Heading",
        text=(
            "Which capabilities do you expect to become more important in "
            "live event production over the next 1 to 3 years? Select up to five."
        ),
        type="multi",
        limit=5,
        options=[
            "More reliable streaming over poor networks",
            "Multi-destination streaming",
            "4K production and recording",
            "HEVC and more efficient codecs",
            "Direct Dante audio in encoders and streamers",
            "ST 2110 workflows",
            "Native NDI workflows",
            "SRT and other reliable transport protocols",
            "Remote production",
            "Cloud-based monitoring and control",
            "Multi-room and fleet management",
            "Automated scheduling and templating",
            "API and control-system integration",
            "Faster file delivery",
            "Smaller portable systems",
            "Higher-density rack systems",
            "AI-assisted production tools (camera, audio, captions)",
            "Other",
        ],
        job_map_step="modify",
        force_signal="pull",
        internal_intent="Roadmap intent — sets up the upcoming hardware refresh.",
    ),
    SurveyQuestion(
        id="le_q43",
        section="Where the Industry is Heading",
        text="What is one thing you wish your live event production gear did better today?",
        type="open",
        job_map_step="modify",
        force_signal="push",
    ),
    SurveyQuestion(
        id="le_q44",
        section="Where the Industry is Heading",
        text="Tell us about a recent live event workflow that was harder than it should have been.",
        type="open",
        job_map_step="execute",
        force_signal="push",
    ),
    SurveyQuestion(
        id="le_q45",
        section="Where the Industry is Heading",
        text="What's the next investment your team is most likely to make in production gear?",
        type="open",
        job_map_step="modify",
        force_signal="pull",
    ),
]


# =============================================================================
# Higher Education — adapted from the BDR playbook personas
# =============================================================================

_HIGHER_ED_QUESTIONS: list[SurveyQuestion] = [
    SurveyQuestion(
        id="he_q1",
        section="About You",
        text="Which best describes your role?",
        type="single",
        options=[
            "AV Director / Director of AV Architecture",
            "IT Director / CIO",
            "Educational Technology Manager / Director of Instructional Technology",
            "AV Coordinator / Media Services Technician",
            "Provost / Academic Affairs",
            "Other",
        ],
        job_map_step="define",
    ),
    SurveyQuestion(
        id="he_q2",
        section="About You",
        text="How many lecture-capture-enabled rooms does your campus operate today?",
        type="single",
        options=[
            "Fewer than 25",
            "25 to 99",
            "100 to 199",
            "200 to 499",
            "500 or more",
            "Not sure",
        ],
        job_map_step="define",
    ),
    SurveyQuestion(
        id="he_q3",
        section="About You",
        text="Across how many buildings or campuses?",
        type="single",
        options=["1", "2 to 4", "5 to 9", "10 or more"],
        job_map_step="locate",
    ),
    SurveyQuestion(
        id="he_q4",
        section="About You",
        text="How many AV / instructional-tech FTEs support those rooms?",
        type="single",
        options=["1 to 2", "3 to 5", "6 to 10", "11 to 20", "More than 20"],
        job_map_step="define",
        internal_intent="Sets the room-per-FTE leverage benchmark.",
    ),
    # Locate
    SurveyQuestion(
        id="he_q5",
        section="LMS and Campus Systems",
        text="Which LMS or video platform partners do you use today? Select all that apply.",
        type="multi",
        options=[
            "Panopto",
            "Kaltura",
            "YuJa",
            "Echo360",
            "Canvas",
            "Blackboard",
            "Moodle",
            "Other / homegrown",
            "Not sure",
        ],
        job_map_step="locate",
        internal_intent=(
            "Partner platforms — never frame as broken. Used to confirm we "
            "feed their existing LMS rather than replacing it."
        ),
    ),
    SurveyQuestion(
        id="he_q6",
        section="LMS and Campus Systems",
        text="What percentage of recordings auto-publish into your LMS without manual intervention?",
        type="single",
        options=[
            "95% or higher",
            "80 to 94%",
            "60 to 79%",
            "Below 60%",
            "We don't track this",
        ],
        job_map_step="monitor",
        force_signal="push",
    ),
    SurveyQuestion(
        id="he_q7",
        section="LMS and Campus Systems",
        text="When recordings fail to publish, where in the chain does it usually break?",
        type="single",
        options=[
            "The capture device / encoder",
            "The classroom PC running a software encoder",
            "The network upload",
            "The LMS ingest",
            "It varies",
            "Not sure",
        ],
        job_map_step="monitor",
        force_signal="push",
    ),
    # Prepare
    SurveyQuestion(
        id="he_q8",
        section="Room Setup and Faculty Experience",
        text="How does a faculty member start a recording today?",
        type="single",
        options=[
            "One-button on the wall / lectern",
            "Software UI on the classroom PC",
            "Auto-scheduled — no faculty action",
            "Phone or web app",
            "It varies by room",
            "Other",
        ],
        job_map_step="prepare",
    ),
    SurveyQuestion(
        id="he_q9",
        section="Room Setup and Faculty Experience",
        text="How much training do you currently provide faculty on the capture system?",
        type="single",
        options=[
            "Zero — it must work without training",
            "5 minutes or less",
            "30 minutes per term",
            "An hour or more per term",
            "Faculty don't need to interact with it",
        ],
        job_map_step="prepare",
        force_signal="anxiety",
    ),
    SurveyQuestion(
        id="he_q10",
        section="Room Setup and Faculty Experience",
        text=(
            "What's your accessibility-complaint volume per term related to "
            "missing or failed recordings?"
        ),
        type="single",
        options=[
            "None",
            "1 to 5",
            "6 to 20",
            "More than 20",
            "We don't track this — but it's a concern",
        ],
        job_map_step="monitor",
        force_signal="push",
    ),
    # Execute / monitor
    SurveyQuestion(
        id="he_q11",
        section="Capture Reliability",
        text="What share of your encoders are still software running on a classroom PC?",
        type="single",
        options=[
            "All software / PC-based",
            "Mostly software with some hardware",
            "Mixed",
            "Mostly hardware",
            "All hardware appliances",
            "Not sure",
        ],
        job_map_step="execute",
        force_signal="habit",
        internal_intent="Surfaces the classroom-PC layer — the failure point.",
    ),
    SurveyQuestion(
        id="he_q12",
        section="Capture Reliability",
        text="How often does a recording session fail outright (no file produced)?",
        type="single",
        options=[
            "Less than 1% of sessions",
            "1 to 5%",
            "5 to 15%",
            "More than 15%",
            "We don't measure",
        ],
        job_map_step="monitor",
        force_signal="push",
    ),
    SurveyQuestion(
        id="he_q13",
        section="Capture Reliability",
        text="How does your team currently know a recording failed?",
        type="single",
        options=[
            "Real-time dashboard / alerts",
            "Faculty complaint after the fact",
            "Student complaint after the fact",
            "Spot-checking a sample",
            "We rarely find out",
        ],
        job_map_step="monitor",
        force_signal="push",
    ),
    SurveyQuestion(
        id="he_q14",
        section="Capture Reliability",
        text=(
            "When something breaks, how does support reach the room? "
            "Select all that apply."
        ),
        type="multi",
        options=[
            "Remote management dashboard",
            "VPN / SSH into the room PC",
            "Truck roll — physical visit",
            "Faculty-self-service guide",
            "Help desk ticket",
            "Other",
        ],
        job_map_step="modify",
    ),
    SurveyQuestion(
        id="he_q15",
        section="Network and Compliance",
        text="What network / security requirements must the capture gear meet? Select all that apply.",
        type="multi",
        options=[
            "VLAN segmentation",
            "802.1X authentication",
            "No agent on the classroom PC",
            "Encrypted-in-transit only (no plaintext)",
            "FERPA-compliant storage",
            "Single-sign-on integration",
            "Centralized firmware patching",
            "Not sure",
        ],
        job_map_step="confirm",
        internal_intent="Network security gating — common procurement blocker.",
    ),
    # Modify / Conclude
    SurveyQuestion(
        id="he_q16",
        section="Procurement and Roadmap",
        text="What's your typical procurement cycle for AV gear?",
        type="single",
        options=[
            "<6 months — pilot funds available",
            "6 to 12 months",
            "12 to 18 months — annual budget cycle",
            "18+ months — RFP-driven",
            "Not sure",
        ],
        job_map_step="modify",
    ),
    SurveyQuestion(
        id="he_q17",
        section="Procurement and Roadmap",
        text="What would most drive an investment in new capture infrastructure?",
        type="multi",
        limit=3,
        options=[
            "Reduce staff time on troubleshooting",
            "Eliminate classroom-PC dependency",
            "Add fleet dashboard / centralized monitoring",
            "Better LMS integration reliability",
            "Sim-lab / multi-camera capability",
            "Lower 5-year TCO",
            "Accessibility / compliance pressure",
            "Provost / Academic Affairs mandate",
            "Other",
        ],
        job_map_step="modify",
        force_signal="pull",
    ),
    SurveyQuestion(
        id="he_q18",
        section="Procurement and Roadmap",
        text=(
            "What's the one thing you wish your capture infrastructure did "
            "better today?"
        ),
        type="open",
        job_map_step="modify",
        force_signal="push",
    ),
]


# =============================================================================
# Courts / Legal — adapted from the BDR playbook personas
# =============================================================================

_LEGAL_QUESTIONS: list[SurveyQuestion] = [
    SurveyQuestion(
        id="ct_q1",
        section="About You",
        text="Which best describes your role?",
        type="single",
        options=[
            "Court Administrator / IT Director",
            "Multimedia Services Director / AV Operations Lead",
            "Court Clerk / Records Manager",
            "Legislative IT / Broadcast Operations Director",
            "Other",
        ],
        job_map_step="define",
    ),
    SurveyQuestion(
        id="ct_q2",
        section="About You",
        text="How many courtrooms / hearing rooms / committee rooms do you support?",
        type="single",
        options=["Fewer than 5", "5 to 14", "15 to 49", "50 or more", "Not sure"],
        job_map_step="define",
    ),
    SurveyQuestion(
        id="ct_q3",
        section="About You",
        text="What types of proceedings do you capture? Select all that apply.",
        type="multi",
        options=[
            "Criminal / civil court hearings",
            "Remote / video testimony",
            "Overflow rooms",
            "Legislative floor sessions",
            "Committee hearings",
            "CLE / legal education seminars",
            "Press briefings",
            "Other",
        ],
        job_map_step="define",
    ),
    # Locate / Prepare
    SurveyQuestion(
        id="ct_q4",
        section="The Record",
        text="What is your evidentiary standard for the official record?",
        type="single",
        options=[
            "Continuous capture, no dropped frames",
            "Multi-angle (witness, judge, evidence)",
            "Audio-only is acceptable",
            "Varies by court",
            "Not sure",
        ],
        job_map_step="define",
        internal_intent=(
            "Sets the bar — a 'gap in the record is grounds for appeal' is "
            "the Challenger reframe."
        ),
    ),
    SurveyQuestion(
        id="ct_q5",
        section="The Record",
        text="How often does your current capture solution drop frames or fail mid-proceeding?",
        type="single",
        options=[
            "Never that we know of",
            "Less than 1% of proceedings",
            "1 to 5%",
            "More than 5%",
            "We don't measure",
        ],
        job_map_step="monitor",
        force_signal="push",
    ),
    SurveyQuestion(
        id="ct_q6",
        section="The Record",
        text="When a gap is found in the record, what's the typical remedy?",
        type="single",
        options=[
            "Reschedule the hearing",
            "Reconstruct from notes / transcriptionist",
            "No remedy — appeal risk",
            "Has not happened to us",
            "Other",
        ],
        job_map_step="modify",
        force_signal="anxiety",
    ),
    # Execute
    SurveyQuestion(
        id="ct_q7",
        section="Capture Setup",
        text="How is the capture system in your courtrooms typically run?",
        type="single",
        options=[
            "Software encoder on a courtroom PC",
            "Hardware appliance, dedicated",
            "Video-conferencing platform recording",
            "Combined: hardware + software backup",
            "Not sure",
        ],
        job_map_step="execute",
        force_signal="habit",
    ),
    SurveyQuestion(
        id="ct_q8",
        section="Capture Setup",
        text="How many camera angles do you typically capture per courtroom?",
        type="single",
        options=[
            "1 wide angle only",
            "2 (wide + judge)",
            "3 (wide + judge + witness)",
            "4 or more",
            "Varies",
        ],
        job_map_step="execute",
    ),
    SurveyQuestion(
        id="ct_q9",
        section="Capture Setup",
        text="How is remote testimony brought into the record today?",
        type="single",
        options=[
            "Embedded in the video conferencing platform's recording",
            "Captured into the courtroom AV system",
            "Both, with sync challenges",
            "Not applicable",
            "Other",
        ],
        job_map_step="execute",
        force_signal="push",
    ),
    # Monitor / Modify
    SurveyQuestion(
        id="ct_q10",
        section="Records Management",
        text="How are recordings tied to the docket / case management system?",
        type="single",
        options=[
            "Auto-tagged with timestamps and case number",
            "Manually tagged after proceeding",
            "Files live in a separate folder, no link to docket",
            "Recordings scattered across multiple systems",
            "Not sure",
        ],
        job_map_step="conclude",
        force_signal="push",
    ),
    SurveyQuestion(
        id="ct_q11",
        section="Records Management",
        text="What's your retention requirement for recorded proceedings?",
        type="single",
        options=[
            "Permanent",
            "10+ years",
            "5 to 10 years",
            "Less than 5 years",
            "Varies by case type",
        ],
        job_map_step="conclude",
    ),
    SurveyQuestion(
        id="ct_q12",
        section="Records Management",
        text="Where are recordings stored long-term?",
        type="single",
        options=[
            "On-prem records server",
            "Government cloud (FedRAMP / state-approved)",
            "Commercial cloud",
            "Mixed",
            "Not sure",
        ],
        job_map_step="conclude",
    ),
    # Modify / pull
    SurveyQuestion(
        id="ct_q13",
        section="Streaming and Public Access",
        text="Do you stream proceedings to public access / livestream?",
        type="single",
        options=[
            "Yes — every public proceeding",
            "Yes — on request",
            "Floor sessions only",
            "No",
            "Planning to start within 12 months",
        ],
        job_map_step="execute",
    ),
    SurveyQuestion(
        id="ct_q14",
        section="Streaming and Public Access",
        text="How important is closed captioning / ADA compliance?",
        type="single",
        options=[
            "Mandatory — already implemented",
            "Mandatory — gap we're closing",
            "Important but not yet required",
            "Not currently required",
            "Not sure",
        ],
        job_map_step="confirm",
    ),
    SurveyQuestion(
        id="ct_q15",
        section="Procurement",
        text="What's your typical procurement cycle?",
        type="single",
        options=[
            "Pilot funds available — under 6 months",
            "Annual budget cycle — 6 to 12 months",
            "Formal RFP — 12 to 24 months",
            "18+ months — multi-year capital",
            "Not sure",
        ],
        job_map_step="modify",
    ),
    SurveyQuestion(
        id="ct_q16",
        section="Procurement",
        text="What would most drive an investment in capture infrastructure?",
        type="multi",
        limit=3,
        options=[
            "Reduce appeal risk from gaps in the record",
            "Multi-angle coverage requirement",
            "Remote-testimony evidentiary standards",
            "ADA / captioning compliance",
            "Records-management integration",
            "End-of-life on legacy gear",
            "Transparency / public-access mandate",
            "Other",
        ],
        job_map_step="modify",
        force_signal="pull",
    ),
    SurveyQuestion(
        id="ct_q17",
        section="Procurement",
        text="What's the one thing you wish your capture infrastructure did better today?",
        type="open",
        job_map_step="modify",
        force_signal="push",
    ),
]


# =============================================================================
# Survey registry + helpers
# =============================================================================


_SURVEYS: dict[str, WorkflowSurvey] = {
    "live_events": WorkflowSurvey(
        vertical="live_events",
        title="The State of Live Event Production",
        intro=(
            "Live event teams are running more shows with smaller crews, "
            "tighter timelines, and clients who expect broadcast-quality "
            "streams plus clean recordings every time. We're asking event "
            "pros how they actually build, deploy, and operate their kits "
            "today, where the workflow breaks, and what they need from the "
            "next generation of production gear. Takes about 6–7 minutes."
        ),
        sections=[
            "About You",
            "Streaming and Recording Workflows",
            "Fly Kits and Mobile Production",
            "Audio over IP, NDI, and Signal Transport",
            "Automation and Control",
            "Current Tools and Competitive Landscape",
            "Sources, Streams, and Delivery",
            "File Handoff and Delivery",
            "Where the Industry is Heading",
        ],
        questions=_LIVE_EVENTS_QUESTIONS,
    ),
    "higher_ed": WorkflowSurvey(
        vertical="higher_ed",
        title="Higher Education Capture Workflow Survey",
        intro=(
            "Lecture capture, hybrid classrooms, and accessibility "
            "expectations are scaling faster than AV staffing. We're asking "
            "campus AV, IT, and ed-tech leaders how their capture stack "
            "actually performs today, and what would have to change to "
            "make a real dent in staff time and recording reliability. "
            "Takes about 5 minutes."
        ),
        sections=[
            "About You",
            "LMS and Campus Systems",
            "Room Setup and Faculty Experience",
            "Capture Reliability",
            "Network and Compliance",
            "Procurement and Roadmap",
        ],
        questions=_HIGHER_ED_QUESTIONS,
    ),
    "legal": WorkflowSurvey(
        vertical="legal",
        title="Courts and Legal Workflow Survey",
        intro=(
            "Capturing the complete record of proceedings, supporting "
            "remote testimony, and meeting transparency mandates without "
            "expanding court IT staff is the current reality. We're asking "
            "court administrators, multimedia leads, clerks, and "
            "legislative IT how their capture and records pipeline holds "
            "up under the workload. Takes about 5 minutes."
        ),
        sections=[
            "About You",
            "The Record",
            "Capture Setup",
            "Records Management",
            "Streaming and Public Access",
            "Procurement",
        ],
        questions=_LEGAL_QUESTIONS,
    ),
}


def get_survey(vertical: str) -> WorkflowSurvey | None:
    """Return the survey for ``vertical`` or ``None`` when not registered.

    Phase 1 covers higher_ed, legal, live_events. Other verticals return
    None — caller decides whether to render a "coming in Phase 2" message
    or fall back to the transcript-only flow.
    """
    return _SURVEYS.get(vertical)


def survey_responses_to_prompt_context(profile: BuyerProfile | None) -> str:
    """Format a BuyerProfile as a prompt-injectable signal block.

    Emits a ``SURVEY-DERIVED SIGNALS`` section containing the four Forces
    of Progress in the prospect's voice plus any structured workflow
    signals (room count, current toolset, etc.). Acts as priors when the
    transcript pass is also present, or as standalone context when survey
    is the only intake.

    Returns empty string for ``None`` — graceful degradation.
    """
    if profile is None:
        return ""

    fop = profile.forces_of_progress
    signal_lines: list[str] = []
    for label, value in (
        ("PUSH", fop.push),
        ("PULL", fop.pull),
        ("ANXIETY", fop.anxiety),
        ("HABIT", fop.habit),
    ):
        if value.strip():
            signal_lines.append(f"- {label}: {value.strip()}")

    workflow_lines: list[str] = []
    for k, v in profile.workflow_signals.items():
        workflow_lines.append(f"- {k}: {v}")

    pain_lines = [
        f"- {anchor} (severity {sev:.2f})" for anchor, sev in profile.pain_points_ranked
    ]

    sections: list[str] = ["SURVEY-DERIVED SIGNALS:"]
    if signal_lines:
        sections.append("Forces of Progress (in the prospect's voice):")
        sections.extend(signal_lines)
    if workflow_lines:
        sections.append("Workflow signals:")
        sections.extend(workflow_lines)
    if pain_lines:
        sections.append("Pain anchors ranked by severity:")
        sections.extend(pain_lines)

    return "\n".join(sections)

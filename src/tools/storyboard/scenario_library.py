"""
Deployment Scenario Library — The Imagination Engine
=====================================================

Curated deployment scenarios that show prospects "here's what other orgs
in your space have built with Epiphan." Used by the transcript-to-scenarios
pipeline to match call signals against creative deployment ideas.

20 scenarios across all 10 verticals (3 each for top 6, 1 each for remaining 4).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DeploymentScenario:
    """A curated Epiphan deployment scenario for prospect imagination."""

    id: str
    name: str
    vertical: str
    trigger_phrases: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    bundle_name: str | None = None
    setup_description: str = ""
    reference_story: str | None = None
    persona_match: list[str] = field(default_factory=list)
    edge_value: str | None = None
    creative_hook: str = ""


# ============================================================================
# Higher Ed (3)
# ============================================================================

HIGHER_ED_CAMPUS_CAPTURE = DeploymentScenario(
    id="higher_ed_campus_capture",
    name="Campus-Wide Lecture Capture Standardization",
    vertical="higher_ed",
    trigger_phrases=[
        "lecture capture",
        "campus-wide",
        "hundreds of rooms",
        "standardize",
        "classroom recording",
        "panopto",
        "kaltura",
        "lms",
        "faculty won't use",
        "too many rooms",
        "one-button",
        "fleet",
        "scale",
    ],
    products=["pearl_mini", "pearl_nexus", "ec20_ptz"],
    bundle_name="Campus Capture Fleet",
    setup_description=(
        "Deploy Pearl Mini or Pearl Nexus in every classroom with an EC20 PTZ camera. "
        "Faculty press one button to record — Epiphan Edge manages the entire fleet remotely. "
        "Recordings auto-publish to your LMS (Panopto, Kaltura, Brightcove) with zero faculty effort."
    ),
    reference_story="NC State — 300+ Pearl units campus-wide; MTSU — 428 rooms centrally managed",
    persona_match=["av_director", "provost", "university_finance"],
    edge_value="Epiphan Edge provides centralized management, monitoring, and scheduling for every room from a single dashboard.",
    creative_hook=(
        "NC State didn't start with 300 rooms. They started with 10, proved the model, "
        "and scaled because Pearl just works — no IT tickets, no faculty complaints."
    ),
)

HIGHER_ED_ONE_BUTTON_STUDIO = DeploymentScenario(
    id="higher_ed_one_button_studio",
    name="Faculty Self-Service Recording Studio",
    vertical="higher_ed",
    trigger_phrases=[
        "recording studio",
        "self-service",
        "one button studio",
        "faculty recording",
        "content creation",
        "green screen",
        "lightboard",
        "asynchronous",
        "flipped classroom",
    ],
    products=["pearl_mini", "ec20_ptz"],
    bundle_name="One-Button Studio Kit",
    setup_description=(
        "Convert a small room into a faculty self-service recording studio. Pearl Mini handles "
        "multi-camera switching, recording, and streaming — faculty walk in, press one button, "
        "and record professional lectures for flipped classrooms or online courses."
    ),
    reference_story="UNLV — 215 rooms with 10-minute deploy per room using Pearl Nexus",
    persona_match=["av_director", "ld_director", "provost"],
    edge_value="Epiphan Edge lets faculty schedule recordings in advance and auto-publish to the LMS.",
    creative_hook=(
        "Your faculty aren't video producers — and they shouldn't have to be. "
        "The best studios are the ones where the technology disappears."
    ),
)

HIGHER_ED_HYBRID_CLASSROOM = DeploymentScenario(
    id="higher_ed_hybrid_classroom",
    name="Hybrid Classroom for Remote Students",
    vertical="higher_ed",
    trigger_phrases=[
        "hybrid",
        "remote students",
        "HyFlex",
        "distance learning",
        "online students",
        "zoom",
        "teams",
        "remote learners",
        "simultaneous",
    ],
    products=["pearl_nexus", "ec20_ptz"],
    bundle_name="Hybrid Classroom Kit",
    setup_description=(
        "Pearl Nexus bridges in-room and remote students seamlessly. The EC20 PTZ auto-tracks "
        "the instructor while Pearl Nexus streams to Zoom/Teams AND records locally. Remote "
        "students get the same experience as in-room — no second-class citizens."
    ),
    reference_story="NTNU (Norway) — 700+ rooms with Pearl Mini + Panopto integration",
    persona_match=["av_director", "provost", "university_president"],
    edge_value="Epiphan Edge enables zero-touch provisioning — IT deploys rooms without visiting each one.",
    creative_hook=(
        "The hybrid classroom isn't a pandemic compromise — it's how every modern university "
        "competes for enrollment. Students choose schools that invest in their experience."
    ),
)

HIGHER_ED_ROOMS_OUT_OF_REACH = DeploymentScenario(
    id="higher_ed_rooms_out_of_reach",
    name="EC20: Capture Every Room That Was Always Out of Reach",
    vertical="higher_ed",
    trigger_phrases=[
        "seminar room",
        "breakout",
        "collaborative",
        "small room",
        "budget",
        "can't afford",
        "too expensive",
        "every room",
        "out of reach",
        "no encoder",
        "single cable",
        "one cable",
        "simple",
        "direct",
        "dante",
        "per-room cost",
    ],
    products=["ec20_ptz"],
    bundle_name=None,
    setup_description=(
        "EC20 PTZ camera records and uploads direct to your CMS/LMS — no encoder needed. "
        "One Ethernet cable delivers PoE+ power, 4K60 video, and Dante audio. "
        "Traditional per-room cost is 3-4x higher with separate camera, encoder, audio, "
        "and electrician. EC20 replaces all of that with a single device and one cable. "
        "Seminar rooms, breakout spaces, collaborative areas, and overflow halls that "
        "could never justify the cost — now capturable. AI tracking keeps the presenter "
        "centered. LCD shows IP at install. Both ceiling and wall mounts in the box."
    ),
    reference_story=None,
    persona_match=["av_director", "provost", "university_finance", "av_integrator"],
    edge_value=(
        "Epiphan Edge fleet-manages every EC20 from one dashboard. "
        "Schedule recordings, monitor health, batch firmware updates — "
        "across every seminar room, breakout space, and classroom on campus."
    ),
    creative_hook=(
        "Your campus has 200 teaching spaces. Lecture capture covers 40 of them because "
        "the other 160 couldn't justify $8K/room. At $1,899 per room with one cable and "
        "no encoder, those 160 rooms just became capturable. "
        "That's the conversation that changes the provost's budget meeting."
    ),
)


# ============================================================================
# K-12 (3)
# ============================================================================

K12_SPORTS_BROADCAST = DeploymentScenario(
    id="k12_sports_broadcast",
    name="Friday Night Lights Streaming",
    vertical="k12",
    trigger_phrases=[
        "sports",
        "football",
        "basketball",
        "game",
        "stream",
        "broadcast",
        "athletic",
        "NFHS",
        "parents",
        "live stream",
        "friday night",
    ],
    products=["pearl_nano", "ec20_ptz"],
    bundle_name="School Sports Streaming Kit",
    setup_description=(
        "Pearl Nano + EC20 PTZ delivers NFL-style multi-camera streaming for every home game. "
        "Student volunteers run the show with minimal training — Pearl Nano's simple interface "
        "means no AV expertise required. Stream to YouTube, Facebook, or NFHS Network simultaneously."
    ),
    reference_story=None,
    persona_match=["av_director", "ld_director"],
    edge_value="Epiphan Edge lets the AD schedule games and monitor streams from their phone.",
    creative_hook=(
        "Every parent in the stands is already streaming on their phone. "
        "Give them a reason to share YOUR professional stream instead."
    ),
)

K12_LIBRARY_STUDIO = DeploymentScenario(
    id="k12_library_studio",
    name="Library Broadcast & Media Studio",
    vertical="k12",
    trigger_phrases=[
        "library",
        "media center",
        "morning announcements",
        "student broadcast",
        "youtube",
        "social media",
        "media literacy",
        "journalism",
    ],
    products=["pearl_nano", "ec20_ptz"],
    bundle_name="School Media Studio Kit",
    setup_description=(
        "Transform the library or media center into a student broadcast studio. Pearl Nano handles "
        "switching between camera, screen share, and graphics while students produce morning "
        "announcements, school news, and social media content — real media literacy in action."
    ),
    reference_story=None,
    persona_match=["av_director", "ld_director"],
    edge_value=None,
    creative_hook=(
        "The school library isn't just books anymore — it's the campus broadcast center. "
        "Students learn real production skills with professional tools."
    ),
)

K12_CLASSROOM_RECORDING = DeploymentScenario(
    id="k12_classroom_recording",
    name="One-Button Classroom Recording for Every Teacher",
    vertical="k12",
    trigger_phrases=[
        "classroom recording",
        "teacher recording",
        "lesson capture",
        "absent students",
        "teacher evaluation",
        "professional development",
        "observation",
        "substitute",
    ],
    products=["pearl_nano", "ec20_ptz"],
    bundle_name="Classroom Capture Starter",
    setup_description=(
        "Pearl Nano in every classroom gives teachers one-button recording for lesson capture. "
        "Absent students catch up, substitutes have reference recordings, and administrators "
        "have non-intrusive classroom observation tools — all without disrupting the teacher."
    ),
    reference_story=None,
    persona_match=["av_director", "ld_director"],
    edge_value="Epiphan Edge enables district-wide fleet management from the central office.",
    creative_hook=(
        "The best teachers already repeat themselves 5 times a day across sections. "
        "Record it once — every student gets the best version."
    ),
)


# ============================================================================
# Houses of Worship (3)
# ============================================================================

HOW_VOLUNTEER_STREAMING = DeploymentScenario(
    id="how_volunteer_streaming",
    name="Volunteer-Friendly Sunday Service Streaming",
    vertical="houses_of_worship",
    trigger_phrases=[
        "volunteer",
        "sunday service",
        "worship",
        "stream",
        "simple",
        "congregation",
        "online church",
        "facebook live",
        "youtube live",
        "no tech person",
    ],
    products=["pearl_nano", "ec20_ptz"],
    bundle_name="Worship Streaming Kit",
    setup_description=(
        "Pearl Nano + EC20 PTZ delivers broadcast-quality Sunday service streaming that any "
        "volunteer can operate. Pre-set camera positions, one-button start, simultaneous streaming "
        "to Facebook Live and YouTube — the congregation at home gets the same experience as the pews."
    ),
    reference_story="Stream Monkey — recommends Pearl to all Houses of Worship clients",
    persona_match=["av_director", "technical_director"],
    edge_value=None,
    creative_hook=(
        "Your best volunteer isn't an AV tech — they're a Sunday school teacher who showed up early. "
        "Pearl Nano is built for exactly that person."
    ),
)

HOW_MULTI_CAMPUS = DeploymentScenario(
    id="how_multi_campus",
    name="Multi-Campus Live Service Distribution",
    vertical="houses_of_worship",
    trigger_phrases=[
        "multi-campus",
        "satellite",
        "campus",
        "multi-site",
        "second location",
        "expansion",
        "plant",
        "church plant",
        "overflow",
    ],
    products=["pearl_2", "pearl_nano"],
    bundle_name="Multi-Campus Distribution System",
    setup_description=(
        "Pearl-2 at the main campus handles full multi-camera production while Pearl Nano units "
        "at satellite campuses receive and display the live feed. Every campus gets the same "
        "sermon, the same worship, the same experience — synchronized across all locations."
    ),
    reference_story=None,
    persona_match=["av_director"],
    edge_value="Epiphan Edge synchronizes scheduling and monitoring across all campus locations from one dashboard.",
    creative_hook=(
        "When you open a second campus, the lead pastor can't be in two places. "
        "But their message can — in broadcast quality, not laptop-on-a-tripod quality."
    ),
)

HOW_SPECIAL_EVENTS = DeploymentScenario(
    id="how_special_events",
    name="Easter/Christmas/Baptism Production Upgrade",
    vertical="houses_of_worship",
    trigger_phrases=[
        "easter",
        "christmas",
        "baptism",
        "special event",
        "holiday",
        "concert",
        "production value",
        "upgrade",
        "professional look",
    ],
    products=["pearl_2", "ec20_ptz"],
    bundle_name="Special Events Production Kit",
    setup_description=(
        "Pearl-2 with multiple EC20 PTZ cameras delivers cinematic production for high-attendance "
        "services. Custom layouts, lower thirds, IMAG support, and simultaneous recording + "
        "streaming — Easter and Christmas services that look like they were produced by a network."
    ),
    reference_story=None,
    persona_match=["av_director", "technical_director"],
    edge_value=None,
    creative_hook=(
        "Easter is your Super Bowl — 2x normal attendance, guests judging everything. "
        "That's not the Sunday to have AV problems."
    ),
)


# ============================================================================
# Legal / Courts (3)
# ============================================================================

LEGAL_COURTROOM_RECORDING = DeploymentScenario(
    id="legal_courtroom_recording",
    name="Courtroom Proceedings Recording System",
    vertical="legal",
    trigger_phrases=[
        "courtroom",
        "court recording",
        "proceedings",
        "hearing",
        "testimony",
        "judge",
        "public access",
        "transparency",
        "record of proceedings",
        "court reporter",
    ],
    products=["pearl_mini", "ec20_ptz"],
    bundle_name="Courtroom Recording System",
    setup_description=(
        "Pearl Mini with multiple EC20 PTZ cameras captures every courtroom proceeding with "
        "tamper-proof recording. Automatic recording on schedule, simultaneous public access "
        "streaming, and archival-grade storage — the official record is always complete."
    ),
    reference_story="Redfish Technologies — 60+ Pearl systems across Washington state courts and councils",
    persona_match=["court_admin", "law_firm_it"],
    edge_value="Epiphan Edge provides remote monitoring and health alerts — IT knows if a courtroom camera goes offline before the hearing starts.",
    creative_hook=(
        "A failed court recording isn't an inconvenience — it's a mistrial risk. "
        "Redfish deployed 60+ Pearl systems across WA courts because hardware reliability "
        "isn't optional when the record is the law."
    ),
)

LEGAL_MOCK_TRIAL = DeploymentScenario(
    id="legal_mock_trial",
    name="Mock Trial & Jury Consulting Facility",
    vertical="legal",
    trigger_phrases=[
        "mock trial",
        "jury",
        "focus group",
        "jury consulting",
        "trial prep",
        "verdict",
        "deliberation",
        "witness prep",
    ],
    products=["pearl_2", "ec20_ptz"],
    bundle_name="Trial Consulting Capture System",
    setup_description=(
        "Pearl-2 captures every angle of mock trials and jury focus groups — attorney presentations, "
        "juror reactions, deliberation room footage. Multi-angle synchronized playback lets trial "
        "consultants analyze body language and engagement second by second."
    ),
    reference_story="Verdict Advantage — Pearl-2 for mock trials, 12.5x settlement increase; Anchor Point — simplified mock trial capture",
    persona_match=["court_admin", "law_firm_it"],
    edge_value=None,
    creative_hook=(
        "Verdict Advantage saw a 12.5x increase in settlement values after adding multi-angle "
        "mock trial video analysis. The jury's body language tells the story the verdict doesn't."
    ),
)

LEGAL_DEPOSITION_STUDIO = DeploymentScenario(
    id="legal_deposition_studio",
    name="Remote Deposition Recording Studio",
    vertical="legal",
    trigger_phrases=[
        "deposition",
        "remote deposition",
        "video deposition",
        "testimony",
        "e-discovery",
        "remote witness",
        "on-premises",
        "data sovereignty",
    ],
    products=["pearl_mini", "ec20_ptz", "avio_4k"],
    bundle_name="Deposition Studio Kit",
    setup_description=(
        "Pearl Mini captures depositions with broadcast-quality video while AV.io 4K "
        "integrates screen shares from virtual participants. All recordings stay on-premises — "
        "no cloud storage concerns for privileged communications. Clean audio for transcription services."
    ),
    reference_story="UCLA School of Law — 4-camera Pearl + Edge moot courtroom",
    persona_match=["law_firm_it", "court_admin"],
    edge_value=None,
    creative_hook=(
        "Remote depositions are now standard — but 'Zoom recording' isn't admissible-quality. "
        "Hardware recording with chain-of-custody controls is what the court expects."
    ),
)


# ============================================================================
# Corporate (3)
# ============================================================================

CORP_TOWN_HALL = DeploymentScenario(
    id="corp_town_hall",
    name="CEO Town Hall Broadcast Studio",
    vertical="corporate",
    trigger_phrases=[
        "town hall",
        "all-hands",
        "ceo",
        "executive",
        "broadcast",
        "company meeting",
        "quarterly",
        "earnings",
        "simulcast",
    ],
    products=["pearl_2", "ec20_ptz"],
    bundle_name="Executive Broadcast System",
    setup_description=(
        "Pearl-2 turns any conference room into a broadcast studio for executive town halls. "
        "Multi-camera switching, custom branded layouts with lower thirds, and simultaneous "
        "streaming to Teams, YouTube, and the corporate intranet — every employee gets the same "
        "broadcast-quality experience regardless of location."
    ),
    reference_story="OpenAI — Pearl-2 for '12 Days of OpenAI' livestream production",
    persona_match=["corp_comms", "av_director"],
    edge_value="Epiphan Edge enables IT to pre-configure layouts and schedules so the comms team just presses start.",
    creative_hook=(
        "OpenAI used Pearl-2 for their '12 Days of OpenAI' livestream — the world's leading "
        "AI company trusts hardware encoding when reliability matters most."
    ),
)

CORP_BOARDROOM_FLEET = DeploymentScenario(
    id="corp_boardroom_fleet",
    name="Boardroom Standardization Across Offices",
    vertical="corporate",
    trigger_phrases=[
        "boardroom",
        "meeting room",
        "conference room",
        "standardize",
        "50 offices",
        "global",
        "consistent",
        "every room",
        "it tickets",
        "hybrid meeting",
    ],
    products=["pearl_mini", "pearl_nexus", "ec20_ptz"],
    bundle_name="Boardroom Fleet Standard",
    setup_description=(
        "Deploy Pearl Mini or Pearl Nexus in every boardroom across all offices. Same setup, "
        "same experience, same one-button operation everywhere. IT manages the entire fleet from "
        "Epiphan Edge — firmware updates, monitoring, and troubleshooting without leaving the desk."
    ),
    reference_story="Fortune 500 boardrooms — standardized on Pearl Mini",
    persona_match=["av_director", "corp_comms"],
    edge_value="Epiphan Edge zero-touch provisioning means new offices get AV that works out of the box.",
    creative_hook=(
        "Every office has different AV because every office was set up by a different integrator "
        "in a different year. Standardize once — IT support tickets for 'the video doesn't work' "
        "drop to near zero."
    ),
)

CORP_TRAINING_CAPTURE = DeploymentScenario(
    id="corp_training_capture",
    name="Expert Knowledge Capture Before Retirement",
    vertical="corporate",
    trigger_phrases=[
        "knowledge capture",
        "training",
        "retirement",
        "onboarding",
        "tribal knowledge",
        "expert",
        "content library",
        "institutional knowledge",
        "succession",
    ],
    products=["pearl_mini", "ec20_ptz"],
    bundle_name="Knowledge Capture Studio",
    setup_description=(
        "Pearl Mini captures expert training sessions and process walkthroughs before institutional "
        "knowledge walks out the door. Multi-camera capture (instructor + screen + demo area) "
        "creates professional training content that every new hire can access forever."
    ),
    reference_story=None,
    persona_match=["ld_director", "corp_comms"],
    edge_value=None,
    creative_hook=(
        "Your best trainer retires next year. Their 30 years of knowledge is worth "
        "recording once — and delivering to every new hire, at every location, forever."
    ),
)


# ============================================================================
# Live Events (3)
# ============================================================================

EVENTS_BREAKOUT_FACTORY = DeploymentScenario(
    id="events_breakout_factory",
    name="Conference Multi-Room Capture Factory",
    vertical="live_events",
    trigger_phrases=[
        "conference",
        "breakout",
        "multi-room",
        "concurrent sessions",
        "content capture",
        "on-demand",
        "attendee",
        "speaker",
    ],
    products=["pearl_mini", "ec20_ptz"],
    bundle_name="Conference Capture Fleet",
    setup_description=(
        "Deploy a Pearl Mini + EC20 PTZ in every breakout room for automatic session capture. "
        "Every speaker, every session, every room — captured simultaneously with zero additional "
        "crew. Attendees get on-demand access to sessions they missed. Event organizers get content "
        "to sell year-round."
    ),
    reference_story="Markey's Rental — 13 concurrent rooms, Pearl per room; Source of Knowledge — 1,000+ conferences, 99.4% capture success",
    persona_match=["av_director", "technical_director"],
    edge_value="Epiphan Edge monitors all rooms in real-time — one operator oversees 13+ simultaneous captures from a single laptop.",
    creative_hook=(
        "Source of Knowledge captured 1,000+ conferences with 99.4% success rate. "
        "One Pearl per room, one operator for the whole venue — that's the math "
        "that makes multi-room capture profitable."
    ),
)

EVENTS_PRODUCTION_RIG = DeploymentScenario(
    id="events_production_rig",
    name="IMAG + ISO + Stream 3-Camera Production",
    vertical="live_events",
    trigger_phrases=[
        "IMAG",
        "ISO",
        "production",
        "3-camera",
        "multi-camera",
        "live switch",
        "program feed",
        "confidence monitor",
        "tally",
    ],
    products=["pearl_2", "ec20_ptz"],
    bundle_name="Live Production Rig",
    setup_description=(
        "Pearl-2 powers a complete 3-camera production with IMAG, ISO recording of every angle, "
        "and simultaneous live streaming. Custom layouts, tally lights, confidence monitors, and "
        "hardware encoding that never crashes mid-show — everything in a single rack unit."
    ),
    reference_story=None,
    persona_match=["technical_director", "av_director"],
    edge_value=None,
    creative_hook=(
        "Software encoders crash. Hardware encoders don't. When the keynote speaker is on stage "
        "and 5,000 people are watching the stream, that's not a philosophical distinction."
    ),
)

EVENTS_RENTAL_STANDARD = DeploymentScenario(
    id="events_rental_standard",
    name="Rental House Standardized Kit",
    vertical="live_events",
    trigger_phrases=[
        "rental",
        "rental house",
        "inventory",
        "standardized kit",
        "cross-rent",
        "freelancer",
        "operator",
        "turnkey",
    ],
    products=["pearl_mini", "pearl_2", "ec20_ptz"],
    bundle_name="Rental Production Standard",
    setup_description=(
        "Standardize your rental inventory on Pearl. Every kit is identical — any freelance "
        "operator picks it up and runs the show without training. Pearl Mini for small gigs, "
        "Pearl-2 for large productions. Consistent client experience regardless of which operator "
        "or which kit ships."
    ),
    reference_story="Markey's Rental — standardized on Pearl for all live event production",
    persona_match=["av_director", "technical_director"],
    edge_value="Epiphan Edge lets the rental house monitor every deployed kit in real-time across multiple venues.",
    creative_hook=(
        "Your freelancer arrives at the venue 2 hours before the show. "
        "They've never seen this kit before. With Pearl, that doesn't matter — "
        "it works the same every time."
    ),
)


# ============================================================================
# Healthcare (1)
# ============================================================================

HEALTHCARE_SIM_DEBRIEF = DeploymentScenario(
    id="healthcare_sim_debrief",
    name="6-Angle Simulation Center Debrief Recording",
    vertical="healthcare",
    trigger_phrases=[
        "simulation",
        "sim center",
        "debrief",
        "manikin",
        "standardized patient",
        "HIPAA",
        "multi-angle",
        "nursing",
        "medical school",
        "clinical",
    ],
    products=["pearl_2", "ec20_ptz", "avio_4k"],
    bundle_name="Simulation Center Capture System",
    setup_description=(
        "Pearl-2 captures 6+ angles simultaneously in simulation labs — patient monitor feeds "
        "via AV.io 4K, room cameras via EC20 PTZ, and close-up procedure views. Synchronized "
        "multi-angle playback in the debrief room lets instructors pause, rewind, and compare "
        "angles. All recordings stay on-premises for HIPAA compliance."
    ),
    reference_story=None,
    persona_match=["sim_center_director", "ld_director"],
    edge_value=None,
    creative_hook=(
        "Your manikin costs $100K. The simulation takes 45 minutes of faculty time. "
        "Without proper recording, every debrief relies on memory — and memory lies. "
        "6-angle playback makes every simulation a reusable teaching moment."
    ),
)


# ============================================================================
# Industrial (1)
# ============================================================================

INDUSTRIAL_SAFETY_CAPTURE = DeploymentScenario(
    id="industrial_safety_capture",
    name="OSHA Safety Training Capture Before Expert Retires",
    vertical="industrial",
    trigger_phrases=[
        "OSHA",
        "safety training",
        "compliance",
        "retirement",
        "tribal knowledge",
        "lockout/tagout",
        "SOP",
        "documentation",
        "incident",
        "audit",
    ],
    products=["pearl_mini", "pearl_nano", "avio_4k"],
    bundle_name="Safety Training Capture Kit",
    setup_description=(
        "Pearl Mini or Pearl Nano captures safety training sessions and process demonstrations "
        "before your most experienced operators retire. Multi-angle recording (instructor + "
        "equipment + screen) creates OSHA-ready documentation. AV.io 4K captures equipment "
        "displays and HMI screens. Every procedure, every plant, standardized and archived."
    ),
    reference_story=None,
    persona_match=["ehs_manager", "ld_director"],
    edge_value="Epiphan Edge enables centralized training content distribution across all plant locations.",
    creative_hook=(
        "Your most experienced operator knows every safety procedure by heart. "
        "They retire in 18 months. OSHA doesn't accept 'we lost the training material' "
        "as an excuse — capture everything now."
    ),
)


# ============================================================================
# Government (bonus — reuses legal_courtroom_recording for courts)
# ============================================================================

# Government is covered by legal_courtroom_recording (courts/councils) and
# the Redfish reference story. The Hawaii State Senate case study also applies.
# No separate government-only scenario needed — the courtroom and council
# chamber use cases are the same product/deployment pattern.


# ============================================================================
# UX Research (bonus)
# ============================================================================

# UX Research is covered by corporate_training_capture patterns (multi-angle
# recording, screen + face) and healthcare_sim_debrief (synchronized playback).
# Pearl Mini + AV.io 4K is the standard UX research setup.


# ============================================================================
# AV Integrator — Cross-Vertical (3)
# ============================================================================

INTEGRATOR_FLEET_STANDARDIZATION = DeploymentScenario(
    id="integrator_fleet_standardization",
    name="Multi-Client Fleet Standardization",
    vertical="corporate",  # Cross-vertical, corporate as default
    trigger_phrases=[
        "integrator",
        "multiple clients",
        "fleet",
        "standardize",
        "manage",
        "support calls",
        "truck roll",
        "margin",
        "remote monitoring",
        "epiphan cloud",
        "AVI-SPL",
        "Diversified",
        "Whitlock",
        "Ford AV",
        "client sites",
        "install base",
    ],
    products=["pearl_mini", "pearl_nexus", "ec20_ptz"],
    bundle_name="Integrator Fleet Standard",
    setup_description=(
        "Standardize all client sites on Pearl Mini or Pearl Nexus with EC20 PTZ cameras. "
        "One product line across universities, corporate HQs, courts, and hospitals — your "
        "field techs learn it once and deploy it everywhere. Epiphan Edge gives you a single "
        "dashboard across 50+ client sites: firmware updates, health monitoring, and remote "
        "troubleshooting without dispatching a truck."
    ),
    reference_story=(
        "MSAVi — manages Disney and Imagine Dragons events on Pearl; "
        "Redfish Technologies — 60+ Pearl systems across WA state courts; "
        "Freeman — world's largest events standardized on Pearl"
    ),
    persona_match=["av_integrator", "dealer_dave", "system_engineer"],
    edge_value=(
        "Epiphan Edge fleet management eliminates per-site monitoring. "
        "One integrator managed 60+ court systems across Washington state from a single dashboard — "
        "zero truck rolls for firmware updates, zero missed recordings from offline devices."
    ),
    creative_hook=(
        "Most integrators manage 5 different product lines across their client base. "
        "That's 5 sets of firmware, 5 support portals, 5 training programs. "
        "Standardize on Pearl and your field techs install in 20 minutes, "
        "your NOC monitors everything from one screen, and your margin stays intact."
    ),
)

INTEGRATOR_UNIVERSITY_RFP = DeploymentScenario(
    id="integrator_university_rfp",
    name="University RFP: 100+ Classroom Lecture Capture",
    vertical="higher_ed",
    trigger_phrases=[
        "RFP",
        "bid",
        "proposal",
        "spec",
        "university",
        "100 rooms",
        "campus",
        "lecture capture",
        "Panopto",
        "Kaltura",
        "installation",
        "commissioning",
        "timeline",
        "rollout",
        "deployment plan",
    ],
    products=["pearl_mini", "pearl_nexus", "ec20_ptz"],
    bundle_name="Campus Capture RFP Response Kit",
    setup_description=(
        "Respond to the university's lecture capture RFP with a turnkey Pearl deployment. "
        "Pearl Mini + EC20 PTZ per classroom, Epiphan Edge for fleet management, native "
        "Panopto/Kaltura integration for the LMS. 20-minute install per room means your crew "
        "deploys 10 rooms/day. The university gets one-button operation for faculty and "
        "centralized management for IT — you get a clean install and zero callbacks."
    ),
    reference_story=(
        "NC State — 300+ Pearl units, single AV team managing all rooms; "
        "MTSU — 428 classrooms, 2-person team; "
        "UNLV — 215 rooms deployed with Pearl Nexus"
    ),
    persona_match=["av_integrator", "system_engineer", "dealer_dave"],
    edge_value=(
        "20-minute install per room (vs 2+ hours for software-based competitors). "
        "Native LMS integration means no middleware layer to configure or maintain. "
        "Epiphan Edge zero-touch provisioning lets you pre-configure rooms before the truck arrives."
    ),
    creative_hook=(
        "NC State didn't spec 300 rooms on day one. They started with a 10-room pilot, "
        "proved zero faculty complaints and zero IT tickets, and the university funded "
        "the full rollout themselves. Your RFP response writes itself when the pilot speaks."
    ),
)

INTEGRATOR_CORPORATE_REFRESH = DeploymentScenario(
    id="integrator_corporate_refresh",
    name="Corporate Campus AV Refresh — Legacy to Pearl",
    vertical="corporate",
    trigger_phrases=[
        "refresh",
        "upgrade",
        "replace",
        "legacy",
        "Extron",
        "Crestron",
        "old system",
        "end of life",
        "frankenstack",
        "mismatched",
        "different vendors",
        "boardroom",
        "meeting room",
        "50 rooms",
        "hybrid",
    ],
    products=["pearl_mini", "pearl_nexus", "ec20_ptz"],
    bundle_name="Corporate AV Refresh Package",
    setup_description=(
        "Replace the frankenstack — 5 different encoder brands across 50 meeting rooms — with "
        "a standardized Pearl deployment. Pearl Mini for small rooms, Pearl Nexus for large "
        "boardrooms, EC20 PTZ for camera. Same control interface everywhere, same Epiphan Edge "
        "management, same Crestron/Q-SYS integration. IT gets a single pane of glass instead of "
        "5 vendor portals. Your team installs in half the time because every room is the same kit."
    ),
    reference_story=(
        "OpenAI — Pearl-2 for corporate livestream production; "
        "Fortune 500 boardrooms standardized on Pearl Mini"
    ),
    persona_match=["av_integrator", "dealer_dave", "av_director"],
    edge_value=(
        "Crestron and Q-SYS control integration out of the box — no custom programming. "
        "Open API for any control system. Your programmer writes the module once and "
        "deploys it to every room. Compared to the current frankenstack, that's a 10x "
        "reduction in programming hours."
    ),
    creative_hook=(
        "Every corporate campus has the same story: Building A has Extron, Building B has "
        "Crestron capture, Building C has a laptop on a cart. IT supports all of them and "
        "none of them well. The refresh isn't about new hardware — it's about one system, "
        "one dashboard, one support number. That's the project your client will thank you for."
    ),
)


# ============================================================================
# Master Library
# ============================================================================

SCENARIO_LIBRARY: list[DeploymentScenario] = [
    # Higher Ed (3)
    HIGHER_ED_CAMPUS_CAPTURE,
    HIGHER_ED_ONE_BUTTON_STUDIO,
    HIGHER_ED_HYBRID_CLASSROOM,
    HIGHER_ED_ROOMS_OUT_OF_REACH,
    # K-12 (3)
    K12_SPORTS_BROADCAST,
    K12_LIBRARY_STUDIO,
    K12_CLASSROOM_RECORDING,
    # Houses of Worship (3)
    HOW_VOLUNTEER_STREAMING,
    HOW_MULTI_CAMPUS,
    HOW_SPECIAL_EVENTS,
    # Legal / Courts (3)
    LEGAL_COURTROOM_RECORDING,
    LEGAL_MOCK_TRIAL,
    LEGAL_DEPOSITION_STUDIO,
    # Corporate (3)
    CORP_TOWN_HALL,
    CORP_BOARDROOM_FLEET,
    CORP_TRAINING_CAPTURE,
    # Live Events (3)
    EVENTS_BREAKOUT_FACTORY,
    EVENTS_PRODUCTION_RIG,
    EVENTS_RENTAL_STANDARD,
    # Healthcare (1)
    HEALTHCARE_SIM_DEBRIEF,
    # Industrial (1)
    INDUSTRIAL_SAFETY_CAPTURE,
    # AV Integrator — Cross-Vertical (3)
    INTEGRATOR_FLEET_STANDARDIZATION,
    INTEGRATOR_UNIVERSITY_RFP,
    INTEGRATOR_CORPORATE_REFRESH,
]

# Index by ID for fast lookup
SCENARIO_BY_ID: dict[str, DeploymentScenario] = {s.id: s for s in SCENARIO_LIBRARY}

# Index by vertical for filtered access
SCENARIOS_BY_VERTICAL: dict[str, list[DeploymentScenario]] = {}
for _scenario in SCENARIO_LIBRARY:
    SCENARIOS_BY_VERTICAL.setdefault(_scenario.vertical, []).append(_scenario)


# ============================================================================
# Matching Functions
# ============================================================================


def match_scenarios_by_phrases(
    text: str,
    *,
    vertical_filter: str | None = None,
    top_n: int = 4,
) -> list[tuple[DeploymentScenario, int]]:
    """
    Match scenarios against transcript text by trigger phrase hits.

    Args:
        text: Transcript or summary text to match against.
        vertical_filter: Optional vertical to restrict matching.
        top_n: Maximum number of results to return.

    Returns:
        List of (scenario, hit_count) tuples sorted by hit count descending.
    """
    text_lower = text.lower()
    candidates = SCENARIO_LIBRARY
    if vertical_filter:
        candidates = SCENARIOS_BY_VERTICAL.get(vertical_filter, SCENARIO_LIBRARY)

    scored: list[tuple[DeploymentScenario, int]] = []
    for scenario in candidates:
        hits = sum(
            1 for phrase in scenario.trigger_phrases if phrase.lower() in text_lower
        )
        if hits > 0:
            scored.append((scenario, hits))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]


def get_scenarios_for_vertical(vertical: str) -> list[DeploymentScenario]:
    """Get all scenarios for a given vertical."""
    return SCENARIOS_BY_VERTICAL.get(vertical, [])


def get_scenario_by_id(scenario_id: str) -> DeploymentScenario | None:
    """Get a scenario by its ID."""
    return SCENARIO_BY_ID.get(scenario_id)

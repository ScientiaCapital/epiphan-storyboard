"""Problem-statement library — verbatim BDR-validated pain language per persona.

Source of truth: ``Problem Statements Per Persona by Vertical.docx``
(Epiphan Video — BDR Call & Email Playbook, April 2026).

The doc covers 9 verticals × ~32 personas × 3–4 statements each. Statements are
written to be read aloud in one breath (≤30 words) and used verbatim as the
opening line of a cold call or email.

This module is the runtime API: schema + a hand-curated constant + retrieval
helpers used by ``prompt_builders.build_knowledge_context`` to ground the LLM
in real, sales-validated pain phrasing.

# Doc-role → AudiencePersona mapping
# ----------------------------------
# The BDR doc uses long composite role strings ("AV Director / Director of AV
# Architecture") while the codebase uses the 17-value ``AudiencePersona`` enum
# from ``epiphan_presets.py``. ``DOC_PERSONA_ALIASES`` documents the mapping
# explicitly so it stays auditable.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Mapping from verbatim doc role strings → AudiencePersona enum values.
# Multiple doc roles can map to a single enum value (e.g. all "AV Director"
# variants → av_director). This is the only place where doc-string ↔ enum
# normalization lives, so reviewers can audit it in one place.
DOC_PERSONA_ALIASES: dict[str, str] = {
    # HIGHER EDUCATION
    "AV Director / Director of AV Architecture": "av_director",
    "IT Director / CIO": "law_firm_it",
    "Educational Technology Manager / Director of Instructional Technology": "edtech_manager",
    "AV Coordinator / Media Services Technician": "av_director",
    # COURTS / LEGAL
    "Court Administrator / IT Director": "court_admin",
    "Multimedia Services Director / AV Operations Lead": "production_director",
    "Court Clerk / Records Manager": "court_admin",
    "Legislative IT / Broadcast Operations Director": "law_firm_it",
    # LIVE EVENTS / PRODUCTION
    "Production Manager / Technical Director": "technical_director",
    "Design Engineer / Systems Integrator": "system_engineer",
    "Director of Event Technology (Venue / Hotel / Convention Center)": "venue_manager",
    "AV Reseller / Account Development Manager": "av_integrator",
    # GOVERNMENT
    "IT Director / AV Manager": "av_director",
    "Public Information Officer / Communications Director": "corp_comms",
    "Sr. Systems Engineer / Infrastructure Engineer": "system_engineer",
    "Video Production Administrator / Broadcast Manager": "production_director",
    # CORPORATE AV
    "VP of IT / Senior Director of IT": "law_firm_it",
    "AV Manager / Audio Visual Support Coordinator": "av_director",
    "Senior Media Producer / Corporate Communications": "corp_comms",
    "Learning & Development / Instructional Designer": "ld_director",
    # HEALTHCARE
    "Director of Instructional Technology (Medical School / Sim Lab)": "sim_center_director",
    "Multimedia Support Coordinator / AV Engineer (Hospital System)": "av_director",
    "Research Professor / Clinical Simulation Director": "sim_center_director",
    # HOUSES OF WORSHIP
    "Senior Pastor / Ministry Director": "venue_manager",
    "Volunteer AV Lead / Technical Director": "technical_director",
    "AV Integrator Serving Houses of Worship": "av_integrator",
    # K-12 EDUCATION
    "IT Director / Chief Technology Officer": "law_firm_it",
    "Instructional Technology Coordinator / Media Specialist": "edtech_manager",
    "Athletic Director / Activities Coordinator": "venue_manager",
    # CHANNEL / AV INTEGRATORS
    "Account Manager / Sales Engineer (National Integrator)": "dealer_dave",
    "Design Engineer / Design Consultant": "system_engineer",
    "Owner / GM (Small-Mid AV Integrator)": "av_integrator",
}


def normalize_doc_persona(role: str) -> str | None:
    """Map a verbatim doc role string to an AudiencePersona enum value.

    Returns ``None`` when no mapping is registered. Callers decide whether to
    skip, fall back to ``av_director``, or surface a warning.
    """
    return DOC_PERSONA_ALIASES.get(role.strip())


class ProblemStatement(BaseModel):
    """One verbatim problem statement, ICP-scored and channel-tagged."""

    vertical: str = Field(
        description="Vertical key. Maps to EPIPHAN_VERTICALS in epiphan_presets.py.",
    )
    persona: str = Field(
        description="AudiencePersona enum value (e.g. 'av_director').",
    )
    statement: str = Field(
        description="Verbatim ≤30-word statement, BDR-validated.",
    )
    pain_anchor: str = Field(
        description="Short tag for the underlying pain (e.g. 'unrecorded_rooms').",
    )
    channel: Literal["call", "email", "both"] = Field(
        default="both",
        description="Where this statement is intended to be used.",
    )
    icp_score: int = Field(
        ge=0,
        le=100,
        description="ICP score for the vertical, sourced from the BDR playbook.",
    )


# ICP scores per vertical, sourced from the BDR playbook (April 2026).
ICP_SCORES: dict[str, int] = {
    "higher_ed": 90,
    "legal": 85,  # "Courts / Legal"
    "live_events": 85,
    "government": 80,
    "corporate": 80,
    "healthcare": 75,
    "houses_of_worship": 70,
    "k12": 65,
    "channel": 0,  # cross-vertical force multiplier; doc lists as N/A
}


# =====================================================================
# PROBLEM_STATEMENTS — verbatim, BDR-validated, ICP-scored, channel-tagged
# =====================================================================
# Every statement is ≤30 words, written to be read in one breath as the
# opening line of a call or email. Source: ``Problem Statements Per Persona
# by Vertical.docx`` (Epiphan Video — BDR Call & Email Playbook, April 2026).
#
# Phase 1 of the rollout seeds the top 3 ICP verticals (Higher Ed, Courts/
# Legal, Live Events). Phase 2 will fill in the remaining 6 verticals.
PROBLEM_STATEMENTS: list[ProblemStatement] = [
    # -----------------------------------------------------------------
    # HIGHER EDUCATION (ICP 90)
    # -----------------------------------------------------------------
    # AV Director / Director of AV Architecture
    ProblemStatement(
        vertical="higher_ed",
        persona="av_director",
        statement=(
            "A lot of AV directors we talk to have rooms going unrecorded "
            "because faculty won't touch the capture system. That's creating "
            "accessibility gaps nobody catches until a student files a complaint."
        ),
        pain_anchor="unrecorded_rooms_accessibility",
        channel="both",
        icp_score=90,
    ),
    ProblemStatement(
        vertical="higher_ed",
        persona="av_director",
        statement=(
            "What we keep hearing is teams are walking room to room to manage "
            "encoders, and that doesn't scale as you add buildings."
        ),
        pain_anchor="unscalable_room_walks",
        channel="both",
        icp_score=90,
    ),
    ProblemStatement(
        vertical="higher_ed",
        persona="av_director",
        statement=(
            "The other thing that comes up is recordings aren't making it into "
            "the LMS reliably. Teams end up as a help desk for upload failures "
            "every semester."
        ),
        pain_anchor="lms_upload_failures",
        channel="both",
        icp_score=90,
    ),
    ProblemStatement(
        vertical="higher_ed",
        persona="av_director",
        statement=(
            "A lot of schools are still encoding on classroom PCs. When that PC "
            "crashes mid-lecture, the recording is gone. No backup, no recovery."
        ),
        pain_anchor="classroom_pc_crash_data_loss",
        channel="both",
        icp_score=90,
    ),
    # IT Director / CIO  (mapped to law_firm_it by alias table)
    ProblemStatement(
        vertical="higher_ed",
        persona="law_firm_it",
        statement=(
            "IT directors we talk to are managing a host of AV vendors across "
            "campus. Every building has a different capture system, and your "
            "team is expected to support all of them."
        ),
        pain_anchor="vendor_fragmentation",
        channel="both",
        icp_score=90,
    ),
    ProblemStatement(
        vertical="higher_ed",
        persona="law_firm_it",
        statement=(
            "What keeps coming up is budget pressure to consolidate. The "
            "provost wants lecture capture in 200 rooms, but IT still has "
            "15-year-old encoders in half of them."
        ),
        pain_anchor="capture_coverage_gap",
        channel="both",
        icp_score=90,
    ),
    ProblemStatement(
        vertical="higher_ed",
        persona="law_firm_it",
        statement=(
            "The network security piece is real. Teams need AV gear that fits "
            "inside the VLAN architecture, supports 802.1X, and doesn't require "
            "firewall exceptions that keep you up at night."
        ),
        pain_anchor="network_security_compliance",
        channel="both",
        icp_score=90,
    ),
    ProblemStatement(
        vertical="higher_ed",
        persona="law_firm_it",
        statement=(
            "CIOs tell us they have no visibility into which rooms are actually "
            "recording and which aren't. There's no dashboard, so problems show "
            "up as complaints, not alerts."
        ),
        pain_anchor="no_room_dashboard",
        channel="both",
        icp_score=90,
    ),
    # Ed Tech Manager
    ProblemStatement(
        vertical="higher_ed",
        persona="edtech_manager",
        statement=(
            "Ed tech managers tell us they're stuck between faculty who won't "
            "learn new tools and IT who won't support the old ones. Most folks "
            "we talk to need capture that works with zero training."
        ),
        pain_anchor="zero_training_capture",
        channel="both",
        icp_score=90,
    ),
    ProblemStatement(
        vertical="higher_ed",
        persona="edtech_manager",
        statement=(
            "The LMS integration is make-or-break. When the encoder layer "
            "feeding your LMS drops files, faculty stop recording and "
            "students lose access to material they're entitled to."
        ),
        pain_anchor="lms_autopublish_break",
        channel="both",
        icp_score=90,
    ),
    ProblemStatement(
        vertical="higher_ed",
        persona="edtech_manager",
        statement=(
            "What we hear is teams are spending half their week troubleshooting "
            "recording failures instead of building curriculum. The technology "
            "should be invisible, not a second job."
        ),
        pain_anchor="curriculum_time_lost_to_av",
        channel="both",
        icp_score=90,
    ),
    ProblemStatement(
        vertical="higher_ed",
        persona="edtech_manager",
        statement=(
            "Nursing and sim labs need multi-camera recording with reliable "
            "failover. One dropped session means a student misses a clinical "
            "competency review they can't redo."
        ),
        pain_anchor="sim_lab_failover_required",
        channel="both",
        icp_score=90,
    ),
    # -----------------------------------------------------------------
    # COURTS / LEGAL (ICP 85)
    # -----------------------------------------------------------------
    # Court Administrator / IT Director
    ProblemStatement(
        vertical="legal",
        persona="court_admin",
        statement=(
            "A lot of courts we work with were failing to capture the complete "
            "record in overflow rooms and remote hearings. That creates real "
            "legal exposure."
        ),
        pain_anchor="incomplete_record_legal_exposure",
        channel="both",
        icp_score=85,
    ),
    ProblemStatement(
        vertical="legal",
        persona="court_admin",
        statement=(
            "What we hear from court IT is their software-based recording drops "
            "frames during proceedings. A gap in the record is potential grounds "
            "for appeal."
        ),
        pain_anchor="dropped_frames_appeal_grounds",
        channel="both",
        icp_score=85,
    ),
    ProblemStatement(
        vertical="legal",
        persona="court_admin",
        statement=(
            "Courts capturing only one angle are missing visual context that "
            "attorneys and transcriptionists need. Witness reactions, evidence "
            "displays — none of that shows up in a wide shot."
        ),
        pain_anchor="single_angle_missing_context",
        channel="both",
        icp_score=85,
    ),
    ProblemStatement(
        vertical="legal",
        persona="court_admin",
        statement=(
            "Courts doing remote hearings tell us unreliable video is causing "
            "reschedules that pile onto an already brutal backlog."
        ),
        pain_anchor="remote_hearing_reschedule_backlog",
        channel="both",
        icp_score=85,
    ),
    # Multimedia Services Director (→ production_director)
    ProblemStatement(
        vertical="legal",
        persona="production_director",
        statement=(
            "Legal education providers tell us they need to stream CLE seminars "
            "to thousands of attorneys simultaneously with zero downtime. One "
            "dropped stream means lost compliance hours for every attendee."
        ),
        pain_anchor="cle_zero_downtime",
        channel="both",
        icp_score=85,
    ),
    ProblemStatement(
        vertical="legal",
        persona="production_director",
        statement=(
            "What we hear is teams are managing multi-room productions for "
            "legal conferences — breakout rooms, plenaries, hybrid attendees — "
            "and every room is a separate headache."
        ),
        pain_anchor="multi_room_legal_conference",
        channel="both",
        icp_score=85,
    ),
    ProblemStatement(
        vertical="legal",
        persona="production_director",
        statement=(
            "The archival requirement is non-negotiable. Every session needs to "
            "be recorded, encoded, and published to the on-demand library "
            "within hours. Manual workflows can't keep that pace."
        ),
        pain_anchor="legal_archive_velocity",
        channel="both",
        icp_score=85,
    ),
    # Legislative IT / Broadcast Operations Director (→ law_firm_it)
    ProblemStatement(
        vertical="legal",
        persona="law_firm_it",
        statement=(
            "Legislative IT teams tell us they're broadcasting floor sessions "
            "and committee hearings to public access and livestream "
            "simultaneously. Downtime during session is a transparency violation."
        ),
        pain_anchor="legislative_transparency_downtime",
        channel="both",
        icp_score=85,
    ),
    ProblemStatement(
        vertical="legal",
        persona="law_firm_it",
        statement=(
            "What we hear is most infrastructure was built for one camera, one "
            "stream, ten years ago. Now every committee room needs multi-camera "
            "switching, captioning, and archival in the same workflow."
        ),
        pain_anchor="legacy_legislative_infra",
        channel="both",
        icp_score=85,
    ),
    ProblemStatement(
        vertical="legal",
        persona="law_firm_it",
        statement=(
            "The procurement cycle is brutal. Eighteen months from RFP to "
            "deployment. Most need hardware that's firmware-upgradeable so it "
            "doesn't age out before it's installed."
        ),
        pain_anchor="long_procurement_aging_hardware",
        channel="both",
        icp_score=85,
    ),
    # -----------------------------------------------------------------
    # LIVE EVENTS / PRODUCTION (ICP 85)
    # -----------------------------------------------------------------
    # Production Manager / Technical Director (→ technical_director)
    ProblemStatement(
        vertical="live_events",
        persona="technical_director",
        statement=(
            "A lot of production teams we talk to are duct-taping encoding "
            "workflows together with multiple boxes and a laptop. One thing "
            "goes down mid-show and there's no failover."
        ),
        pain_anchor="ducttape_encoding_no_failover",
        channel="both",
        icp_score=85,
    ),
    ProblemStatement(
        vertical="live_events",
        persona="technical_director",
        statement=(
            "What we hear is most are burning hours on-site configuring gear "
            "for every event because nothing carries over from the last setup."
        ),
        pain_anchor="onsite_reconfig_burn",
        channel="both",
        icp_score=85,
    ),
    ProblemStatement(
        vertical="live_events",
        persona="technical_director",
        statement=(
            "Clients now expect a simultaneous livestream on top of the in-room "
            "production, and most current rigs weren't built for that without "
            "adding headcount."
        ),
        pain_anchor="livestream_addon_headcount",
        channel="both",
        icp_score=85,
    ),
    # Design Engineer / Systems Integrator (→ system_engineer)
    ProblemStatement(
        vertical="live_events",
        persona="system_engineer",
        statement=(
            "Design engineers tell us they're spec'ing systems where the client "
            "needs encoding, switching, and streaming in the same unit. The more "
            "boxes in the signal chain, the more failure points in your design."
        ),
        pain_anchor="signal_chain_failure_points",
        channel="both",
        icp_score=85,
    ),
    ProblemStatement(
        vertical="live_events",
        persona="system_engineer",
        statement=(
            "What we hear is clients are asking for NDI, SRT, and RTMP "
            "simultaneously. Most encoders do one well and hack the rest. That "
            "forces you into multi-device designs that blow the budget."
        ),
        pain_anchor="ndi_srt_rtmp_multidevice_budget",
        channel="both",
        icp_score=85,
    ),
    # Director of Event Technology (→ venue_manager)
    ProblemStatement(
        vertical="live_events",
        persona="venue_manager",
        statement=(
            "Venue AV directors tell us they're running 20-plus events a week "
            "across multiple ballrooms. Every client wants a different streaming "
            "destination, and teams are manually configuring encoders for each one."
        ),
        pain_anchor="venue_per_client_reconfig",
        channel="both",
        icp_score=85,
    ),
    ProblemStatement(
        vertical="live_events",
        persona="venue_manager",
        statement=(
            "What keeps coming up is labor cost. Staffing a tech per room for "
            "live events when the encoding and switching should be automated "
            "enough for one tech to cover three rooms."
        ),
        pain_anchor="one_tech_three_rooms",
        channel="both",
        icp_score=85,
    ),
    ProblemStatement(
        vertical="live_events",
        persona="venue_manager",
        statement=(
            "Venue teams say gear needs to be rental-proof. Road-ready, quick "
            "to deploy, and impossible for a client's team to misconfigure. "
            "Consumer-grade encoders don't survive the banquet circuit."
        ),
        pain_anchor="rental_proof_gear",
        channel="both",
        icp_score=85,
    ),
    # AV Reseller / Account Development Manager (→ av_integrator)
    ProblemStatement(
        vertical="live_events",
        persona="av_integrator",
        statement=(
            "Resellers tell us they need demo-ready solutions they can show a "
            "client in 15 minutes. If it takes a full-day install to prove "
            "value, you've already lost the deal to a software-only competitor."
        ),
        pain_anchor="demo_15min_or_lose",
        channel="both",
        icp_score=85,
    ),
]


# Stop-words excluded from keyword-overlap scoring. Trimmed to general English
# function words plus a few transcript-prevalent fillers ("yeah", "okay")
# that would otherwise inflate every score.
_SCORING_STOPWORDS: frozenset[str] = frozenset(
    """
    a an and are as at be been being by for from has have had he her him his
    i in is it its me my no not of on or our she so than that the their them
    they this to was we were what when where which who will with you your
    yeah okay just like really kind of sort um uh got going get
    """.split()
)


def _tokenize_for_scoring(text: str) -> set[str]:
    """Lowercase, strip punctuation, split, drop stop-words and short tokens."""
    import re

    tokens = re.findall(r"[A-Za-z][A-Za-z0-9'-]+", text.lower())
    return {t for t in tokens if len(t) > 2 and t not in _SCORING_STOPWORDS}


def match_statements_to_transcript(
    transcript: str,
    vertical: str,
    persona: str,
    limit: int | None = None,
) -> list[tuple[ProblemStatement, float]]:
    """Score problem statements by keyword overlap with the transcript.

    Returns ``[(statement, score), ...]`` sorted descending by score. Score is
    the count of unique non-stop-word tokens that appear in BOTH the statement
    and the transcript (cheap, deterministic, good enough for prompt grounding).

    Filters to records matching ``vertical`` + ``persona`` first. Empty list
    when nothing matches the filter.
    """
    candidates = get_problem_statements(vertical=vertical, persona=persona)
    if not candidates:
        return []

    transcript_tokens = _tokenize_for_scoring(transcript)
    scored: list[tuple[ProblemStatement, float]] = []
    for ps in candidates:
        statement_tokens = _tokenize_for_scoring(ps.statement)
        overlap = transcript_tokens & statement_tokens
        scored.append((ps, float(len(overlap))))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    if limit is not None:
        scored = scored[:limit]
    return scored


def get_problem_statements(
    vertical: str,
    persona: str,
    channel: str = "both",
    limit: int | None = None,
) -> list[ProblemStatement]:
    """Return problem statements matching the (vertical, persona) filter.

    ``channel='both'`` matches every record. Any other channel value matches
    records whose channel equals the requested channel OR is ``'both'`` (a
    "both" statement is by definition usable on either channel).

    Returns an empty list if nothing matches — callers should not depend on
    exceptions for unknown verticals/personas.
    """
    matches = [
        ps
        for ps in PROBLEM_STATEMENTS
        if ps.vertical == vertical and ps.persona == persona
    ]
    if channel != "both":
        matches = [ps for ps in matches if ps.channel in (channel, "both")]
    if limit is not None:
        matches = matches[:limit]
    return matches

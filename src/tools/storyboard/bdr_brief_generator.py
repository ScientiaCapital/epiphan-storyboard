"""BDR Call Brief generator — deterministic core for Phase 1.

The brief is the structured artifact a BDR consumes after a discovery call
or a self-serve survey submission. This module ships the deterministic
parts (persona detection, problem-statement matching, Forces summarization,
NBA selection, NSTTD email assembly) so the brief is useful even when the
LLM-augmented pieces (Challenger reframe, calibrated-question generation)
are unavailable or skipped to save cost.

LLM augmentation can layer on top by extending ``generate_brief_from_*``
to accept an optional ``challenger_reframe`` and ``calibrated_questions``
override produced by the meeting-recap pipeline.

This module never makes a network call directly. Its job is to assemble
already-known signals into a Pydantic ``BDRCallBrief``.
"""

from __future__ import annotations

import logging
import re
from typing import Final

from src.storyboard.schemas import (
    BDRCallBrief,
    BuyerProfile,
    ForcesOfProgress,
)
from src.tools.storyboard.problem_statements import (
    ICP_SCORES,
    get_problem_statements,
    match_statements_to_transcript,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Calibrated-question filter — NSTTD discipline
# =============================================================================


_CALIBRATED_OPENERS: Final[tuple[str, ...]] = ("what", "how")


def filter_calibrated_questions(questions: list[str]) -> list[str]:
    """Keep only NSTTD-style calibrated questions.

    Rules:
      * Must start with What or How (case-insensitive)
      * Must not contain "Why" anywhere (it triggers defensiveness per NSTTD)
      * Must end with "?" (callers may add this)
      * Must not be a yes/no question (no "Did", "Have", "Do", etc.)

    Returns the filtered subset in original order.
    """
    out: list[str] = []
    for raw in questions:
        q = raw.strip()
        if not q:
            continue
        first = q.split()[0].rstrip(".,;:?").lower() if q.split() else ""
        if first not in _CALIBRATED_OPENERS:
            continue
        if re.search(r"\bwhy\b", q.lower()):
            continue
        out.append(q if q.endswith("?") else q + "?")
    return out


# =============================================================================
# Next-best-action selection
# =============================================================================


def _force_strength(forces: ForcesOfProgress) -> int:
    """Coarse signal strength: count non-empty Forces fields."""
    return sum(
        1
        for v in (forces.push, forces.pull, forces.anxiety, forces.habit)
        if v and v.strip()
    )


def select_next_best_action(
    forces: ForcesOfProgress,
    icp_score: int,
    extraction_confidence: float,
) -> str:
    """Pick the recommended next move based on signal strength + ICP fit.

    Decision matrix:
        ICP < 30                    → disqualify (poor fit)
        Strong push + ICP ≥ 70      → schedule_15min (qualified, motivated)
        Strong push + ICP ≥ 40      → schedule_15min (qualified)
        Forces ≥ 3 / 4              → schedule_15min (rich signal)
        ICP ≥ 80 + low confidence   → schedule_15min (high-fit, get a real call)
        Otherwise                   → send_problem_email (nurture)
    """
    if icp_score < 30:
        return "disqualify"

    has_strong_push = bool(forces.push and len(forces.push.split()) >= 5)
    if has_strong_push and icp_score >= 40:
        return "schedule_15min"

    if _force_strength(forces) >= 3:
        return "schedule_15min"

    if icp_score >= 80 and extraction_confidence < 0.5:
        # High-fit prospect with thin extraction — get a live discovery call.
        return "schedule_15min"

    return "send_problem_email"


# =============================================================================
# JTBD job statement template
# =============================================================================


_JOB_STATEMENT_BY_PERSONA: Final[dict[str, str]] = {
    "av_director": (
        "When managing AV across many rooms, I want to ensure capture "
        "reliability scales without adding staff, so I can deliver "
        "recordings on demand without becoming a help desk."
    ),
    "law_firm_it": (
        "When AV is one line item in a much larger IT portfolio, I want a "
        "stack that fits inside our network architecture and security "
        "posture, so I can support faculty without adding firewall "
        "exceptions or vendor sprawl."
    ),
    "edtech_manager": (
        "When faculty rely on the LMS for every recorded lecture, I want "
        "the capture-to-LMS pipeline to be invisible and reliable, so "
        "instructors can teach instead of troubleshoot."
    ),
    "court_admin": (
        "When the official record of proceedings is the deliverable, I "
        "want continuous, multi-angle capture that meets evidentiary "
        "standards, so a gap in the record never becomes grounds for "
        "appeal."
    ),
    "production_director": (
        "When delivering broadcast-quality CLE or legal events, I want "
        "stream and recording to land within hours of the session, so "
        "compliance hours and on-demand archives stay current."
    ),
    "technical_director": (
        "When running multi-source live events with tight timelines, I "
        "want encode/stream/record consolidated with reliable failover, "
        "so a single mid-show failure doesn't end the broadcast."
    ),
    "system_engineer": (
        "When designing systems that the client will own for years, I "
        "want fewer boxes in the signal chain and a single control "
        "surface, so post-install support stays profitable."
    ),
    "venue_manager": (
        "When running 20+ events a week across multiple ballrooms, I "
        "want gear that's rental-proof and operable by one tech across "
        "rooms, so labor scales with revenue, not with bookings."
    ),
    "av_integrator": (
        "When pitching a turnkey solution under tight competitive "
        "pressure, I want demo-ready hardware that proves value in 15 "
        "minutes, so I close instead of losing to a software-only "
        "alternative."
    ),
}


def _job_statement_for(persona: str, vertical: str) -> str:
    """Return the persona-keyed JTBD job statement template."""
    return _JOB_STATEMENT_BY_PERSONA.get(
        persona,
        (
            f"When evaluating capture and streaming infrastructure for "
            f"{vertical}, I want a solution that scales with workload "
            f"without adding staff, so I can deliver consistent "
            f"outcomes."
        ),
    )


# =============================================================================
# Challenger reframe — template-driven for Phase 1
# =============================================================================


_CHALLENGER_REFRAME_BY_PERSONA: Final[dict[str, str]] = {
    "av_director": (
        "Most AV teams assume their biggest cost is hardware. What we "
        "consistently hear at scale is that the bigger cost is staff "
        "time troubleshooting software encoders on classroom PCs. The "
        "fix isn't a bigger team — it's removing the PC layer entirely "
        "with appliance-based capture that survives OS updates, "
        "antivirus, and reboots."
    ),
    "law_firm_it": (
        "Most IT leaders assume AV consolidation means picking one "
        "vendor for everything. What actually moves the needle is "
        "picking gear that fits cleanly into your existing VLAN, "
        "802.1X, and SIEM posture so AV stops being the network's "
        "weakest link."
    ),
    "edtech_manager": (
        "Most ed-tech teams treat capture-to-LMS as a pipeline they own. "
        "The pattern at scale: the failure point isn't the LMS — it's "
        "the encoder layer feeding it. Replace the encoder with a "
        "hardware appliance and the LMS pipeline goes from "
        "high-touch to invisible."
    ),
    "court_admin": (
        "Most court IT teams treat 'reliable enough' video as the goal. "
        "The pattern: a software-encoder gap on one hearing becomes a "
        "transcribed appeal six months later. The solution isn't "
        "better software — it's continuous hardware-based capture with "
        "redundant recording paths."
    ),
    "production_director": (
        "Most legal-content production teams scale by adding more "
        "operators per room. The leverage move is fewer boxes per "
        "room — encode, stream, and record on one appliance with "
        "fleet-wide management — so one tech runs three rooms."
    ),
    "technical_director": (
        "Most production teams duct-tape encoding with multiple boxes "
        "and a laptop. One thing goes down mid-show and there's no "
        "failover. The new way: a 1-RU appliance that does encode + "
        "stream + record with internal redundancy."
    ),
    "system_engineer": (
        "Most integrators design around vendor specialization — one box "
        "per protocol. The pattern that wins: a single appliance that "
        "speaks NDI, SRT, and RTMP natively, so your design has fewer "
        "failure points and fits a tighter rack."
    ),
    "venue_manager": (
        "Most venues budget AV as a cost center. The leverage move: "
        "encoders that survive the road, deploy in 30 minutes, and "
        "let one tech monitor three ballrooms — labor scales with "
        "revenue, not with bookings."
    ),
    "av_integrator": (
        "Most resellers compete on price. The win: hardware demo-ready "
        "in 15 minutes, recurring fleet-management revenue, and "
        "channel protection that keeps your install profitable for "
        "years."
    ),
}


def _challenger_reframe_for(persona: str) -> str:
    """Return the persona-keyed Challenger reframe template."""
    return _CHALLENGER_REFRAME_BY_PERSONA.get(
        persona,
        (
            "The pattern we see at scale: the most expensive line item "
            "isn't the hardware — it's the staff time spent "
            "troubleshooting workarounds. The fix is consolidating "
            "into appliance-based capture so the workflow becomes "
            "invisible."
        ),
    )


# =============================================================================
# Calibrated questions — Phase 1 templates
# =============================================================================


_CALIBRATED_BY_PERSONA: Final[dict[str, list[str]]] = {
    "av_director": [
        "What does success look like for capture across your portfolio in 12 months?",
        "How do you currently know when a room's recording fails before a complaint comes in?",
        "What would have to be true for one tech to manage twice as many rooms?",
        "How does your team prioritize capture issues against the rest of the AV ticket queue?",
        "What's your timeline for replacing or augmenting the current capture stack?",
    ],
    "law_firm_it": [
        "What does AV need to satisfy on your network to pass review?",
        "How do you typically evaluate AV vendors for security posture?",
        "What would have to be true for AV to stop generating firewall exceptions?",
        "How do you currently discover when a room's capture is down?",
        "What's the procurement cycle for AV upgrades at your institution?",
    ],
    "edtech_manager": [
        "What's the current week-by-week impact of recording failures on faculty?",
        "How do you measure whether the LMS pipeline is healthy?",
        "What would have to be true for the recording experience to be invisible to faculty?",
        "How does your team currently handle a failed-recording escalation?",
        "What's your roadmap for moving from software encoders on classroom PCs?",
    ],
    "court_admin": [
        "What does a complete record of a proceeding look like for your court?",
        "How does your team currently know if a hearing's capture had a gap?",
        "What would have to be true for remote testimony to meet your evidentiary standard?",
        "How does retention and chain-of-custody flow into your records system today?",
        "What's the procurement vehicle and timeline for capture upgrades?",
    ],
    "technical_director": [
        "What's the most common point of failure mid-show for your team?",
        "How long does it take one technician to be show-ready at a new venue?",
        "What would have to be true to consolidate encode/stream/record into one box?",
        "How does your team currently detect a stream drop before the client does?",
        "What's the next investment your team is considering for fly-kit gear?",
    ],
}


def _calibrated_questions_for(persona: str) -> list[str]:
    """Return persona-keyed calibrated questions, falling back to generics."""
    return _CALIBRATED_BY_PERSONA.get(
        persona,
        [
            "What does success look like for this initiative in the next 12 months?",
            "How does this fit into your broader priorities?",
            "What would have to be true for you to feel confident moving forward?",
            "How do you typically evaluate vendors for projects like this?",
            "What's your timeline and what's driving it?",
        ],
    )


# =============================================================================
# NSTTD email — accusation audit + no-oriented CTA
# =============================================================================


def build_nsttd_email(
    persona: str,
    vertical: str,
    top_pain_phrase: str,
    prospect_first_name: str | None = None,
) -> str:
    """Build a ≤100-word NSTTD email with accusation audit + no-CTA.

    The email opens by front-running the most likely negative reaction
    (accusation audit), names the persona's top pain in their own words,
    and ends with a no-oriented CTA ("would it be ridiculous to..." or
    "have you given up on...").
    """
    name = prospect_first_name or "there"
    return (
        f"Hi {name},\n\n"
        "You probably get pitched by AV vendors every week. Fair enough.\n\n"
        f"But the thing we keep hearing from {vertical.replace('_', ' ')} "
        f"teams is the same: {top_pain_phrase}. The fix isn't more vendors "
        "or more staff — it's consolidating the encoder layer so the "
        "workflow goes invisible.\n\n"
        "Would it be ridiculous to spend 15 minutes comparing notes on "
        "what other teams are doing?\n\n"
        "Either way, no worries.\n\n"
        "Tim"
    )


# =============================================================================
# Persona detection from survey responses
# =============================================================================


def _persona_from_role_answer(role_answer: str | None) -> str | None:
    """Map a survey role-question answer to an AudiencePersona enum value.

    Reuses the doc-role alias table from problem_statements when possible
    and falls back to keyword matching for free-form roles.
    """
    if not role_answer:
        return None
    from src.tools.storyboard.problem_statements import normalize_doc_persona

    direct = normalize_doc_persona(role_answer)
    if direct:
        return direct

    lower = role_answer.lower()
    if "av director" in lower or "av architecture" in lower:
        return "av_director"
    if "production manager" in lower or "technical director" in lower:
        return "technical_director"
    if "court admin" in lower:
        return "court_admin"
    if "venue" in lower:
        return "venue_manager"
    if "design engineer" in lower or "systems integrator" in lower:
        return "system_engineer"
    return None


# =============================================================================
# Public entry points
# =============================================================================


def generate_brief_from_transcript(
    transcript: str,
    vertical: str,
    persona: str,
    *,
    forces: ForcesOfProgress | None = None,
    extraction_confidence: float = 0.7,
    prospect_first_name: str | None = None,
) -> BDRCallBrief:
    """Generate a BDRCallBrief from a pasted transcript + known vertical/persona.

    Deterministic Phase 1 implementation:
      * Match top 3 problem statements against the transcript
      * Use provided ``forces`` (typically from meeting-recap LLM extraction)
        or default to empty Forces
      * Pull the persona-keyed JTBD job statement, Challenger reframe,
        and calibrated-question template
      * Assemble a ≤100-word NSTTD email anchored on the top problem
      * Pick the next-best-action from the decision matrix
    """
    forces_used = forces or ForcesOfProgress()
    icp_score = ICP_SCORES.get(vertical, 50)

    matched = match_statements_to_transcript(
        transcript=transcript,
        vertical=vertical,
        persona=persona,
        limit=3,
    )
    top_statements = [ps.statement for ps, _score in matched if _score > 0]
    if not top_statements:
        # Fall back to the first 3 verbatim records for this persona
        top_statements = [
            ps.statement
            for ps in get_problem_statements(
                vertical=vertical, persona=persona, limit=3
            )
        ]

    top_pain_phrase = _extract_pain_phrase(top_statements)
    nsttd_email = build_nsttd_email(
        persona=persona,
        vertical=vertical,
        top_pain_phrase=top_pain_phrase,
        prospect_first_name=prospect_first_name,
    )

    nba = select_next_best_action(
        forces=forces_used,
        icp_score=icp_score,
        extraction_confidence=extraction_confidence,
    )

    return BDRCallBrief(
        detected_persona=persona,
        detected_vertical=vertical,
        icp_score=icp_score,
        job_statement=_job_statement_for(persona, vertical),
        forces_of_progress=forces_used,
        top_problem_statements=top_statements,
        challenger_reframe=_challenger_reframe_for(persona),
        calibrated_questions=filter_calibrated_questions(
            _calibrated_questions_for(persona)
        ),
        nsttd_email=nsttd_email,
        next_best_action=nba,
        confidence=extraction_confidence,
    )


def generate_brief_from_profile(
    profile: BuyerProfile,
    *,
    extraction_confidence: float = 0.6,
    prospect_first_name: str | None = None,
) -> BDRCallBrief:
    """Generate a BDRCallBrief from a survey-only BuyerProfile.

    No transcript means we fall back to the verbatim Phase-1 problem
    statements for the (vertical, persona) combo rather than scoring
    against the transcript. ``extraction_confidence`` defaults lower for
    survey-only since we have less raw text to ground on.
    """
    icp_score = ICP_SCORES.get(profile.detected_vertical, 50)
    statements = [
        ps.statement
        for ps in get_problem_statements(
            vertical=profile.detected_vertical,
            persona=profile.detected_persona,
            limit=3,
        )
    ]

    top_pain_phrase = _extract_pain_phrase(statements)
    nsttd_email = build_nsttd_email(
        persona=profile.detected_persona,
        vertical=profile.detected_vertical,
        top_pain_phrase=top_pain_phrase,
        prospect_first_name=prospect_first_name,
    )

    nba = select_next_best_action(
        forces=profile.forces_of_progress,
        icp_score=icp_score,
        extraction_confidence=extraction_confidence,
    )

    return BDRCallBrief(
        detected_persona=profile.detected_persona,
        detected_vertical=profile.detected_vertical,
        icp_score=icp_score,
        job_statement=_job_statement_for(
            profile.detected_persona, profile.detected_vertical
        ),
        forces_of_progress=profile.forces_of_progress,
        top_problem_statements=statements,
        challenger_reframe=_challenger_reframe_for(profile.detected_persona),
        calibrated_questions=filter_calibrated_questions(
            _calibrated_questions_for(profile.detected_persona)
        ),
        nsttd_email=nsttd_email,
        next_best_action=nba,
        confidence=extraction_confidence,
    )


def _extract_pain_phrase(statements: list[str]) -> str:
    """Pick the most useful 3–8-word pain phrase from the top statement.

    Looks for noun-phrase chunks after triggers like 'rooms', 'captures',
    'recording'. Falls back to the first 12 words of the first statement.
    """
    if not statements:
        return "recording reliability falling short of what your team needs"
    first = statements[0]
    # Try to find a "rooms going X" / "Y fails" / "Z is broken" chunk first
    for trigger in (
        r"(rooms (?:going|with) [^.]+?)[\.\,]",
        r"((?:recordings? |encoder |upload |the LMS )[^.]+?(?:fails?|breaks?|crashes?))[\.\,]",
        r"((?:burning|spending) [^.]+? (?:hours?|week))",
        r"(no (?:failover|backup|recovery|dashboard))",
    ):
        m = re.search(trigger, first, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return " ".join(first.split()[:12])

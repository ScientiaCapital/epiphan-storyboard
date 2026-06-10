"""Extractive transcript compaction — replaces 32 K hard truncation.

The current prompt-builder pipeline truncates transcripts at 32 000 chars
(``prompt_builders.py:_build_transcript_prompt``). Long calls (>30 min) lose
the back third where Forces of Progress (anxiety/habit) and decisions live.
This module provides extractive summarization instead: segment by speaker
turn, score each turn for JTBD-relevant signal, keep top-N turns plus the
first and last 10 % of the call.

Strategy:
1. Split the transcript into speaker turns (``Speaker 1:`` / ``Tim Kipper:``
   patterns; also bare paragraph breaks as fallback).
2. Score each turn (``score_turn``): pain phrases, vendor mentions,
   time/budget/authority cues, workaround language.
3. Always retain the first ``edge_pct`` and last ``edge_pct`` of total chars.
4. Greedy-include remaining turns by score, in original chronological order,
   until the running total reaches ``target_chars``.
5. ``key_moments`` is a tighter (≤8 K) subset of just the highest-scored
   turns, intended as the first prompt pass.
6. If the algorithm cannot reduce the input by ≥20 %, fall back to plain
   truncation and set ``fallback_used=True`` — better to over-include than
   to mangle a transcript that's already information-dense.

This module is read-only: it never touches the network and never calls an
LLM. All scoring is deterministic regex/keyword counting, which keeps it
cheap to run on every request.
"""

from __future__ import annotations

import logging
import re
from typing import Final

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public schema
# ---------------------------------------------------------------------------


class CompactedTranscript(BaseModel):
    """Result of running ``compact_transcript`` on a raw transcript string."""

    key_moments: str = Field(
        description=(
            "≤8 K-char subset of the highest-scored turns. Fed to the "
            "extractor first so the model sees the JTBD-rich content before "
            "the full context."
        )
    )
    full_context: str = Field(
        description=(
            "≤target_chars compaction preserving chronological order. "
            "Always includes the first/last edge_pct of the call."
        )
    )
    compaction_ratio: float = Field(
        ge=0.0,
        le=1.0,
        description="len(full_context) / len(original). 1.0 means no reduction.",
    )
    fallback_used: bool = Field(
        default=False,
        description=(
            "True when extractive summarization couldn't hit the ≥20 % "
            "reduction threshold and we fell back to slice truncation."
        ),
    )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


# Pain-language phrases the BDR team has validated as high-signal in real
# calls. Sourced from problem_statements.py + the Live Events workflow doc.
_PAIN_PHRASES: Final[tuple[str, ...]] = (
    "we had to",
    "we ended up",
    "we wound up",
    "we keep",
    "honestly",
    "the biggest pain",
    "burning hours",
    "doesn't scale",
    "doesnt scale",
    "drops frames",
    "drop frames",
    "fails",
    "failed",
    "crashes",
    "crashed",
    "broken",
    "workaround",
    "work around",
    "duct-tape",
    "duct tape",
    "ducttape",
    "frankenstack",
    "frankenstein",
    "not designed for",
    "not built for",
    "in addition to",
    "manually configuring",
    "every single",
    "every time",
    "no failover",
    "no backup",
    "no recovery",
    "single point of failure",
    "fall back",
    "rip and replace",
)

# Vendor/product names that, when mentioned, indicate the prospect is
# describing their actual stack — high context value for grounding.
_VENDOR_TOKENS: Final[tuple[str, ...]] = (
    "panopto",
    "kaltura",
    "echo360",
    "yuja",
    "canvas",
    "blackboard",
    "moodle",
    "zoom",
    "teams",
    "webex",
    "obs",
    "vmix",
    "wirecast",
    "tricaster",
    "atem",
    "blackmagic",
    "crestron",
    "extron",
    "vaddio",
    "matrox",
    "magewell",
    "teradek",
    "liveu",
    "aja",
    "helo",
    "kiloview",
    "birddog",
    "ndi",
    "srt",
    "rtmp",
    "dante",
    "epiphan",
    "pearl",
    "ec20",
)

# Authority / budget / timeline cues — MEDDIC signal.
_MEDDIC_CUES: Final[tuple[str, ...]] = (
    "budget",
    "fiscal year",
    "this quarter",
    "next quarter",
    "by end of",
    "approve",
    "approval",
    "sign off",
    "signed off",
    "procurement",
    "rfp",
    "decision",
    "stakeholder",
    "champion",
    "boss",
    "cto",
    "cio",
    "vp",
    "director",
)


def score_turn(text: str) -> int:
    """Return an integer signal score for one speaker turn.

    Higher = more JTBD-relevant. Score is the sum of:
      * 3 points per pain phrase match
      * 2 points per vendor/product token match
      * 1 point per MEDDIC cue match

    Punctuation-insensitive and case-insensitive. Returns 0 for empty turns
    or pure filler.
    """
    if not text:
        return 0
    lower = text.lower()
    score = 0
    for phrase in _PAIN_PHRASES:
        if phrase in lower:
            score += 3
    for vendor in _VENDOR_TOKENS:
        # Word-boundary check so "ndi" doesn't match "indicate".
        if re.search(rf"\b{re.escape(vendor)}\b", lower):
            score += 2
    for cue in _MEDDIC_CUES:
        if cue in lower:
            score += 1
    return score


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------


# A "speaker turn" begins at a line that looks like ``Name:`` at the start.
# Falls back to paragraph splits when the transcript has no speaker labels.
_SPEAKER_RE: Final[re.Pattern[str]] = re.compile(
    r"^([A-Z][\w .'-]{0,40}):\s", re.MULTILINE
)


def _segment_into_turns(text: str) -> list[str]:
    """Split a transcript into speaker turns.

    Uses ``Speaker N:`` / ``First Last:`` patterns. Falls back to splitting
    by blank-line paragraphs when no speaker labels are detected.
    """
    matches = list(_SPEAKER_RE.finditer(text))
    if len(matches) >= 2:
        turns: list[str] = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            turn = text[start:end].strip()
            if turn:
                turns.append(turn)
        return turns

    # Fallback — paragraph segmentation.
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return paragraphs if paragraphs else [text.strip()]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def compact_transcript(
    text: str,
    target_chars: int = 28_000,
    *,
    edge_pct: float = 0.10,
    key_moments_chars: int = 8_000,
    fallback_threshold: float = 0.20,
) -> CompactedTranscript:
    """Compact ``text`` to ≤ ``target_chars`` using extractive summarization.

    Args:
        text: Raw transcript string.
        target_chars: Upper bound on the returned ``full_context``.
        edge_pct: Fraction of the original to retain unconditionally at the
            head and tail of the call (default 10 %).
        key_moments_chars: Upper bound on ``key_moments``.
        fallback_threshold: Minimum reduction ratio required to consider the
            extractive pass useful. If we can't hit it, fall back to
            truncation.

    Returns:
        ``CompactedTranscript`` with the compacted output.

    The function never raises on bad input — empty transcripts return an
    empty result and a 1.0 ratio (nothing to compact).
    """
    original_len = len(text)
    if original_len == 0:
        return CompactedTranscript(
            key_moments="", full_context="", compaction_ratio=1.0
        )

    # Already under target — pass through.
    if original_len <= target_chars:
        return CompactedTranscript(
            key_moments=text[:key_moments_chars],
            full_context=text,
            compaction_ratio=1.0,
        )

    turns = _segment_into_turns(text)
    if len(turns) <= 2:
        # Can't segment meaningfully (no speaker labels, no paragraph breaks)
        # — fall back to truncation. Log it: the model is getting a plain
        # head-slice of a long transcript, so the tail is being dropped.
        logger.warning(
            "[COMPACT] Transcript (%d chars) segmented into %d turn(s); "
            "cannot compact extractively, falling back to head-slice "
            "truncation — call tail will be dropped.",
            original_len,
            len(turns),
        )
        return _truncate_fallback(text, target_chars, key_moments_chars)

    # Edge budget — always retain head + tail for context. Capped at a
    # fraction of target_chars so edges never crowd out middle highlights
    # when the original is many multiples of the target.
    edge_budget_per_side = min(
        max(int(original_len * edge_pct), 1),
        max(int(target_chars * edge_pct * 2), 1),
    )
    head_turns: list[tuple[int, str]] = []
    tail_turns: list[tuple[int, str]] = []

    head_consumed = 0
    for idx, turn in enumerate(turns):
        if head_consumed >= edge_budget_per_side:
            break
        head_turns.append((idx, turn))
        head_consumed += len(turn) + 1  # +1 for the joining newline

    tail_consumed = 0
    for idx in range(len(turns) - 1, -1, -1):
        if tail_consumed >= edge_budget_per_side:
            break
        if any(idx == i for i, _ in head_turns):
            break  # don't double-count when head already covers tail
        tail_turns.append((idx, turns[idx]))
        tail_consumed += len(turns[idx]) + 1
    tail_turns.reverse()

    head_idxs = {i for i, _ in head_turns}
    tail_idxs = {i for i, _ in tail_turns}
    forced_idxs = head_idxs | tail_idxs

    # Score the remaining middle turns.
    middle_scored: list[tuple[int, int, str]] = []
    for idx, turn in enumerate(turns):
        if idx in forced_idxs:
            continue
        middle_scored.append((idx, score_turn(turn), turn))

    middle_scored.sort(key=lambda t: t[1], reverse=True)

    # Greedy fill.
    forced_chars = sum(len(turns[i]) + 1 for i in forced_idxs)
    selected_idxs: set[int] = set(forced_idxs)
    running = forced_chars

    for idx, _score, turn in middle_scored:
        cost = len(turn) + 1
        if running + cost > target_chars:
            continue
        selected_idxs.add(idx)
        running += cost

    # Reassemble in chronological order.
    full_context = "\n".join(turns[i] for i in sorted(selected_idxs))

    # Threshold check — if we couldn't meaningfully reduce, fall back.
    achieved_ratio = len(full_context) / max(original_len, 1)
    if (1.0 - achieved_ratio) < fallback_threshold:
        logger.warning(
            "[COMPACT] Extractive pass reduced transcript by only %.0f%% "
            "(<%.0f%% threshold); falling back to head-slice truncation. "
            "Input is information-dense (%d chars).",
            (1.0 - achieved_ratio) * 100,
            fallback_threshold * 100,
            original_len,
        )
        return _truncate_fallback(text, target_chars, key_moments_chars)

    # Build key_moments from the top-scored turns across ALL selected
    # turns — including the forced head/tail ranges. High-signal content
    # often lives at call boundaries (intros set the agenda, outros mention
    # decisions/next steps), so we re-score every selected turn here rather
    # than relying on middle_scored alone.
    all_selected_scored: list[tuple[int, int, str]] = sorted(
        ((i, score_turn(turns[i]), turns[i]) for i in selected_idxs),
        key=lambda t: t[1],
        reverse=True,
    )
    km_idxs: set[int] = set()
    km_running = 0
    for idx, _score, turn in all_selected_scored:
        cost = len(turn) + 1
        if km_running + cost > key_moments_chars:
            continue
        km_idxs.add(idx)
        km_running += cost
    key_moments = "\n".join(turns[i] for i in sorted(km_idxs))

    return CompactedTranscript(
        key_moments=key_moments,
        full_context=full_context,
        compaction_ratio=achieved_ratio,
    )


def _truncate_fallback(
    text: str, target_chars: int, key_moments_chars: int
) -> CompactedTranscript:
    """Plain slice truncation when extractive summarization can't reduce."""
    truncated = text[:target_chars]
    return CompactedTranscript(
        key_moments=text[:key_moments_chars],
        full_context=truncated,
        compaction_ratio=len(truncated) / max(len(text), 1),
        fallback_used=True,
    )

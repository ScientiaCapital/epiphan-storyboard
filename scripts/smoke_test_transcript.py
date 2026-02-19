#!/usr/bin/env python3
"""
Smoke Test — TranscriptToScenariosTool End-to-End Pipeline
==========================================================

Runs the full 4-stage transcript-to-scenarios pipeline against a hardcoded
K-12 sample transcript and verifies that:

  Stage 1  EXTRACT   — Detects vertical, persona, pain points, interests
  Stage 2  MATCH     — Ranks and customizes scenarios from the library
  Stage 3  GENERATE  — Produces one storyboard PNG per matched scenario
  Stage 4  EMAIL     — Drafts a BDR follow-up email

Output PNGs are saved to output/ (created if absent).
Email draft is printed to stdout.
Timing is reported per stage.

Usage:
    python scripts/smoke_test_transcript.py
    python scripts/smoke_test_transcript.py --transcript-file path/to/file.txt
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import logging
import os
import sys
from pathlib import Path
from time import perf_counter

# ---------------------------------------------------------------------------
# Path setup — allow running from repo root without installing the package
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from src.tools.base import ToolResult  # noqa: E402
from src.tools.storyboard.transcript_to_scenarios import (  # noqa: E402
    TranscriptToScenariosTool,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hardcoded K-12 sample transcript (~500 words)
# ---------------------------------------------------------------------------
SAMPLE_TRANSCRIPT = """\
Speaker 1 (BDR — Alex, Epiphan Video): Hey Coach Miller, thanks for making \
time this afternoon. I know the spring semester just kicked off and you've \
got a lot going on over at Lincoln High.

Speaker 2 (Coach Miller, AV & Athletics Admin, Lincoln High School): Yeah, no \
problem. We've been talking about this since January. The short story is we \
want to live stream our varsity sports — football, basketball, maybe baseball \
— but everything we've tried has looked really unprofessional.

Speaker 1: Tell me more about what you've tried so far.

Speaker 2: Last fall we had a parent volunteer bring in a consumer camcorder \
on a tripod and we streamed to YouTube. The stream kept dropping, the audio \
was terrible from the crowd noise, and the picture was basically unwatchable \
on a phone screen. Parents were frustrated. Booster club was asking for their \
money back.

Speaker 1: How many home events are you looking at per year — just the main \
sports?

Speaker 2: Football is 8 home games. Basketball runs two seasons, boys and \
girls, so we're probably at 20 home games there. Then baseball and softball \
in the spring, maybe 10. So realistically 40 events, maybe more if we make \
playoffs.

Speaker 1: And who would be running the actual stream on game day?

Speaker 2: That's the other thing. We don't have a dedicated AV person. Our \
students in the media class help out, but they change every semester and \
they're 16. Whatever we get has to be dead simple — like, if it takes more \
than one button press, we're going to have problems.

Speaker 1: Totally understand. Is there a budget range you're working within?

Speaker 2: The booster club said they'd put up around four thousand dollars if \
we can show it works. The district IT department might co-fund if we can \
extend it to classroom recording — two principals have been asking about \
recording teachers for professional development and teacher evaluations.

Speaker 1: Interesting — so there's actually a dual use case here. Live \
streaming athletics and potentially classroom recording for instructional \
improvement.

Speaker 2: Exactly. And honestly, if we can do morning announcements from the \
media center too, the journalism teacher would love that. She's been begging \
for a proper studio setup for three years.

Speaker 1: What platform are you expecting to stream to? YouTube? NFHS Network?

Speaker 2: YouTube for sure — parents know how to find it. NFHS would be a \
bonus because they do the subscriptions and it helps with recruiting. Ideally \
we can push to both at the same time.

Speaker 1: Got it. Simultaneous multistream, simple operator interface, \
ruggedized enough for a gym or sideline, and budget-conscious. Are you \
the final decision maker on the purchase or does it need to go to the \
principal or district?

Speaker 2: I make the recommendation. Principal signs off if it's under five \
thousand. Above that it needs a board vote, which takes forever. So under \
five thousand is the sweet spot.

Speaker 1: Perfect. That aligns really well with what I want to show you. \
Let me put together a few visual deployment scenarios based on what you've \
described and send them over — things other K-12 districts have actually built \
with us. Give you something concrete to bring to the booster club meeting.

Speaker 2: Yeah, that would be great. Visuals help a lot when you're \
presenting to a booster club — they're not technical, they just want to see \
what it's going to look like.
"""

# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path(__file__).parent.parent / "output"


def ensure_output_dir(output_dir: Path) -> None:
    """Create the output directory if it does not exist."""
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")


def save_png(b64_data: str, path: Path) -> int:
    """Decode base64 PNG and write to disk. Returns byte count."""
    if not b64_data:
        logger.warning(f"  Empty PNG data — skipping {path.name}")
        return 0
    png_bytes = base64.b64decode(b64_data)
    path.write_bytes(png_bytes)
    return len(png_bytes)


def print_email_draft(email: dict[str, str]) -> None:
    """Print the email draft to stdout in a readable format."""
    separator = "=" * 70
    print(f"\n{separator}")
    print("BDR FOLLOW-UP EMAIL DRAFT")
    print(separator)
    print(f"Subject: {email.get('subject', '(no subject)')}")
    print("-" * 70)
    print(email.get("body", "(no body)"))
    print(separator)


def report_stage(label: str, elapsed_ms: float) -> None:
    """Print a formatted stage timing line."""
    marker = "OK" if elapsed_ms < 30_000 else "SLOW"
    print(f"  [{marker}] {label:<40} {elapsed_ms:>7.0f} ms")


# ---------------------------------------------------------------------------
# Main async entrypoint
# ---------------------------------------------------------------------------
async def run_smoke_test(transcript: str) -> int:
    """
    Execute the full pipeline and return 0 on success, 1 on failure.

    Instruments each stage individually by monkey-patching the tool methods
    so we get per-stage timing without modifying the source tool.
    """
    ensure_output_dir(OUTPUT_DIR)

    tool = TranscriptToScenariosTool()

    arguments: dict = {
        "transcript": transcript,
        "prospect_name": "Coach Miller",
        "prospect_company": "Lincoln High School",
    }

    # ------------------------------------------------------------------
    # Instrument stages individually for timing
    # ------------------------------------------------------------------
    stage_times: dict[str, float] = {}

    original_extract = tool.extract_signals
    original_match = tool.match_and_customize
    original_generate = tool.generate_all_storyboards
    original_email = tool.draft_email

    async def timed_extract(*args, **kwargs):
        t0 = perf_counter()
        result = await original_extract(*args, **kwargs)
        stage_times["1_extract"] = (perf_counter() - t0) * 1000
        return result

    async def timed_match(*args, **kwargs):
        t0 = perf_counter()
        result = await original_match(*args, **kwargs)
        stage_times["2_match"] = (perf_counter() - t0) * 1000
        return result

    async def timed_generate(*args, **kwargs):
        t0 = perf_counter()
        result = await original_generate(*args, **kwargs)
        stage_times["3_generate"] = (perf_counter() - t0) * 1000
        return result

    async def timed_email(*args, **kwargs):
        t0 = perf_counter()
        result = await original_email(*args, **kwargs)
        stage_times["4_email"] = (perf_counter() - t0) * 1000
        return result

    tool.extract_signals = timed_extract  # type: ignore[method-assign]
    tool.match_and_customize = timed_match  # type: ignore[method-assign]
    tool.generate_all_storyboards = timed_generate  # type: ignore[method-assign]
    tool.draft_email = timed_email  # type: ignore[method-assign]

    # ------------------------------------------------------------------
    # Run pipeline
    # ------------------------------------------------------------------
    print("\nStarting TranscriptToScenariosTool smoke test...")
    print("Prospect : Coach Miller @ Lincoln High School")
    print(f"Transcript: {len(transcript)} chars")
    print()

    pipeline_start = perf_counter()
    result: ToolResult = await tool.run(arguments)
    total_ms = (perf_counter() - pipeline_start) * 1000

    # ------------------------------------------------------------------
    # Timing report
    # ------------------------------------------------------------------
    print("Pipeline stage timings:")
    report_stage("Stage 1 — Extract signals", stage_times.get("1_extract", 0))
    report_stage("Stage 2 — Match + customize scenarios", stage_times.get("2_match", 0))
    report_stage("Stage 3 — Generate storyboards (parallel)", stage_times.get("3_generate", 0))
    report_stage("Stage 4 — Draft email", stage_times.get("4_email", 0))
    print(f"  {'Total pipeline time':<44} {total_ms:>7.0f} ms")

    # ------------------------------------------------------------------
    # Handle failure
    # ------------------------------------------------------------------
    if not result.success:
        logger.error(f"Pipeline FAILED: {result.error}")
        return 1

    data = result.result or {}

    # ------------------------------------------------------------------
    # Detection summary
    # ------------------------------------------------------------------
    print("\nDetection results:")
    print(f"  Vertical   : {data.get('detected_vertical', 'unknown')}")
    print(f"  Persona    : {data.get('detected_persona', 'unknown')}")
    print(f"  Confidence : {data.get('extraction_confidence', 0):.2f}")

    signals = data.get("signals", {})
    if signals.get("interests"):
        print(f"  Interests  : {', '.join(signals['interests'][:3])}")
    if signals.get("pain_points"):
        print(f"  Pain points: {', '.join(signals['pain_points'][:3])}")

    # ------------------------------------------------------------------
    # Save storyboard PNGs
    # ------------------------------------------------------------------
    scenarios: list[dict] = data.get("scenarios", [])
    print(f"\nScenarios matched: {len(scenarios)}")

    saved_count = 0
    for i, scenario in enumerate(scenarios, start=1):
        name = scenario.get("scenario_name", f"scenario_{i}")
        sid = scenario.get("scenario_id", f"scenario_{i}")
        products = scenario.get("products", [])
        png_b64 = scenario.get("storyboard_png", "")

        print(f"\n  [{i}] {name}")
        print(f"       ID      : {sid}")
        print(f"       Products: {', '.join(products) if products else '—'}")
        print(f"       Hook    : {scenario.get('creative_hook', '')[:80]}...")

        # Save PNG
        safe_sid = sid.replace("/", "_").replace(" ", "_")
        png_path = OUTPUT_DIR / f"scenario_{i:02d}_{safe_sid}.png"
        byte_count = save_png(png_b64, png_path)
        if byte_count:
            print(f"       Saved   : {png_path} ({byte_count / 1024:.0f} KB)")
            saved_count += 1
        else:
            print("       PNG     : (empty — generation may have failed)")

    # ------------------------------------------------------------------
    # Email draft
    # ------------------------------------------------------------------
    email = data.get("email_draft", {})
    if email:
        print_email_draft(email)
    else:
        logger.warning("No email draft returned by pipeline")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\nSmoke test complete.")
    print(f"  Scenarios   : {len(scenarios)} matched")
    print(f"  PNGs saved  : {saved_count} to {OUTPUT_DIR}/")
    print(f"  Total time  : {total_ms:.0f} ms")

    if len(scenarios) == 0:
        logger.error("FAIL — no scenarios were matched")
        return 1

    logger.info("PASS — pipeline completed successfully")
    return 0


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="smoke_test_transcript",
        description=(
            "End-to-end smoke test for the TranscriptToScenariosTool pipeline. "
            "Uses a hardcoded K-12 sample transcript by default, or reads from "
            "a file via --transcript-file."
        ),
    )
    parser.add_argument(
        "--transcript-file",
        metavar="PATH",
        help="Path to a plain-text transcript file to use instead of the built-in sample.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def main() -> None:
    args = parse_args()

    if args.transcript_file:
        transcript_path = Path(args.transcript_file)
        if not transcript_path.is_file():
            logger.error(f"Transcript file not found: {transcript_path}")
            sys.exit(1)
        transcript = transcript_path.read_text(encoding="utf-8")
        logger.info(f"Using transcript from: {transcript_path} ({len(transcript)} chars)")
    else:
        transcript = SAMPLE_TRANSCRIPT
        logger.info("Using built-in K-12 sample transcript")

    # Validate required environment variables
    missing: list[str] = []
    for key in ("GOOGLE_API_KEY", "OPENROUTER_API_KEY"):
        if not os.environ.get(key):
            missing.append(key)
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Copy .env.example to .env and fill in your API keys.")
        sys.exit(1)

    exit_code = asyncio.run(run_smoke_test(transcript))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

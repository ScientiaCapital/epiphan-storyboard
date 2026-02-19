"""
Visual Audit Script — Generate 6 Storyboards for Brand Verification
====================================================================

Generates storyboards across 3 stages x 2 personas to verify:
- Navy (#1D2B51) and lime (#8CBE3F) brand colors are present
- No construction/MEP/contractor imagery
- AV/IT relevant icons (cameras, displays, lecture halls)
- Professional, LinkedIn-ready quality
- Persona-appropriate messaging

Usage:
    python scripts/visual_audit.py

Requires: GOOGLE_API_KEY and OPENROUTER_API_KEY in environment.
Output: audit_output/*.png
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.storyboard.epiphan_presets import EPIPHAN_ICP
from src.tools.storyboard.gemini_client import GeminiStoryboardClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Sample code snippet for understand_code stage
SAMPLE_CODE = '''
class FleetDashboard:
    """Centralized monitoring for all Pearl devices across campus."""

    async def get_fleet_status(self, org_id: str) -> dict:
        """Get real-time status of all Pearl encoders."""
        devices = await self.db.query(
            "SELECT * FROM devices WHERE org_id = ? AND active = true",
            org_id,
        )
        return {
            "total_devices": len(devices),
            "streaming": sum(1 for d in devices if d.status == "streaming"),
            "recording": sum(1 for d in devices if d.status == "recording"),
            "idle": sum(1 for d in devices if d.status == "idle"),
            "alerts": [d for d in devices if d.has_alert],
        }

    async def schedule_recording(self, room_id: str, schedule: dict) -> bool:
        """Schedule automated recording for a room."""
        device = await self.get_device_for_room(room_id)
        return await device.set_schedule(
            start=schedule["start"],
            end=schedule["end"],
            layout=schedule.get("layout", "auto"),
            destinations=schedule.get("destinations", ["local"]),
        )
'''

STAGES = ["preview", "demo", "shipped"]
PERSONAS = ["av_director", "sim_center_director"]

OUTPUT_DIR = Path(__file__).parent.parent / "audit_output"


async def generate_storyboard(
    client: GeminiStoryboardClient,
    stage: str,
    persona: str,
) -> Path | None:
    """Generate a single storyboard and save to disk."""
    filename = f"{stage}_{persona}.png"
    output_path = OUTPUT_DIR / filename

    logger.info(f"Generating: {filename} ...")

    try:
        # Stage 1: Understand
        understanding = await client.understand_code(
            code_content=SAMPLE_CODE,
            icp_preset=EPIPHAN_ICP,
            audience=persona,
            file_name="fleet_dashboard.py",
        )
        logger.info(f"  Understanding: {understanding.headline}")

        # Stage 2: Generate image
        png_bytes = await client.generate_storyboard(
            understanding=understanding,
            stage=stage,
            audience=persona,
            icp_preset=EPIPHAN_ICP,
        )

        # Save
        output_path.write_bytes(png_bytes)
        size_kb = len(png_bytes) / 1024
        logger.info(f"  Saved: {output_path} ({size_kb:.0f} KB)")
        return output_path

    except Exception as e:
        logger.error(f"  FAILED: {filename} — {e}")
        return None


async def main() -> None:
    # Verify API keys
    if not os.environ.get("GOOGLE_API_KEY"):
        logger.error("GOOGLE_API_KEY not set")
        sys.exit(1)
    if not os.environ.get("OPENROUTER_API_KEY"):
        logger.error("OPENROUTER_API_KEY not set")
        sys.exit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)

    client = GeminiStoryboardClient()

    results: dict[str, str] = {}
    total = len(STAGES) * len(PERSONAS)
    completed = 0

    logger.info(f"Starting visual audit: {total} storyboards")
    logger.info(f"Stages: {STAGES}")
    logger.info(f"Personas: {PERSONAS}")
    logger.info(f"Output: {OUTPUT_DIR}/")
    logger.info("=" * 60)

    for stage in STAGES:
        for persona in PERSONAS:
            key = f"{stage}_{persona}"
            path = await generate_storyboard(client, stage, persona)
            results[key] = "PASS" if path else "FAIL"
            completed += 1
            logger.info(f"Progress: {completed}/{total}")
            logger.info("")

    # Summary
    logger.info("=" * 60)
    logger.info("VISUAL AUDIT SUMMARY")
    logger.info("=" * 60)
    for key, status in results.items():
        logger.info(f"  {key}: {status}")

    passed = sum(1 for s in results.values() if s == "PASS")
    logger.info(f"\nResult: {passed}/{total} generated successfully")
    logger.info("\nManual review checklist for each PNG:")
    logger.info("  [ ] Navy (#1D2B51) and lime (#8CBE3F) colors present")
    logger.info("  [ ] No construction/MEP/contractor imagery")
    logger.info("  [ ] AV/IT icons (cameras, displays, lecture halls)")
    logger.info("  [ ] Professional, LinkedIn-ready quality")
    logger.info("  [ ] Persona-appropriate messaging")


if __name__ == "__main__":
    asyncio.run(main())

"""
Regenerate product_visual_specs.py from the Epiphan MCP knowledge sources.
==========================================================================

This is a human/Claude-run helper. It is NOT imported by ``src/`` and is NOT
run at request time: the Epiphan Knowledge + Epiphan AI MCP servers are only
reachable from a Claude Code session, never from the Vercel serverless runtime.

WORKFLOW
--------
Run this inside a Claude Code session that has BOTH MCP servers connected:
  * Epiphan Knowledge  — search(query) / fetch(id) for verbatim product docs
  * Epiphan AI         — search_product_knowledge / search_product_catalog

For each product id below:
  1. Run every query in ``PRODUCT_QUERIES[product_id]`` against the MCPs.
  2. Read the returned pages and pull out, VERBATIM:
       - a 1-2 sentence visual description an image model can draw from
       - concrete visual traits (chassis, ports, screen, mounts, indicators)
       - true technical capabilities worth depicting/labeling
       - false/excluded claims to AVOID (feature exclusions matter most here)
  3. Paste the verified facts into the matching ``ProductVisualSpec`` in
     ``src/tools/storyboard/product_visual_specs.py``. Do NOT invent specs
     beyond what the MCP returns; for uncovered fields, derive conservatively
     from epiphan_presets.py (form_factor / key_specs) and keep them generic.
  4. Bump ``SPECS_VERSION`` (date-stamped, e.g. "2026.06.17").

Then verify:
  python -m pytest tests/tools/storyboard/test_product_visual_specs.py -q
  ruff check src/tools/storyboard/product_visual_specs.py
  python -m mypy src/tools/storyboard/product_visual_specs.py --ignore-missing-imports

This module is dependency-free and importable without side effects.
"""

from __future__ import annotations

# Per-product MCP search queries. Run each against Epiphan Knowledge (search)
# and Epiphan AI (search_product_knowledge / search_product_catalog).
PRODUCT_QUERIES: dict[str, list[str]] = {
    "pearl_mini": [
        "Pearl Mini physical dimensions enclosure front panel touchscreen",
        "Pearl Mini ports connectors SD card USB audio",
        "Pearl Mini capabilities encoder recorder streamer switcher",
    ],
    "pearl_nano": [
        "Pearl Nano form factor front screen connectors",
        "Pearl Nano inputs SDI HDMI audio XLR RCA",
        "Pearl Nano NDI Dante support exclusions single channel",
    ],
    "pearl_nexus": [
        "Pearl Nexus rackmount 1RU channels",
        "Pearl Nexus NDI HX ingest storage SSD power",
        "Pearl Nexus capabilities encoder switcher recorder",
    ],
    "pearl_2": [
        "Pearl-2 form factor rackmount twin front panel rear I/O",
        "Pearl-2 channels encoding NDI SRT RTSP",
        "Pearl-2 4K add-on HDMI SDI inputs",
    ],
    "ec20_ptz": [
        "EC20 PTZ camera form factor mount lens tally PoE",
        "EC20 outputs HDMI SDI USB-C NDI HX SRT RTMP zoom",
        "EC20 AI tracking record direct to CMS LMS no encoder Dante",
    ],
    "epiphan_edge": [
        "Epiphan Edge dashboard UI devices online offline",
        "Epiphan Edge fleet management remote reboot stream record grouping",
        "Epiphan Edge side navigation device menu batch operations Premium",
    ],
    # Pearl Duo is PRE-LAUNCH (ships December 2026) and not yet in the Epiphan
    # Knowledge MCP corpus. Its current spec was sourced from the marketing doc
    # (ephiphan-docs/Marketing/Pearl+Duo.doc) + hero render. Re-run these once
    # the Duo wiki pages land in the Knowledge MCP to replace the doc-sourced data.
    "pearl_duo": [
        "Pearl Duo dual-channel encoder form factor touchscreens front panel",
        "Pearl Duo 4K H.265 12G-SDI HDMI passthrough SSD PoE USB-C protocols",
        "Pearl Duo Epiphan Edge open APIs Stream Deck Crestron Q-SYS boundaries no CMS",
    ],
}


def main() -> None:
    """Print the regeneration instructions and the query plan."""
    print(__doc__)
    print("=" * 60)
    print("QUERY PLAN")
    print("=" * 60)
    for product_id, queries in PRODUCT_QUERIES.items():
        print(f"\n{product_id}:")
        for query in queries:
            print(f"  - {query}")
    print(
        "\nAfter pasting verified facts, bump SPECS_VERSION and run the "
        "verification commands listed in this module's docstring."
    )


if __name__ == "__main__":
    main()

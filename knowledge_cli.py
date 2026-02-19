#!/usr/bin/env python3
"""
Coperniq Knowledge Brain CLI
=============================

CLI tool for ingesting knowledge from various sources.

Usage:
    # Ingest from Close CRM (last 7 days)
    python knowledge_cli.py close --days 7

    # Ingest a Loom transcript
    python knowledge_cli.py loom --url "https://loom.com/share/abc" --transcript "Full transcript..."

    # Ingest a Miro board screenshot
    python knowledge_cli.py miro --image /path/to/screenshot.png

    # Ingest code file
    python knowledge_cli.py code --file /path/to/feature.py

    # Search knowledge base
    python knowledge_cli.py search "scheduling pain points"

    # List knowledge stats
    python knowledge_cli.py stats

Environment Variables:
    CLOSE_API_KEY - Close CRM API key
    OPENROUTER_API_KEY - For LLM extraction
    SUPABASE_URL - Supabase project URL
    SUPABASE_SERVICE_KEY - Supabase service key
    GOOGLE_API_KEY - For Miro vision processing
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("knowledge_cli")


async def cmd_close(args):
    """Ingest from Close CRM."""
    from src.knowledge import KnowledgeIngestionService

    print(f"\n{'='*60}")
    print("CLOSE CRM INGESTION")
    print(f"{'='*60}")
    print(f"Days back: {args.days}")
    print(f"Include calls: {not args.no_calls}")
    print(f"Include notes: {not args.no_notes}")
    print()

    if not os.getenv("CLOSE_API_KEY"):
        print("ERROR: CLOSE_API_KEY not set")
        return 1

    service = KnowledgeIngestionService()
    results = await service.ingest_close_crm(
        days_back=args.days,
        limit=args.limit,
        include_calls=not args.no_calls,
        include_notes=not args.no_notes,
    )

    print(f"\nResults:")
    print(f"  Calls processed: {len(results.get('calls', []))}")
    print(f"  Notes processed: {len(results.get('notes', []))}")
    print(f"  Total extracted: {results.get('total_extracted', 0)}")

    if results.get("errors"):
        print(f"\nErrors:")
        for err in results["errors"]:
            print(f"  - {err}")

    return 0


async def cmd_loom(args):
    """Ingest a Loom transcript."""
    from src.knowledge import KnowledgeIngestionService

    print(f"\n{'='*60}")
    print("LOOM TRANSCRIPT INGESTION")
    print(f"{'='*60}")
    print(f"URL: {args.url}")

    # Read transcript from file or argument
    if args.transcript_file:
        with open(args.transcript_file) as f:
            transcript = f.read()
        print(f"Transcript file: {args.transcript_file}")
    elif args.transcript:
        transcript = args.transcript
        print(f"Transcript length: {len(transcript)} chars")
    else:
        print("ERROR: Provide --transcript or --transcript-file")
        return 1

    service = KnowledgeIngestionService()
    result = await service.ingest_loom_transcript(
        video_url=args.url,
        transcript=transcript,
        title=args.title,
    )

    print(f"\nResults:")
    print(f"  Items extracted: {result.items_extracted}")
    print(f"  Execution time: {result.execution_time_ms}ms")

    if result.entries:
        print(f"\nExtracted knowledge:")
        for entry in result.entries[:10]:  # Show first 10
            print(f"  [{entry.knowledge_type.value}] {entry.content[:60]}...")

    if result.error:
        print(f"\nError: {result.error}")

    return 0


async def cmd_miro(args):
    """Ingest a Miro board screenshot."""
    from src.knowledge import KnowledgeIngestionService

    print(f"\n{'='*60}")
    print("MIRO BOARD INGESTION")
    print(f"{'='*60}")
    print(f"Image: {args.image}")

    if not os.path.exists(args.image):
        print(f"ERROR: Image file not found: {args.image}")
        return 1

    with open(args.image, "rb") as f:
        image_data = f.read()

    print(f"Image size: {len(image_data)} bytes")

    service = KnowledgeIngestionService()
    result = await service.ingest_miro_board(
        image_data=image_data,
        board_url=args.url,
        title=args.title,
    )

    print(f"\nResults:")
    print(f"  Items extracted: {result.items_extracted}")
    print(f"  Execution time: {result.execution_time_ms}ms")

    if result.entries:
        print(f"\nExtracted knowledge:")
        for entry in result.entries[:10]:
            print(f"  [{entry.knowledge_type.value}] {entry.content[:60]}...")

    if result.error:
        print(f"\nError: {result.error}")

    return 0


async def cmd_code(args):
    """Ingest a code file."""
    from src.knowledge import KnowledgeIngestionService

    print(f"\n{'='*60}")
    print("CODE INGESTION")
    print(f"{'='*60}")
    print(f"File: {args.file}")

    if not os.path.exists(args.file):
        print(f"ERROR: File not found: {args.file}")
        return 1

    with open(args.file) as f:
        code_content = f.read()

    print(f"Code length: {len(code_content)} chars")

    service = KnowledgeIngestionService()
    result = await service.ingest_code(
        code_content=code_content,
        file_path=args.file,
        author=args.author,
    )

    print(f"\nResults:")
    print(f"  Items extracted: {result.items_extracted}")
    print(f"  Execution time: {result.execution_time_ms}ms")

    if result.entries:
        print(f"\nExtracted knowledge:")
        for entry in result.entries:
            print(f"  [{entry.knowledge_type.value}] {entry.content[:60]}...")

    if result.error:
        print(f"\nError: {result.error}")

    return 0


async def cmd_search(args):
    """Search knowledge base."""
    from src.knowledge import KnowledgeIngestionService

    print(f"\n{'='*60}")
    print("KNOWLEDGE SEARCH")
    print(f"{'='*60}")
    print(f"Query: {args.query}")

    service = KnowledgeIngestionService()
    entries = await service.search_knowledge(
        query=args.query,
        knowledge_types=args.types.split(",") if args.types else None,
        limit=args.limit,
    )

    print(f"\nFound {len(entries)} results:\n")
    for i, entry in enumerate(entries, 1):
        print(f"{i}. [{entry.knowledge_type.value.upper()}]")
        print(f"   {entry.content}")
        if entry.context:
            print(f"   Context: {entry.context[:80]}...")
        print()

    return 0


async def cmd_stats(args):
    """Show knowledge base statistics."""
    from supabase import create_client

    print(f"\n{'='*60}")
    print("KNOWLEDGE BASE STATISTICS")
    print(f"{'='*60}\n")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required")
        return 1

    client = create_client(url, key)

    # Get counts by type
    response = client.table("coperniq_knowledge").select("knowledge_type").execute()
    type_counts = {}
    for row in response.data:
        kt = row["knowledge_type"]
        type_counts[kt] = type_counts.get(kt, 0) + 1

    print("Knowledge by Type:")
    for kt, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {kt:20} {count:5}")

    print(f"\n  {'TOTAL':20} {sum(type_counts.values()):5}")

    # Get source counts
    response = client.table("knowledge_sources").select("source_type").execute()
    source_counts = {}
    for row in response.data:
        st = row["source_type"]
        source_counts[st] = source_counts.get(st, 0) + 1

    print(f"\nSources by Type:")
    for st, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"  {st:20} {count:5}")

    print(f"\n  {'TOTAL':20} {sum(source_counts.values()):5}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Coperniq Knowledge Brain CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Close CRM command
    close_parser = subparsers.add_parser("close", help="Ingest from Close CRM")
    close_parser.add_argument("--days", type=int, default=7, help="Days back to fetch")
    close_parser.add_argument("--limit", type=int, default=100, help="Max items")
    close_parser.add_argument("--no-calls", action="store_true", help="Skip calls")
    close_parser.add_argument("--no-notes", action="store_true", help="Skip notes")

    # Loom command
    loom_parser = subparsers.add_parser("loom", help="Ingest a Loom transcript")
    loom_parser.add_argument("--url", required=True, help="Loom share URL")
    loom_parser.add_argument("--transcript", help="Transcript text")
    loom_parser.add_argument("--transcript-file", help="Path to transcript file")
    loom_parser.add_argument("--title", help="Video title")

    # Miro command
    miro_parser = subparsers.add_parser("miro", help="Ingest a Miro board screenshot")
    miro_parser.add_argument("--image", required=True, help="Path to screenshot")
    miro_parser.add_argument("--url", help="Miro board URL")
    miro_parser.add_argument("--title", help="Board title")

    # Code command
    code_parser = subparsers.add_parser("code", help="Ingest a code file")
    code_parser.add_argument("--file", required=True, help="Path to code file")
    code_parser.add_argument("--author", help="Code author")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search knowledge base")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--types", help="Comma-separated types to filter")
    search_parser.add_argument("--limit", type=int, default=20, help="Max results")

    # Stats command
    subparsers.add_parser("stats", help="Show knowledge base statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Run the appropriate command
    if args.command == "close":
        return asyncio.run(cmd_close(args))
    elif args.command == "loom":
        return asyncio.run(cmd_loom(args))
    elif args.command == "miro":
        return asyncio.run(cmd_miro(args))
    elif args.command == "code":
        return asyncio.run(cmd_code(args))
    elif args.command == "search":
        return asyncio.run(cmd_search(args))
    elif args.command == "stats":
        return asyncio.run(cmd_stats(args))


if __name__ == "__main__":
    sys.exit(main() or 0)

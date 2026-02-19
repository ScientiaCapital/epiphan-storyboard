#!/usr/bin/env python3
"""
Conductor-AI Storyboard Demo CLI

Generate executive storyboards from code, images, or built-in examples.
Uses Google Gemini 2.0 Flash (NO OpenAI).
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Example files mapping
EXAMPLES = {
    "video_script_generator": "src/tools/video/video_script_generator.py",
    "unified_storyboard": "src/tools/storyboard/unified_storyboard.py",
    "video_scheduler": "src/tools/video/video_scheduler.py",
    "video_generator": "src/tools/video/video_generator.py",
    "gemini_client": "src/tools/storyboard/gemini_client.py",
}


def print_header():
    """Print CLI header."""
    print("\n" + "=" * 70)
    print("🧿 CONDUCTOR-AI STORYBOARD GENERATOR")
    print("=" * 70 + "\n")


def list_examples():
    """List available built-in examples."""
    print("📚 Available Examples:\n")
    for name, path in EXAMPLES.items():
        exists = "✅" if Path(path).exists() else "❌"
        print(f"  {exists} {name:<25} → {path}")
    print()


def read_file_content(file_path: str) -> str:
    """Read content from file or stdin."""
    if file_path == "-":
        print("📖 Reading from stdin (Ctrl+D to finish)...")
        return sys.stdin.read()

    path = Path(file_path)
    if not path.exists():
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)

    return path.read_text()


def read_image_as_base64(image_path: str) -> str:
    """Read image file and convert to base64 data URI."""
    import base64
    from mimetypes import guess_type

    path = Path(image_path)
    if not path.exists():
        print(f"❌ Error: Image file not found: {image_path}")
        sys.exit(1)

    # Determine MIME type
    mime_type, _ = guess_type(str(path))
    if not mime_type or not mime_type.startswith("image/"):
        print(f"❌ Error: Not a valid image file: {image_path}")
        sys.exit(1)

    # Read and encode
    with open(path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime_type};base64,{image_data}"


async def generate_storyboard(
    input_content: str,
    stage: str,
    audience: str,
    open_browser: bool,
) -> dict:
    """Generate storyboard using UnifiedStoryboardTool."""
    from src.tools.storyboard import UnifiedStoryboardTool

    print("🚀 Initializing UnifiedStoryboardTool...\n")

    tool = UnifiedStoryboardTool()

    # Prepare arguments
    args = {
        "input": input_content,
        "stage": stage,
        "audience": audience,
    }

    print(f"⚙️  Stage: {stage}")
    print(f"👥 Audience: {audience}")
    print(f"🌐 Open in browser: {open_browser}\n")

    print("🔄 Generating storyboard (this may take 10-30 seconds)...\n")

    # Run the tool
    result = await tool.run(args)

    if not result.success:
        print(f"❌ Error: {result.error}")
        return None

    return result.result


def print_results(result: dict, open_browser: bool):
    """Print storyboard generation results."""
    print("\n" + "=" * 70)
    print("✅ STORYBOARD GENERATED SUCCESSFULLY")
    print("=" * 70 + "\n")

    # Print understanding
    understanding = result.get("understanding", {})
    print("📊 Understanding:\n")
    print(f"  📌 Headline: {understanding.get('headline', 'N/A')}")
    print(f"  💰 Business Value: {understanding.get('business_value', 'N/A')}")
    print(f"  🎯 Key Features: {', '.join(understanding.get('key_features', []))}")
    print(
        f"  🚀 Technical Complexity: {understanding.get('technical_complexity', 'N/A')}"
    )
    print()

    # Print file info
    file_path = result.get("file_path")
    if file_path:
        print(f"💾 Saved to: {file_path}\n")

    # Browser status
    if open_browser:
        print("🌐 Opening in default browser...")
    else:
        print("ℹ️  Use --browser to open automatically")

    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate executive storyboards from code, images, or examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available examples
  %(prog)s --list-examples

  # Generate from built-in example
  %(prog)s --example video_script_generator

  # Generate from code file
  %(prog)s --code src/tools/video/video_scheduler.py --stage demo

  # Generate from stdin
  cat calculator.py | %(prog)s --code - --audience business_owner

  # Generate from image (Miro screenshot)
  %(prog)s --image roadmap.png --stage shipped --no-browser
        """,
    )

    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "-l",
        "--list-examples",
        action="store_true",
        help="List available built-in examples",
    )
    input_group.add_argument(
        "-e",
        "--example",
        metavar="NAME",
        choices=list(EXAMPLES.keys()),
        help="Generate from built-in example",
    )
    input_group.add_argument(
        "-i",
        "--image",
        metavar="PATH",
        help="Generate from image file (PNG, JPG)",
    )
    input_group.add_argument(
        "-c",
        "--code",
        metavar="PATH",
        help="Generate from code file (use '-' for stdin)",
    )

    # Options
    parser.add_argument(
        "--stage",
        choices=["preview", "demo", "shipped"],
        default="preview",
        help="Development stage (default: preview)",
    )
    parser.add_argument(
        "--audience",
        choices=[
            "business_owner",
            "c_suite",
            "btl_champion",
            "top_tier_vc",
            "field_crew",
        ],
        default="c_suite",
        help="Target audience: c_suite, business_owner, btl_champion, top_tier_vc, or field_crew (simple infographics)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open result in browser",
    )

    args = parser.parse_args()

    print_header()

    # Handle --list-examples
    if args.list_examples:
        list_examples()
        return

    # Determine input content
    input_content = None

    if args.example:
        example_path = EXAMPLES[args.example]
        print(f"📚 Using example: {args.example}")
        print(f"📄 File: {example_path}\n")
        input_content = read_file_content(example_path)

    elif args.code:
        print(f"📄 Reading code file: {args.code}\n")
        input_content = read_file_content(args.code)

    elif args.image:
        print(f"🖼️  Reading image file: {args.image}\n")
        input_content = read_image_as_base64(args.image)

    if not input_content:
        print("❌ Error: No input content provided")
        sys.exit(1)

    # Generate storyboard
    open_browser = not args.no_browser
    result = asyncio.run(
        generate_storyboard(
            input_content=input_content,
            stage=args.stage,
            audience=args.audience,
            open_browser=open_browser,
        )
    )

    if result:
        print_results(result, open_browser)
    else:
        print("\n❌ Storyboard generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

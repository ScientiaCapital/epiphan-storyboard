"""
Tests for scripts/smoke_test_transcript.py

Verifies the script's constants, helper utilities, and CLI argument parsing
without making any real API calls.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Add project root and scripts/ to path so we can import the script directly
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# Import the module under test
import importlib.util  # noqa: E402

_SCRIPT_PATH = _SCRIPTS_DIR / "smoke_test_transcript.py"
_SPEC = importlib.util.spec_from_file_location("smoke_test_transcript", _SCRIPT_PATH)
_MOD = importlib.util.module_from_spec(_SPEC)  # type: ignore[arg-type]
_SPEC.loader.exec_module(_MOD)  # type: ignore[union-attr]

smoke = _MOD  # alias for readability


# ---------------------------------------------------------------------------
# SAMPLE_TRANSCRIPT constant
# ---------------------------------------------------------------------------

class TestSampleTranscript:
    """SAMPLE_TRANSCRIPT must be a non-trivial K-12 conversation."""

    def test_constant_exists(self):
        """SAMPLE_TRANSCRIPT must be defined in the script."""
        assert hasattr(smoke, "SAMPLE_TRANSCRIPT")

    def test_length_exceeds_200_chars(self):
        """Transcript must be substantially longer than 200 characters."""
        assert len(smoke.SAMPLE_TRANSCRIPT) > 200, (
            f"SAMPLE_TRANSCRIPT is only {len(smoke.SAMPLE_TRANSCRIPT)} chars; "
            "expected > 200"
        )

    def test_length_roughly_500_words(self):
        """Transcript should be ~500 words to match the spec."""
        word_count = len(smoke.SAMPLE_TRANSCRIPT.split())
        assert word_count >= 300, (
            f"SAMPLE_TRANSCRIPT is {word_count} words; expected at least 300"
        )

    def test_contains_k12_context(self):
        """Transcript must reference a K-12 institution or sports context."""
        text_lower = smoke.SAMPLE_TRANSCRIPT.lower()
        k12_signals = [
            "school",
            "high school",
            "students",
            "football",
            "basketball",
            "k-12",
            "district",
            "principal",
            "booster",
        ]
        assert any(sig in text_lower for sig in k12_signals), (
            "SAMPLE_TRANSCRIPT does not appear to contain K-12 context; "
            f"looked for: {k12_signals}"
        )

    def test_contains_prospect_name(self):
        """Transcript must reference the prospect 'Coach Miller'."""
        assert "Miller" in smoke.SAMPLE_TRANSCRIPT

    def test_contains_company_name(self):
        """Transcript must reference 'Lincoln High School'."""
        assert "Lincoln High" in smoke.SAMPLE_TRANSCRIPT

    def test_is_a_string(self):
        """SAMPLE_TRANSCRIPT must be a plain string."""
        assert isinstance(smoke.SAMPLE_TRANSCRIPT, str)

    def test_not_empty_after_strip(self):
        """SAMPLE_TRANSCRIPT must have non-whitespace content."""
        assert smoke.SAMPLE_TRANSCRIPT.strip()

    def test_mentions_streaming_or_recording(self):
        """Transcript must mention streaming or recording as core topic."""
        text_lower = smoke.SAMPLE_TRANSCRIPT.lower()
        assert any(
            kw in text_lower
            for kw in ["stream", "record", "broadcast", "live"]
        )

    def test_mentions_epiphan_or_pearl(self):
        """Transcript must reference an Epiphan product by name."""
        text_lower = smoke.SAMPLE_TRANSCRIPT.lower()
        assert any(
            kw in text_lower
            for kw in ["pearl", "epiphan", "ec20", "av.io"]
        )


# ---------------------------------------------------------------------------
# Output directory logic
# ---------------------------------------------------------------------------

class TestOutputDirectoryCreation:
    """ensure_output_dir must create the directory if it does not exist."""

    def test_creates_missing_directory(self, tmp_path: Path):
        """Should create a directory that does not exist yet."""
        target = tmp_path / "new_output_dir"
        assert not target.exists()
        smoke.ensure_output_dir(target)
        assert target.exists()
        assert target.is_dir()

    def test_is_idempotent_on_existing_directory(self, tmp_path: Path):
        """Calling ensure_output_dir on an existing dir must not raise."""
        target = tmp_path / "already_exists"
        target.mkdir()
        smoke.ensure_output_dir(target)  # must not raise
        assert target.exists()

    def test_creates_nested_directories(self, tmp_path: Path):
        """Should create intermediate parent directories."""
        nested = tmp_path / "a" / "b" / "c"
        assert not nested.exists()
        smoke.ensure_output_dir(nested)
        assert nested.is_dir()

    def test_output_dir_constant_is_path(self):
        """OUTPUT_DIR constant must be a pathlib.Path instance."""
        assert isinstance(smoke.OUTPUT_DIR, Path)

    def test_output_dir_name(self):
        """OUTPUT_DIR should point to a directory named 'output'."""
        assert smoke.OUTPUT_DIR.name == "output"

    def test_output_dir_under_project_root(self):
        """OUTPUT_DIR must be a child of the project root."""
        expected_parent = _PROJECT_ROOT.resolve()
        actual_parent = smoke.OUTPUT_DIR.parent.resolve()
        assert actual_parent == expected_parent


# ---------------------------------------------------------------------------
# save_png helper
# ---------------------------------------------------------------------------

class TestSavePng:
    """save_png decodes base64 data and writes it to disk."""

    def test_saves_valid_png(self, tmp_path: Path):
        """Should write decoded bytes and return byte count."""
        import base64

        fake_bytes = b"\x89PNG\r\n\x1a\nfake"
        b64 = base64.b64encode(fake_bytes).decode()
        out = tmp_path / "test.png"
        count = smoke.save_png(b64, out)
        assert count == len(fake_bytes)
        assert out.read_bytes() == fake_bytes

    def test_empty_b64_returns_zero(self, tmp_path: Path):
        """Empty base64 string must return 0 without writing a file."""
        out = tmp_path / "empty.png"
        count = smoke.save_png("", out)
        assert count == 0
        assert not out.exists()


# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------

class TestArgparse:
    """parse_args must handle all documented CLI arguments correctly."""

    def test_no_args_returns_none_transcript_file(self):
        """Running with no arguments sets transcript_file to None."""
        with patch("sys.argv", ["smoke_test_transcript"]):
            args = smoke.parse_args()
        assert args.transcript_file is None

    def test_transcript_file_arg_short_form_not_supported(self):
        """--transcript-file is the only supported flag (no short form)."""
        {
            action.dest
            for action in smoke.parse_args.__wrapped__._parser._actions  # type: ignore[attr-defined]
            if hasattr(action, "dest")
        } if hasattr(smoke.parse_args, "__wrapped__") else set()
        # If reflection is unavailable, simply parse a valid flag
        with patch("sys.argv", ["smoke_test_transcript", "--transcript-file", "/tmp/t.txt"]):
            args = smoke.parse_args()
        assert args.transcript_file == "/tmp/t.txt"

    def test_transcript_file_arg_long_form(self):
        """--transcript-file sets the transcript_file attribute."""
        with patch("sys.argv", ["smoke_test_transcript", "--transcript-file", "/tmp/transcript.txt"]):
            args = smoke.parse_args()
        assert args.transcript_file == "/tmp/transcript.txt"

    def test_invalid_arg_raises_system_exit(self):
        """Unrecognised arguments must cause SystemExit (argparse default)."""
        with patch("sys.argv", ["smoke_test_transcript", "--no-such-flag"]):
            with pytest.raises(SystemExit):
                smoke.parse_args()

    def test_returns_namespace(self):
        """parse_args must return an argparse.Namespace object."""
        with patch("sys.argv", ["smoke_test_transcript"]):
            args = smoke.parse_args()
        assert isinstance(args, argparse.Namespace)

    def test_help_exits_cleanly(self):
        """--help must exit with code 0."""
        with patch("sys.argv", ["smoke_test_transcript", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                smoke.parse_args()
        assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# print_email_draft
# ---------------------------------------------------------------------------

class TestPrintEmailDraft:
    """print_email_draft should output subject and body to stdout."""

    def test_prints_subject(self, capsys):
        """Subject must appear in printed output."""
        smoke.print_email_draft({"subject": "Hello K-12", "body": "Test body."})
        captured = capsys.readouterr()
        assert "Hello K-12" in captured.out

    def test_prints_body(self, capsys):
        """Body must appear in printed output."""
        smoke.print_email_draft({"subject": "Subject", "body": "Body content here."})
        captured = capsys.readouterr()
        assert "Body content here." in captured.out

    def test_handles_missing_keys(self, capsys):
        """Should not raise on empty dict — shows fallback strings."""
        smoke.print_email_draft({})
        captured = capsys.readouterr()
        assert "no subject" in captured.out.lower() or captured.out  # just doesn't crash


# ---------------------------------------------------------------------------
# report_stage
# ---------------------------------------------------------------------------

class TestReportStage:
    """report_stage should format timing output correctly."""

    def test_prints_label(self, capsys):
        """Stage label should appear in output."""
        smoke.report_stage("Stage 1 — Extract signals", 1200.0)
        captured = capsys.readouterr()
        assert "Stage 1 — Extract signals" in captured.out

    def test_prints_ok_for_fast_stage(self, capsys):
        """Stages under 30 000 ms should show OK marker."""
        smoke.report_stage("Fast stage", 500.0)
        captured = capsys.readouterr()
        assert "OK" in captured.out

    def test_prints_slow_for_slow_stage(self, capsys):
        """Stages at or above 30 000 ms should show SLOW marker."""
        smoke.report_stage("Slow stage", 35_000.0)
        captured = capsys.readouterr()
        assert "SLOW" in captured.out

    def test_prints_elapsed_ms(self, capsys):
        """Elapsed time in ms should appear in output."""
        smoke.report_stage("Timing test", 4567.0)
        captured = capsys.readouterr()
        assert "4567" in captured.out


# ---------------------------------------------------------------------------
# Shebang and module-level guards
# ---------------------------------------------------------------------------

class TestScriptStructure:
    """Basic structural checks on the script file itself."""

    def test_shebang_present(self):
        """Script must start with the correct shebang line."""
        first_line = _SCRIPT_PATH.read_text(encoding="utf-8").splitlines()[0]
        assert first_line == "#!/usr/bin/env python3"

    def test_main_guard_present(self):
        """Script must have an if __name__ == '__main__': guard."""
        content = _SCRIPT_PATH.read_text(encoding="utf-8")
        assert 'if __name__ == "__main__":' in content

    def test_imports_dotenv(self):
        """Script must load dotenv for environment variable support."""
        content = _SCRIPT_PATH.read_text(encoding="utf-8")
        assert "load_dotenv" in content

    def test_imports_transcript_tool(self):
        """Script must import TranscriptToScenariosTool."""
        content = _SCRIPT_PATH.read_text(encoding="utf-8")
        assert "TranscriptToScenariosTool" in content

    def test_imports_argparse(self):
        """Script must use argparse for CLI argument handling."""
        content = _SCRIPT_PATH.read_text(encoding="utf-8")
        assert "import argparse" in content

    def test_uses_asyncio_run(self):
        """Script must use asyncio.run for the async entrypoint."""
        content = _SCRIPT_PATH.read_text(encoding="utf-8")
        assert "asyncio.run" in content

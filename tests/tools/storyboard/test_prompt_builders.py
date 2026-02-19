"""Tests for prompt_builders.py — snapshot-style prompt content verification."""

import pytest

from src.tools.storyboard import prompt_builders


class TestBuildExtractionPromptCode:
    """Tests for code extraction prompts."""

    def test_code_prompt_contains_audience(self):
        """Code prompt should reference the target audience."""
        prompt = prompt_builders.build_extraction_prompt(
            "code", audience="av_director", content="def foo(): pass"
        )
        assert "av_director" in prompt

    def test_code_prompt_contains_content(self):
        """Code prompt should include the actual code."""
        prompt = prompt_builders.build_extraction_prompt(
            "code", audience="av_director", content="def calculate_roi(): return 42"
        )
        assert "calculate_roi" in prompt

    def test_code_prompt_contains_json_schema(self):
        """Code prompt should include the expected JSON schema fields."""
        prompt = prompt_builders.build_extraction_prompt(
            "code", audience="av_director", content="def foo(): pass"
        )
        assert "headline" in prompt
        assert "what_it_does" in prompt
        assert "business_value" in prompt
        assert "extraction_confidence" in prompt

    def test_code_prompt_contains_file_name(self):
        """Code prompt should include file name when provided."""
        prompt = prompt_builders.build_extraction_prompt(
            "code",
            audience="av_director",
            content="def foo(): pass",
            file_name="calculator.py",
        )
        assert "calculator.py" in prompt

    def test_code_prompt_never_contains_mep(self):
        """Code prompt must NEVER reference MEP/contractor content."""
        for audience in [
            "av_director",
            "ld_director",
            "sim_center_director",
            "court_admin",
            "corp_comms",
            "ehs_manager",
            "law_firm_it",
            "technical_director",
        ]:
            prompt = prompt_builders.build_extraction_prompt(
                "code", audience=audience, content="def foo(): pass"
            )
            prompt_lower = prompt.lower()
            assert "mep" not in prompt_lower, f"MEP found in {audience} code prompt"
            assert (
                "contractor" not in prompt_lower
            ), f"contractor found in {audience} code prompt"


class TestBuildExtractionPromptTranscript:
    """Tests for transcript extraction prompts."""

    def test_transcript_prompt_contains_content(self):
        """Transcript prompt should include the transcript text."""
        prompt = prompt_builders.build_extraction_prompt(
            "transcript",
            audience="av_director",
            content="John: We need better AV in room 301.",
        )
        assert "room 301" in prompt

    def test_transcript_prompt_contains_context(self):
        """Transcript prompt should include context when provided."""
        prompt = prompt_builders.build_extraction_prompt(
            "transcript",
            audience="av_director",
            content="Some transcript",
            context="Gong call with NC State",
        )
        assert "Gong call with NC State" in prompt

    def test_transcript_prompt_has_extraction_priorities(self):
        """Transcript prompt should instruct for exact quote preservation."""
        prompt = prompt_builders.build_extraction_prompt(
            "transcript", audience="av_director", content="Some transcript"
        )
        assert "EXACT quotes" in prompt


class TestBuildExtractionPromptImage:
    """Tests for image extraction prompts."""

    def test_image_prompt_contains_audience(self):
        """Image prompt should reference the target audience."""
        prompt = prompt_builders.build_extraction_prompt(
            "image", audience="sim_center_director"
        )
        assert "sim_center_director" in prompt

    def test_image_prompt_with_supplementary_context(self):
        """Image prompt should include supplementary text context."""
        prompt = prompt_builders.build_extraction_prompt(
            "image",
            audience="av_director",
            supplementary_context="This is a Miro board showing our Q3 roadmap",
        )
        assert "Q3 roadmap" in prompt
        assert "PRIMARY INPUT" in prompt

    def test_image_prompt_without_supplementary_context(self):
        """Image prompt should work without supplementary context."""
        prompt = prompt_builders.build_extraction_prompt(
            "image", audience="av_director"
        )
        assert "Analyze" in prompt


class TestBuildExtractionPromptMultiImage:
    """Tests for multi-image extraction prompts."""

    def test_multi_image_prompt_references_count(self):
        """Multi-image prompt should reference the number of images."""
        prompt = prompt_builders.build_extraction_prompt(
            "images", audience="av_director", num_images=3
        )
        assert "3" in prompt

    def test_multi_image_prompt_has_synthesis_instruction(self):
        """Multi-image prompt should instruct to synthesize across images."""
        prompt = prompt_builders.build_extraction_prompt(
            "images", audience="av_director", num_images=2
        )
        assert "SYNTHESIZE" in prompt or "synthesize" in prompt


class TestBuildExtractionPromptInvalidType:
    """Tests for invalid content type."""

    def test_raises_on_unknown_content_type(self):
        """Should raise ValueError for unknown content type."""
        with pytest.raises(ValueError, match="Unknown content_type"):
            prompt_builders.build_extraction_prompt("spreadsheet")


class TestBuildKnowledgeContext:
    """Tests for knowledge context builder."""

    def test_returns_string(self):
        """Should always return a string (empty if cache not loaded)."""
        result = prompt_builders.build_knowledge_context("av_director")
        assert isinstance(result, str)

    def test_graceful_degradation(self):
        """Should not raise even if knowledge cache is unavailable."""
        # This tests the try/except in the function
        result = prompt_builders.build_knowledge_context("nonexistent_audience")
        assert isinstance(result, str)


class TestBuildLanguageGuidelinesMinimal:
    """Tests for minimal language guidelines builder."""

    def test_returns_string(self):
        """Should always return a string."""
        result = prompt_builders.build_language_guidelines_minimal("av_director")
        assert isinstance(result, str)

    def test_graceful_degradation(self):
        """Should not raise even if knowledge cache is unavailable."""
        result = prompt_builders.build_language_guidelines_minimal("nonexistent")
        assert isinstance(result, str)

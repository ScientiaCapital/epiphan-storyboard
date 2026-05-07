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
            assert "contractor" not in prompt_lower, (
                f"contractor found in {audience} code prompt"
            )


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


# =============================================================================
# Phase 1.3 — Prompt Builder polish
# =============================================================================


class TestBuildProblemStatementAnchor:
    """Fix #3 — verbatim BDR pain language injected as ground truth."""

    def test_returns_empty_when_vertical_or_persona_missing(self):
        """Without both vertical+persona resolved, no anchor block is emitted."""
        assert prompt_builders.build_problem_statement_anchor(None, None) == ""
        assert prompt_builders.build_problem_statement_anchor(None, "av_director") == ""
        assert prompt_builders.build_problem_statement_anchor("higher_ed", None) == ""

    def test_returns_block_for_known_combo(self):
        """A known (vertical, persona) yields a labeled VERBATIM PAIN LANGUAGE block."""
        block = prompt_builders.build_problem_statement_anchor(
            "higher_ed", "av_director"
        )
        assert "VERBATIM PAIN LANGUAGE" in block.upper()
        # Should include verbatim text from the seeded library
        assert "AV directors" in block or "rooms going unrecorded" in block

    def test_block_caps_at_three_statements(self):
        """The anchor block contains at most 3 verbatim statements (per plan)."""
        block = prompt_builders.build_problem_statement_anchor(
            "higher_ed", "av_director"
        )
        # Count bullet markers — implementation must use a stable bullet ("- ")
        # and should never emit more than 3 of them.
        assert block.count("\n- ") <= 3

    def test_returns_empty_for_unknown_combo(self):
        """No matches → empty string (silently degrade, never raise)."""
        block = prompt_builders.build_problem_statement_anchor(
            "bogus_vertical", "av_director"
        )
        assert block == ""

    def test_anchor_appears_in_transcript_prompt(self):
        """When vertical+persona are passed, the anchor block lands in the prompt."""
        prompt = prompt_builders.build_extraction_prompt(
            "transcript",
            audience="av_director",
            vertical="higher_ed",
            content="Sample transcript content for testing.",
        )
        assert "VERBATIM PAIN LANGUAGE" in prompt.upper()


class TestTranscriptCompactorWired:
    """Fix #1 — transcript truncation replaced by compact_transcript()."""

    def test_long_transcript_does_not_blindly_slice_at_32k(self):
        """A 60K transcript with high-signal content at the END must not lose it."""
        # Build a transcript where the high-signal turn is at position ~50K
        # (well past the old 32K hard cut). After polish, that turn must
        # survive compaction and appear in the prompt. Brand-agnostic
        # phrasing — the prospect describes the workaround layer, not any
        # partner platform.
        filler = "Speaker 1: " + ("uh yeah okay so " * 80) + "\n"
        late_signal = (
            "Speaker 2: Honestly the biggest pain is that our software encoder "
            "fails about 30 percent of the time and it's burning our team's "
            "entire week troubleshooting it.\n"
        )
        text = filler * 40 + late_signal + filler * 5  # late_signal at ~50K

        prompt = prompt_builders.build_extraction_prompt(
            "transcript",
            audience="av_director",
            vertical="higher_ed",
            content=text,
        )
        assert "software encoder" in prompt, (
            "Compactor must preserve high-signal turns past the old 32K cut"
        )

    def test_short_transcript_passes_through_unchanged_in_prompt(self):
        """A short transcript should appear in the prompt as-is."""
        text = "Speaker 1: Quick question about lecture capture."
        prompt = prompt_builders.build_extraction_prompt(
            "transcript",
            audience="av_director",
            content=text,
        )
        assert "lecture capture" in prompt


class TestImplicitFrankenstackPatterns:
    """Fix #4 — implicit-workaround patterns surface in the prompt's signal list."""

    def test_implicit_workaround_phrases_listed_in_prompt(self):
        """The transcript prompt instructs the LLM to look for implicit workarounds."""
        prompt = prompt_builders.build_extraction_prompt(
            "transcript",
            audience="av_director",
            content="Sample transcript.",
        )
        # The polish adds explicit instruction to detect workaround patterns
        # like 'we had to', 'work around', 'in addition to'. The exact phrasing
        # is implementation-specific but must include the WORKAROUND concept.
        assert "workaround" in prompt.lower() or "work around" in prompt.lower()

    def test_known_workaround_combos_documented(self):
        """The prompt mentions at least one classic Frankenstack pattern.

        We frame combos in terms of the *broken capture/encoder layer* — never
        in terms of a partner LMS / CMS / conferencing platform. Partners are
        partners; the workaround is the duct-tape underneath.
        """
        prompt = prompt_builders.build_extraction_prompt(
            "transcript",
            audience="av_director",
            content="Sample transcript.",
        )
        lower = prompt.lower()
        # The Frankenstack block calls out the classroom-PC + software-encoder
        # pattern, multi-box switcher rigs, and bonded cellular orchestration.
        assert any(
            combo in lower
            for combo in (
                "classroom pc",
                "software encoder",
                "vmix",
                "separate recorder",
                "control without capture",
            )
        )


class TestTwoPassNarrativeExtraction:
    """Fix #2 — narrative+schema two-pass Forces extraction is exposed."""

    def test_narrative_extraction_prompt_function_exists(self):
        """The two-pass narrative extractor is a public function callable from
        gemini_client. It should accept a transcript and return a prompt that
        asks for free-text Forces of Progress narrative (no JSON schema)."""
        prompt = prompt_builders.build_narrative_extraction_prompt(
            transcript="Sample transcript",
            audience="av_director",
            vertical="higher_ed",
        )
        assert isinstance(prompt, str)
        # Free-text pass should NOT ask for JSON
        assert "Return JSON" not in prompt
        # But should still ask about Forces of Progress
        lower = prompt.lower()
        assert "push" in lower
        assert "pull" in lower
        assert "anxiety" in lower
        assert "habit" in lower

    def test_schema_mapping_prompt_takes_narrative(self):
        """Pass-2 prompt accepts pass-1 narrative text and asks for strict JSON.

        Brand-agnostic narrative — describes the failure layer (the software
        encoder / classroom PC) without naming any LMS / CMS / conferencing
        partner.
        """
        narrative_marker = "their software encoder layer crashes mid-lecture"
        prompt = prompt_builders.build_schema_mapping_prompt(
            narrative=f"The team is frustrated with how often {narrative_marker}.",
            audience="av_director",
        )
        assert "Return JSON" in prompt or "return json" in prompt.lower()
        assert narrative_marker in prompt  # narrative must be embedded verbatim
        assert "forces_of_progress" in prompt

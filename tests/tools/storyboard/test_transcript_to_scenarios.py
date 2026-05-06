"""Tests for TranscriptToScenariosTool — the transcript-to-scenarios pipeline."""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.storyboard.schemas import (
    EmailDraft,
    JobType,
    ScenarioResult,
    TranscriptStoryboardRequest,
    TranscriptStoryboardResponse,
)
from src.tools.base import BaseTool, ToolCategory, ToolResult
from src.tools.storyboard.gemini_client import StoryboardUnderstanding
from src.tools.storyboard.transcript_to_scenarios import TranscriptToScenariosTool


# ── Sample Transcripts ────────────────────────────────────────────────────

K12_TRANSCRIPT = """
Speaker 1 (BDR): Thanks for taking the time, Mike. I know you're busy with the start of the school year.

Speaker 2 (Mike, Athletic Director): Yeah, it's been crazy. So we've been talking about streaming our Friday night football games. Parents keep asking about it. We tried doing it with a phone on a tripod last year and it looked terrible.

Speaker 1: How many games are we talking?

Speaker 2: About 10 home football games, plus basketball — so maybe 30 events total. We don't have a big budget and our "AV team" is basically student volunteers.

Speaker 1: That's exactly the use case Pearl Nano is built for...
"""

HIGHER_ED_TRANSCRIPT = """
Speaker 1 (BDR): So tell me about your lecture capture situation.

Speaker 2 (AV Director): We have about 150 classrooms and right now maybe 20 have recording capability. Faculty are complaining they want recorded lectures for students who miss class. We've been looking at Panopto for the software side but need hardware that just works.

Speaker 1: Are you standardized on any platform?

Speaker 2: No, that's the problem. Every room is different. Some have old Extron systems, some have Crestron, some have nothing. We need to standardize campus-wide but faculty won't use anything that's more than one button.
"""

LEGAL_TRANSCRIPT = """
Speaker 1 (BDR): How are you handling courtroom recording today?

Speaker 2 (Court Admin): We have an old system that fails about once a month. Last week we lost 2 hours of testimony. The judge was furious. We need something reliable for court proceedings and public access streaming.

Speaker 1: How many courtrooms?

Speaker 2: 8 courtrooms plus 2 hearing rooms. We need recording in all of them. Chain of custody is critical — everything has to be tamper-proof for the record of proceedings.
"""

CORPORATE_TRANSCRIPT = """
Speaker 1 (BDR): Tell me about the town hall situation.

Speaker 2 (Comms Director): Our CEO does quarterly all-hands for 5,000 employees globally. Right now it looks like a bad Zoom call. We need broadcast quality — this is executive communication, it reflects our brand. We also want to simulcast to YouTube and our intranet.
"""


class TestToolDefinition:
    """Tests for tool definition."""

    def test_definition_name(self):
        tool = TranscriptToScenariosTool()
        assert tool.definition.name == "transcript_to_scenarios"

    def test_definition_category(self):
        tool = TranscriptToScenariosTool()
        assert tool.definition.category == ToolCategory.DATA

    def test_definition_has_description(self):
        tool = TranscriptToScenariosTool()
        desc = tool.definition.description
        assert "transcript" in desc.lower()
        assert "scenario" in desc.lower()
        assert len(desc) > 50

    def test_definition_has_required_transcript(self):
        tool = TranscriptToScenariosTool()
        params = tool.definition.parameters
        assert "transcript" in params["properties"]
        assert "transcript" in params["required"]

    def test_definition_has_optional_params(self):
        tool = TranscriptToScenariosTool()
        params = tool.definition.parameters["properties"]
        assert "vertical_hint" in params
        assert "persona_hint" in params
        assert "prospect_name" in params
        assert "prospect_company" in params

    def test_inherits_from_base_tool(self):
        tool = TranscriptToScenariosTool()
        assert isinstance(tool, BaseTool)

    def test_does_not_require_approval(self):
        tool = TranscriptToScenariosTool()
        assert tool.definition.requires_approval is False


class TestTranscriptStoryboardRequest:
    """Tests for the request schema."""

    def test_valid_request(self):
        req = TranscriptStoryboardRequest(transcript="Some call transcript here")
        assert req.transcript == "Some call transcript here"

    def test_empty_transcript_rejected(self):
        with pytest.raises(Exception):
            TranscriptStoryboardRequest(transcript="")

    def test_whitespace_transcript_rejected(self):
        with pytest.raises(Exception):
            TranscriptStoryboardRequest(transcript="   ")

    def test_optional_fields_default_none(self):
        req = TranscriptStoryboardRequest(transcript="test")
        assert req.vertical_hint is None
        assert req.persona_hint is None
        assert req.prospect_name is None
        assert req.prospect_company is None

    def test_all_fields_populated(self):
        req = TranscriptStoryboardRequest(
            transcript="call notes here",
            vertical_hint="k12",
            persona_hint="av_director",
            prospect_name="Mike",
            prospect_company="Lincoln High School",
        )
        assert req.vertical_hint == "k12"
        assert req.prospect_name == "Mike"


class TestTranscriptStoryboardResponse:
    """Tests for the response schema."""

    def test_empty_response(self):
        resp = TranscriptStoryboardResponse()
        assert resp.scenarios == []
        assert resp.email_draft is None
        assert resp.detected_vertical == ""
        assert resp.extraction_confidence == 0.0

    def test_full_response(self):
        resp = TranscriptStoryboardResponse(
            scenarios=[
                ScenarioResult(
                    scenario_id="k12_sports_broadcast",
                    scenario_name="Friday Night Lights Streaming",
                    vertical="k12",
                    products=["Pearl Nano", "EC20 PTZ"],
                    setup_description="Stream high school games with Pearl Nano",
                )
            ],
            email_draft=EmailDraft(
                subject="Following up on streaming",
                body="Hi Mike, great chat about streaming your games.",
            ),
            detected_vertical="k12",
            detected_persona="av_director",
            extraction_confidence=0.85,
        )
        assert len(resp.scenarios) == 1
        assert resp.email_draft.subject == "Following up on streaming"
        assert resp.detected_vertical == "k12"


class TestJobTypeEnum:
    """Tests for the new JobType value."""

    def test_transcript_job_type_exists(self):
        assert JobType.TRANSCRIPT_TO_STORYBOARD == "transcript_to_storyboard"

    def test_all_job_types(self):
        types = [j.value for j in JobType]
        assert "code_to_storyboard" in types
        assert "roadmap_to_storyboard" in types
        assert "transcript_to_storyboard" in types


class TestExtractSignals:
    """Tests for Stage 1: signal extraction from transcript."""

    @pytest.mark.asyncio
    async def test_extract_k12_signals(self):
        """Should detect K-12 vertical and sports-related signals."""
        tool = TranscriptToScenariosTool()

        # Mock the DeepSeek call
        mock_client = MagicMock()
        mock_client._call_deepseek = AsyncMock(
            return_value=json.dumps(
                {
                    "detected_vertical": "k12",
                    "detected_persona": "av_director",
                    "interests": ["sports streaming", "football games"],
                    "pain_points": ["phone on a tripod looked terrible"],
                    "products_mentioned": [],
                    "org_size_hints": ["30 events total"],
                    "buyer_signals": ["parents keep asking about it"],
                    "confidence": 0.9,
                }
            )
        )
        tool._gemini_client = mock_client

        signals = await tool.extract_signals(K12_TRANSCRIPT)

        assert signals["detected_vertical"] == "k12"
        assert signals["confidence"] >= 0.5
        assert len(signals["interests"]) > 0

    @pytest.mark.asyncio
    async def test_vertical_hint_overrides(self):
        """BDR vertical hint should override AI detection."""
        tool = TranscriptToScenariosTool()

        mock_client = MagicMock()
        mock_client._call_deepseek = AsyncMock(
            return_value=json.dumps(
                {
                    "detected_vertical": "corporate",
                    "detected_persona": "av_director",
                    "interests": [],
                    "pain_points": [],
                    "products_mentioned": [],
                    "org_size_hints": [],
                    "buyer_signals": [],
                    "confidence": 0.5,
                }
            )
        )
        tool._gemini_client = mock_client

        signals = await tool.extract_signals("Some transcript", vertical_hint="k12")
        assert signals["detected_vertical"] == "k12"

    @pytest.mark.asyncio
    async def test_extract_handles_bad_json(self):
        """Should gracefully handle unparseable LLM response."""
        tool = TranscriptToScenariosTool()

        mock_client = MagicMock()
        mock_client._call_deepseek = AsyncMock(return_value="Not valid JSON at all")
        tool._gemini_client = mock_client

        signals = await tool.extract_signals("Some transcript")

        # Should fall back to defaults
        assert "detected_vertical" in signals
        assert signals["confidence"] == 0.3


class TestMatchAndCustomize:
    """Tests for Stage 2: scenario matching and customization."""

    @pytest.mark.asyncio
    async def test_match_returns_scenarios(self):
        """Should return 1-4 matched scenarios."""
        tool = TranscriptToScenariosTool()

        mock_client = MagicMock()
        mock_client._call_deepseek = AsyncMock(
            return_value=json.dumps(
                [
                    {
                        "scenario_id": "k12_sports_broadcast",
                        "customized_setup": "Stream Lincoln High's 10 home football games with Pearl Nano + EC20 PTZ. Student volunteers run the show.",
                        "customized_hook": "Parents are already filming on phones — give them a professional stream to share instead.",
                        "relevance_reason": "Direct match: sports streaming, volunteer operators, budget-conscious",
                    },
                    {
                        "scenario_id": "k12_library_studio",
                        "customized_setup": "Transform the media center into a student broadcast studio.",
                        "customized_hook": "Real media literacy with professional tools.",
                        "relevance_reason": "Related: student content creation",
                    },
                ]
            )
        )
        tool._gemini_client = mock_client

        signals = {
            "detected_vertical": "k12",
            "interests": ["sports streaming"],
            "pain_points": ["phone on tripod"],
            "org_size_hints": ["30 events"],
        }

        matched = await tool.match_and_customize(K12_TRANSCRIPT, signals)

        assert len(matched) >= 1
        assert len(matched) <= 4
        assert matched[0]["scenario_id"] == "k12_sports_broadcast"
        assert "products" in matched[0]
        assert matched[0]["scenario_name"] == "Friday Night Lights Streaming"

    @pytest.mark.asyncio
    async def test_match_enriches_with_product_names(self):
        """Matched scenarios should have human-readable product names."""
        tool = TranscriptToScenariosTool()

        mock_client = MagicMock()
        mock_client._call_deepseek = AsyncMock(
            return_value=json.dumps(
                [
                    {
                        "scenario_id": "k12_sports_broadcast",
                        "customized_setup": "Custom setup",
                        "customized_hook": "Custom hook",
                        "relevance_reason": "Match",
                    }
                ]
            )
        )
        tool._gemini_client = mock_client

        matched = await tool.match_and_customize(
            "football streaming", {"detected_vertical": "k12"}
        )

        assert len(matched) >= 1
        products = matched[0]["products"]
        assert "Pearl Nano" in products
        assert "Epiphan EC20 PTZ Camera" in products

    @pytest.mark.asyncio
    async def test_match_handles_custom_scenarios(self):
        """Should handle LLM-invented custom scenarios."""
        tool = TranscriptToScenariosTool()

        mock_client = MagicMock()
        mock_client._call_deepseek = AsyncMock(
            return_value=json.dumps(
                [
                    {
                        "scenario_id": "custom_1",
                        "customized_setup": "Custom deployment for unique use case",
                        "customized_hook": "Unique angle for this prospect",
                        "relevance_reason": "Prospect described non-standard use case",
                    }
                ]
            )
        )
        tool._gemini_client = mock_client

        matched = await tool.match_and_customize(
            "unique transcript", {"detected_vertical": "corporate"}
        )

        assert len(matched) == 1
        assert matched[0]["scenario_id"] == "custom_1"

    @pytest.mark.asyncio
    async def test_match_handles_bad_json(self):
        """Should fall back to keyword matching on bad LLM response."""
        tool = TranscriptToScenariosTool()

        mock_client = MagicMock()
        mock_client._call_deepseek = AsyncMock(return_value="Bad JSON response")
        tool._gemini_client = mock_client

        # Use a transcript with known trigger phrases
        matched = await tool.match_and_customize(
            "We need lecture capture campus-wide for hundreds of rooms",
            {"detected_vertical": "higher_ed"},
        )

        # Should fall back to keyword matches
        assert len(matched) >= 1


class TestDraftEmail:
    """Tests for Stage 4: email drafting."""

    @pytest.mark.asyncio
    async def test_draft_email_returns_subject_and_body(self):
        """Should return email with subject and body."""
        tool = TranscriptToScenariosTool()

        mock_client = MagicMock()
        mock_client._call_deepseek = AsyncMock(
            return_value=json.dumps(
                {
                    "subject": "Visual scenarios for Lincoln High's game streaming",
                    "body": "Hi Mike,\n\nGreat chatting about streaming your football games. Attached are a few deployment scenarios based on what we discussed.\n\nBest",
                }
            )
        )
        tool._gemini_client = mock_client

        scenarios = [{"scenario_name": "Friday Night Lights Streaming"}]
        signals = {
            "detected_vertical": "k12",
            "interests": ["football streaming"],
            "pain_points": ["phone on tripod"],
        }

        email = await tool.draft_email(
            scenarios, signals, prospect_name="Mike", prospect_company="Lincoln High"
        )

        assert "subject" in email
        assert "body" in email
        assert len(email["subject"]) > 0
        assert len(email["body"]) > 0

    @pytest.mark.asyncio
    async def test_draft_email_handles_bad_json(self):
        """Should return fallback email on bad LLM response."""
        tool = TranscriptToScenariosTool()

        mock_client = MagicMock()
        mock_client._call_deepseek = AsyncMock(return_value="not json")
        tool._gemini_client = mock_client

        email = await tool.draft_email(
            [{"scenario_name": "Test"}],
            {"detected_vertical": "k12"},
            prospect_name="Mike",
        )

        assert "subject" in email
        assert "body" in email
        assert "Mike" in email["body"]


class TestGenerateStoryboards:
    """Tests for Stage 3: storyboard generation."""

    @pytest.mark.asyncio
    async def test_generate_single_storyboard(self):
        """Should generate a base64 PNG for a scenario."""
        tool = TranscriptToScenariosTool()

        mock_client = MagicMock()
        mock_client.generate_storyboard = AsyncMock(return_value=b"fake-png-bytes")
        tool._gemini_client = mock_client

        scenario = {
            "scenario_id": "k12_sports_broadcast",
            "scenario_name": "Friday Night Lights Streaming",
            "vertical": "k12",
            "products": ["Pearl Nano"],
            "setup_description": "Stream games with Pearl Nano",
            "creative_hook": "Give parents a reason to share YOUR stream",
            "reference_story": None,
            "bundle_name": None,
            "relevance_reason": "Sports streaming match",
        }

        png_b64 = await tool.generate_scenario_storyboard(scenario, "av_director")

        assert len(png_b64) > 0
        assert mock_client.generate_storyboard.called

    @pytest.mark.asyncio
    async def test_generate_all_storyboards_parallel(self):
        """Should generate storyboards for all scenarios in parallel."""
        tool = TranscriptToScenariosTool()

        mock_client = MagicMock()
        mock_client.generate_storyboard = AsyncMock(return_value=b"png-bytes")
        tool._gemini_client = mock_client

        scenarios = [
            {
                "scenario_id": f"test_{i}",
                "scenario_name": f"Test {i}",
                "vertical": "k12",
                "products": [],
                "setup_description": "Test",
                "creative_hook": "Test",
                "relevance_reason": "Test",
            }
            for i in range(3)
        ]

        pngs = await tool.generate_all_storyboards(scenarios, "av_director")

        assert len(pngs) == 3
        assert all(len(p) > 0 for p in pngs)
        assert mock_client.generate_storyboard.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_handles_failures_gracefully(self):
        """Should return empty string for failed storyboards instead of crashing."""
        tool = TranscriptToScenariosTool()

        mock_client = MagicMock()
        mock_client.generate_storyboard = AsyncMock(side_effect=Exception("API error"))
        tool._gemini_client = mock_client

        scenarios = [
            {
                "scenario_id": "test_1",
                "scenario_name": "Test",
                "vertical": "k12",
                "products": [],
                "setup_description": "Test",
                "creative_hook": "Test",
                "relevance_reason": "Test",
            }
        ]

        pngs = await tool.generate_all_storyboards(scenarios, "av_director")

        assert len(pngs) == 1
        assert pngs[0] == ""  # Empty string for failed generation


class TestFullPipeline:
    """Integration tests for the full pipeline (all stages mocked)."""

    @pytest.mark.asyncio
    async def test_missing_transcript_returns_error(self):
        """Should return error when no transcript provided."""
        tool = TranscriptToScenariosTool()
        result = await tool.run({})

        assert result.success is False
        assert "transcript" in result.error.lower()

    @pytest.mark.asyncio
    async def test_empty_transcript_returns_error(self):
        """Should return error when transcript is empty."""
        tool = TranscriptToScenariosTool()
        result = await tool.run({"transcript": ""})

        assert result.success is False

    @pytest.mark.asyncio
    async def test_full_pipeline_k12(self):
        """Should produce scenarios and email for a K-12 transcript."""
        tool = TranscriptToScenariosTool()

        mock_client = MagicMock()

        # Stage 1: extract_signals
        mock_client._call_deepseek = AsyncMock(
            side_effect=[
                # Call 1: extract_signals
                json.dumps(
                    {
                        "detected_vertical": "k12",
                        "detected_persona": "av_director",
                        "interests": ["football streaming"],
                        "pain_points": ["phone on tripod"],
                        "products_mentioned": [],
                        "org_size_hints": ["30 events"],
                        "buyer_signals": ["parents asking"],
                        "confidence": 0.9,
                    }
                ),
                # Call 2: match_and_customize
                json.dumps(
                    [
                        {
                            "scenario_id": "k12_sports_broadcast",
                            "customized_setup": "Stream Lincoln High's games with Pearl Nano",
                            "customized_hook": "Parents want a professional stream",
                            "relevance_reason": "Direct sports streaming match",
                        },
                    ]
                ),
                # Call 3: draft_email
                json.dumps(
                    {
                        "subject": "Streaming scenarios for your Friday night games",
                        "body": "Hi Mike, great chat about streaming your football games.",
                    }
                ),
            ]
        )

        # Stage 3: generate_storyboard
        mock_client.generate_storyboard = AsyncMock(return_value=b"fake-png")
        tool._gemini_client = mock_client

        result = await tool.run(
            {
                "transcript": K12_TRANSCRIPT,
                "prospect_name": "Mike",
                "prospect_company": "Lincoln High School",
            }
        )

        assert result.success is True
        assert result.tool_name == "transcript_to_scenarios"

        data = result.result
        assert "scenarios" in data
        assert "email_draft" in data
        assert "detected_vertical" in data
        assert data["detected_vertical"] == "k12"
        assert len(data["scenarios"]) >= 1
        assert data["scenarios"][0]["scenario_id"] == "k12_sports_broadcast"
        assert data["email_draft"]["subject"]

    @pytest.mark.asyncio
    async def test_full_pipeline_result_structure(self):
        """Should return properly structured ToolResult."""
        tool = TranscriptToScenariosTool()

        mock_client = MagicMock()
        mock_client._call_deepseek = AsyncMock(
            side_effect=[
                json.dumps(
                    {
                        "detected_vertical": "higher_ed",
                        "detected_persona": "av_director",
                        "interests": ["lecture capture"],
                        "pain_points": ["rooms are different"],
                        "products_mentioned": ["Panopto"],
                        "org_size_hints": ["150 classrooms"],
                        "buyer_signals": ["faculty complaining"],
                        "confidence": 0.85,
                    }
                ),
                json.dumps(
                    [
                        {
                            "scenario_id": "higher_ed_campus_capture",
                            "customized_setup": "Deploy Pearl Nexus in 150 classrooms",
                            "customized_hook": "NC State started with 10 rooms too",
                            "relevance_reason": "Campus-wide lecture capture",
                        }
                    ]
                ),
                json.dumps(
                    {
                        "subject": "Lecture capture scenarios for your 150 classrooms",
                        "body": "Great chat about standardizing your classrooms.",
                    }
                ),
            ]
        )
        mock_client.generate_storyboard = AsyncMock(return_value=b"png-data")
        tool._gemini_client = mock_client

        result = await tool.run({"transcript": HIGHER_ED_TRANSCRIPT})

        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.execution_time_ms >= 0

        data = result.result
        assert "signals" in data
        assert "extraction_confidence" in data
        assert data["extraction_confidence"] >= 0.0

    @pytest.mark.asyncio
    async def test_pipeline_handles_exception(self):
        """Should return error ToolResult on unexpected exception."""
        tool = TranscriptToScenariosTool()

        mock_client = MagicMock()
        mock_client._call_deepseek = AsyncMock(side_effect=Exception("API down"))
        tool._gemini_client = mock_client

        result = await tool.run({"transcript": "Some transcript"})

        assert result.success is False
        assert result.error is not None
        assert "API down" in result.error

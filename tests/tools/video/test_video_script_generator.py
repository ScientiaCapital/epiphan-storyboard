"""Tests for VideoScriptGeneratorTool."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

from src.tools.video.video_script_generator import VideoScriptGeneratorTool
from src.tools.base import ToolCategory, ToolResult


class TestVideoScriptGeneratorDefinition:
    """Tests for tool definition."""

    def test_definition_name(self):
        tool = VideoScriptGeneratorTool()
        assert tool.definition.name == "video_script_generator"

    def test_definition_category(self):
        tool = VideoScriptGeneratorTool()
        assert tool.definition.category == ToolCategory.DATA

    def test_definition_has_parameters(self):
        tool = VideoScriptGeneratorTool()
        params = tool.definition.parameters
        assert params["type"] == "object"
        assert "prospect_name" in params["properties"]
        assert "company_name" in params["properties"]
        assert "industry" in params["properties"]

    def test_definition_required_fields(self):
        tool = VideoScriptGeneratorTool()
        params = tool.definition.parameters
        required = params.get("required", [])
        assert "prospect_name" in required
        assert "company_name" in required
        assert "industry" in required

    def test_definition_description(self):
        tool = VideoScriptGeneratorTool()
        assert "script" in tool.definition.description.lower()


class TestVideoScriptGeneratorConstants:
    """Tests for tool constants."""

    def test_default_model_is_deepseek(self):
        tool = VideoScriptGeneratorTool()
        assert "deepseek" in tool.DEFAULT_MODEL.lower()

    def test_fallback_model_is_qwen(self):
        tool = VideoScriptGeneratorTool()
        assert "qwen" in tool.FALLBACK_MODEL.lower()

    def test_industry_contexts_exist(self):
        tool = VideoScriptGeneratorTool()
        expected_industries = ["solar", "hvac", "electrical", "mep", "roofing"]
        for industry in expected_industries:
            assert industry in tool.INDUSTRY_CONTEXTS


class TestVideoScriptGeneratorRun:
    """Tests for tool execution."""

    @pytest.mark.asyncio
    async def test_missing_prospect_name(self):
        """Test error when prospect_name is missing."""
        tool = VideoScriptGeneratorTool()
        result = await tool.run({
            "company_name": "SunPower Solar",
            "industry": "solar",
        })
        assert result.success is False

    @pytest.mark.asyncio
    async def test_missing_company_name(self):
        """Test error when company_name is missing."""
        tool = VideoScriptGeneratorTool()
        result = await tool.run({
            "prospect_name": "John Smith",
            "industry": "solar",
        })
        assert result.success is False

    @pytest.mark.asyncio
    async def test_missing_industry(self):
        """Test error when industry is missing."""
        tool = VideoScriptGeneratorTool()
        result = await tool.run({
            "prospect_name": "John Smith",
            "company_name": "SunPower Solar",
        })
        assert result.success is False


class TestIndustryContexts:
    """Tests for industry-specific context."""

    def test_solar_context_has_pain_points(self):
        tool = VideoScriptGeneratorTool()
        solar = tool.INDUSTRY_CONTEXTS.get("solar", {})
        assert "pain_points" in solar
        assert len(solar["pain_points"]) > 0

    def test_hvac_context_has_proof_examples(self):
        tool = VideoScriptGeneratorTool()
        hvac = tool.INDUSTRY_CONTEXTS.get("hvac", {})
        assert "proof_examples" in hvac
        assert len(hvac["proof_examples"]) > 0

    def test_all_industries_have_required_keys(self):
        tool = VideoScriptGeneratorTool()
        required_keys = ["pain_points", "proof_examples"]
        for industry, context in tool.INDUSTRY_CONTEXTS.items():
            for key in required_keys:
                assert key in context, f"{industry} missing {key}"

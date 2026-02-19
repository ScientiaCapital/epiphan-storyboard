"""Tests for auto-storyboard generation on connector sync."""

import asyncio
import base64
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.connectors.base import ConnectorInstance, ConnectorStatus, ConnectorType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_hubspot_instance() -> ConnectorInstance:
    """Create a mock HubSpot connector instance."""
    return ConnectorInstance(
        id="inst-001",
        org_id="org-001",
        connector_type=ConnectorType.HUBSPOT,
        status=ConnectorStatus.CONNECTED,
        config={"api_key": "test-token"},
    )


def _make_clari_instance() -> ConnectorInstance:
    """Create a mock Clari connector instance."""
    return ConnectorInstance(
        id="inst-002",
        org_id="org-001",
        connector_type=ConnectorType.CLARI,
        status=ConnectorStatus.CONNECTED,
        config={"api_key": "test-key", "api_password": "test-pass"},
    )


def _make_gong_instance() -> ConnectorInstance:
    """Create a mock Gong connector instance (not supported for auto-storyboard)."""
    return ConnectorInstance(
        id="inst-003",
        org_id="org-001",
        connector_type=ConnectorType.GONG,
        status=ConnectorStatus.CONNECTED,
        config={"access_token": "test-token"},
    )


FAKE_PNG_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100).decode()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_storyboard_hubspot_success(tmp_path: Path):
    """Test auto-storyboard generation for HubSpot calls."""
    from src.routers.connectors import _auto_generate_storyboards

    mock_call = MagicMock()
    mock_call.id = "call-123"
    mock_call.properties.hs_call_body = "A" * 200

    mock_response = MagicMock()
    mock_response.results = [mock_call]

    mock_client = AsyncMock()
    mock_client.get_calls = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    mock_tool_result = MagicMock()
    mock_tool_result.success = True
    mock_tool_result.result = {
        "scenarios": [
            {"scenario_id": "k12_sports_broadcast", "storyboard_png": FAKE_PNG_B64}
        ]
    }

    instance = _make_hubspot_instance()

    with (
        patch(
            "src.connectors.hubspot.client.HubSpotAPIClient",
            return_value=mock_client,
        ),
        patch(
            "src.connectors.hubspot.transformer.HubSpotTransformer"
        ) as mock_transformer_cls,
        patch(
            "src.tools.storyboard.transcript_to_scenarios.TranscriptToScenariosTool"
        ) as mock_tool_cls,
    ):
        mock_transformer = mock_transformer_cls.return_value
        mock_transformer.call_to_transcript_request.return_value = {
            "transcript": "A" * 200,
            "prospect_name": "Test User",
            "prospect_company": "Test Corp",
        }

        mock_tool = mock_tool_cls.return_value
        mock_tool.run = AsyncMock(return_value=mock_tool_result)

        await _auto_generate_storyboards(instance)

    mock_client.get_calls.assert_awaited_once()
    mock_tool.run.assert_awaited_once()


@pytest.mark.asyncio
async def test_auto_storyboard_skips_short_transcripts():
    """Test that calls with short transcripts (<= 100 chars) are skipped."""
    from src.routers.connectors import _auto_generate_storyboards

    mock_call = MagicMock()
    mock_call.id = "call-short"
    mock_call.properties.hs_call_body = "Too short"

    mock_response = MagicMock()
    mock_response.results = [mock_call]

    mock_client = AsyncMock()
    mock_client.get_calls = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    instance = _make_hubspot_instance()

    with patch(
        "src.connectors.hubspot.client.HubSpotAPIClient",
        return_value=mock_client,
    ):
        # Should complete without calling the pipeline
        await _auto_generate_storyboards(instance)


@pytest.mark.asyncio
async def test_auto_storyboard_skips_unsupported_connector():
    """Test that non-HubSpot/Clari connectors are silently skipped."""
    from src.routers.connectors import _auto_generate_storyboards

    instance = _make_gong_instance()
    # Should return immediately without any API calls
    await _auto_generate_storyboards(instance)


@pytest.mark.asyncio
async def test_auto_storyboard_handles_pipeline_failure():
    """Test that pipeline failure is logged but doesn't raise."""
    from src.routers.connectors import _auto_generate_storyboards

    mock_call = MagicMock()
    mock_call.id = "call-fail"
    mock_call.properties.hs_call_body = "A" * 200

    mock_response = MagicMock()
    mock_response.results = [mock_call]

    mock_client = AsyncMock()
    mock_client.get_calls = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    mock_tool_result = MagicMock()
    mock_tool_result.success = False
    mock_tool_result.error = "API error"

    instance = _make_hubspot_instance()

    with (
        patch(
            "src.connectors.hubspot.client.HubSpotAPIClient",
            return_value=mock_client,
        ),
        patch(
            "src.connectors.hubspot.transformer.HubSpotTransformer"
        ) as mock_transformer_cls,
        patch(
            "src.tools.storyboard.transcript_to_scenarios.TranscriptToScenariosTool"
        ) as mock_tool_cls,
    ):
        mock_transformer = mock_transformer_cls.return_value
        mock_transformer.call_to_transcript_request.return_value = {
            "transcript": "A" * 200,
        }

        mock_tool = mock_tool_cls.return_value
        mock_tool.run = AsyncMock(return_value=mock_tool_result)

        # Should NOT raise despite pipeline failure
        await _auto_generate_storyboards(instance)


@pytest.mark.asyncio
async def test_auto_storyboard_handles_exception():
    """Test that exceptions during auto-generation are caught and logged."""
    from src.routers.connectors import _auto_generate_storyboards

    instance = _make_hubspot_instance()

    with patch(
        "src.connectors.hubspot.client.HubSpotAPIClient",
        side_effect=Exception("Connection refused"),
    ):
        # Should NOT raise
        await _auto_generate_storyboards(instance)


@pytest.mark.asyncio
async def test_auto_storyboard_respects_semaphore():
    """Test that semaphore limits concurrent pipeline runs to 3."""
    from src.routers.connectors import _auto_generate_storyboards

    calls = []
    for i in range(5):
        mock_call = MagicMock()
        mock_call.id = f"call-{i}"
        mock_call.properties.hs_call_body = f"Transcript {i} " * 50
        calls.append(mock_call)

    mock_response = MagicMock()
    mock_response.results = calls

    mock_client = AsyncMock()
    mock_client.get_calls = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    mock_tool_result = MagicMock()
    mock_tool_result.success = True
    mock_tool_result.result = {"scenarios": []}

    max_concurrent = 0
    current_concurrent = 0
    lock = asyncio.Lock()

    async def tracked_run(args):
        nonlocal max_concurrent, current_concurrent
        async with lock:
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
        await asyncio.sleep(0.01)
        async with lock:
            current_concurrent -= 1
        return mock_tool_result

    instance = _make_hubspot_instance()

    with (
        patch(
            "src.connectors.hubspot.client.HubSpotAPIClient",
            return_value=mock_client,
        ),
        patch(
            "src.connectors.hubspot.transformer.HubSpotTransformer"
        ) as mock_transformer_cls,
        patch(
            "src.tools.storyboard.transcript_to_scenarios.TranscriptToScenariosTool"
        ) as mock_tool_cls,
    ):
        mock_transformer = mock_transformer_cls.return_value
        mock_transformer.call_to_transcript_request.return_value = {
            "transcript": "A" * 200,
        }

        mock_tool = mock_tool_cls.return_value
        mock_tool.run = AsyncMock(side_effect=tracked_run)

        await _auto_generate_storyboards(instance)

    assert max_concurrent <= 3
    assert mock_tool.run.await_count == 5


@pytest.mark.asyncio
async def test_auto_storyboard_no_token_hubspot():
    """Test that missing HubSpot token returns early without error."""
    from src.routers.connectors import _auto_generate_storyboards

    instance = ConnectorInstance(
        id="inst-no-token",
        org_id="org-001",
        connector_type=ConnectorType.HUBSPOT,
        status=ConnectorStatus.CONNECTED,
        config={},
    )

    # Should return early without error
    await _auto_generate_storyboards(instance)

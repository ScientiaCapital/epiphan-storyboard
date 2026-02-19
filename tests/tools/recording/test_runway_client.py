"""
Tests for RunwayClient.

Following TDD: Write tests FIRST, watch them fail, then implement.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx


class TestRunwayClientInit:
    """Tests for RunwayClient initialization."""

    def test_init_with_default_config(self):
        """RunwayClient should initialize with default config."""
        from src.tools.recording.runway_client import RunwayClient

        client = RunwayClient()
        assert client.config is not None
        assert client.config.base_url == "https://api.runwayml.com/v1"
        assert client.config.default_model == "gen3a_turbo"

    def test_init_with_custom_config(self):
        """RunwayClient should accept custom config."""
        from src.tools.recording.runway_client import RunwayClient
        from src.tools.recording.config import RunwayConfig

        config = RunwayConfig(
            api_key="custom_key",
            default_model="gen3a",
            timeout=60,
        )
        client = RunwayClient(config=config)
        assert client.config.api_key == "custom_key"
        assert client.config.default_model == "gen3a"
        assert client.config.timeout == 60


class TestRunwayClientTextToVideo:
    """Tests for text-to-video generation."""

    @pytest.mark.asyncio
    async def test_generate_from_text_requires_api_key(self):
        """generate_from_text should raise if API key missing."""
        from src.tools.recording.runway_client import RunwayClient
        from src.tools.recording.config import RunwayConfig

        config = RunwayConfig(api_key=None)
        client = RunwayClient(config=config)

        with pytest.raises(ValueError, match="API key"):
            await client.generate_from_text(prompt="A sunset over mountains")

    @pytest.mark.asyncio
    async def test_generate_from_text_requires_prompt(self):
        """generate_from_text should raise if prompt empty."""
        from src.tools.recording.runway_client import RunwayClient
        from src.tools.recording.config import RunwayConfig

        config = RunwayConfig(api_key="test_key")
        client = RunwayClient(config=config)

        with pytest.raises(ValueError, match="prompt"):
            await client.generate_from_text(prompt="")

    @pytest.mark.asyncio
    async def test_generate_from_text_success(self):
        """generate_from_text should return task ID on success."""
        from src.tools.recording.runway_client import RunwayClient
        from src.tools.recording.config import RunwayConfig

        config = RunwayConfig(api_key="test_key")
        client = RunwayClient(config=config)

        mock_response = {
            "id": "task_123",
            "status": "PENDING",
        }

        with patch.object(client, "_call_api_with_retry", return_value=mock_response):
            result = await client.generate_from_text(prompt="A sunset over mountains")

        assert result["id"] == "task_123"
        assert result["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_generate_from_text_uses_default_model(self):
        """generate_from_text should use default model from config."""
        from src.tools.recording.runway_client import RunwayClient
        from src.tools.recording.config import RunwayConfig

        config = RunwayConfig(api_key="test_key", default_model="gen3a")
        client = RunwayClient(config=config)

        called_with = {}

        async def capture_call(method, endpoint, payload):
            called_with.update(payload)
            return {"id": "task_123", "status": "PENDING"}

        with patch.object(client, "_call_api_with_retry", side_effect=capture_call):
            await client.generate_from_text(prompt="Test prompt")

        assert called_with.get("model") == "gen3a"

    @pytest.mark.asyncio
    async def test_generate_from_text_custom_duration(self):
        """generate_from_text should accept custom duration."""
        from src.tools.recording.runway_client import RunwayClient
        from src.tools.recording.config import RunwayConfig

        config = RunwayConfig(api_key="test_key")
        client = RunwayClient(config=config)

        called_with = {}

        async def capture_call(method, endpoint, payload):
            called_with.update(payload)
            return {"id": "task_123", "status": "PENDING"}

        with patch.object(client, "_call_api_with_retry", side_effect=capture_call):
            await client.generate_from_text(prompt="Test", duration=10)

        assert called_with.get("duration") == 10


class TestRunwayClientImageToVideo:
    """Tests for image-to-video generation."""

    @pytest.mark.asyncio
    async def test_generate_from_image_requires_api_key(self):
        """generate_from_image should raise if API key missing."""
        from src.tools.recording.runway_client import RunwayClient
        from src.tools.recording.config import RunwayConfig

        config = RunwayConfig(api_key=None)
        client = RunwayClient(config=config)

        with pytest.raises(ValueError, match="API key"):
            await client.generate_from_image(
                image_data="base64data",
                prompt="Camera slowly zooms in",
            )

    @pytest.mark.asyncio
    async def test_generate_from_image_requires_image_data(self):
        """generate_from_image should raise if image_data empty."""
        from src.tools.recording.runway_client import RunwayClient
        from src.tools.recording.config import RunwayConfig

        config = RunwayConfig(api_key="test_key")
        client = RunwayClient(config=config)

        with pytest.raises(ValueError, match="image"):
            await client.generate_from_image(image_data="", prompt="Zoom in")

    @pytest.mark.asyncio
    async def test_generate_from_image_success(self):
        """generate_from_image should return task ID on success."""
        from src.tools.recording.runway_client import RunwayClient
        from src.tools.recording.config import RunwayConfig

        config = RunwayConfig(api_key="test_key")
        client = RunwayClient(config=config)

        mock_response = {
            "id": "task_456",
            "status": "PENDING",
        }

        with patch.object(client, "_call_api_with_retry", return_value=mock_response):
            result = await client.generate_from_image(
                image_data="base64data",
                prompt="Camera slowly zooms in",
            )

        assert result["id"] == "task_456"


class TestRunwayClientGetStatus:
    """Tests for generation status polling."""

    @pytest.mark.asyncio
    async def test_get_generation_status_success(self):
        """get_generation_status should return task status."""
        from src.tools.recording.runway_client import RunwayClient
        from src.tools.recording.config import RunwayConfig

        config = RunwayConfig(api_key="test_key")
        client = RunwayClient(config=config)

        mock_response = {
            "id": "task_123",
            "status": "SUCCEEDED",
            "output": ["https://cdn.runway.com/video.mp4"],
            "progress": 100,
        }

        with patch.object(client, "_call_api_with_retry", return_value=mock_response):
            result = await client.get_generation_status("task_123")

        assert result["status"] == "SUCCEEDED"
        assert "output" in result

    @pytest.mark.asyncio
    async def test_get_generation_status_pending(self):
        """get_generation_status should return progress for pending tasks."""
        from src.tools.recording.runway_client import RunwayClient
        from src.tools.recording.config import RunwayConfig

        config = RunwayConfig(api_key="test_key")
        client = RunwayClient(config=config)

        mock_response = {
            "id": "task_123",
            "status": "RUNNING",
            "progress": 45,
        }

        with patch.object(client, "_call_api_with_retry", return_value=mock_response):
            result = await client.get_generation_status("task_123")

        assert result["status"] == "RUNNING"
        assert result["progress"] == 45


class TestRunwayClientDownload:
    """Tests for video download."""

    @pytest.mark.asyncio
    async def test_download_video_success(self):
        """download_video should save video to path."""
        from src.tools.recording.runway_client import RunwayClient
        from src.tools.recording.config import RunwayConfig
        from pathlib import Path
        import tempfile

        config = RunwayConfig(api_key="test_key")
        client = RunwayClient(config=config)

        # Mock status response
        mock_status = {
            "id": "task_123",
            "status": "SUCCEEDED",
            "output": ["https://cdn.runway.com/video.mp4"],
        }

        # Mock video download
        mock_video_content = b"fake video content"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.mp4"

            async def mock_get_status(task_id):
                return mock_status

            with patch.object(client, "get_generation_status", side_effect=mock_get_status):
                # Mock the httpx get call
                mock_response = MagicMock()
                mock_response.content = mock_video_content
                mock_response.raise_for_status = MagicMock()

                async def mock_get(*args, **kwargs):
                    return mock_response

                with patch("httpx.AsyncClient.get", side_effect=mock_get):
                    result = await client.download_video("task_123", output_path)

            assert result == str(output_path)
            assert output_path.exists()
            assert output_path.read_bytes() == mock_video_content

    @pytest.mark.asyncio
    async def test_download_video_not_ready(self):
        """download_video should raise if generation not complete."""
        from src.tools.recording.runway_client import RunwayClient
        from src.tools.recording.config import RunwayConfig
        from pathlib import Path

        config = RunwayConfig(api_key="test_key")
        client = RunwayClient(config=config)

        mock_status = {
            "id": "task_123",
            "status": "RUNNING",
            "progress": 50,
        }

        with patch.object(client, "get_generation_status", return_value=mock_status):
            with pytest.raises(ValueError, match="not complete"):
                await client.download_video("task_123", Path("/tmp/output.mp4"))


class TestRunwayClientRetry:
    """Tests for API retry logic."""

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self):
        """Should retry with exponential backoff on 429."""
        from src.tools.recording.runway_client import RunwayClient
        from src.tools.recording.config import RunwayConfig

        config = RunwayConfig(api_key="test_key")
        client = RunwayClient(config=config)

        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            if call_count < 3:
                mock_resp.status_code = 429
                mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Rate limited", request=MagicMock(), response=mock_resp
                )
            else:
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"id": "task_123"}
                mock_resp.raise_for_status.return_value = None
            return mock_resp

        with patch("httpx.AsyncClient.post", side_effect=mock_request):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client._call_api_with_retry("POST", "/text-to-video", {"prompt": "test"})

        assert result["id"] == "task_123"
        assert call_count == 3

"""Tests for image-to-image conditioning + product grounding in generation.

Covers Agent B's wiring:
- `StoryboardUnderstanding.recommended_products` survives into generation and the
  product visual block is injected into the prompt.
- `generate_storyboard(reference_images=...)` attaches the bytes on BOTH model
  paths (Google genai SDK + OpenRouter), and degrades to text-only when None.

All model calls are mocked — no live API.
"""

import base64
import sys
import types as _pytypes
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.storyboard.gemini_client import (
    GeminiConfig,
    GeminiStoryboardClient,
    StoryboardUnderstanding,
    _sniff_image_mime,
)


class TestSniffImageMime:
    def test_png(self):
        assert _sniff_image_mime(b"\x89PNG\r\n\x1a\n") == "image/png"

    def test_jpeg(self):
        assert _sniff_image_mime(b"\xff\xd8\xff\xe0abc") == "image/jpeg"

    def test_webp(self):
        assert _sniff_image_mime(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"

    def test_gif(self):
        assert _sniff_image_mime(b"GIF89a...") == "image/gif"

    def test_unknown_defaults_png(self):
        assert _sniff_image_mime(b"random-bytes") == "image/png"


def _fake_genai_modules():
    """Build a fake `google.genai` package — the real SDK is serverless-only
    and not installed in the test env. Returns the dict for patch.dict(sys.modules).
    `types.Part.from_bytes` returns the sentinel "IMG_PART" so tests can count it.
    """
    fake_types = _pytypes.ModuleType("google.genai.types")
    fake_types.Part = MagicMock()
    fake_types.Part.from_bytes = MagicMock(return_value="IMG_PART")
    fake_types.GenerateContentConfig = MagicMock(return_value=MagicMock())
    fake_genai = _pytypes.ModuleType("google.genai")
    fake_genai.types = fake_types
    fake_google = _pytypes.ModuleType("google")
    fake_google.genai = fake_genai
    return {
        "google": fake_google,
        "google.genai": fake_genai,
        "google.genai.types": fake_types,
    }


def _understanding(**overrides) -> StoryboardUnderstanding:
    base = {
        "headline": "Direct-to-CMS lecture capture",
        "what_it_does": "Records lectures straight to the CMS",
        "business_value": "Saves 4 hours/week",
        "who_benefits": "AV directors",
        "differentiator": "No encoder PC required",
        "pain_point_addressed": "Manual file shuffling",
    }
    base.update(overrides)
    return StoryboardUnderstanding(**base)


class TestRecommendedProductsField:
    def test_field_defaults_empty(self):
        assert _understanding().recommended_products == []

    def test_field_populated_from_extraction_json(self):
        # StoryboardUnderstanding(**data) is how extraction parses LLM JSON.
        u = StoryboardUnderstanding(
            headline="h",
            what_it_does="w",
            business_value="b",
            who_benefits="wb",
            differentiator="d",
            pain_point_addressed="p",
            recommended_products=["ec20_ptz", "pearl_mini"],
        )
        assert u.recommended_products == ["ec20_ptz", "pearl_mini"]


class TestContentSectionGrounding:
    def test_product_block_injected_when_recommended(self):
        client = GeminiStoryboardClient(GeminiConfig(api_key="real-key"))
        from src.tools.storyboard.epiphan_presets import (
            EPIPHAN_ICP,
            get_audience_persona,
        )

        persona = get_audience_persona("av_director", EPIPHAN_ICP)
        section = client._build_generation_content_section(
            _understanding(recommended_products=["ec20_ptz"]),
            "av_director",
            persona,
        )
        assert "PRODUCTS TO DEPICT" in section
        assert "20x" in section  # EC20 visual trait reaches the prompt

    def test_no_product_block_when_empty(self):
        client = GeminiStoryboardClient(GeminiConfig(api_key="real-key"))
        from src.tools.storyboard.epiphan_presets import (
            EPIPHAN_ICP,
            get_audience_persona,
        )

        persona = get_audience_persona("av_director", EPIPHAN_ICP)
        section = client._build_generation_content_section(
            _understanding(recommended_products=[]),
            "av_director",
            persona,
        )
        assert "PRODUCTS TO DEPICT" not in section


def _genai_response_with_image() -> MagicMock:
    part = MagicMock()
    part.inline_data = MagicMock()
    part.inline_data.data = b"PNGBYTES"
    candidate = MagicMock()
    candidate.content.parts = [part]
    resp = MagicMock()
    resp.candidates = [candidate]
    return resp


class TestGenaiPathImageToImage:
    @pytest.mark.asyncio
    async def test_reference_images_attached_as_parts(self):
        client = GeminiStoryboardClient(GeminiConfig(api_key="real-key"))
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = (
            _genai_response_with_image()
        )

        with (
            patch.dict(sys.modules, _fake_genai_modules()),
            patch.object(client, "_ensure_client"),
            patch.object(client, "_client", mock_client, create=True),
        ):
            out = await client.generate_storyboard(
                _understanding(),
                reference_images=[b"room-photo-1", b"room-photo-2"],
            )

        assert out == b"PNGBYTES"
        kwargs = mock_client.models.generate_content.call_args.kwargs
        contents = kwargs["contents"]
        assert isinstance(contents, list)
        # prompt string first, then one Part per reference image
        assert isinstance(contents[0], str)
        assert contents.count("IMG_PART") == 2

    @pytest.mark.asyncio
    async def test_no_reference_images_keeps_text_only(self):
        client = GeminiStoryboardClient(GeminiConfig(api_key="real-key"))
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = (
            _genai_response_with_image()
        )

        with (
            patch.dict(sys.modules, _fake_genai_modules()),
            patch.object(client, "_ensure_client"),
            patch.object(client, "_client", mock_client, create=True),
        ):
            await client.generate_storyboard(_understanding(), reference_images=None)

        contents = mock_client.models.generate_content.call_args.kwargs["contents"]
        assert isinstance(contents, str)  # unchanged text-only shape


class TestOpenRouterPathImageToImage:
    def _client_no_google(self) -> GeminiStoryboardClient:
        return GeminiStoryboardClient(
            GeminiConfig(api_key="placeholder", openrouter_api_key="or-key")
        )

    @pytest.mark.asyncio
    async def test_reference_images_build_multimodal_messages(self):
        client = self._client_no_google()
        captured: dict = {}

        async def fake_openrouter(prompt, reference_images=None):
            captured["prompt"] = prompt
            captured["reference_images"] = reference_images
            return b"PNG"

        with patch.object(
            client, "_generate_image_via_openrouter", side_effect=fake_openrouter
        ):
            await client.generate_storyboard(
                _understanding(), reference_images=[b"abc"]
            )
        assert captured["reference_images"] == [b"abc"]

    @pytest.mark.asyncio
    async def test_openrouter_payload_has_image_url_parts(self):
        client = self._client_no_google()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        b64 = base64.b64encode(b"GENERATED").decode()
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "images": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{b64}"
                                },
                            }
                        ]
                    }
                }
            ]
        }
        mock_async_client = MagicMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)
        mock_async_client.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_async_client):
            out = await client._generate_image_via_openrouter(
                "draw it", reference_images=[b"room"]
            )

        assert out == b"GENERATED"
        payload = mock_async_client.post.call_args.kwargs["json"]
        content = payload["messages"][0]["content"]
        assert isinstance(content, list)
        assert any(p.get("type") == "image_url" for p in content)
        assert any(p.get("type") == "text" for p in content)

    @pytest.mark.asyncio
    async def test_openrouter_text_only_when_no_reference(self):
        client = self._client_no_google()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        b64 = base64.b64encode(b"GENERATED").decode()
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "images": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{b64}"
                                },
                            }
                        ]
                    }
                }
            ]
        }
        mock_async_client = MagicMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)
        mock_async_client.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_async_client):
            await client._generate_image_via_openrouter("draw it")

        payload = mock_async_client.post.call_args.kwargs["json"]
        assert payload["messages"][0]["content"] == "draw it"  # unchanged

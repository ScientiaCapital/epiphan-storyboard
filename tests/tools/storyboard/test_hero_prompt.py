"""Tests for the TEXT-FREE hero-image prompt (Track C).

When ``text_free_hero=True`` the diffusion model must paint ONLY an editorial
illustration — no headline, no copy, no labels. All text is composited on
canvas client-side, so the model never gets a chance to garble it. These tests
pin that the hero prompt (a) forbids text emphatically, (b) does NOT smuggle the
extracted copy into the prompt, (c) keeps the brand palette, and (d) preserves
product grounding.
"""

from src.tools.storyboard.gemini_client import (
    GeminiStoryboardClient,
    StoryboardUnderstanding,
)


def _client() -> GeminiStoryboardClient:
    # The prompt builder is pure (no API key / network), so bypass __init__.
    return GeminiStoryboardClient.__new__(GeminiStoryboardClient)


def _understanding(**overrides) -> StoryboardUnderstanding:
    base = {
        "headline": "Walk SD cards no more",
        "tagline": "One box from capture to cloud",
        "what_it_does": "Pearl Nexus records every room without an operator.",
        "business_value": "Saves $6,600 per room vs traditional AV",
        "who_benefits": "AV Directors",
        "differentiator": "Only Pearl pairs capture with fleet management",
        "pain_point_addressed": "Manual SD card collection after every lecture",
        "recommended_products": ["pearl_nexus"],
    }
    base.update(overrides)
    return StoryboardUnderstanding(**base)


def test_hero_prompt_forbids_text() -> None:
    prompt = _client()._build_hero_prompt(_understanding(), vertical="higher_ed")
    low = prompt.lower()
    assert "no text" in low
    assert "no words" in low
    assert "no labels" in low


def test_hero_prompt_excludes_extracted_copy() -> None:
    u = _understanding()
    prompt = _client()._build_hero_prompt(u, vertical="higher_ed")
    # The literal copy must never reach the diffusion model.
    assert u.headline not in prompt
    assert "$6,600" not in prompt
    assert u.pain_point_addressed not in prompt


def test_hero_prompt_keeps_brand_palette() -> None:
    prompt = _client()._build_hero_prompt(_understanding(), vertical="higher_ed")
    assert "#1D2B51" in prompt
    assert "#8CBE3F" in prompt


def test_hero_prompt_grounds_recommended_product() -> None:
    prompt = _client()._build_hero_prompt(
        _understanding(recommended_products=["pearl_nexus"]), vertical="higher_ed"
    )
    assert "Pearl Nexus" in prompt


def test_hero_prompt_no_product_block_when_empty() -> None:
    # No recommended product → still a valid, text-free prompt.
    prompt = _client()._build_hero_prompt(
        _understanding(recommended_products=[]), vertical=None
    )
    assert "no text" in prompt.lower()

"""Field-aware competitor + brand-voice checks in the quality gate.

Regression: an Epiphan-branded card shipped with Sony positioned as the hero
(headline "Sony's seamless proxy workflow revolutionizes live production").
Three gaps let it through: the gate was never wired into the generation path,
its competitor list missed Sony entirely, and competitor mentions were
warnings only. These tests pin the fixed behavior:

* Competitor in a HERO field (headline/tagline/what_it_does/differentiator/
  business_value) -> critical, gate fails.
* Competitor in a CONTRAST field (pain_point_addressed/frankenstack/
  raw_extracted_text) -> allowed; that's the Challenger before-state.
* Competitor anywhere else -> warning (pre-existing behavior, kept).
* Brand-voice hype words ("revolutionizes", "game-changing") in hero
  fields -> warning.
"""

from src.tools.storyboard.epiphan_presets import COMPETITOR_TOKENS
from src.tools.storyboard.quality_gate import (
    QualityReport,
    find_hero_competitors,
    run_quality_gate,
)


def _understanding(**overrides) -> dict:
    """A clean, Epiphan-positioned understanding dict."""
    base = {
        "headline": "Stop babysitting AV carts",
        "tagline": "One box from capture to cloud",
        "what_it_does": "Pearl Mini records and streams every room without an operator.",
        "business_value": "Cuts 12 truck rolls per month",
        "who_benefits": "AV Directors",
        "differentiator": "Only Pearl pairs capture with fleet management via Epiphan Edge",
        "pain_point_addressed": "Manual SD card collection after every event",
        "recommended_products": ["pearl_mini"],
    }
    base.update(overrides)
    return base


def _brand_issues(report: QualityReport) -> list:
    return [i for i in report.issues if i.category == "brand"]


class TestCompetitorTokens:
    def test_includes_broadcast_vendors(self):
        for vendor in ("sony", "panasonic", "blackmagic", "extron", "matrox"):
            assert vendor in COMPETITOR_TOKENS

    def test_excludes_epiphan_and_protocols(self):
        for token in ("epiphan", "pearl", "ec20", "ndi", "srt", "rtmp", "dante"):
            assert token not in COMPETITOR_TOKENS


class TestCompetitorAsHero:
    def test_sony_in_headline_is_critical(self):
        report = run_quality_gate(
            _understanding(
                headline="Sony's seamless proxy workflow transforms live production"
            ),
            audience="production_director",
        )
        criticals = [i for i in _brand_issues(report) if i.severity == "critical"]
        assert criticals, "Sony in headline must be a critical brand issue"
        assert report.passed is False

    def test_competitor_in_differentiator_is_critical(self):
        report = run_quality_gate(
            _understanding(
                differentiator="Only Blackmagic offers simultaneous proxy uploads"
            ),
            audience="av_director",
        )
        criticals = [i for i in _brand_issues(report) if i.severity == "critical"]
        assert criticals
        assert report.passed is False

    def test_competitor_in_contrast_fields_is_allowed(self):
        report = run_quality_gate(
            _understanding(
                pain_point_addressed="Their Sony proxy workflow drops files mid-event",
                frankenstack="Sony cameras + vMix + manual uploads",
            ),
            audience="av_director",
        )
        assert not _brand_issues(report), (
            "Competitors in the before-state contrast fields are the "
            "Challenger pattern — must not be flagged"
        )

    def test_competitor_in_other_field_is_warning_not_critical(self):
        report = run_quality_gate(
            _understanding(who_benefits="Sony camera operators"),
            audience="av_director",
        )
        issues = _brand_issues(report)
        assert issues
        assert all(i.severity == "warning" for i in issues)

    def test_word_boundary_no_false_positive(self):
        report = run_quality_gate(
            _understanding(headline="Sonya's team stopped babysitting AV"),
            audience="av_director",
        )
        assert not [i for i in _brand_issues(report) if i.severity == "critical"]

    def test_find_hero_competitors_maps_field_to_vendors(self):
        hits = find_hero_competitors(
            _understanding(
                headline="Sony's proxy workflow wins",
                differentiator="Panasonic fleet tools included",
            )
        )
        assert "sony" in hits["headline"]
        assert "panasonic" in hits["differentiator"]
        assert "pain_point_addressed" not in hits

    def test_find_hero_competitors_empty_for_clean_copy(self):
        assert find_hero_competitors(_understanding()) == {}


class TestBrandVoice:
    def test_revolutionizes_in_headline_warns(self):
        report = run_quality_gate(
            _understanding(headline="Pearl revolutionizes live production"),
            audience="av_director",
        )
        voice = [i for i in report.issues if i.category == "voice"]
        assert voice
        assert all(i.severity == "warning" for i in voice)

    def test_game_changing_warns(self):
        report = run_quality_gate(
            _understanding(what_it_does="A game-changing capture appliance."),
            audience="av_director",
        )
        assert [i for i in report.issues if i.category == "voice"]

    def test_exclamation_point_warns(self):
        report = run_quality_gate(
            _understanding(tagline="Capture everything, everywhere!"),
            audience="av_director",
        )
        assert [i for i in report.issues if i.category == "voice"]

    def test_clean_copy_has_no_voice_issues(self):
        report = run_quality_gate(_understanding(), audience="av_director")
        assert not [i for i in report.issues if i.category == "voice"]


class TestReportHelpers:
    def test_has_critical_filters_by_category(self):
        report = run_quality_gate(
            _understanding(headline="Sony's proxy workflow wins"),
            audience="av_director",
        )
        assert report.has_critical("brand") is True
        assert report.has_critical("nsttd") is False

    def test_clean_understanding_passes(self):
        report = run_quality_gate(_understanding(), audience="av_director")
        assert report.passed is True
        assert report.has_critical("brand") is False

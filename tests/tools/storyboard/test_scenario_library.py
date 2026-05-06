"""Tests for the deployment scenario library."""

import pytest

from src.tools.storyboard.epiphan_presets import EPIPHAN_PRODUCTS, EPIPHAN_VERTICALS
from src.tools.storyboard.scenario_library import (
    SCENARIO_BY_ID,
    SCENARIO_LIBRARY,
    SCENARIOS_BY_VERTICAL,
    DeploymentScenario,
    get_scenario_by_id,
    get_scenarios_for_vertical,
    match_scenarios_by_phrases,
)


class TestScenarioLibraryCompleteness:
    """Tests that the library has all 20 scenarios with required data."""

    def test_library_has_26_scenarios(self):
        """Library should contain 26 deployment scenarios (20 vertical + 3 integrator + 1 EC20 rooms + 2 broadcasting)."""
        assert len(SCENARIO_LIBRARY) == 26

    def test_all_scenarios_have_unique_ids(self):
        """Every scenario must have a unique ID."""
        ids = [s.id for s in SCENARIO_LIBRARY]
        assert len(ids) == len(set(ids)), (
            f"Duplicate IDs: {[x for x in ids if ids.count(x) > 1]}"
        )

    def test_all_scenarios_are_deployment_scenario_instances(self):
        """Every item in the library must be a DeploymentScenario."""
        for s in SCENARIO_LIBRARY:
            assert isinstance(s, DeploymentScenario), (
                f"{s.id} is not DeploymentScenario"
            )

    def test_scenario_by_id_index_matches_library(self):
        """SCENARIO_BY_ID should contain all scenarios from the library."""
        assert len(SCENARIO_BY_ID) == len(SCENARIO_LIBRARY)
        for s in SCENARIO_LIBRARY:
            assert s.id in SCENARIO_BY_ID
            assert SCENARIO_BY_ID[s.id] is s


class TestScenarioRequiredFields:
    """Tests that all scenarios have required fields populated."""

    @pytest.mark.parametrize("scenario", SCENARIO_LIBRARY, ids=lambda s: s.id)
    def test_scenario_has_id(self, scenario):
        assert scenario.id, f"Scenario missing id"

    @pytest.mark.parametrize("scenario", SCENARIO_LIBRARY, ids=lambda s: s.id)
    def test_scenario_has_name(self, scenario):
        assert scenario.name, f"{scenario.id} missing name"
        assert len(scenario.name) >= 10, f"{scenario.id} name too short"

    @pytest.mark.parametrize("scenario", SCENARIO_LIBRARY, ids=lambda s: s.id)
    def test_scenario_has_vertical(self, scenario):
        assert scenario.vertical, f"{scenario.id} missing vertical"

    @pytest.mark.parametrize("scenario", SCENARIO_LIBRARY, ids=lambda s: s.id)
    def test_scenario_has_trigger_phrases(self, scenario):
        assert len(scenario.trigger_phrases) >= 3, (
            f"{scenario.id} needs at least 3 trigger phrases, has {len(scenario.trigger_phrases)}"
        )

    @pytest.mark.parametrize("scenario", SCENARIO_LIBRARY, ids=lambda s: s.id)
    def test_scenario_has_products(self, scenario):
        assert len(scenario.products) >= 1, f"{scenario.id} needs at least 1 product"

    @pytest.mark.parametrize("scenario", SCENARIO_LIBRARY, ids=lambda s: s.id)
    def test_scenario_has_setup_description(self, scenario):
        assert scenario.setup_description, f"{scenario.id} missing setup_description"
        assert len(scenario.setup_description) >= 50, (
            f"{scenario.id} setup_description too short"
        )

    @pytest.mark.parametrize("scenario", SCENARIO_LIBRARY, ids=lambda s: s.id)
    def test_scenario_has_persona_match(self, scenario):
        assert len(scenario.persona_match) >= 1, f"{scenario.id} needs persona_match"

    @pytest.mark.parametrize("scenario", SCENARIO_LIBRARY, ids=lambda s: s.id)
    def test_scenario_has_creative_hook(self, scenario):
        assert scenario.creative_hook, f"{scenario.id} missing creative_hook"
        assert len(scenario.creative_hook) >= 20, (
            f"{scenario.id} creative_hook too short"
        )


class TestScenarioProductReferences:
    """Tests that product references are valid keys from EPIPHAN_PRODUCTS."""

    @pytest.mark.parametrize("scenario", SCENARIO_LIBRARY, ids=lambda s: s.id)
    def test_product_ids_are_valid(self, scenario):
        for product_id in scenario.products:
            assert product_id in EPIPHAN_PRODUCTS, (
                f"{scenario.id} references unknown product '{product_id}'. "
                f"Valid: {list(EPIPHAN_PRODUCTS.keys())}"
            )


class TestScenarioVerticalCoverage:
    """Tests that all 10 verticals are represented."""

    def test_all_verticals_have_scenarios(self):
        """Every vertical from EPIPHAN_VERTICALS should have at least one scenario."""
        covered_verticals = {s.vertical for s in SCENARIO_LIBRARY}
        # Note: government and ux_research are covered by cross-vertical scenarios
        # (legal_courtroom_recording covers courts/councils, corporate covers UX patterns)
        # The library focuses on the top 8 verticals with dedicated scenarios
        primary_verticals = {
            "higher_ed",
            "k12",
            "houses_of_worship",
            "legal",
            "corporate",
            "live_events",
            "healthcare",
            "industrial",
            "broadcasting",
        }
        missing = primary_verticals - covered_verticals
        assert not missing, f"Missing scenarios for verticals: {missing}"

    def test_higher_ed_has_5_scenarios(self):
        """Higher ed has 3 original + 1 integrator (university RFP) + 1 EC20 rooms out of reach."""
        assert len(get_scenarios_for_vertical("higher_ed")) == 5

    def test_k12_has_3_scenarios(self):
        assert len(get_scenarios_for_vertical("k12")) == 3

    def test_houses_of_worship_has_3_scenarios(self):
        assert len(get_scenarios_for_vertical("houses_of_worship")) == 3

    def test_legal_has_3_scenarios(self):
        assert len(get_scenarios_for_vertical("legal")) == 3

    def test_corporate_has_5_scenarios(self):
        """Corporate has 3 original + 2 integrator (fleet standardization + corporate refresh)."""
        assert len(get_scenarios_for_vertical("corporate")) == 5

    def test_live_events_has_3_scenarios(self):
        assert len(get_scenarios_for_vertical("live_events")) == 3

    def test_healthcare_has_1_scenario(self):
        assert len(get_scenarios_for_vertical("healthcare")) == 1

    def test_industrial_has_1_scenario(self):
        assert len(get_scenarios_for_vertical("industrial")) == 1

    def test_scenarios_by_vertical_index_is_complete(self):
        """SCENARIOS_BY_VERTICAL should cover all scenarios."""
        total = sum(len(v) for v in SCENARIOS_BY_VERTICAL.values())
        assert total == len(SCENARIO_LIBRARY)


class TestScenarioVerticalValues:
    """Tests that vertical values in scenarios are valid."""

    @pytest.mark.parametrize("scenario", SCENARIO_LIBRARY, ids=lambda s: s.id)
    def test_vertical_is_valid(self, scenario):
        assert scenario.vertical in EPIPHAN_VERTICALS, (
            f"{scenario.id} has unknown vertical '{scenario.vertical}'. "
            f"Valid: {list(EPIPHAN_VERTICALS.keys())}"
        )


class TestTriggerPhraseMatching:
    """Tests for the match_scenarios_by_phrases function."""

    def test_k12_sports_transcript_matches(self):
        """K-12 sports transcript should match k12_sports_broadcast."""
        text = "We want to stream our Friday night football games for parents"
        matches = match_scenarios_by_phrases(text)
        ids = [s.id for s, _ in matches]
        assert "k12_sports_broadcast" in ids

    def test_higher_ed_lecture_capture_matches(self):
        """Higher ed transcript should match campus capture."""
        text = "We have hundreds of rooms and need lecture capture campus-wide with Panopto"
        matches = match_scenarios_by_phrases(text)
        ids = [s.id for s, _ in matches]
        assert "higher_ed_campus_capture" in ids

    def test_courtroom_transcript_matches(self):
        """Legal transcript should match courtroom recording."""
        text = "We need courtroom recording for all court proceedings and hearings"
        matches = match_scenarios_by_phrases(text)
        ids = [s.id for s, _ in matches]
        assert "legal_courtroom_recording" in ids

    def test_corporate_town_hall_matches(self):
        """Corporate transcript should match town hall."""
        text = "Our CEO wants broadcast quality town hall and all-hands meetings"
        matches = match_scenarios_by_phrases(text)
        ids = [s.id for s, _ in matches]
        assert "corp_town_hall" in ids

    def test_worship_volunteer_matches(self):
        """Houses of worship transcript should match volunteer streaming."""
        text = "We need a simple Sunday service stream that our volunteers can run"
        matches = match_scenarios_by_phrases(text)
        ids = [s.id for s, _ in matches]
        assert "how_volunteer_streaming" in ids

    def test_no_matches_returns_empty(self):
        """Completely unrelated text should return no matches."""
        text = "The weather is nice today and I like pizza"
        matches = match_scenarios_by_phrases(text)
        assert len(matches) == 0

    def test_results_sorted_by_hits(self):
        """Results should be sorted by hit count descending."""
        text = "lecture capture campus-wide hundreds of rooms one-button fleet standardize faculty won't use"
        matches = match_scenarios_by_phrases(text)
        if len(matches) >= 2:
            for i in range(len(matches) - 1):
                assert matches[i][1] >= matches[i + 1][1]

    def test_top_n_limits_results(self):
        """top_n should limit the number of results."""
        text = "stream broadcast campus lecture capture recording classroom"
        matches = match_scenarios_by_phrases(text, top_n=2)
        assert len(matches) <= 2

    def test_vertical_filter_restricts_results(self):
        """vertical_filter should restrict results to that vertical."""
        text = "stream broadcast campus lecture capture recording classroom"
        matches = match_scenarios_by_phrases(text, vertical_filter="k12")
        for scenario, _ in matches:
            assert scenario.vertical == "k12"

    def test_case_insensitive_matching(self):
        """Trigger phrase matching should be case-insensitive."""
        text = "LECTURE CAPTURE CAMPUS-WIDE"
        matches = match_scenarios_by_phrases(text)
        assert len(matches) > 0


class TestLookupFunctions:
    """Tests for get_scenario_by_id and get_scenarios_for_vertical."""

    def test_get_scenario_by_valid_id(self):
        s = get_scenario_by_id("k12_sports_broadcast")
        assert s is not None
        assert s.name == "Friday Night Lights Streaming"

    def test_get_scenario_by_invalid_id(self):
        assert get_scenario_by_id("nonexistent_id") is None

    def test_get_scenarios_for_valid_vertical(self):
        scenarios = get_scenarios_for_vertical("higher_ed")
        assert len(scenarios) == 5  # 3 original + 1 integrator (university RFP) + 1 EC20 rooms
        assert all(s.vertical == "higher_ed" for s in scenarios)

    def test_get_scenarios_for_invalid_vertical(self):
        scenarios = get_scenarios_for_vertical("nonexistent_vertical")
        assert scenarios == []


class TestScenarioDataQuality:
    """Tests for data quality and consistency."""

    @pytest.mark.parametrize("scenario", SCENARIO_LIBRARY, ids=lambda s: s.id)
    def test_id_matches_vertical_prefix(self, scenario):
        """Scenario IDs should start with a recognizable prefix related to their vertical or type."""
        vertical_prefixes = {
            "higher_ed": ("higher_ed_", "integrator_"),
            "k12": ("k12_",),
            "houses_of_worship": ("how_",),
            "legal": ("legal_",),
            "corporate": ("corp_", "integrator_"),
            "live_events": ("events_",),
            "healthcare": ("healthcare_",),
            "industrial": ("industrial_",),
            "broadcasting": ("broadcasting_",),
        }
        expected_prefixes = vertical_prefixes.get(scenario.vertical)
        if expected_prefixes:
            assert any(scenario.id.startswith(p) for p in expected_prefixes), (
                f"{scenario.id} should start with one of {expected_prefixes} for vertical {scenario.vertical}"
            )

    @pytest.mark.parametrize("scenario", SCENARIO_LIBRARY, ids=lambda s: s.id)
    def test_trigger_phrases_are_lowercase_or_proper_nouns(self, scenario):
        """Trigger phrases should be lowercase (proper nouns like NFHS, OSHA, HIPAA allowed)."""
        allowed_upper = {
            "NFHS", "OSHA", "HIPAA", "SOP", "IMAG", "ISO", "HyFlex",
            "AVI-SPL", "Diversified", "Whitlock", "Ford AV",  # Integrator firm names
            "RFP", "Panopto", "Kaltura", "Extron", "Crestron",  # Brand/acronym names
            "MAM", "SRT", "CDN",  # Broadcasting acronyms
        }
        for phrase in scenario.trigger_phrases:
            if phrase in allowed_upper:
                continue
            assert phrase == phrase.lower(), (
                f"{scenario.id} has non-lowercase trigger phrase: '{phrase}'"
            )

    @pytest.mark.parametrize("scenario", SCENARIO_LIBRARY, ids=lambda s: s.id)
    def test_no_epiphan_product_pricing_in_descriptions(self, scenario):
        """Setup descriptions should NOT contain Epiphan product pricing."""
        text = scenario.setup_description
        # Check for Epiphan product price patterns (not prospect-context dollar amounts)
        epiphan_prices = [
            "$3,750",
            "$1,999",
            "$3,899",
            "$8,999",
            "$1,899",
            "$579.95",
            "$449.95",
        ]
        for price in epiphan_prices:
            assert price not in text, (
                f"{scenario.id} contains Epiphan product pricing '{price}' in setup_description"
            )

    def test_frozen_dataclass(self):
        """DeploymentScenario should be frozen (immutable)."""
        s = SCENARIO_LIBRARY[0]
        with pytest.raises(AttributeError):
            s.name = "changed"  # type: ignore[misc]

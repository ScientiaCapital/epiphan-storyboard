"""Technical-accuracy gate — flags hero copy that makes FALSE product claims.

Mirror of the competitor-as-hero gate. The authoritative "do NOT depict"
phrases live in product_visual_specs.py (the SSOT); this gate flags any hero
field that ASSERTS one of those excluded limitations for a recommended product.

Canonical cases pinned here:
  * EC20 "needs a separate encoder to record to the CMS" -> critical (the #1
    false claim). The TRUE claim ("records direct — no encoder required") must
    NOT be flagged: negation guard.
  * Pearl Nano "streams native NDI" -> critical (Nano does not support NDI).
  * Same false copy with no recommended_products -> not flagged (no SSOT to
    ground against).
  * Epiphan Edge is a valid recommendation even though it has no catalog
    entry — _check_product_references must exempt it.
"""

from src.tools.storyboard.quality_gate import (
    QualityReport,
    _check_product_references,
    _check_technical_accuracy,
    find_tech_accuracy_violations,
    run_quality_gate,
)


def _understanding(**overrides) -> dict:
    """A clean, technically accurate, Epiphan-positioned understanding dict."""
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


class TestFindTechAccuracyViolations:
    def test_ec20_separate_encoder_claim_flagged(self):
        hits = find_tech_accuracy_violations(
            _understanding(
                differentiator="The EC20 requires a separate encoder to record to the CMS",
                recommended_products=["ec20_ptz"],
            )
        )
        assert "differentiator" in hits
        assert hits["differentiator"], "must name the offending do_not_depict phrase"

    def test_same_copy_not_flagged_without_recommended_products(self):
        hits = find_tech_accuracy_violations(
            _understanding(
                differentiator="The EC20 requires a separate encoder to record to the CMS",
                recommended_products=[],
            )
        )
        assert hits == {}, "no recommended products -> no SSOT to ground against"

    def test_true_encoder_claim_not_flagged(self):
        # The TRUE Epiphan claim: EC20 records direct, no separate encoder.
        hits = find_tech_accuracy_violations(
            _understanding(
                what_it_does="Record straight to your CMS — no encoder required",
                recommended_products=["ec20_ptz"],
            )
        )
        assert hits == {}, "negated (true) claim must not be flagged"

    def test_pearl_nano_false_ndi_claim_flagged(self):
        hits = find_tech_accuracy_violations(
            _understanding(
                what_it_does="Pearl Nano streams native NDI to the network",
                recommended_products=["pearl_nano"],
            )
        )
        assert "what_it_does" in hits

    def test_clean_copy_returns_empty(self):
        assert find_tech_accuracy_violations(_understanding()) == {}

    def test_unknown_product_id_does_not_crash(self):
        # Unknown ids carry no do_not_depict phrases -> empty, no error.
        hits = find_tech_accuracy_violations(
            _understanding(recommended_products=["not_a_real_product"])
        )
        assert hits == {}


class TestCheckTechnicalAccuracy:
    def test_adds_critical_issue_for_violation(self):
        report = QualityReport()
        _check_technical_accuracy(
            _understanding(
                differentiator="The EC20 requires a separate encoder to record to the CMS",
                recommended_products=["ec20_ptz"],
            ),
            report,
        )
        tech = [i for i in report.issues if i.category == "tech_accuracy"]
        assert tech
        assert all(i.severity == "critical" for i in tech)

    def test_adds_nothing_for_clean_copy(self):
        report = QualityReport()
        _check_technical_accuracy(_understanding(), report)
        assert not [i for i in report.issues if i.category == "tech_accuracy"]


class TestRunQualityGateIntegration:
    def test_violating_dict_yields_critical_tech_accuracy(self):
        report = run_quality_gate(
            _understanding(
                what_it_does="Pearl Nano streams native NDI to the network",
                recommended_products=["pearl_nano"],
            ),
            audience="av_director",
        )
        assert report.has_critical("tech_accuracy") is True
        assert report.passed is False

    def test_clean_dict_has_no_tech_accuracy_critical(self):
        report = run_quality_gate(_understanding(), audience="av_director")
        assert report.has_critical("tech_accuracy") is False


class TestEpiphanEdgeExemption:
    def test_epiphan_edge_not_flagged_as_unknown_product(self):
        report = QualityReport()
        _check_product_references(
            _understanding(recommended_products=["epiphan_edge"]), report
        )
        assert not [
            i
            for i in report.issues
            if i.category == "brand" and "Unknown product" in i.message
        ], "epiphan_edge is a valid synthetic id and must be exempt"

    def test_real_unknown_product_still_flagged(self):
        report = QualityReport()
        _check_product_references(
            _understanding(recommended_products=["totally_made_up"]), report
        )
        assert [
            i
            for i in report.issues
            if i.category == "brand" and "Unknown product" in i.message
        ]


class TestPearlDuoTechAccuracy:
    """Pearl Duo has NO CMS/lecture-capture — the #1 false-claim trap for Duo."""

    def test_lecture_capture_claim_flagged(self):
        hits = find_tech_accuracy_violations(
            _understanding(
                headline="Pearl Duo: the easiest lecture capture device for classrooms",
                recommended_products=["pearl_duo"],
            )
        )
        assert "headline" in hits

    def test_broadcast_switcher_claim_flagged(self):
        hits = find_tech_accuracy_violations(
            _understanding(
                differentiator="A full broadcast production switcher in one box",
                recommended_products=["pearl_duo"],
            )
        )
        assert "differentiator" in hits

    def test_classroom_recording_claim_flagged(self):
        # Evasion of "lecture": implies CMS/lecture use without the word "lecture".
        hits = find_tech_accuracy_violations(
            _understanding(
                what_it_does="A classroom recording and CMS publishing solution",
                recommended_products=["pearl_duo"],
            )
        )
        assert "what_it_does" in hits

    def test_single_screen_claim_flagged(self):
        hits = find_tech_accuracy_violations(
            _understanding(
                headline="A sleek single screen at the operator's fingertips",
                recommended_products=["pearl_duo"],
            )
        )
        assert "headline" in hits

    def test_local_dashboard_claim_flagged(self):
        hits = find_tech_accuracy_violations(
            _understanding(
                differentiator="Manage the whole fleet from a local on-device dashboard",
                recommended_products=["pearl_duo"],
            )
        )
        assert "differentiator" in hits

    def test_playback_scrubbing_claim_flagged(self):
        hits = find_tech_accuracy_violations(
            _understanding(
                what_it_does="Full playback and scrubbing of every recording on the device",
                recommended_products=["pearl_duo"],
            )
        )
        assert "what_it_does" in hits

    def test_clean_dual_channel_copy_passes(self):
        hits = find_tech_accuracy_violations(
            _understanding(
                headline="Record program and ISO with confident on-device control",
                what_it_does="Pearl Duo records and streams two channels at once.",
                differentiator="Dual-channel recording managed via Epiphan Edge",
                recommended_products=["pearl_duo"],
            )
        )
        assert hits == {}


class TestPearlNexusDante:
    """Pearl Nexus licenses Dante but it is NOT functional until ~fall 2026.

    Copy must not claim Dante works today. The do_not_depict SSOT enforces it.
    """

    def test_dante_today_claim_flagged(self):
        hits = find_tech_accuracy_violations(
            _understanding(
                differentiator="Pearl Nexus delivers Dante audio today, right out of the box.",
                recommended_products=["pearl_nexus"],
            )
        )
        assert "differentiator" in hits

    def test_clean_nexus_copy_without_dante_passes(self):
        hits = find_tech_accuracy_violations(
            _understanding(
                headline="Capture every room in one rack unit",
                what_it_does="Pearl Nexus records and streams several rooms without an operator.",
                differentiator="Only Pearl pairs capture with fleet management via Epiphan Edge",
                business_value="Cuts truck rolls across campus",
                pain_point_addressed="Manual SD card collection after every lecture",
                recommended_products=["pearl_nexus"],
            )
        )
        assert hits == {}


class TestTechAccuracyFalsePositives:
    """Regression: correct one-cable / multi-product higher-ed copy was wrongly
    flagged because do_not_depict parentheticals (the TRUE state) leaked words
    like 'cable'/'pearl' into the match signal, and generic plumbing nouns
    ('power','cable') matched on their own. (Reported 2026-06-20 from the demo.)
    """

    def test_one_cable_headline_not_flagged(self):
        hits = find_tech_accuracy_violations(
            _understanding(
                headline="One-cable lecture capture for every room",
                what_it_does="Pearl records and streams every classroom without an operator.",
                recommended_products=["ec20_ptz", "pearl_nano"],
            )
        )
        assert hits == {}, hits

    def test_single_cable_carries_power_not_flagged(self):
        hits = find_tech_accuracy_violations(
            _understanding(
                what_it_does="One PoE+ cable carries power and video to the camera.",
                recommended_products=["ec20_ptz"],
            )
        )
        assert "what_it_does" not in hits, hits

    def test_pearl_mention_not_flagged_via_nano_parenthetical(self):
        hits = find_tech_accuracy_violations(
            _understanding(
                differentiator="Pearl pairs capture with fleet management via Epiphan Edge",
                what_it_does="Pearl records and streams to every classroom.",
                recommended_products=["pearl_nano"],
            )
        )
        assert hits == {}, hits

    def test_real_ec20_separate_encoder_still_flagged(self):
        # The fix must NOT weaken the #1 true claim to block.
        hits = find_tech_accuracy_violations(
            _understanding(
                what_it_does="The EC20 needs a separate encoder to record to your CMS.",
                recommended_products=["ec20_ptz"],
            )
        )
        assert "what_it_does" in hits, hits

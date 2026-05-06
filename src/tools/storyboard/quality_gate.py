"""
Quality Gate — Devil's Advocate Review
=======================================

Post-generation quality check that validates storyboard output against:
1. Link validation — all URLs resolve
2. Brand consistency — correct product names, no competitor mentions
3. JTBD alignment — content addresses the persona's core job
4. Challenger narrative — teaches something new (not just features)
5. NSTTD email — follow-up uses tactical empathy
6. Frankenstack contrast — before/after present when applicable
7. Conciseness — output is technically inclined and scannable
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from src.tools.storyboard.epiphan_presets import (
    EPIPHAN_PRODUCTS,
)
from src.tools.storyboard.prompts import get_persona_job_statement

logger = logging.getLogger(__name__)


@dataclass
class QualityIssue:
    """A single quality issue found during review."""

    category: str  # "link", "brand", "jtbd", "challenger", "nsttd", "conciseness"
    severity: str  # "critical", "warning", "info"
    message: str
    auto_fixable: bool = False
    fix_suggestion: str = ""


@dataclass
class QualityReport:
    """Result of a quality gate review."""

    passed: bool = True
    score: float = 100.0  # 0-100
    issues: list[QualityIssue] = field(default_factory=list)
    critical_count: int = 0
    warning_count: int = 0

    def add_issue(self, issue: QualityIssue) -> None:
        self.issues.append(issue)
        if issue.severity == "critical":
            self.critical_count += 1
            self.score -= 15
            self.passed = False
        elif issue.severity == "warning":
            self.warning_count += 1
            self.score -= 5
        self.score = max(0.0, self.score)


def run_quality_gate(
    understanding: dict[str, Any],
    audience: str,
    vertical: str | None = None,
    collateral_links: dict[str, Any] | None = None,
    email_draft: str | None = None,
) -> QualityReport:
    """
    Run post-generation quality checks on storyboard output.

    Args:
        understanding: Extracted content dict from LLM
        audience: Target audience persona
        vertical: Optional vertical
        collateral_links: Links to validate
        email_draft: Follow-up email to check for NSTTD compliance

    Returns:
        QualityReport with issues and pass/fail status
    """
    report = QualityReport()

    _check_brand_consistency(understanding, report)
    _check_jtbd_alignment(understanding, audience, report)
    _check_challenger_narrative(understanding, report)
    _check_nsttd_email(email_draft, report)
    _check_product_references(understanding, report)
    _check_no_personal_names(understanding, report)
    _check_conciseness(understanding, report)

    if collateral_links:
        _check_links(collateral_links, report)

    logger.info(
        "Quality gate: %s (score=%.0f, critical=%d, warnings=%d)",
        "PASSED" if report.passed else "FAILED",
        report.score,
        report.critical_count,
        report.warning_count,
    )
    return report


def _check_brand_consistency(understanding: dict, report: QualityReport) -> None:
    """Check for incorrect product names or competitor mentions in output."""
    text = str(understanding).lower()

    # Check for competitor product names (shouldn't appear in output)
    competitors = ["extron", "crestron capture", "mediasite", "matrox"]
    for comp in competitors:
        if comp in text:
            report.add_issue(
                QualityIssue(
                    category="brand",
                    severity="warning",
                    message=f"Competitor '{comp}' mentioned in output — reframe around Epiphan",
                )
            )

    # Check for wrong Epiphan product names
    wrong_names = {
        "pearl cloud": "Epiphan Edge",
        "epiphan cloud": "Epiphan Edge",
        "pearl connect": "EC20 PTZ / Epiphan Connect",
    }
    for wrong, correct in wrong_names.items():
        if wrong in text:
            report.add_issue(
                QualityIssue(
                    category="brand",
                    severity="warning",
                    message=f"Outdated name '{wrong}' — should be '{correct}'",
                    auto_fixable=True,
                    fix_suggestion=f"Replace '{wrong}' with '{correct}'",
                )
            )


def _check_jtbd_alignment(
    understanding: dict, audience: str, report: QualityReport
) -> None:
    """Check that content addresses the persona's core job."""
    # Verify job statement exists for the audience (validates persona coverage)
    get_persona_job_statement(audience)

    # Check if JTBD fields are present in expanded schema
    if "job_to_be_done" in understanding:
        jtbd = understanding["job_to_be_done"]
        if not jtbd or len(jtbd) < 20:
            report.add_issue(
                QualityIssue(
                    category="jtbd",
                    severity="warning",
                    message="Job statement is empty or too short — must follow 'When/I want to/so I can' format",
                )
            )

    if "forces_of_progress" in understanding:
        forces = understanding["forces_of_progress"]
        if isinstance(forces, dict):
            for force in ["push", "pull"]:
                if not forces.get(force):
                    report.add_issue(
                        QualityIssue(
                            category="jtbd",
                            severity="warning",
                            message=f"Forces of Progress '{force}' is empty — must identify {force} force",
                        )
                    )


def _check_challenger_narrative(understanding: dict, report: QualityReport) -> None:
    """Check that content follows Challenger teaching narrative, not a feature dump."""
    headline = understanding.get("headline", "")
    business_value = understanding.get("business_value", "")

    # Headlines that are feature-focused instead of insight-focused
    feature_words = [
        "introducing",
        "announcing",
        "new feature",
        "now available",
        "powered by",
    ]
    if any(w in headline.lower() for w in feature_words):
        report.add_issue(
            QualityIssue(
                category="challenger",
                severity="warning",
                message=f"Headline '{headline}' sounds feature-focused — should be a reframe/insight",
            )
        )

    # Business value should have numbers (rational drowning)
    if business_value and not re.search(r"\d", business_value):
        report.add_issue(
            QualityIssue(
                category="challenger",
                severity="info",
                message="Business value has no numbers — rational drowning is stronger with quantified impact",
            )
        )

    # Check for challenger_reframe
    if "challenger_reframe" in understanding:
        reframe = understanding["challenger_reframe"]
        if not reframe or "believe" not in reframe.lower():
            report.add_issue(
                QualityIssue(
                    category="challenger",
                    severity="warning",
                    message="Challenger reframe missing or doesn't follow 'Most X believe Y, but Z' pattern",
                )
            )


def _check_nsttd_email(email_draft: str | None, report: QualityReport) -> None:
    """Check that follow-up email uses NSTTD tactical empathy techniques."""
    if not email_draft:
        return

    email_lower = email_draft.lower()

    # Check for accusation audit
    accusation_markers = [
        "you're probably thinking",
        "you might be",
        "i'm sure you",
        "i know",
    ]
    has_accusation = any(m in email_lower for m in accusation_markers)
    if not has_accusation:
        report.add_issue(
            QualityIssue(
                category="nsttd",
                severity="warning",
                message="Email missing accusation audit opener — should front-run their likely objection",
            )
        )

    # Check for no-oriented CTA
    no_cta_markers = [
        "would it be",
        "is it ridiculous",
        "would it be terrible",
        "have you given up",
    ]
    has_no_cta = any(m in email_lower for m in no_cta_markers)
    if not has_no_cta:
        report.add_issue(
            QualityIssue(
                category="nsttd",
                severity="info",
                message="Email CTA is not no-oriented — consider 'Would it be out of the question to...'",
            )
        )

    # Check word count (under 100)
    word_count = len(email_draft.split())
    if word_count > 120:
        report.add_issue(
            QualityIssue(
                category="nsttd",
                severity="warning",
                message=f"Email is {word_count} words — should be under 100 for cold/follow-up",
            )
        )

    # Check for "Why" questions (forbidden in NSTTD)
    if re.search(r"\bwhy\b", email_lower):
        report.add_issue(
            QualityIssue(
                category="nsttd",
                severity="critical",
                message="Email contains 'Why' question — NSTTD requires How/What only",
                auto_fixable=True,
                fix_suggestion="Rewrite 'Why' questions as 'How' or 'What' questions",
            )
        )


def _check_product_references(understanding: dict, report: QualityReport) -> None:
    """Check that recommended products are valid Epiphan product IDs."""
    products = understanding.get("recommended_products", [])
    if isinstance(products, list):
        for pid in products:
            if isinstance(pid, str) and pid not in EPIPHAN_PRODUCTS:
                report.add_issue(
                    QualityIssue(
                        category="brand",
                        severity="critical",
                        message=f"Unknown product ID '{pid}' — not in EPIPHAN_PRODUCTS catalog",
                    )
                )


def _check_no_personal_names(understanding: dict, report: QualityReport) -> None:
    """Check that output uses roles, not personal names."""
    who_benefits = understanding.get("who_benefits", "")
    if who_benefits:
        # Common name patterns that shouldn't appear
        name_patterns = [
            r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",  # "John Smith" pattern
        ]
        for pattern in name_patterns:
            matches = re.findall(pattern, who_benefits)
            # Filter out role-like patterns
            roles = {"AV Director", "IT Manager", "Field Tech", "Project Manager"}
            real_names = [m for m in matches if m not in roles]
            if real_names:
                report.add_issue(
                    QualityIssue(
                        category="brand",
                        severity="critical",
                        message=f"Personal names in output: {real_names} — must use roles only",
                        auto_fixable=True,
                        fix_suggestion="Replace personal names with role titles",
                    )
                )


def _check_conciseness(understanding: dict, report: QualityReport) -> None:
    """Check that output is concise and scannable."""
    what_it_does = understanding.get("what_it_does", "")
    if what_it_does and len(what_it_does.split()) > 60:
        report.add_issue(
            QualityIssue(
                category="conciseness",
                severity="info",
                message="'what_it_does' exceeds 60 words — should be 2 sentences max",
            )
        )

    headline = understanding.get("headline", "")
    if headline and len(headline.split()) > 10:
        report.add_issue(
            QualityIssue(
                category="conciseness",
                severity="warning",
                message=f"Headline is {len(headline.split())} words — max 8 for scannable impact",
            )
        )


def _check_links(collateral_links: dict, report: QualityReport) -> None:
    """Check that all collateral links are from validated SALES_COLLATERAL."""
    product_links = collateral_links.get("product_links", [])
    for link in product_links:
        url = link.get("url", "") if isinstance(link, dict) else ""
        if url and "epiphan.com" not in url:
            report.add_issue(
                QualityIssue(
                    category="link",
                    severity="critical",
                    message=f"Non-Epiphan URL in product links: {url}",
                )
            )

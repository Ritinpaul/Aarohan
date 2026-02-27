"""
NHCX Readiness Score Engine — Aarohan++ Phase 2
Orchestrates all 4 dimension scorers into a composite Readiness Score (0-100).
Implements:
  - Weighted aggregation across 4 dimensions
  - Gap deduplication and severity sorting
  - Rejection risk prediction
  - Actionable insight generation
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field

from app.quality.structural_scorer import score_structural_completeness
from app.quality.terminology_scorer import score_terminology_coverage
from app.quality.profile_scorer import score_profile_compliance
from app.quality.consent_scorer import score_consent_readiness

logger = logging.getLogger(__name__)

# ─── Default weights from config.py ─────────────────────────────────────────
DEFAULT_WEIGHTS = {
    "structural_completeness": 0.30,
    "terminology_coverage": 0.25,
    "profile_compliance": 0.30,
    "consent_readiness": 0.15,
}

SEVERITY_ORDER = {"blocking": 0, "critical": 1, "warning": 2, "info": 3}
SEVERITY_SCORE_IMPACT = {"blocking": -30, "critical": -15, "warning": -5, "info": -1}


class GapItem(BaseModel):
    field: str
    severity: str
    message: str
    auto_fix_available: bool = False
    fhir_path: Optional[str] = None
    current_value: Optional[str] = None


class DimensionScore(BaseModel):
    score: float
    weight: float
    weighted_contribution: float
    passed: int
    total: int
    gap_count: int


class ReadinessScore(BaseModel):
    overall_score: float = Field(description="Composite NHCX Readiness Score (0-100)")
    grade: str = Field(description="Letter grade: A/B/C/D/F")
    dimensions: dict[str, DimensionScore]
    gaps: list[GapItem] = Field(description="Sorted list of actionable gaps, most severe first")
    blocking_count: int
    critical_count: int
    warning_count: int
    info_count: int
    rejection_risk: str = Field(description="low/medium/high/very_high")
    rejection_risk_reasons: list[str]
    auto_fixable_count: int
    summary: str
    target_profile: str
    processing_time_ms: Optional[float] = None


def _grade(score: float) -> str:
    if score >= 90: return "A"
    if score >= 75: return "B"
    if score >= 60: return "C"
    if score >= 40: return "D"
    return "F"


def _rejection_risk(overall: float, blocking: int, critical: int) -> tuple[str, list[str]]:
    reasons = []
    if blocking > 0:
        reasons.append(f"{blocking} blocking issue(s) will prevent submission")
    if critical > 2:
        reasons.append(f"{critical} critical issues may trigger claim rejection")
    if overall < 40:
        reasons.append("Overall score below 40 — very high rejection probability")

    if blocking > 0 or overall < 40:
        return "very_high", reasons
    if critical > 2 or overall < 60:
        return "high", reasons
    if critical > 0 or overall < 75:
        return "medium", reasons
    return "low", reasons


def compute_readiness_score(
    parsed: dict,
    target_profile: str = "ClaimBundle",
    weights: Optional[dict] = None,
) -> ReadinessScore:
    """
    Full Readiness Score pipeline: run all 4 scorers → aggregate → return ReadinessScore.
    """
    import time
    start = time.time()

    w = weights or DEFAULT_WEIGHTS

    # ── Run all 4 scorers ────────────────────────────────────────────────────
    structural = score_structural_completeness(parsed)
    terminology = score_terminology_coverage(parsed)
    profile = score_profile_compliance(parsed, target_profile)
    consent = score_consent_readiness(parsed)

    results = {
        "structural_completeness": structural,
        "terminology_coverage": terminology,
        "profile_compliance": profile,
        "consent_readiness": consent,
    }

    # ── Weighted aggregation ──────────────────────────────────────────────────
    overall = 0.0
    dimensions = {}
    all_gaps: list[dict] = []

    for key, result in results.items():
        weight = w.get(key, 0.25)
        score = result.get("score", 0.0)
        contribution = round(score * weight, 2)
        overall += contribution

        dimensions[key] = DimensionScore(
            score=score,
            weight=weight,
            weighted_contribution=contribution,
            passed=result.get("passed", 0),
            total=result.get("total", 0),
            gap_count=len(result.get("gaps", [])),
        )
        all_gaps.extend(result.get("gaps", []))

    overall = round(overall, 1)

    # ── Deduplicate + sort gaps ───────────────────────────────────────────────
    seen_fields = set()
    unique_gaps = []
    for gap in sorted(all_gaps, key=lambda g: SEVERITY_ORDER.get(g.get("severity", "info"), 99)):
        key = gap.get("field", "") + gap.get("message", "")[:30]
        if key not in seen_fields:
            seen_fields.add(key)
            unique_gaps.append(GapItem(**{k: gap.get(k) for k in GapItem.model_fields}))

    # ── Severity counts ───────────────────────────────────────────────────────
    blocking = sum(1 for g in unique_gaps if g.severity == "blocking")
    critical = sum(1 for g in unique_gaps if g.severity == "critical")
    warning = sum(1 for g in unique_gaps if g.severity == "warning")
    info = sum(1 for g in unique_gaps if g.severity == "info")
    auto_fixable = sum(1 for g in unique_gaps if g.auto_fix_available)

    # ── Rejection risk ────────────────────────────────────────────────────────
    risk_level, risk_reasons = _rejection_risk(overall, blocking, critical)

    # ── Summary ───────────────────────────────────────────────────────────────
    grade = _grade(overall)
    summary = (
        f"NHCX Readiness Score: {overall}/100 (Grade {grade}). "
        f"{blocking} blocking, {critical} critical, {warning} warning issues. "
        f"Rejection risk: {risk_level.replace('_', ' ')}. "
        f"{auto_fixable} gap(s) can be auto-healed."
    )

    elapsed_ms = round((time.time() - start) * 1000, 1)

    return ReadinessScore(
        overall_score=overall,
        grade=grade,
        dimensions=dimensions,
        gaps=unique_gaps,
        blocking_count=blocking,
        critical_count=critical,
        warning_count=warning,
        info_count=info,
        rejection_risk=risk_level,
        rejection_risk_reasons=risk_reasons,
        auto_fixable_count=auto_fixable,
        summary=summary,
        target_profile=target_profile,
        processing_time_ms=elapsed_ms,
    )

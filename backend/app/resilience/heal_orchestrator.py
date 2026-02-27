"""
Heal Orchestrator — Aarohan++ Phase 4
Applies all Phase 4 healers in sequence to a parsed healthcare record.

Pipeline:
  raw parsed dict
      ↓ DateHealer      ─ normalise all date fields to ISO 8601
      ↓ NameNormaliser  ─ clean name, infer missing gender
      ↓ ABHAEnricher    ─ inject ABHA placeholder + consent fields
      ↓ TerminologyHealer ─ map free-text diagnoses → ICD-10/SNOMED
      ↓ DrugHealer      ─ brand→generic, dosage extraction, drug codes
      ↓ ConfidenceScorer ─ tag all inferred values with confidence
      → HealResult (healed parsed dict + confidence report + gap diff)
"""

import copy
import logging
import time
from typing import Optional
from pydantic import BaseModel

from app.resilience.date_healer import heal_dates
from app.resilience.name_normaliser import normalise_patient
from app.resilience.abha_enricher import enrich_patient_abha, enrich_consent
from app.resilience.terminology_healer import heal_diagnoses
from app.resilience.drug_healer import heal_medications
from app.resilience.confidence_scorer import (
    score_patient_confidence,
    score_diagnoses_confidence,
    score_medications_confidence,
    compute_overall_confidence,
)

logger = logging.getLogger(__name__)


class HealReport(BaseModel):
    """Detailed report of all changes made by the Resilience Healer."""
    patient: dict = {}
    diagnoses: list = []
    medications: list = []
    overall_confidence: float = 0.0
    abha_generated: bool = False
    gender_inferred: bool = False
    dates_healed: int = 0
    codes_mapped: int = 0
    drugs_healed: int = 0
    brands_resolved: int = 0
    processing_time_ms: float = 0.0


class HealResult(BaseModel):
    """Full output of the Resilience Healer."""
    healed: dict               # Fully healed parsed dict
    original: dict             # Original (pre-heal) for comparison
    report: HealReport
    heal_applied: bool         # True if any changes were made
    score_before: Optional[float] = None
    score_after: Optional[float] = None
    score_delta: Optional[float] = None


def _extract_all_patients(parsed: dict) -> list[dict]:
    """Pull patient dicts from both top-level and records."""
    patients = []
    if parsed.get("patient"):
        patients.append(parsed["patient"])
    for rec in parsed.get("records", []):
        if rec.get("patient"):
            patients.append(rec["patient"])
    return patients


def _extract_all_diagnoses(parsed: dict) -> list[dict]:
    diags = list(parsed.get("diagnoses", []))
    for rec in parsed.get("records", []):
        diags.extend(rec.get("diagnoses", []))
    return diags


def _extract_all_medications(parsed: dict) -> list[dict]:
    meds = list(parsed.get("medications", []))
    for rec in parsed.get("records", []):
        meds.extend(rec.get("medications", []))
    return meds


def heal(parsed: dict, run_readiness: bool = True) -> HealResult:
    """
    Apply the full Phase 4 resilience healing pipeline to a parsed dict.

    Args:
        parsed: Dict from any parser (csv/hl7/xml/pdf)
        run_readiness: Whether to compute before/after readiness scores

    Returns:
        HealResult containing healed dict, confidence report, and score delta
    """
    t0 = time.time()
    original = copy.deepcopy(parsed)
    healed = copy.deepcopy(parsed)

    # ── Score BEFORE ──────────────────────────────────────────────────────────
    score_before = None
    if run_readiness:
        try:
            from app.quality.readiness_engine import compute_readiness_score
            score_before = compute_readiness_score(healed).overall_score
        except Exception as e:
            logger.warning(f"Pre-heal scoring failed: {e}")

    # ── Step 1: Date Healing ──────────────────────────────────────────────────
    dates_before = _count_bad_dates(healed)
    heal_dates(healed)
    for rec in healed.get("records", []):
        heal_dates(rec)
    dates_healed = max(0, dates_before - _count_bad_dates(healed))

    # ── Step 2: Name & Gender Normalisation ───────────────────────────────────
    gender_inferred = False
    for patient in _extract_all_patients(healed):
        was_unknown = (patient.get("gender") or "").lower() in ("", "unknown")
        normalise_patient(patient)
        if was_unknown and patient.get("gender_inferred"):
            gender_inferred = True

    # ── Step 3: ABHA Enrichment ───────────────────────────────────────────────
    abha_generated = False
    for patient in _extract_all_patients(healed):
        enrich_patient_abha(patient)
        if patient.get("abha_generated"):
            abha_generated = True
    enrich_consent(healed)

    # ── Step 4: Terminology Healing (Diagnoses → ICD-10) ─────────────────────
    codes_before = _count_uncoded_diagnoses(original)
    heal_diagnoses(healed.get("diagnoses", []))
    for rec in healed.get("records", []):
        heal_diagnoses(rec.get("diagnoses", []))
    codes_mapped = max(0, codes_before - _count_uncoded_diagnoses(healed))

    # ── Step 5: Drug Healing ──────────────────────────────────────────────────
    drugs_before = len(_extract_all_medications(original))
    if "medications" in healed:
        healed["medications"] = heal_medications(healed["medications"])
    for rec in healed.get("records", []):
        if "medications" in rec:
            rec["medications"] = heal_medications(rec["medications"])
    drugs_after = len(_extract_all_medications(healed))
    drugs_healed = max(0, drugs_after - drugs_before) + sum(
        1 for m in _extract_all_medications(healed) if m.get("code")
    )
    brands_resolved = sum(
        1 for m in _extract_all_medications(healed) if m.get("brand_resolved")
    )

    # ── Step 6: Confidence Scoring ────────────────────────────────────────────
    patients = _extract_all_patients(healed)
    conf_patient = score_patient_confidence(patients[0]) if patients else {}
    conf_diagnoses = score_diagnoses_confidence(_extract_all_diagnoses(healed))
    conf_medications = score_medications_confidence(_extract_all_medications(healed))

    confidence_map = {
        "patient": conf_patient,
        "diagnoses": conf_diagnoses,
        "medications": conf_medications,
    }
    overall_conf = compute_overall_confidence(confidence_map)

    # ── Score AFTER ───────────────────────────────────────────────────────────
    score_after = None
    if run_readiness:
        try:
            from app.quality.readiness_engine import compute_readiness_score
            score_after = compute_readiness_score(healed).overall_score
        except Exception as e:
            logger.warning(f"Post-heal scoring failed: {e}")

    elapsed_ms = round((time.time() - t0) * 1000, 1)

    report = HealReport(
        patient=conf_patient,
        diagnoses=conf_diagnoses,
        medications=conf_medications,
        overall_confidence=overall_conf,
        abha_generated=abha_generated,
        gender_inferred=gender_inferred,
        dates_healed=dates_healed,
        codes_mapped=codes_mapped,
        drugs_healed=drugs_healed,
        brands_resolved=brands_resolved,
        processing_time_ms=elapsed_ms,
    )

    heal_applied = any([
        dates_healed > 0, gender_inferred, abha_generated,
        codes_mapped > 0, drugs_healed > 0, brands_resolved > 0
    ])

    score_delta = round(score_after - score_before, 1) if (score_before is not None and score_after is not None) else None

    return HealResult(
        healed=healed,
        original=original,
        report=report,
        heal_applied=heal_applied,
        score_before=score_before,
        score_after=score_after,
        score_delta=score_delta,
    )


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _count_bad_dates(parsed: dict) -> int:
    """Heuristically count non-ISO date strings in parsed dict."""
    import re
    count = 0
    BAD_PATTERN = re.compile(r"\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}")

    def _walk(obj):
        nonlocal count
        if isinstance(obj, str):
            if BAD_PATTERN.search(obj):
                count += 1
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(parsed)
    return count


def _count_uncoded_diagnoses(parsed: dict) -> int:
    count = 0
    for d in parsed.get("diagnoses", []):
        if not d.get("code"):
            count += 1
    for rec in parsed.get("records", []):
        for d in rec.get("diagnoses", []):
            if not d.get("code"):
                count += 1
    return count

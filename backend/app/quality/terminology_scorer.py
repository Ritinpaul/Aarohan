"""
Terminology Coverage Scorer — Aarohan++ Phase 2
Checks whether diagnoses, medications, observations are backed by standard terminology
codes (SNOMED CT, ICD-10, LOINC, NRCeS Drug Codes) instead of free-text only.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Known code system patterns ────────────────────────────────────────────────
ICD10_PATTERN = re.compile(r"^[A-Z]\d{2}(\.\d{1,4})?$")
SNOMED_PATTERN = re.compile(r"^\d{6,18}$")
LOINC_PATTERN = re.compile(r"^\d{1,5}-\d$")

# ─── Indian medical free-text that should be flagged ──────────────────────────
HINDI_FREE_TEXT_FLAGS = [
    "sugar ki bimari", "bukhar", "peyt dard", "sir dard", "khansi",
    "pet mein dard", "weakness", "kamzori"
]

KNOWN_SYSTEMS = {
    "http://snomed.info/sct",
    "http://hl7.org/fhir/sid/icd-10",
    "http://loinc.org",
    "https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-drugcode",
}


def _is_valid_code(code: Optional[str], system: Optional[str]) -> bool:
    """Check if a code looks structurally valid for its system."""
    if not code:
        return False
    if system == "http://hl7.org/fhir/sid/icd-10":
        return bool(ICD10_PATTERN.match(code.strip()))
    if system == "http://snomed.info/sct":
        return bool(SNOMED_PATTERN.match(code.strip()))
    if system == "http://loinc.org":
        return bool(LOINC_PATTERN.match(code.strip()))
    # Unknown system — still credit having a code
    return len(code.strip()) > 2


def _is_hindi_free_text(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in HINDI_FREE_TEXT_FLAGS)


def score_terminology_coverage(parsed: dict) -> dict:
    """
    Score terminology coverage across diagnoses, medications, observations.

    Returns:
        dict with score (0-100), gaps, breakdown by resource type
    """
    gaps = []
    total_checks = 0
    passed_checks = 0
    breakdown = {
        "diagnoses": {"coded": 0, "total": 0},
        "medications": {"coded": 0, "total": 0},
        "observations": {"coded": 0, "total": 0},
    }

    # ── Gather all items ──────────────────────────────────────────────────────
    diagnoses = _collect(parsed, "diagnoses")
    medications = _collect(parsed, "medications")
    observations = _collect(parsed, "observations")

    # ── Score Diagnoses ───────────────────────────────────────────────────────
    for i, diag in enumerate(diagnoses):
        total_checks += 1
        breakdown["diagnoses"]["total"] += 1
        code = diag.get("code")
        system = diag.get("system")
        text = diag.get("text", "")

        if _is_valid_code(code, system) and system in KNOWN_SYSTEMS:
            passed_checks += 1
            breakdown["diagnoses"]["coded"] += 1
        elif _is_valid_code(code, system):
            # Has code but unknown system — partial credit
            passed_checks += 0.5
            breakdown["diagnoses"]["coded"] += 1
            gaps.append({
                "field": f"Condition[{i}].code.coding.system",
                "severity": "warning",
                "message": f"Diagnosis code '{code}' has unrecognized system '{system}'. Expected SNOMED or ICD-10.",
                "auto_fix_available": True,
                "fhir_path": "Condition.code.coding",
            })
        else:
            # Free-text only
            severity = "critical"
            auto_fix = True
            hint = f"Map free-text '{text[:40]}' to SNOMED CT or ICD-10 code."
            if _is_hindi_free_text(text):
                severity = "critical"
                hint += " (Note: Hindi free-text detected — use Bharat terminology mapper.)"

            gaps.append({
                "field": f"Condition[{i}].code",
                "severity": severity,
                "message": f"Diagnosis has no standard code. {hint}",
                "current_value": text[:80] if text else None,
                "auto_fix_available": auto_fix,
                "fhir_path": "Condition.code.coding",
            })

    # ── Score Medications ─────────────────────────────────────────────────────
    for i, med in enumerate(medications):
        total_checks += 1
        breakdown["medications"]["total"] += 1
        code = med.get("code")
        system = med.get("system")
        text = med.get("text", "")

        if _is_valid_code(code, system):
            passed_checks += 1
            breakdown["medications"]["coded"] += 1
        else:
            gaps.append({
                "field": f"MedicationRequest[{i}].medication.code",
                "severity": "warning",
                "message": f"Medication '{text[:50]}' has no NRCeS drug code. Use drug code mapper.",
                "auto_fix_available": True,
                "fhir_path": "MedicationRequest.medication[x].coding",
            })

    # ── Score Observations ────────────────────────────────────────────────────
    for i, obs in enumerate(observations):
        total_checks += 1
        breakdown["observations"]["total"] += 1
        code = obs.get("code")
        system = obs.get("system")
        display = obs.get("display", "")

        if _is_valid_code(code, system) and ("loinc" in (system or "").lower() or system in KNOWN_SYSTEMS):
            passed_checks += 1
            breakdown["observations"]["coded"] += 1
        else:
            gaps.append({
                "field": f"Observation[{i}].code",
                "severity": "warning",
                "message": f"Observation '{display or code}' missing LOINC code.",
                "auto_fix_available": False,
                "fhir_path": "Observation.code.coding",
            })

    # ── If no items at all ────────────────────────────────────────────────────
    if total_checks == 0:
        # No clinical items parsed — this is a structural deficit, not terminology
        return {
            "score": 0.0,
            "passed": 0,
            "total": 0,
            "gaps": [{
                "field": "Terminology",
                "severity": "blocking",
                "message": "No clinical items (diagnoses/medications/observations) found to score terminology.",
                "auto_fix_available": False,
                "fhir_path": None,
            }],
            "dimension": "terminology_coverage",
            "breakdown": breakdown,
        }

    score = round((passed_checks / total_checks) * 100, 1)

    return {
        "score": score,
        "passed": passed_checks,
        "total": total_checks,
        "gaps": gaps,
        "dimension": "terminology_coverage",
        "breakdown": breakdown,
    }


def _collect(parsed: dict, key: str) -> list:
    """Collect items from top-level or nested records."""
    items = list(parsed.get(key, []))
    for rec in parsed.get("records", []):
        items.extend(rec.get(key, []))
    return items

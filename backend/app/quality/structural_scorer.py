"""
Structural Completeness Scorer — Aarohan++ Phase 2
Evaluates whether mandatory FHIR elements required by NRCeS profiles are present in parsed data.
Score: fraction of present/required fields × 100
"""

from typing import Any
import logging

logger = logging.getLogger(__name__)

# ─── NRCeS Mandatory Element Requirements per resource type ────────────────────
# Derived from docs/NRCES_PROFILE_MATRIX.md
PATIENT_REQUIRED = [
    "name",       # Patient.name
    "gender",     # Patient.gender
    "birth_date", # Patient.birthDate (or age substitute)
    "identifiers", # Patient.identifier (ABHA)
]

PATIENT_RECOMMENDED = [
    "phone",
    "address",
]

ENCOUNTER_REQUIRED = [
    "type",
    "facility_name",
]

DIAGNOSIS_REQUIRED = [
    "text",
]

COVERAGE_REQUIRED = [
    "scheme_name",
    "network",
]


def _check_present(obj: dict, key: str) -> bool:
    """Returns True if a key is present and non-empty in the dict."""
    val = obj.get(key)
    if val is None:
        return False
    if isinstance(val, (str, list, dict)):
        return bool(val)
    return True


def score_structural_completeness(parsed: dict) -> dict:
    """
    Compute structural completeness score for a parsed healthcare record.

    Args:
        parsed: Output from any parser (PDF/CSV/HL7/XML)

    Returns:
        dict with score (0-100), gaps, and dimension details
    """
    gaps = []
    total_checks = 0
    passed_checks = 0

    # Extract patient from various parser output formats
    patient = parsed.get("patient", {})
    if not patient and parsed.get("records"):
        patient = parsed["records"][0].get("patient", {})

    # 1) Patient mandatory fields
    for field in PATIENT_REQUIRED:
        total_checks += 1
        # 'identifiers' is satisfied by either identifiers list OR abha_id
        if field == "identifiers":
            if _check_present(patient, "identifiers") or _check_present(patient, "abha_id"):
                passed_checks += 1
            else:
                gaps.append({
                    "field": "Patient.identifier[ABHA]",
                    "severity": "blocking",
                    "message": "ABHA identifier missing. Required for NHCX compliance.",
                    "auto_fix_available": True,
                    "fhir_path": "Patient.identifier",
                })
        elif _check_present(patient, field):
            passed_checks += 1
        else:
            gaps.append({
                "field": f"Patient.{field}",
                "severity": "blocking" if field == "identifiers" else "critical",
                "message": f"Missing mandatory patient field: '{field}'",
                "auto_fix_available": field in ("identifiers", "gender"),
                "fhir_path": f"Patient.{_to_fhir_name(field)}",
            })

    # Note: ABHA specifically is checked in the identifiers loop above.
    # No duplicate check needed here.
    # 2) Patient recommended fields
    for field in PATIENT_RECOMMENDED:
        total_checks += 1
        if _check_present(patient, field):
            passed_checks += 1
        else:
            gaps.append({
                "field": f"Patient.{field}",
                "severity": "warning",
                "message": f"Recommended patient field missing: '{field}'",
                "auto_fix_available": False,
                "fhir_path": f"Patient.{_to_fhir_name(field)}",
            })

    # 3) Encounter / encounter list
    encounters = parsed.get("encounters", [])
    if not encounters and parsed.get("records"):
        enc = parsed["records"][0].get("encounter", {})
        if enc:
            encounters = [enc]

    if not encounters:
        gaps.append({
            "field": "Encounter",
            "severity": "critical",
            "message": "No encounter/visit information found.",
            "auto_fix_available": False,
            "fhir_path": "Encounter",
        })
    total_checks += 1
    if encounters:
        passed_checks += 1

    # 4) Diagnoses
    diagnoses = parsed.get("diagnoses", [])
    if not diagnoses and parsed.get("records"):
        for rec in parsed["records"]:
            diagnoses.extend(rec.get("diagnoses", []))

    if not diagnoses:
        gaps.append({
            "field": "Condition",
            "severity": "critical",
            "message": "No diagnosis/condition found. Required for claim bundles.",
            "auto_fix_available": False,
            "fhir_path": "Condition",
        })
    total_checks += 1
    if diagnoses:
        passed_checks += 1

        # Check diagnosis text completeness
        for i, diag in enumerate(diagnoses[:3]):
            total_checks += 1
            if _check_present(diag, "text"):
                passed_checks += 1
            else:
                gaps.append({
                    "field": f"Condition[{i}].code.text",
                    "severity": "critical",
                    "message": "Diagnosis has no text description.",
                    "auto_fix_available": False,
                    "fhir_path": "Condition.code.text",
                })

    # 5) Coverage check
    coverage_list = parsed.get("coverage", [])
    if not coverage_list and parsed.get("records"):
        for rec in parsed["records"]:
            cov = rec.get("coverage", {})
            if cov:
                coverage_list.append(cov)

    if not coverage_list:
        gaps.append({
            "field": "Coverage",
            "severity": "critical",
            "message": "No insurance coverage information found.",
            "auto_fix_available": False,
            "fhir_path": "Coverage",
        })
    total_checks += 1
    if coverage_list:
        passed_checks += 1

    # Compute score
    score = round((passed_checks / max(total_checks, 1)) * 100, 1)

    return {
        "score": score,
        "passed": passed_checks,
        "total": total_checks,
        "gaps": gaps,
        "dimension": "structural_completeness",
    }


def _to_fhir_name(snake: str) -> str:
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])

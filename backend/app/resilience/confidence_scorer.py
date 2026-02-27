"""
Confidence Scorer — Aarohan++ Phase 4
Adds per-field confidence scores to a healed parsed dict.

Every inferred or healed value is tagged with:
  - confidence: 0.0 – 1.0
  - source: "original", "inferred", "generated", "healed"
  - flag: True if confidence < threshold (default 0.75)

Used to build the HealReport returned by the /heal endpoint.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.75


def _tag(value: Any, confidence: float, source: str = "healed") -> dict:
    return {
        "value": value,
        "confidence": round(confidence, 3),
        "source": source,
        "flagged": confidence < CONFIDENCE_THRESHOLD,
    }


def score_patient_confidence(patient: dict) -> dict:
    """
    Return a confidence map for every field in a patient dict.
    """
    result = {}

    # Name
    name = patient.get("name") or ""
    name_conf = 0.9 if len(name.split()) >= 2 else 0.6
    result["name"] = _tag(name, name_conf, "original")

    # Gender
    gender = patient.get("gender") or "unknown"
    if patient.get("gender_inferred"):
        result["gender"] = _tag(gender, 0.65, "inferred")
    elif gender not in ("unknown", ""):
        result["gender"] = _tag(gender, 1.0, "original")
    else:
        result["gender"] = _tag(gender, 0.0, "missing")

    # ABHA
    abha = patient.get("abha_id")
    if abha:
        conf = 0.0 if patient.get("abha_generated") else 1.0
        source = "generated" if patient.get("abha_generated") else "original"
        result["abha_id"] = _tag(abha, conf, source)
    else:
        result["abha_id"] = _tag(None, 0.0, "missing")

    # DOB / Age
    if patient.get("birth_date") or patient.get("dob"):
        result["birth_date"] = _tag(
            patient.get("birth_date") or patient.get("dob"), 0.95, "original"
        )
    elif patient.get("age"):
        result["age"] = _tag(patient.get("age"), 0.8, "original")

    # Phone
    result["phone"] = _tag(
        patient.get("phone"), 0.9 if patient.get("phone") else 0.0,
        "original" if patient.get("phone") else "missing"
    )

    return result


def score_diagnoses_confidence(diagnoses: list) -> list:
    result = []
    for d in diagnoses:
        code = d.get("code")
        conf = d.get("code_confidence", 0.0)
        mtype = d.get("code_match_type", "none")

        entry = {
            "text": d.get("text", ""),
            "code": _tag(code, conf if code else 0.0, mtype if code else "missing"),
            "system": d.get("system"),
        }
        result.append(entry)
    return result


def score_medications_confidence(medications: list) -> list:
    result = []
    for m in medications:
        code = m.get("code")
        conf = m.get("code_confidence", 0.0)
        mtype = m.get("code_match_type", "none")
        entry = {
            "text": m.get("text", ""),
            "code": _tag(code, conf if code else 0.0, mtype if code else "missing"),
            "dosage": _tag(m.get("dosage_instruction"), 0.9 if m.get("dosage_instruction") else 0.0, "extracted"),
            "brand_resolved": m.get("brand_resolved", False),
        }
        result.append(entry)
    return result


def compute_overall_confidence(report: dict) -> float:
    """
    Calculate an overall confidence score [0, 1] for a heal report.
    """
    scores = []

    patient_conf = report.get("patient", {})
    for field_data in patient_conf.values():
        if isinstance(field_data, dict) and "confidence" in field_data:
            scores.append(field_data["confidence"])

    for diag in report.get("diagnoses", []):
        code_info = diag.get("code", {})
        if isinstance(code_info, dict):
            scores.append(code_info.get("confidence", 0.0))

    for med in report.get("medications", []):
        code_info = med.get("code", {})
        if isinstance(code_info, dict):
            scores.append(code_info.get("confidence", 0.0))

    return round(sum(scores) / len(scores), 3) if scores else 0.0

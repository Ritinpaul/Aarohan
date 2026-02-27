"""
Consent Readiness Scorer — Aarohan++ Phase 2
Checks for ABDM consent artifacts required before NHCX submission:
  - ABHA number as identifier
  - Consent mode (explicit/implicit)
  - Purpose of use
  - Linking status of health facility
"""

import re
import logging

logger = logging.getLogger(__name__)

ABHA_PATTERN = re.compile(r"\d{2}-\d{4}-\d{4}-\d{4}")


def score_consent_readiness(parsed: dict) -> dict:
    """
    Score ABDM consent readiness.

    Returns:
        dict with score (0-100), gaps, and dimension key
    """
    gaps = []
    total = 0
    passed = 0

    patient = parsed.get("patient", {})
    if not patient and parsed.get("records"):
        patient = parsed["records"][0].get("patient", {})

    # ── 1. ABHA present ───────────────────────────────────────────────────────
    total += 1
    abha_id = patient.get("abha_id")
    identifiers = patient.get("identifiers", [])
    abha_in_identifiers = any(
        ABHA_PATTERN.search(str(i.get("value", "") if isinstance(i, dict) else i))
        for i in (identifiers or [])
    )

    if abha_id or abha_in_identifiers:
        passed += 1
    else:
        gaps.append({
            "field": "Patient.identifier[ABHA]",
            "severity": "blocking",
            "message": "ABHA (Ayushman Bharat Health Account) number not found. "
                       "ABDM consent linking requires ABHA.",
            "auto_fix_available": True,
            "fhir_path": "Patient.identifier",
        })

    # ── 2. Consent mode (explicit/implicit) ───────────────────────────────────
    total += 1
    consent_mode = parsed.get("consent_mode")
    if consent_mode in ("EXPLICIT", "IMPLICIT", "OPEN"):
        passed += 1
    else:
        gaps.append({
            "field": "Consent.provision.type",
            "severity": "critical",
            "message": "Consent mode not specified. ABDM requires explicit or implicit consent "
                       "for PHR access (EXPLICIT/IMPLICIT/OPEN).",
            "auto_fix_available": False,
            "fhir_path": "Consent.provision.type",
        })

    # ── 3. Purpose of use ─────────────────────────────────────────────────────
    total += 1
    purpose = parsed.get("consent_purpose")
    valid_purposes = {"CAREMGT", "BTG", "PUBHLTH", "HPAYMT", "ETREAT"}
    if purpose in valid_purposes:
        passed += 1
    else:
        gaps.append({
            "field": "Consent.purpose",
            "severity": "warning",
            "message": f"Consent purpose '{purpose or 'missing'}' not set. "
                       f"Common values: CAREMGT (Care Management), HPAYMT (Healthcare Payment).",
            "auto_fix_available": False,
            "fhir_path": "Consent.purpose",
        })

    # ── 4. Health facility linkage hint ────────────────────────────────────────
    total += 1
    encounters = parsed.get("encounters", [])
    if not encounters and parsed.get("records"):
        enc = parsed["records"][0].get("encounter", {})
        if enc:
            encounters = [enc]

    has_facility = any(e.get("facility_name") for e in encounters)
    if has_facility:
        passed += 1
    else:
        gaps.append({
            "field": "Organization.identifier[NIN]",
            "severity": "warning",
            "message": "Facility name not present. ABDM consent requires a linked health facility "
                       "with a valid NIN (National Identifier Number).",
            "auto_fix_available": False,
            "fhir_path": "Organization.identifier",
        })

    score = round((passed / max(total, 1)) * 100, 1)

    return {
        "score": score,
        "passed": passed,
        "total": total,
        "gaps": gaps,
        "dimension": "consent_readiness",
    }

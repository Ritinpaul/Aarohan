"""
NRCeS Coverage Resource Builder — Aarohan++ Phase 3
Builds FHIR Coverage resources from Indian insurance scheme data
(PMJAY, CMCHIS, YSR Aarogyasri, ECHS, state schemes from seed/schemes.json).
"""

import uuid
import logging
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)

NRCES_BASE = "https://nrces.in/ndhm/fhir/r4/StructureDefinition/"

# Known scheme identifiers  →  FHIR class code
SCHEME_CLASS_MAP = {
    "PMJAY":    {"code": "PMJAY",    "display": "Pradhan Mantri Jan Arogya Yojana (Ayushman Bharat)"},
    "AYUSHMAN": {"code": "PMJAY",    "display": "Pradhan Mantri Jan Arogya Yojana (Ayushman Bharat)"},
    "CMCHIS":   {"code": "CMCHIS",   "display": "Chief Minister's Comprehensive Health Insurance Scheme (TN)"},
    "YSR":      {"code": "YSRAAROGYASRI", "display": "YSR Aarogyasri (AP)"},
    "AAROGYASRI": {"code": "YSRAAROGYASRI", "display": "YSR Aarogyasri (AP)"},
    "MJPJAY":   {"code": "MJPJAY",   "display": "Mahatma Jyotiba Phule Jan Arogya Yojana (MH)"},
    "ECHS":     {"code": "ECHS",     "display": "Ex-Servicemen Contributory Health Scheme"},
    "CGHS":     {"code": "CGHS",     "display": "Central Government Health Scheme"},
    "ESI":      {"code": "ESI",      "display": "Employees' State Insurance"},
    "ABPMJAY":  {"code": "PMJAY",    "display": "AB PM-JAY"},
}

INSURANCE_TYPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/v3-ActCode"


def _uuid() -> str:
    return str(uuid.uuid4())


def _resolve_scheme(scheme_name: str) -> dict:
    """Normalize scheme name to a known class code entry."""
    upper = (scheme_name or "").upper().strip()
    for key, val in SCHEME_CLASS_MAP.items():
        if key in upper:
            return val
    return {"code": upper or "UNKNOWN", "display": scheme_name or "Unknown Scheme"}


def build_coverage(
    coverage_data: dict,
    patient_ref: str,
    insurer_ref: Optional[str] = None,
    coverage_id: Optional[str] = None,
) -> dict:
    """
    Build a NRCeS-compliant FHIR Coverage resource.

    Args:
        coverage_data: Dict with scheme_name, claim_amount, policy_number, etc.
        patient_ref: FHIR Patient resource ID
        insurer_ref: FHIR Organization ID for the insurer
        coverage_id: Optional pre-assigned resource ID
    """
    cid = coverage_id or _uuid()
    scheme_name = coverage_data.get("scheme_name", "")
    schema_class = _resolve_scheme(scheme_name)

    resource = {
        "resourceType": "Coverage",
        "id": cid,
        "meta": {"profile": [f"{NRCES_BASE}Coverage"]},
        "status": "active",
        "type": {
            "coding": [{
                "system": INSURANCE_TYPE_SYSTEM,
                "code": "PUBLICPOL",
                "display": "public healthcare"
            }]
        },
        "subscriber": {"reference": f"Patient/{patient_ref}"},
        "beneficiary": {"reference": f"Patient/{patient_ref}"},
        "relationship": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/subscriber-relationship",
                "code": "self",
                "display": "Self"
            }]
        },
        "payor": [{"reference": f"Organization/{insurer_ref}"}] if insurer_ref else [{"display": "Unknown Insurer"}],
        "class": [{
            "type": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/coverage-class",
                    "code": "group"
                }]
            },
            "value": schema_class["code"],
            "name": schema_class["display"]
        }]
    }

    # Claim amount → costToBeneficiary
    claim_amount = coverage_data.get("claim_amount") or coverage_data.get("coverage_amount")
    if claim_amount:
        resource["costToBeneficiary"] = [{
            "type": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/coverage-copay-type",
                    "code": "gpvisit"
                }]
            },
            "valueMoney": {
                "value": float(claim_amount),
                "currency": "INR"
            }
        }]

    # Policy number
    policy_num = coverage_data.get("policy_number") or coverage_data.get("plan_id")
    if policy_num:
        resource["subscriberId"] = str(policy_num)

    return resource

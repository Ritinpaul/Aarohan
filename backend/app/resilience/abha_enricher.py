"""
ABHA Enricher — Aarohan++ Phase 4
Generates deterministic placeholder ABHA (Ayushman Bharat Health Account) IDs
for demo purposes when a real ABHA is unavailable.

ABHA ID Format: XX-XXXX-XXXX-XXXX (14 digits, dash-separated in 2-4-4-4 groups)

Real ABHA lookup requires ABDM API access (out of scope for hackathon demo).
We generate a deterministic ID from: sha256(patient_name + dob) so the same
patient always gets the same ABHA placeholder — making the demo repeatable.

Confidence: 0.0 (not a real ABHA — always flagged as generated)
"""

import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

ABHA_SYSTEM = "https://healthid.ndhm.gov.in"
ABHA_FLAG = "generated_placeholder"


def _make_abha_id(seed: str) -> str:
    """
    Generate a deterministic 14-digit ABHA-like ID from a string seed.
    Format: ZZ-XXXX-XXXX-XXXX (first 2 digits = 99 for placeholder namespace)
    """
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    # Extract 12 numeric digits from hex digest
    digits = "".join(c for c in digest if c.isdigit())
    digits = (digits * 4)[:12]  # pad if needed
    return f"99-{digits[0:4]}-{digits[4:8]}-{digits[8:12]}"


def generate_abha(patient: dict) -> tuple[str, bool]:
    """
    Return an ABHA ID for a patient.

    Priority:
      1. Use existing ABHA if present in identifiers or abha_id field
      2. Generate deterministic placeholder

    Returns:
        (abha_id, is_generated)
    """
    # Check if ABHA already exists
    for ident in patient.get("identifiers", []):
        if isinstance(ident, dict):
            system = ident.get("system", "")
            if "healthid" in system or "abha" in system.lower():
                return ident.get("value", ""), False

    if patient.get("abha_id"):
        return patient["abha_id"], False

    # Generate deterministic placeholder
    name = (patient.get("name") or "unknown").lower().strip()
    dob = str(patient.get("birth_date") or patient.get("dob") or "")
    age = str(patient.get("age") or "")
    pid = str(patient.get("id") or "")
    seed = f"{name}|{dob}|{age}|{pid}"
    abha = _make_abha_id(seed)
    return abha, True


def enrich_patient_abha(patient: dict) -> dict:
    """
    Add ABHA ID to patient dict if missing.
    Marks generated IDs clearly.
    Returns the mutated patient dict.
    """
    abha_id, is_generated = generate_abha(patient)
    if not abha_id:
        return patient

    patient["abha_id"] = abha_id
    patient["abha_generated"] = is_generated
    patient["abha_confidence"] = 0.0 if is_generated else 1.0

    if "identifiers" not in patient:
        patient["identifiers"] = []

    # Add to identifiers list if not already present
    existing_systems = {
        i.get("system") for i in patient["identifiers"] if isinstance(i, dict)
    }
    if ABHA_SYSTEM not in existing_systems:
        patient["identifiers"].append({
            "system": ABHA_SYSTEM,
            "value": abha_id,
            "generated": is_generated,
        })

    if is_generated:
        logger.debug(f"ABHAEnricher: Generated placeholder ABHA '{abha_id}' for patient '{patient.get('name')}'")
    else:
        logger.debug(f"ABHAEnricher: Found existing ABHA '{abha_id}'")

    return patient


def enrich_consent(parsed: dict) -> dict:
    """
    Inject ABDM consent fields if missing — required for NRCeS ClaimBundle.
    """
    if not parsed.get("consent_mode"):
        parsed["consent_mode"] = "EXPLICIT"
        parsed["consent_purpose"] = "HPAYMT"   # Healthcare Payment
        logger.debug("ABHAEnricher: Injected ABDM consent_mode=EXPLICIT")

    if not parsed.get("meta_profile"):
        parsed["meta_profile"] = "https://nrces.in/ndhm/fhir/r4/StructureDefinition/ClaimBundle"

    return parsed

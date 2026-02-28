"""
Dummy Payer Integration — Aarohan++ Phase 5
Simulates NHCX Payer gateway calls for demo/hackathon use.

Simulates three NHCX payer flows:
  1. CoverageEligibilityRequest → CoverageEligibilityResponse
  2. ClaimPreauthorization      → ClaimResponse (queued/approved)
  3. ClaimSubmission            → ClaimResponse (approved/rejected with reason)

Responses are deterministic by scheme name — making demos predictable.
Follows NHCX Payer API v1.0 response envelope format.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PayerResponse(BaseModel):
    """Unified NHCX-style payer response."""
    request_id: str
    response_id: str
    flow: Literal["eligibility", "preauth", "claim"]
    status: Literal["approved", "queued", "rejected", "pending"]
    scheme_name: str
    insurer: str
    subscriber_id: str
    coverage_status: str
    benefit_amount: float
    currency: str = "INR"
    remarks: str
    timestamp: str
    fhir_response: dict


_SCHEME_PAYERS: dict[str, str] = {
    "pmjay":       "National Health Authority (NHA)",
    "cghs":        "Central Government Health Scheme",
    "echs":        "Ex-Servicemen Contributory Health Scheme",
    "esis":        "Employee State Insurance Corporation",
    "cmchis":      "Chief Minister's Comprehensive Health Insurance (TN)",
    "ysr":         "YSR Aarogyasri Health Care Trust",
    "chiranjeevi": "Chiranjeevi Yojana (Rajasthan)",
    "self pay":    "Not Insured (Self Pay)",
}

_SCHEME_LIMITS: dict[str, float] = {
    "pmjay": 500000.0,
    "cghs":  300000.0,
    "echs":  500000.0,
    "esis":  200000.0,
    "cmchis": 400000.0,
    "ysr":   500000.0,
    "chiranjeevi":  150000.0,
    "self pay": 0.0,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_cov_elig_response(
    request_id: str, patient_name: str, scheme: str, subscriber_id: str
) -> dict:
    return {
        "resourceType": "CoverageEligibilityResponse",
        "id": str(uuid.uuid4()),
        "status": "active",
        "purpose": ["benefits"],
        "patient": {"display": patient_name},
        "created": _now(),
        "request": {"reference": f"CoverageEligibilityRequest/{request_id}"},
        "outcome": "complete",
        "insurer": {"display": _SCHEME_PAYERS.get(scheme, "Unknown Insurer")},
        "insurance": [{
            "coverage": {"display": scheme.upper()},
            "inforce": True,
            "item": [{
                "category": {"coding": [{"code": "benefits"}]},
                "benefitBalance": [{
                    "category": {"coding": [{"code": "medical"}]},
                    "used": [{"type": {"coding": [{"code": "benefit"}]},
                               "allowedMoney": {"value": _SCHEME_LIMITS.get(scheme, 0), "currency": "INR"}}]
                }]
            }]
        }]
    }


def _build_claim_response(
    claim_id: str, outcome: str, scheme: str, amount: float, remarks: str
) -> dict:
    return {
        "resourceType": "ClaimResponse",
        "id": str(uuid.uuid4()),
        "status": "active",
        "type": {"coding": [{"code": "institutional"}]},
        "use": "claim",
        "patient": {"display": "Patient"},
        "created": _now(),
        "insurer": {"display": _SCHEME_PAYERS.get(scheme, "Unknown Insurer")},
        "request": {"reference": f"Claim/{claim_id}"},
        "outcome": outcome,
        "disposition": remarks,
        "payment": {
            "type": {"coding": [{"code": outcome}]},
            "amount": {"value": amount if outcome == "complete" else 0.0, "currency": "INR"},
            "date": _now()[:10],
        }
    }


def check_eligibility(
    bundle: dict, subscriber_id: str = "SUB-0001"
) -> PayerResponse:
    """Simulate a CoverageEligibilityRequest → Response."""
    scheme = _extract_scheme(bundle)
    patient_name = _extract_patient_name(bundle)
    request_id = bundle.get("id", str(uuid.uuid4()))
    limit = _SCHEME_LIMITS.get(scheme, 0.0)
    insurer = _SCHEME_PAYERS.get(scheme, "Unknown")

    logger.info(f"PayerSim: CovElig — scheme={scheme} limit={limit}")
    return PayerResponse(
        request_id=request_id,
        response_id=str(uuid.uuid4()),
        flow="eligibility",
        status="approved" if limit > 0 else "rejected",
        scheme_name=scheme,
        insurer=insurer,
        subscriber_id=subscriber_id,
        coverage_status="active" if limit > 0 else "inactive",
        benefit_amount=limit,
        remarks=f"Eligible for up to ₹{limit:,.0f} under {scheme.upper()}" if limit > 0 else "Self-pay — no scheme coverage",
        timestamp=_now(),
        fhir_response=_build_cov_elig_response(request_id, patient_name, scheme, subscriber_id),
    )


def request_preauth(
    bundle: dict, claim_amount: float = 50000.0, subscriber_id: str = "SUB-0001"
) -> PayerResponse:
    """Simulate a Pre-Authorization submission."""
    scheme = _extract_scheme(bundle)
    limit = _SCHEME_LIMITS.get(scheme, 0.0)
    insurer = _SCHEME_PAYERS.get(scheme, "Unknown")
    request_id = bundle.get("id", str(uuid.uuid4()))
    approved = claim_amount <= limit

    logger.info(f"PayerSim: PreAuth — scheme={scheme} amount={claim_amount} approved={approved}")
    return PayerResponse(
        request_id=request_id,
        response_id=str(uuid.uuid4()),
        flow="preauth",
        status="queued" if approved else "rejected",
        scheme_name=scheme,
        insurer=insurer,
        subscriber_id=subscriber_id,
        coverage_status="active",
        benefit_amount=min(claim_amount, limit),
        remarks=(
            f"Pre-auth queued — amount ₹{claim_amount:,.0f} within limit ₹{limit:,.0f}"
            if approved
            else f"Claim ₹{claim_amount:,.0f} exceeds scheme limit ₹{limit:,.0f}"
        ),
        timestamp=_now(),
        fhir_response=_build_claim_response(
            request_id, "queued" if approved else "error", scheme, claim_amount,
            "Pre-authorization queued for review" if approved else "Exceeds benefit limit"
        ),
    )


def submit_claim(
    bundle: dict, claim_amount: float = 50000.0, subscriber_id: str = "SUB-0001"
) -> PayerResponse:
    """Simulate a full Claim submission and adjudication."""
    scheme = _extract_scheme(bundle)
    limit = _SCHEME_LIMITS.get(scheme, 0.0)
    insurer = _SCHEME_PAYERS.get(scheme, "Unknown")
    request_id = bundle.get("id", str(uuid.uuid4()))

    # Deterministic adjudication rules
    if scheme == "self pay":
        status, outcome, remarks = "rejected", "error", "No scheme — self-pay only"
        approved_amount = 0.0
    elif claim_amount > limit:
        status, outcome, remarks = "rejected", "error", f"Amount ₹{claim_amount:,.0f} exceeds ₹{limit:,.0f} limit"
        approved_amount = 0.0
    else:
        status, outcome, remarks = "approved", "complete", f"Claim approved — ₹{claim_amount:,.0f} will be settled within 7 working days"
        approved_amount = claim_amount

    logger.info(f"PayerSim: Claim — scheme={scheme} amount={claim_amount} outcome={outcome}")
    return PayerResponse(
        request_id=request_id,
        response_id=str(uuid.uuid4()),
        flow="claim",
        status=status,
        scheme_name=scheme,
        insurer=insurer,
        subscriber_id=subscriber_id,
        coverage_status="active",
        benefit_amount=approved_amount,
        remarks=remarks,
        timestamp=_now(),
        fhir_response=_build_claim_response(request_id, outcome, scheme, approved_amount, remarks),
    )


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _extract_scheme(bundle: dict) -> str:
    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        if res.get("resourceType") == "Coverage":
            # Check subscriberId text or class name
            for cls in res.get("class", []):
                name = (cls.get("name") or "").lower()
                for key in _SCHEME_PAYERS:
                    if key in name:
                        return key
            # Check meta/extension
            sub = (res.get("subscriberId") or "").lower()
            for key in _SCHEME_PAYERS:
                if key in sub:
                    return key
    return "self pay"


def _extract_patient_name(bundle: dict) -> str:
    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        if res.get("resourceType") == "Patient":
            names = res.get("name", [])
            if names:
                n = names[0]
                parts = [n.get("text", "")]
                if n.get("family"):
                    parts.append(n["family"])
                given = n.get("given", [])
                if given:
                    parts = given + [n.get("family", "")]
                return " ".join(p for p in parts if p).strip()
    return "Unknown Patient"

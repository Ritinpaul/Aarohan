"""
NRCeS FHIR Validation Gate — Aarohan++ Phase 5
Validates a FHIR R4 bundle against NRCeS profile constraints.

Two-tier validation:
  1. Structural validation — required resources present, required fields filled
  2. Profile validation  — NRCeS-specific constraints (meta.profile, coding systems)

Validation levels:
  ERROR   — Bundle must not be submitted (blocking)
  WARNING — Submittable but may be rejected by payer
  INFO    — Best-practice recommendations

Does NOT require a running HAPI FHIR server — runs deterministically in-process.
Mirrors what HAPI FHIR OperationOutcome would return.
"""

from __future__ import annotations

import logging
from typing import Literal
from pydantic import BaseModel

logger = logging.getLogger(__name__)

NRCES_BASE = "https://nrces.in/ndhm/fhir/r4/StructureDefinition/"

REQUIRED_RESOURCES = {
    "ClaimBundle": [
        "Patient", "Claim", "Coverage", "Organization", "Encounter",
    ],
    "CoverageEligibilityRequestBundle": [
        "Patient", "CoverageEligibilityRequest", "Coverage", "Organization",
    ],
}

NRCES_PROFILES = {
    "Patient":    f"{NRCES_BASE}Patient",
    "Claim":      f"{NRCES_BASE}Claim",
    "Coverage":   f"{NRCES_BASE}Coverage",
    "Organization": f"{NRCES_BASE}Organization",
    "Encounter":  f"{NRCES_BASE}Encounter",
    "Condition":  f"{NRCES_BASE}Condition",
    "MedicationRequest": f"{NRCES_BASE}MedicationRequest",
    "Observation": f"{NRCES_BASE}Observation",
}

VALID_GENDER_CODES = {"male", "female", "other", "unknown"}
VALID_CLAIM_USE   = {"claim", "preauthorization", "predetermination"}
VALID_BUNDLE_TYPES = {"collection", "transaction", "document"}


class ValidationIssue(BaseModel):
    severity: Literal["error", "warning", "info"]
    code: str
    details: str
    expression: str = ""


class ValidationReport(BaseModel):
    valid: bool                         # True if zero errors
    profile: str
    resource_types_found: list[str]
    issues: list[ValidationIssue]
    error_count: int
    warning_count: int
    info_count: int
    fhir_version: str = "R4"
    nrces_compliant: bool               # True if zero errors AND profiles match


def _get_resource_types(bundle: dict) -> list[str]:
    return [
        e.get("resource", {}).get("resourceType", "Unknown")
        for e in bundle.get("entry", [])
        if e.get("resource")
    ]


def _get_resources_by_type(bundle: dict) -> dict[str, list[dict]]:
    typed: dict[str, list[dict]] = {}
    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        rt = res.get("resourceType", "")
        if rt:
            typed.setdefault(rt, []).append(res)
    return typed


def validate_bundle(bundle: dict, profile: str = "ClaimBundle") -> ValidationReport:
    """
    Run full NRCeS structural + profile validation on a FHIR bundle dict.

    Returns a ValidationReport with issues categorised by severity.
    """
    issues: list[ValidationIssue] = []
    resource_types = _get_resource_types(bundle)
    by_type = _get_resources_by_type(bundle)

    # ── 1. Bundle meta checks ─────────────────────────────────────────────────
    if not bundle.get("resourceType") == "Bundle":
        issues.append(ValidationIssue(
            severity="error", code="invalid-type",
            details="Root resource must have resourceType='Bundle'",
            expression="Bundle.resourceType",
        ))

    btype = bundle.get("type", "")
    if btype not in VALID_BUNDLE_TYPES:
        issues.append(ValidationIssue(
            severity="error", code="invalid-bundle-type",
            details=f"Bundle.type '{btype}' is not a valid FHIR R4 bundle type",
            expression="Bundle.type",
        ))

    if not bundle.get("id"):
        issues.append(ValidationIssue(
            severity="warning", code="missing-id",
            details="Bundle.id is missing — recommended for tracking",
            expression="Bundle.id",
        ))

    if not bundle.get("timestamp"):
        issues.append(ValidationIssue(
            severity="warning", code="missing-timestamp",
            details="Bundle.timestamp is missing — required for NHCX audit trail",
            expression="Bundle.timestamp",
        ))

    # ── 2. Required resource checks ───────────────────────────────────────────
    required = REQUIRED_RESOURCES.get(profile, [])
    for rtype in required:
        if rtype not in resource_types:
            severity = "error" if rtype in ("Patient", "Claim", "CoverageEligibilityRequest") else "warning"
            issues.append(ValidationIssue(
                severity=severity, code="missing-required-resource",
                details=f"Required resource '{rtype}' not found in bundle for profile '{profile}'",
                expression=f"Bundle.entry[resourceType={rtype}]",
            ))

    # ── 3. Patient resource checks ────────────────────────────────────────────
    for patient in by_type.get("Patient", []):
        if not patient.get("name") and not patient.get("name", []):
            issues.append(ValidationIssue(
                severity="error", code="missing-patient-name",
                details="Patient.name is required by NRCeS", expression="Patient.name",
            ))
        gender = patient.get("gender", "")
        if gender and gender.lower() not in VALID_GENDER_CODES:
            issues.append(ValidationIssue(
                severity="error", code="invalid-gender",
                details=f"Patient.gender '{gender}' is not a valid FHIR gender code",
                expression="Patient.gender",
            ))
        # Check for ABHA identifier
        has_abha = any(
            "healthid" in str(i.get("system", "")).lower() or "abha" in str(i.get("system", "")).lower()
            for i in patient.get("identifier", [])
        )
        if not has_abha:
            issues.append(ValidationIssue(
                severity="info", code="missing-abha",
                details="Patient has no ABHA identifier — recommended for PMJAY/state scheme claims",
                expression="Patient.identifier[system=healthid.ndhm.gov.in]",
            ))

    # ── 4. Claim resource checks ──────────────────────────────────────────────
    for claim in by_type.get("Claim", []):
        use = claim.get("use", "")
        if use not in VALID_CLAIM_USE:
            issues.append(ValidationIssue(
                severity="error", code="invalid-claim-use",
                details=f"Claim.use '{use}' must be one of: {VALID_CLAIM_USE}",
                expression="Claim.use",
            ))
        if not claim.get("patient"):
            issues.append(ValidationIssue(
                severity="error", code="missing-claim-patient",
                details="Claim.patient is required", expression="Claim.patient",
            ))
        if not claim.get("insurance"):
            issues.append(ValidationIssue(
                severity="error", code="missing-claim-insurance",
                details="Claim.insurance is required for NHCX submission",
                expression="Claim.insurance",
            ))
        if not claim.get("total"):
            issues.append(ValidationIssue(
                severity="warning", code="missing-claim-total",
                details="Claim.total is recommended — payer may reject without it",
                expression="Claim.total",
            ))

    # ── 5. Coverage checks ────────────────────────────────────────────────────
    for cov in by_type.get("Coverage", []):
        if not cov.get("beneficiary"):
            issues.append(ValidationIssue(
                severity="error", code="missing-coverage-beneficiary",
                details="Coverage.beneficiary (patient ref) is required",
                expression="Coverage.beneficiary",
            ))
        if not cov.get("payor"):
            issues.append(ValidationIssue(
                severity="warning", code="missing-coverage-payor",
                details="Coverage.payor is missing — required for payer routing",
                expression="Coverage.payor",
            ))

    # ── 6. NRCeS profile URLs on key resources ────────────────────────────────
    profile_matches = 0
    for rtype, url in NRCES_PROFILES.items():
        for res in by_type.get(rtype, []):
            meta_profiles = res.get("meta", {}).get("profile", [])
            if url in meta_profiles:
                profile_matches += 1
            elif rtype in ("Patient", "Claim"):
                issues.append(ValidationIssue(
                    severity="warning", code="missing-nrces-profile",
                    details=f"{rtype}.meta.profile does not include NRCeS URL '{url}'",
                    expression=f"{rtype}.meta.profile",
                ))

    # ── 7. Coding systems ─────────────────────────────────────────────────────
    for condition in by_type.get("Condition", []):
        for cc in condition.get("code", {}).get("coding", []):
            system = cc.get("system", "")
            if system and "icd" not in system.lower() and "snomed" not in system.lower():
                issues.append(ValidationIssue(
                    severity="info", code="non-standard-coding-system",
                    details=f"Condition.code.coding.system '{system}' — prefer ICD-10 or SNOMED CT",
                    expression="Condition.code.coding.system",
                ))

    errors   = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    infos    = sum(1 for i in issues if i.severity == "info")

    return ValidationReport(
        valid=errors == 0,
        profile=profile,
        resource_types_found=list(set(resource_types)),
        issues=issues,
        error_count=errors,
        warning_count=warnings,
        info_count=infos,
        nrces_compliant=errors == 0 and profile_matches > 0,
    )

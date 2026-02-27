"""
Profile Compliance Scorer — Aarohan++ Phase 2
Validates parsed data structure against NRCeS FHIR StructureDefinition constraints.
Checks: data type correctness, cardinality rules, required extensions, meta.profile URLs.
"""

import re
import logging
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)

# ─── NRCeS Profile URLs ────────────────────────────────────────────────────────
NRCES_BASE = "https://nrces.in/ndhm/fhir/r4/StructureDefinition/"
VALID_PROFILE_URLS = {
    "Patient": f"{NRCES_BASE}Patient",
    "Coverage": f"{NRCES_BASE}Coverage",
    "ClaimBundle": f"{NRCES_BASE}ClaimBundle",
    "CoverageEligibilityRequestBundle": f"{NRCES_BASE}CoverageEligibilityRequestBundle",
    "Organization": f"{NRCES_BASE}Organization",
}

VALID_GENDERS = {"male", "female", "other", "unknown"}
VALID_ENCOUNTER_TYPES = {"IMP", "AMB", "EMER", "HH", "VR"}

PHONE_PATTERN = re.compile(r"^[6-9]\d{9}$")   # Indian mobile: 10 digits starting 6-9
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")  # ISO 8601

ABHA_PATTERN = re.compile(r"^\d{2}-\d{4}-\d{4}-\d{4}$")


class ProfileComplianceScorer:
    """
    Validates records against NRCeS profile constraints.
    Assigns severity: blocking / critical / warning / info.
    """

    def score(self, parsed: dict, target_profile: str = "ClaimBundle") -> dict:
        gaps = []
        total = 0
        passed = 0

        patient = parsed.get("patient", {})
        if not patient and parsed.get("records"):
            patient = parsed["records"][0].get("patient", {})

        # ── Patient ────────────────────────────────────────────────────────────
        # Gender
        total += 1
        gender = patient.get("gender", "")
        if gender in VALID_GENDERS:
            passed += 1
        else:
            gaps.append(self._gap(
                f"Patient.gender",
                "critical",
                f"Gender value '{gender}' is not a valid FHIR code. Must be: {VALID_GENDERS}",
                True,
            ))

        # Birth Date
        total += 1
        dob = patient.get("birth_date") or patient.get("dob")
        age = patient.get("age")
        if dob or age:
            passed += 1
            if dob and isinstance(dob, str) and not DATE_PATTERN.match(dob):
                gaps.append(self._gap(
                    "Patient.birthDate",
                    "warning",
                    f"birthDate '{dob}' not in ISO 8601 format (YYYY-MM-DD).",
                    True,
                ))
        else:
            gaps.append(self._gap(
                "Patient.birthDate",
                "critical",
                "Patient has neither birthDate nor age. One is required.",
                False,
            ))

        # ABHA format validation
        total += 1
        abha_id = patient.get("abha_id")
        if abha_id:
            if ABHA_PATTERN.match(str(abha_id)):
                passed += 1
            else:
                gaps.append(self._gap(
                    "Patient.identifier[ABHA].value",
                    "critical",
                    f"ABHA ID '{abha_id}' has invalid format. Expected: XX-XXXX-XXXX-XXXX",
                    True,
                ))
        else:
            gaps.append(self._gap(
                "Patient.identifier[ABHA]",
                "blocking",
                "ABHA identifier not present. Mandatory for NHCX submissions.",
                True,
            ))

        # Phone format
        phone = patient.get("phone", "")
        if phone:
            total += 1
            clean_phone = re.sub(r"[\s\-\+]", "", str(phone))
            if PHONE_PATTERN.match(clean_phone[-10:]) if len(clean_phone) >= 10 else False:
                passed += 1
            else:
                gaps.append(self._gap(
                    "Patient.telecom.value",
                    "info",
                    f"Phone number '{phone}' may not be a valid Indian mobile number.",
                    False,
                ))

        # ── Encounters ─────────────────────────────────────────────────────────
        encounters = parsed.get("encounters", [])
        if not encounters and parsed.get("records"):
            enc = parsed["records"][0].get("encounter", {})
            if enc:
                encounters = [enc]

        for i, enc in enumerate(encounters[:2]):
            total += 1
            enc_type = enc.get("type", "")
            if enc_type in VALID_ENCOUNTER_TYPES:
                passed += 1
            else:
                gaps.append(self._gap(
                    f"Encounter[{i}].class",
                    "warning",
                    f"Encounter class '{enc_type}' not valid. Must be: {VALID_ENCOUNTER_TYPES}",
                    True,
                ))

        # ── Diagnoses ──────────────────────────────────────────────────────────
        diagnoses = list(parsed.get("diagnoses", []))
        for rec in parsed.get("records", []):
            diagnoses.extend(rec.get("diagnoses", []))

        for i, diag in enumerate(diagnoses[:5]):
            total += 1
            text = diag.get("text", "")
            code = diag.get("code")
            if text and len(text.strip()) >= 2:
                passed += 1
            else:
                gaps.append(self._gap(
                    f"Condition[{i}].code.text",
                    "critical",
                    "Condition has no displayable text.",
                    False,
                ))

            # Code length sanity check
            if code and len(str(code).strip()) > 20:
                gaps.append(self._gap(
                    f"Condition[{i}].code.coding.code",
                    "warning",
                    f"Code value '{code[:30]}' seems too long for a standard clinical code.",
                    False,
                ))

        # ── Profile URL check ──────────────────────────────────────────────────
        total += 1
        expected_url = VALID_PROFILE_URLS.get(target_profile)
        meta_profile = parsed.get("meta_profile")
        if meta_profile == expected_url:
            passed += 1
        else:
            gaps.append(self._gap(
                "Bundle.meta.profile",
                "blocking" if not meta_profile else "critical",
                f"meta.profile must be '{expected_url}'. Got: '{meta_profile or 'missing'}'",
                True,
            ))

        score = round((passed / max(total, 1)) * 100, 1)

        return {
            "score": score,
            "passed": passed,
            "total": total,
            "gaps": gaps,
            "dimension": "profile_compliance",
            "target_profile": target_profile,
        }

    @staticmethod
    def _gap(field: str, severity: str, message: str, auto_fix: bool) -> dict:
        return {
            "field": field,
            "severity": severity,
            "message": message,
            "auto_fix_available": auto_fix,
            "fhir_path": field,
        }


def score_profile_compliance(parsed: dict, target_profile: str = "ClaimBundle") -> dict:
    return ProfileComplianceScorer().score(parsed, target_profile)

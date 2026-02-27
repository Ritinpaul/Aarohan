"""
NHCX Bundle Packager — Aarohan++ Phase 3
Assembles NRCeS-compliant FHIR Bundles:
  - ClaimBundle (for full claims)
  - CoverageEligibilityRequestBundle (for eligibility checks)
Supports both NHCX (collection) and OpenHCX (transaction) bundle types.
"""

import uuid
import logging
from datetime import datetime
from typing import Optional

from app.fhir.resource_builder import (
    build_patient, build_condition, build_medication_request,
    build_observation, build_encounter, build_organization
)
from app.fhir.coverage_builder import build_coverage
from app.fhir.drug_mapper import get_mapper

logger = logging.getLogger(__name__)

NRCES_BASE = "https://nrces.in/ndhm/fhir/r4/StructureDefinition/"


def _uuid() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+05:30")


def _bundle_entry(resource: dict, full_url_prefix: str = "") -> dict:
    rtype = resource.get("resourceType", "Resource")
    rid = resource.get("id", _uuid())
    return {
        "fullUrl": f"{full_url_prefix}{rtype}/{rid}",
        "resource": resource,
    }


class BundlePackager:
    """
    Assembles a complete NHCX/OpenHCX FHIR Bundle from parsed data.
    """

    def __init__(self, network: str = "nhcx"):
        self.network = network
        self.bundle_type = "collection" if network == "nhcx" else "transaction"
        self.drug_mapper = get_mapper()

    def pack_claim_bundle(
        self,
        parsed: dict,
        context: Optional[dict] = None,
        hospital_name: Optional[str] = None,
        insurer_name: Optional[str] = None,
    ) -> dict:
        """
        Build a ClaimBundle from parsed healthcare data.

        Returns a fully assembled FHIR Bundle dict.
        """
        entries = []
        context = context or {}

        # ── Extract patient data ──────────────────────────────────────────────
        patient_data = parsed.get("patient", {})
        if not patient_data and parsed.get("records"):
            patient_data = parsed["records"][0].get("patient", {})

        patient_id = _uuid()
        patient = build_patient(patient_data, patient_id)
        entries.append(_bundle_entry(patient))

        # ── Organization (provider hospital) ─────────────────────────────────
        facility_name = (
            hospital_name
            or parsed.get("facility_name")
            or parsed.get("facility", {}).get("name")
            or context.get("hospital_tier_label", "Unknown Hospital")
        )
        provider_id = _uuid()
        provider = build_organization(
            name=facility_name,
            org_type="prov",
            org_id=provider_id,
        )
        entries.append(_bundle_entry(provider))

        # ── Organization (insurer) ────────────────────────────────────────────
        insurer_name_str = insurer_name or "National Insurance"
        if context.get("eligible_schemes"):
            first_scheme = context["eligible_schemes"][0]
            if isinstance(first_scheme, dict):
                insurer_name_str = first_scheme.get("name", insurer_name_str)
        insurer_id = _uuid()
        insurer = build_organization(
            name=insurer_name_str,
            org_type="ins",
            org_id=insurer_id,
        )
        entries.append(_bundle_entry(insurer))

        # ── Encounter ─────────────────────────────────────────────────────────
        encounters = parsed.get("encounters", [])
        if not encounters and parsed.get("records"):
            enc = parsed["records"][0].get("encounter", {})
            if enc:
                encounters = [enc]

        encounter_id = None
        if encounters:
            enc_data = encounters[0]
            encounter_id = _uuid()
            encounter = build_encounter(
                enc_data, patient_id,
                organization_ref=provider_id,
                encounter_id=encounter_id,
            )
            entries.append(_bundle_entry(encounter))

        # ── Diagnoses → Conditions ────────────────────────────────────────────
        diagnoses = list(parsed.get("diagnoses", []))
        for rec in parsed.get("records", []):
            diagnoses.extend(rec.get("diagnoses", []))

        condition_ids = []
        for diag in diagnoses[:10]:
            cond_id = _uuid()
            cond = build_condition(diag, patient_id, cond_id, encounter_id)
            entries.append(_bundle_entry(cond))
            condition_ids.append(cond_id)

        # ── Medications ───────────────────────────────────────────────────────
        medications = list(parsed.get("medications", []))
        for rec in parsed.get("records", []):
            medications.extend(rec.get("medications", []))

        # Enrich with drug codes
        medications = self.drug_mapper.enrich_medications(medications)

        for med in medications[:20]:
            med_id = _uuid()
            med_resource = build_medication_request(med, patient_id, med_id, encounter_id)
            entries.append(_bundle_entry(med_resource))

        # ── Observations ──────────────────────────────────────────────────────
        observations = list(parsed.get("observations", []))
        for obs in observations[:10]:
            obs_id = _uuid()
            obs_resource = build_observation(obs, patient_id, obs_id, encounter_id)
            entries.append(_bundle_entry(obs_resource))

        # ── Coverage ──────────────────────────────────────────────────────────
        coverage_list = list(parsed.get("coverage", []))
        for rec in parsed.get("records", []):
            cov_data = rec.get("coverage", {})
            if cov_data and cov_data.get("scheme_name"):
                coverage_list.append(cov_data)

        # Add scheme from context if available
        if not coverage_list and context.get("eligible_schemes"):
            first = context["eligible_schemes"][0]
            if isinstance(first, dict):
                coverage_list.append({"scheme_name": first.get("name", "")})

        # Add a fallback Coverage resource if still empty (required by NRCeS)
        if not coverage_list:
            coverage_list.append({"scheme_name": "Self Pay"})

        for cov_data in coverage_list[:3]:
            cov_id = _uuid()
            cov = build_coverage(cov_data, patient_id, insurer_id, cov_id)
            entries.append(_bundle_entry(cov))

        # ── Claim Resource ────────────────────────────────────────────────────
        claim_id = _uuid()
        claim = self._build_claim(
            claim_id=claim_id,
            patient_ref=patient_id,
            provider_ref=provider_id,
            insurer_ref=insurer_id,
            condition_ids=condition_ids,
            network=self.network,
        )
        entries.insert(0, _bundle_entry(claim))  # Claim is first entry per NRCeS spec

        # ── Assemble bundle ───────────────────────────────────────────────────
        bundle_id = _uuid()
        bundle = {
            "resourceType": "Bundle",
            "id": bundle_id,
            "meta": {
                "profile": [f"{NRCES_BASE}ClaimBundle"],
                "lastUpdated": _now_iso(),
            },
            "type": self.bundle_type,
            "timestamp": _now_iso(),
            "entry": entries,
        }

        if self.network == "openhcx":
            bundle["type"] = "transaction"
            for entry in bundle["entry"]:
                entry["request"] = {
                    "method": "POST",
                    "url": entry["resource"]["resourceType"],
                }

        logger.info(
            f"Assembled ClaimBundle: {len(entries)} entries, network={self.network}"
        )
        return bundle

    def pack_coverage_eligibility_bundle(
        self,
        parsed: dict,
        context: Optional[dict] = None,
    ) -> dict:
        """Build a CoverageEligibilityRequestBundle."""
        entries = []
        context = context or {}

        patient_data = parsed.get("patient", {})
        if not patient_data and parsed.get("records"):
            patient_data = parsed["records"][0].get("patient", {})

        patient_id = _uuid()
        patient = build_patient(patient_data, patient_id)
        entries.append(_bundle_entry(patient))

        # Provider
        facility_name = parsed.get("facility_name") or context.get("hospital_tier_label", "Unknown")
        provider_id = _uuid()
        entries.append(_bundle_entry(build_organization(facility_name, "prov", provider_id)))

        # Insurer
        insurer_name = "Unknown Insurer"
        if context.get("eligible_schemes"):
            first = context["eligible_schemes"][0]
            insurer_name = first.get("name", insurer_name) if isinstance(first, dict) else insurer_name
        insurer_id = _uuid()
        entries.append(_bundle_entry(build_organization(insurer_name, "ins", insurer_id)))

        # Coverage
        coverage_list = list(parsed.get("coverage", []))
        for rec in parsed.get("records", []):
            cov = rec.get("coverage", {})
            if cov and cov.get("scheme_name"):
                coverage_list.append(cov)

        cov_id = _uuid()
        cov_data = coverage_list[0] if coverage_list else {}
        cov = build_coverage(cov_data, patient_id, insurer_id, cov_id)
        entries.append(_bundle_entry(cov))

        # CoverageEligibilityRequest (the first mandatory entry)
        cer_id = _uuid()
        cer = {
            "resourceType": "CoverageEligibilityRequest",
            "id": cer_id,
            "status": "active",
            "purpose": ["validation"],
            "patient": {"reference": f"Patient/{patient_id}"},
            "servicedDate": _now_iso()[:10],
            "created": _now_iso()[:10],
            "insurer": {"reference": f"Organization/{insurer_id}"},
            "provider": {"reference": f"Organization/{provider_id}"},
            "insurance": [{"coverage": {"reference": f"Coverage/{cov_id}"}}],
        }
        entries.insert(0, _bundle_entry(cer))

        bundle_id = _uuid()
        return {
            "resourceType": "Bundle",
            "id": bundle_id,
            "meta": {
                "profile": [f"{NRCES_BASE}CoverageEligibilityRequestBundle"],
                "lastUpdated": _now_iso(),
            },
            "type": self.bundle_type,
            "timestamp": _now_iso(),
            "entry": entries,
        }

    def _build_claim(
        self,
        claim_id: str,
        patient_ref: str,
        provider_ref: str,
        insurer_ref: str,
        condition_ids: list,
        network: str = "nhcx",
    ) -> dict:
        """Build a basic FHIR Claim resource."""
        return {
            "resourceType": "Claim",
            "id": claim_id,
            "status": "active",
            "type": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/claim-type",
                    "code": "institutional",
                    "display": "Institutional"
                }]
            },
            "use": "claim",
            "patient": {"reference": f"Patient/{patient_ref}"},
            "created": _now_iso()[:10],
            "insurer": {"reference": f"Organization/{insurer_ref}"},
            "provider": {"reference": f"Organization/{provider_ref}"},
            "priority": {
                "coding": [{"code": "normal"}]
            },
            "diagnosis": [
                {
                    "sequence": i + 1,
                    "diagnosisReference": {"reference": f"Condition/{cid}"},
                }
                for i, cid in enumerate(condition_ids)
            ],
        }

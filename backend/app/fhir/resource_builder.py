"""
FHIR Resource Builder — Aarohan++ Phase 3
Transforms canonical internal models into NRCeS-compliant FHIR R4 resources.
Uses the `fhir.resources` library for proper FHIR object construction.
"""

import uuid
import logging
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)

# NRCeS profile URLs
NRCES_BASE = "https://nrces.in/ndhm/fhir/r4/StructureDefinition/"
ABHA_SYSTEM = "https://healthid.ndhm.gov.in"
ICD10_SYSTEM = "http://hl7.org/fhir/sid/icd-10"
SNOMED_SYSTEM = "http://snomed.info/sct"
LOINC_SYSTEM = "http://loinc.org"


def _uuid() -> str:
    return str(uuid.uuid4())


def _today_iso() -> str:
    return date.today().isoformat()


def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+05:30")


# ─────────────────────────────────────────────────────────────────────────────
# Patient Resource
# ─────────────────────────────────────────────────────────────────────────────

def build_patient(patient_data: dict, patient_id: Optional[str] = None) -> dict:
    """
    Build a NRCeS-compliant FHIR Patient resource dict.

    Args:
        patient_data: Canonical patient dict (from any parser output)
        patient_id: Optional pre-assigned FHIR resource ID

    Returns:
        FHIR Patient dict ready to embed in a bundle entry
    """
    pid = patient_id or _uuid()

    # Build identifiers list
    identifiers = []
    abha_id = patient_data.get("abha_id")
    if abha_id:
        identifiers.append({
            "type": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                    "code": "SN",
                    "display": "Subscriber Number"
                }]
            },
            "system": ABHA_SYSTEM,
            "value": str(abha_id)
        })

    # Existing identifiers list
    for ident in patient_data.get("identifiers", []):
        if isinstance(ident, dict):
            identifiers.append(ident)
        elif isinstance(ident, str):
            identifiers.append({"system": "urn:oid:unknown", "value": ident})

    # Build HumanName
    name_str = patient_data.get("name", "")
    family = patient_data.get("family_name", "")
    given = patient_data.get("given_name", "")

    if not family and name_str:
        parts = name_str.strip().split()
        family = parts[-1] if parts else name_str
        given = " ".join(parts[:-1]) if len(parts) > 1 else ""

    human_name = {"use": "official"}
    if family:
        human_name["family"] = family
    if given:
        human_name["given"] = [given]
    if name_str and not family:
        human_name["text"] = name_str

    # Gender mapping
    gender_map = {
        "male": "male", "female": "female",
        "m": "male", "f": "female",
        "other": "other", "unknown": "unknown",
    }
    gender = gender_map.get(str(patient_data.get("gender", "unknown")).lower(), "unknown")

    # Birth date — use dob or derive from age
    birth_date = None
    dob = patient_data.get("birth_date") or patient_data.get("dob")
    if dob:
        if isinstance(dob, date):
            birth_date = dob.isoformat()
        else:
            birth_date = str(dob)
    elif patient_data.get("age"):
        approx_year = date.today().year - int(patient_data["age"])
        birth_date = f"{approx_year}-01-01"

    # Telecom
    telecom = []
    phone = patient_data.get("phone")
    if phone:
        telecom.append({
            "system": "phone",
            "value": str(phone),
            "use": "mobile"
        })

    # Address
    address = []
    addr_str = patient_data.get("address", "")
    if addr_str:
        address.append({
            "use": "home",
            "text": addr_str,
            "country": "IN"
        })

    resource = {
        "resourceType": "Patient",
        "id": pid,
        "meta": {
            "profile": [f"{NRCES_BASE}Patient"]
        },
        "identifier": identifiers,
        "name": [human_name],
        "gender": gender,
    }

    if birth_date:
        resource["birthDate"] = birth_date
    if telecom:
        resource["telecom"] = telecom
    if address:
        resource["address"] = address

    return resource


# ─────────────────────────────────────────────────────────────────────────────
# Condition (Diagnosis) Resource
# ─────────────────────────────────────────────────────────────────────────────

def build_condition(
    diagnosis: dict,
    patient_ref: str,
    condition_id: Optional[str] = None,
    encounter_ref: Optional[str] = None,
) -> dict:
    """Build a NRCeS-compliant FHIR Condition resource."""
    cid = condition_id or _uuid()
    code_text = diagnosis.get("text", "Unknown condition")
    code_val = diagnosis.get("code")
    code_system = diagnosis.get("system", ICD10_SYSTEM)

    coding = []
    if code_val:
        coding.append({
            "system": code_system,
            "code": str(code_val),
            "display": code_text
        })

    resource = {
        "resourceType": "Condition",
        "id": cid,
        "meta": {
            "profile": [f"{NRCES_BASE}Condition"]
        },
        "clinicalStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
        },
        "verificationStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]
        },
        "code": {
            "coding": coding,
            "text": code_text
        },
        "subject": {"reference": f"Patient/{patient_ref}"},
        "recordedDate": _today_iso(),
    }

    if encounter_ref:
        resource["encounter"] = {"reference": f"Encounter/{encounter_ref}"}

    return resource


# ─────────────────────────────────────────────────────────────────────────────
# MedicationRequest Resource
# ─────────────────────────────────────────────────────────────────────────────

def build_medication_request(
    medication: dict,
    patient_ref: str,
    med_req_id: Optional[str] = None,
    encounter_ref: Optional[str] = None,
) -> dict:
    """Build a NRCeS-compliant FHIR MedicationRequest resource."""
    mrid = med_req_id or _uuid()

    med_text = medication.get("text", "")
    generic = medication.get("generic_name", "")
    code_val = medication.get("code")
    code_system = medication.get("system", "https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-drugcode")

    coding = []
    if code_val:
        coding.append({
            "system": code_system,
            "code": str(code_val),
            "display": generic or med_text
        })

    resource = {
        "resourceType": "MedicationRequest",
        "id": mrid,
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": coding,
            "text": generic or med_text or "Unknown medication"
        },
        "subject": {"reference": f"Patient/{patient_ref}"},
        "authoredOn": _today_iso(),
    }

    if encounter_ref:
        resource["encounter"] = {"reference": f"Encounter/{encounter_ref}"}

    # Dosage
    dosage_text = medication.get("dosage", "")
    freq = medication.get("frequency", "")
    duration = medication.get("duration_raw", "")

    if dosage_text or freq:
        dosage = {}
        if dosage_text:
            dosage["text"] = f"{dosage_text} {freq}".strip()
        resource["dosageInstruction"] = [dosage]

    return resource


# ─────────────────────────────────────────────────────────────────────────────
# Observation Resource
# ─────────────────────────────────────────────────────────────────────────────

def build_observation(
    observation: dict,
    patient_ref: str,
    obs_id: Optional[str] = None,
    encounter_ref: Optional[str] = None,
) -> dict:
    """Build a NRCeS-compliant FHIR Observation resource."""
    oid = obs_id or _uuid()
    code_val = observation.get("code", "")
    display = observation.get("display", "")
    system = observation.get("system", LOINC_SYSTEM)
    value = observation.get("value", "")
    unit = observation.get("unit", "")

    resource = {
        "resourceType": "Observation",
        "id": oid,
        "status": "final",
        "code": {
            "coding": [{
                "system": system,
                "code": str(code_val),
                "display": display
            }],
            "text": display
        },
        "subject": {"reference": f"Patient/{patient_ref}"},
        "effectiveDateTime": _now_iso(),
    }

    # Value — try numeric first, then string
    try:
        numeric = float(value)
        resource["valueQuantity"] = {
            "value": numeric,
            "unit": unit,
            "system": "http://unitsofmeasure.org",
            "code": unit
        }
    except (ValueError, TypeError):
        if value:
            resource["valueString"] = str(value)

    if encounter_ref:
        resource["encounter"] = {"reference": f"Encounter/{encounter_ref}"}

    return resource


# ─────────────────────────────────────────────────────────────────────────────
# Encounter Resource
# ─────────────────────────────────────────────────────────────────────────────

def build_encounter(
    encounter_data: dict,
    patient_ref: str,
    organization_ref: Optional[str] = None,
    encounter_id: Optional[str] = None,
) -> dict:
    """Build a NRCeS-compliant FHIR Encounter resource."""
    eid = encounter_id or _uuid()

    class_code_map = {
        "IMP": ("IMP", "inpatient encounter"),
        "AMB": ("AMB", "ambulatory"),
        "EMER": ("EMER", "emergency"),
        "HH": ("HH", "home health"),
        "VR": ("VR", "virtual"),
    }
    enc_class = encounter_data.get("type", "AMB")
    class_code, class_display = class_code_map.get(enc_class, ("AMB", "ambulatory"))

    resource = {
        "resourceType": "Encounter",
        "id": eid,
        "status": "finished",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": class_code,
            "display": class_display
        },
        "subject": {"reference": f"Patient/{patient_ref}"},
    }

    # Period
    period = {}
    adm = encounter_data.get("admission_date") or encounter_data.get("date")
    dis = encounter_data.get("discharge_date")
    if adm:
        period["start"] = adm.isoformat() if isinstance(adm, date) else str(adm)
    if dis:
        period["end"] = dis.isoformat() if isinstance(dis, date) else str(dis)
    if period:
        resource["period"] = period

    if organization_ref:
        resource["serviceProvider"] = {"reference": f"Organization/{organization_ref}"}

    return resource


# ─────────────────────────────────────────────────────────────────────────────
# Organization Resource
# ─────────────────────────────────────────────────────────────────────────────

def build_organization(
    name: str,
    org_type: str = "prov",
    org_id: Optional[str] = None,
    identifier_value: Optional[str] = None,
) -> dict:
    """Build a NRCeS-compliant FHIR Organization resource (provider or insurer)."""
    oid = org_id or _uuid()

    resource = {
        "resourceType": "Organization",
        "id": oid,
        "meta": {"profile": [f"{NRCES_BASE}Organization"]},
        "name": name or "Unknown Organization",
        "type": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/organization-type",
                "code": org_type,
                "display": "Healthcare Provider" if org_type == "prov" else "Insurance Company"
            }]
        }]
    }

    if identifier_value:
        resource["identifier"] = [{
            "system": "https://facility.ndhm.gov.in",
            "value": identifier_value
        }]

    return resource

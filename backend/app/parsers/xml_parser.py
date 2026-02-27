"""
XML Parser — Aarohan++ Phase 1
Parses pharmacy/HMIS XML exports from Indian PHCs, like phc_rajasthan_pharmacy.xml.
Handles: custom namespaces, nested prescriptions, Hindi fields, missing codes.
"""

import re
import logging
from typing import Optional
from datetime import date
from pathlib import Path
from lxml import etree

logger = logging.getLogger(__name__)

HINDI_MEDICAL_MAP = {
    "bukhar": "Fever",
    "peyt dard": "Abdominal pain",
    "sir dard": "Headache",
    "khansi": "Cough",
    "sugar": "Diabetes mellitus",
    "bp": "Hypertension",
    "sans phoolna": "Dyspnoea",
    "kamzori": "Weakness",
    "ulti": "Vomiting",
    "dast": "Diarrhoea",
}


def _normalize_hindi(text: str) -> str:
    lower = text.strip().lower()
    for hindi, english in HINDI_MEDICAL_MAP.items():
        if hindi in lower:
            lower = lower.replace(hindi, english)
    return lower.strip().title()


def _parse_date(val: str) -> Optional[date]:
    if not val:
        return None
    val = val.strip()
    for pat, order in [
        (r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", "dmy"),
        (r"(\d{4})-(\d{2})-(\d{2})", "ymd"),
    ]:
        m = re.fullmatch(pat, val)
        if m:
            a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                if order == "dmy":
                    y = c + 2000 if c < 100 else c
                    return date(y, b, a)
                else:
                    return date(a, b, c)
            except ValueError:
                continue
    return None


def _text(el, path: str, ns: dict = None) -> str:
    """Extract text from an XPath (returns empty string if not found)."""
    try:
        results = el.xpath(path, namespaces=ns) if ns else el.xpath(path)
        return (results[0] or "").strip() if results else ""
    except Exception:
        return ""


def _normalize_gender(val: str) -> str:
    v = val.strip().lower()
    return "male" if v in ("m", "male") else "female" if v in ("f", "female") else "unknown"


class XMLParser:
    """
    XML parser for PHC / pharmacy HMIS exports.
    Handles arbitrary tag naming conventions and missing/empty elements gracefully.
    """

    def parse(self, filepath: str) -> dict:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"XML not found: {filepath}")

        result = {
            "source_file": path.name,
            "source_type": "xml",
            "facility": {},
            "records": [],
            "errors": [],
        }

        try:
            tree = etree.parse(str(path))
            root = tree.getroot()
        except Exception as e:
            result["errors"].append(f"XML parse error: {e}")
            return result

        # Strip namespace from tag names for convenience
        def tag(el):
            return re.sub(r"\{[^}]+\}", "", el.tag)

        def child_text(el, *names) -> str:
            for name in names:
                for child in el:
                    if tag(child).lower() in [n.lower() for n in [name]]:
                        return (child.text or "").strip()
            return ""

        def find_el(el, *names):
            for name in names:
                for child in el:
                    if tag(child).lower() == name.lower():
                        return child
            return None

        # ── Facility ─────────────────────────────────────────────────────────
        facility_el = find_el(root, "Facility", "facility", "Hospital", "hospital", "FacilityInfo")
        if facility_el is not None:
            result["facility"] = {
                "name": child_text(facility_el, "Name", "HospitalName", "FacilityName"),
                "id": facility_el.get("id") or child_text(facility_el, "ID", "FacilityID"),
                "type": child_text(facility_el, "Type", "HospitalType", "FacilityType"),
                "state": child_text(facility_el, "State"),
                "district": child_text(facility_el, "District"),
                "pincode": child_text(facility_el, "Pincode", "PIN"),
            }

        # ── Patient Records ───────────────────────────────────────────────────
        # Strategy 1: Standard patient containers
        patient_containers = ["Patients", "patients", "PatientList", "Records", "Data"]
        patient_tags = ["Patient", "patient", "Record", "Case"]

        # Strategy 2: Prescription-based containers (PHC pharmacy style)
        prescription_containers = ["Prescriptions", "prescriptions", "PrescriptionList"]
        prescription_tags = ["Prescription", "prescription", "Rx"]

        found_records = False

        # Try patient-based containers first
        container = None
        for c_name in patient_containers:
            container = find_el(root, c_name)
            if container is not None:
                break

        if container is not None:
            for child in container:
                if tag(child) not in patient_tags and tag(child).lower() not in [t.lower() for t in patient_tags]:
                    continue
                try:
                    record = self._parse_patient(child, child_text, find_el, tag)
                    if record["patient"].get("name") or record["diagnoses"] or record["medications"]:
                        result["records"].append(record)
                        found_records = True
                except Exception as e:
                    result["errors"].append(f"Patient parse error: {e}")

        # Try prescription-based containers (Prescriptions → Prescription → Patient + Visit + Medications)
        if not found_records:
            rx_container = None
            for c_name in prescription_containers:
                rx_container = find_el(root, c_name)
                if rx_container is not None:
                    break

            if rx_container is not None:
                for child in rx_container:
                    if tag(child).lower() not in [t.lower() for t in prescription_tags]:
                        continue
                    try:
                        # In this structure, Patient / Visit / Medications are CHILDREN of Prescription
                        record = self._parse_prescription(child, child_text, find_el, tag)
                        if record["patient"].get("name") or record["diagnoses"] or record["medications"]:
                            result["records"].append(record)
                    except Exception as e:
                        result["errors"].append(f"Prescription parse error: {e}")

        return result

    def _parse_prescription(self, rx_el, child_text_fn, find_el_fn, tag_fn) -> dict:
        """
        Parse a Prescription element where Patient, Visit, Medications are direct children.
        PHC Rajasthan pharmacy style: <Prescription id=...><Patient>...</Patient><Visit>...</Visit>...
        """
        # ── Patient ───────────────────────────────────────────────────────────
        pat_el = find_el_fn(rx_el, "Patient", "patient")
        patient = {}
        if pat_el is not None:
            patient = {
                "id":     child_text_fn(pat_el, "PatientID", "ID", "MRN"),
                "name":   child_text_fn(pat_el, "Name", "PatientName", "FullName"),
                "age":    child_text_fn(pat_el, "Age"),
                "gender": _normalize_gender(child_text_fn(pat_el, "Gender", "Sex")),
                "address": child_text_fn(pat_el, "Address", "Village", "Locality"),
                "phone":  child_text_fn(pat_el, "Phone", "Mobile", "Contact"),
                "bpl_card": child_text_fn(pat_el, "BPLCard", "BPLCardNumber", "BPL"),
                "abha_id":  child_text_fn(pat_el, "ABHA", "ABHANumber", "HealthID"),
            }

        # ── Visit / Encounter ─────────────────────────────────────────────────
        visit_el = find_el_fn(rx_el, "Visit", "Encounter", "VisitInfo")
        encounter = {}
        diagnoses = []
        if visit_el is not None:
            enc_type_raw = child_text_fn(visit_el, "Type", "VisitType")
            type_map = {"opd": "AMB", "ipd": "IMP", "emergency": "EMER"}
            encounter = {
                "type": type_map.get(enc_type_raw.lower(), "AMB"),
                "date": _parse_date(child_text_fn(visit_el, "Date", "VisitDate")),
                "chief_complaint": child_text_fn(visit_el, "Complaint", "ChiefComplaint"),
                "facility_name": "",
            }

            # Diagnosis is a sibling of Patient inside Visit in Rajasthan format
            diag_text = child_text_fn(visit_el, "Diagnosis", "DiagnosisName", "Description")
            diag_code = child_text_fn(visit_el, "DiagnosisCode", "Code", "ICD")
            if diag_text:
                diagnoses.append({
                    "text": _normalize_hindi(diag_text),
                    "raw": diag_text,
                    "code": diag_code or None,
                    "system": "http://hl7.org/fhir/sid/icd-10" if diag_code else None,
                })

        # ── Medications ───────────────────────────────────────────────────────
        medications = []
        meds_el = find_el_fn(rx_el, "Medications", "Drugs", "Medicines")
        if meds_el is not None:
            for med_el in meds_el:
                try:
                    brand   = child_text_fn(med_el, "BrandName", "DrugName", "Name", "Medicine")
                    generic = child_text_fn(med_el, "GenericName", "Generic")
                    code    = child_text_fn(med_el, "DrugCode", "Code", "LocalCode")
                    dosage  = child_text_fn(med_el, "Dosage", "Dose", "Strength")
                    freq    = child_text_fn(med_el, "Frequency", "Freq", "Schedule")
                    duration= child_text_fn(med_el, "Duration", "Days", "DurationDays")
                    if brand or generic:
                        medications.append({
                            "text": generic or brand,  # prefer generic for drug mapping
                            "brand_name": brand,
                            "generic_name": generic,
                            "code": code or None,
                            "system": None,
                            "dosage": dosage,
                            "frequency": freq,
                            "duration_raw": duration,
                        })
                except Exception:
                    pass

        return {"patient": patient, "encounter": encounter,
                "diagnoses": diagnoses, "medications": medications}

    def _parse_patient(self, el, child_text_fn, find_el_fn, tag_fn) -> dict:
        """Extract a single patient record from an XML element."""

        patient = {
            "id": el.get("id") or child_text_fn(el, "PatientID", "ID", "MRN"),
            "name": child_text_fn(el, "Name", "PatientName", "FullName"),
            "age": child_text_fn(el, "Age"),
            "gender": _normalize_gender(child_text_fn(el, "Gender", "Sex")),
            "address": child_text_fn(el, "Address", "Village", "Locality"),
            "phone": child_text_fn(el, "Phone", "Mobile", "Contact"),
            "bpl_card": child_text_fn(el, "BPLCardNumber", "BPL", "RationCardNumber"),
            "abha_id": child_text_fn(el, "ABHA", "ABHANumber", "HealthID"),
        }

        # ── Visit / Encounter ─────────────────────────────────────────────────
        visit_el = find_el_fn(el, "Visit", "Encounter", "VisitInfo")
        encounter = {}
        if visit_el is not None:
            encounter = {
                "type": "AMB",
                "date": _parse_date(child_text_fn(visit_el, "Date", "VisitDate", "AdmissionDate")),
                "chief_complaint": child_text_fn(visit_el, "ChiefComplaint", "Complaint", "Presenting Complaint"),
            }

        # ── Diagnoses ─────────────────────────────────────────────────────────
        diagnoses = []
        diag_el = find_el_fn(el, "Diagnosis", "Diagnoses", "DiagnosisInfo")
        if diag_el is not None:
            diag_text = child_text_fn(diag_el, "Name", "DiagnosisName", "Description", "Text")
            diag_code = child_text_fn(diag_el, "Code", "DiagnosisCode", "ICD", "SNOMED")
            if diag_text:
                diagnoses.append({
                    "text": _normalize_hindi(diag_text),
                    "raw": diag_text,
                    "code": diag_code or None,
                    "system": "http://hl7.org/fhir/sid/icd-10" if diag_code else None,
                })

        # ── Medications ───────────────────────────────────────────────────────
        medications = []
        meds_el = find_el_fn(el, "Medications", "Prescription", "Drugs", "Medicines")
        if meds_el is not None:
            for med_el in meds_el:
                try:
                    brand = child_text_fn(med_el, "BrandName", "DrugName", "Name", "Medicine")
                    generic = child_text_fn(med_el, "GenericName", "Generic")
                    code = child_text_fn(med_el, "DrugCode", "Code", "LocalCode")
                    dosage = child_text_fn(med_el, "Dosage", "Dose", "Strength")
                    freq = child_text_fn(med_el, "Frequency", "Freq", "Schedule")
                    duration = child_text_fn(med_el, "Duration", "Days", "DurationDays")

                    if brand or generic:
                        medications.append({
                            "text": brand or generic,
                            "generic_name": generic,
                            "code": code or None,
                            "system": None,
                            "dosage": dosage,
                            "frequency": freq,
                            "duration_raw": duration,
                        })
                except Exception:
                    pass

        return {
            "patient": patient,
            "encounter": encounter,
            "diagnoses": diagnoses,
            "medications": medications,
        }

"""
HL7v2 Parser — Aarohan++ Phase 1
Parses HL7v2 ADT^A01 (and related) messages from Indian hospitals.
Handles Tamil script names, ICD-10 codes, LOINC coded observations, insurance segments.
Uses the `hl7` library for reliable segment access.
"""

import re
import logging
from typing import Optional
from datetime import date, datetime

logger = logging.getLogger(__name__)


def _parse_hl7_date(val: str) -> Optional[date]:
    """Parse HL7 date formats: YYYYMMDD, YYYY-MM-DD."""
    val = val.strip()
    try:
        if len(val) == 8 and val.isdigit():
            return date(int(val[:4]), int(val[4:6]), int(val[6:8]))
        if re.match(r"\d{4}-\d{2}-\d{2}", val):
            return date(int(val[:4]), int(val[5:7]), int(val[8:10]))
    except ValueError:
        pass
    return None


def _normalize_gender_hl7(val: str) -> str:
    v = val.strip().upper()
    return "male" if v == "M" else "female" if v == "F" else "unknown"


def _get_field(segment, field_idx: int, comp_idx: int = 0) -> str:
    """Safely extract a field/component from an hl7 segment."""
    try:
        field = segment[field_idx]
        if isinstance(field, list):
            comp = field[comp_idx] if comp_idx < len(field) else field[0]
            return str(comp).strip()
        return str(field).strip()
    except (IndexError, TypeError, AttributeError):
        return ""


class HL7Parser:
    """
    HL7v2 parser targeting ADT^A01, ADT^A08 message types.
    Extracts PID, PV1, DG1, IN1, PR1, OBX, AL1 segments.
    """

    def parse(self, filepath: str) -> dict:
        try:
            import hl7
        except ImportError:
            raise ImportError("hl7 library not installed. Run: pip install hl7")

        result = {
            "source_file": filepath,
            "source_type": "hl7v2",
            "patient": {},
            "encounters": [],
            "diagnoses": [],
            "medications": [],
            "observations": [],
            "coverage": [],
            "procedures": [],
            "allergies": [],
            "errors": [],
        }

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()
        except Exception as e:
            result["errors"].append(f"Read error: {e}")
            return result

        # hl7 library requires \r as segment separator
        raw = raw.replace("\r\n", "\r").replace("\n", "\r")

        try:
            msg = hl7.parse(raw)
        except Exception as e:
            result["errors"].append(f"HL7 parse error: {e}")
            return result

        # ── PID — Patient Identification ─────────────────────────────────────
        try:
            pid = msg.segment("PID")
            name_raw = _get_field(pid, 5)   # e.g. "Murugesan^Arjun^^^Mr"
            name_parts = name_raw.split("^")
            family = name_parts[0] if name_parts else ""
            given = name_parts[1] if len(name_parts) > 1 else ""

            dob_raw = _get_field(pid, 7)
            gender_raw = _get_field(pid, 8)
            phone_raw = _get_field(pid, 13)
            address_raw = _get_field(pid, 11)

            # Check for ABHA in ID field (PID-3)
            abha_id = None
            try:
                pid3 = str(pid[3]).strip()
                abha_match = re.search(r"\d{2}-\d{4}-\d{4}-\d{4}", pid3)
                if abha_match:
                    abha_id = abha_match.group(0)
            except Exception:
                pass

            result["patient"] = {
                "name": f"{given} {family}".strip(),
                "family_name": family,
                "given_name": given,
                "dob": _parse_hl7_date(dob_raw),
                "gender": _normalize_gender_hl7(gender_raw),
                "phone": re.sub(r"[^\d+]", "", phone_raw)[:13] if phone_raw else None,
                "address": address_raw,
                "abha_id": abha_id,
            }
        except Exception as e:
            result["errors"].append(f"PID parse error: {e}")

        # ── PV1 — Patient Visit ───────────────────────────────────────────────
        try:
            pv1 = msg.segment("PV1")
            admit_raw = _get_field(pv1, 44)
            discharge_raw = _get_field(pv1, 45)
            visit_type = _get_field(pv1, 2)
            class_map = {"I": "IMP", "O": "AMB", "E": "EMER", "R": "AMB"}

            result["encounters"].append({
                "type": class_map.get(visit_type, "AMB"),
                "admission_date": _parse_hl7_date(admit_raw),
                "discharge_date": _parse_hl7_date(discharge_raw),
                "facility_name": _get_field(pv1, 3),
            })
        except Exception as e:
            result["errors"].append(f"PV1 parse error: {e}")

        # ── DG1 — Diagnosis ───────────────────────────────────────────────────
        for seg in msg:
            if str(seg[0]) != "DG1":
                continue
            try:
                code_raw = str(seg[3]).strip()
                parts = code_raw.split("^")
                code = parts[0] if parts else ""
                system_raw = parts[2] if len(parts) > 2 else ""
                system = "http://hl7.org/fhir/sid/icd-10" if "ICD" in system_raw.upper() else \
                         "http://snomed.info/sct" if "SNOMED" in system_raw.upper() else None
                description = parts[1] if len(parts) > 1 else str(seg[4]).strip()

                result["diagnoses"].append({
                    "text": description,
                    "code": code,
                    "system": system,
                    "confidence": 0.9 if code else 0.5,
                })
            except Exception as e:
                result["errors"].append(f"DG1 parse error: {e}")

        # ── IN1 — Insurance ───────────────────────────────────────────────────
        for seg in msg:
            if str(seg[0]) != "IN1":
                continue
            try:
                result["coverage"].append({
                    "plan_name": str(seg[4]).strip(),
                    "plan_id": str(seg[2]).strip(),
                    "insurer_name": str(seg[4]).strip(),
                    "policy_number": str(seg[36]).strip(),
                })
            except Exception as e:
                result["errors"].append(f"IN1 parse error: {e}")

        # ── OBX — Observations ────────────────────────────────────────────────
        for seg in msg:
            if str(seg[0]) != "OBX":
                continue
            try:
                code_raw = str(seg[3]).strip().split("^")
                code = code_raw[0]
                display = code_raw[1] if len(code_raw) > 1 else ""
                system_raw = code_raw[2] if len(code_raw) > 2 else ""
                system = "http://loinc.org" if "LN" in system_raw or "LOINC" in system_raw.upper() else None

                result["observations"].append({
                    "code": code,
                    "display": display,
                    "system": system,
                    "value": str(seg[5]).strip(),
                    "unit": str(seg[6]).strip() if len(seg) > 6 else None,
                })
            except Exception as e:
                result["errors"].append(f"OBX parse error: {e}")

        # ── PR1 — Procedures ──────────────────────────────────────────────────
        for seg in msg:
            if str(seg[0]) != "PR1":
                continue
            try:
                code_raw = str(seg[3]).strip().split("^")
                result["procedures"].append({
                    "code": code_raw[0],
                    "display": code_raw[1] if len(code_raw) > 1 else "",
                    "date": _parse_hl7_date(str(seg[5]).strip()),
                })
            except Exception as e:
                result["errors"].append(f"PR1 parse error: {e}")

        # ── AL1 — Allergies ───────────────────────────────────────────────────
        for seg in msg:
            if str(seg[0]) != "AL1":
                continue
            try:
                result["allergies"].append({
                    "code": str(seg[3]).strip().split("^")[0],
                    "display": str(seg[3]).strip().split("^")[1] if "^" in str(seg[3]) else str(seg[3]).strip(),
                    "severity": str(seg[4]).strip(),
                })
            except Exception as e:
                result["errors"].append(f"AL1 parse error: {e}")

        return result

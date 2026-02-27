"""
CSV Parser — Aarohan++ Phase 1
Parses flat CSV exports from Indian HMIS like district_hospital_bihar.csv.
Handles: Hindi free-text fields, mixed date formats, missing values, auto-delimiters.
"""

import re
import csv
import io
import logging
from pathlib import Path
from typing import Optional
from datetime import date

logger = logging.getLogger(__name__)


# ─── Hindi → English medical term map ──────────────────────────────────────────
HINDI_MEDICAL_MAP = {
    "sugar ki bimari": "Diabetes mellitus",
    "madhumeh": "Diabetes mellitus",
    "bp ki bimari": "Hypertension",
    "ucch raktachaap": "Hypertension",
    "peyt mein dard": "Abdominal pain",
    "pet dard": "Abdominal pain",
    "bukhar": "Fever",
    "khansi": "Cough",
    "sans ki takleef": "Dyspnoea",
    "seene mein dard": "Chest pain",
    "sir dard": "Headache",
    "kamzori": "Weakness",
    "chakkar": "Vertigo/Dizziness",
    "urine mein jalan": "Burning micturition",
    "khoon ki kami": "Anaemia",
    "hath pair mein soojan": "Pedal oedema",
}


def _normalize_hindi(text: str) -> str:
    """Translate known Hindi medical phrases to English equivalents."""
    lower = text.strip().lower()
    for hindi, english in HINDI_MEDICAL_MAP.items():
        if hindi in lower:
            lower = lower.replace(hindi, english)
    return lower.strip().title()


def _detect_delimiter(sample: str) -> str:
    """Auto-detect CSV delimiter from a text sample."""
    counts = {d: sample.count(d) for d in [",", ";", "\t", "|"]}
    return max(counts, key=counts.get)


def _parse_date(val: str) -> Optional[date]:
    """Try multiple Indian date formats."""
    val = val.strip()
    patterns = [
        (r"(\d{1,2})/(\d{1,2})/(\d{2,4})", "dmy"),
        (r"(\d{1,2})-(\d{1,2})-(\d{2,4})", "dmy"),
        (r"(\d{4})-(\d{2})-(\d{2})", "ymd"),
    ]
    for pat, order in patterns:
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


def _safe_int(val: str) -> Optional[int]:
    try:
        return int(val.strip())
    except (ValueError, AttributeError):
        return None


def _safe_float(val: str) -> Optional[float]:
    try:
        return float(val.strip().replace(",", ""))
    except (ValueError, AttributeError):
        return None


def _normalize_gender(val: str) -> str:
    v = val.strip().lower()
    if v in ("m", "male", "purush"):
        return "male"
    if v in ("f", "female", "mahila", "stri"):
        return "female"
    return "unknown"


class CSVParser:
    """
    CSV parser for flat Indian HMIS exports.
    Auto-detects delimiters, normalises Hindi free-text, and extracts canonical records.
    """

    # Flexible column aliases  (lowercase)
    COLUMN_ALIASES = {
        "patient_id": ["patient_id", "pid", "patient id", "id"],
        "name": ["patient_name", "name", "patient name", "name of patient"],
        "age": ["age", "patient_age", "age (years)", "age_years"],
        "gender": ["gender", "sex", "patient_gender"],
        "address": ["address", "patient_address", "village", "locality"],
        "phone": ["phone", "mobile", "contact", "mobile_no"],
        "date": ["date", "visit_date", "admission_date", "date of visit"],
        "diagnosis": ["diagnosis", "chief_diagnosis", "final_diagnosis", "primary_diagnosis",
                      "diagnosis_code", "icd_code"],
        "drug_name": ["drug_prescribed", "drug_name", "medicine", "medication", "prescription"],
        "hospital_name": ["hospital_name", "facility", "hospital", "hf_name"],
        "insurance_scheme": ["insurance_scheme", "scheme", "scheme_name", "payer"],
        "claim_amount": ["claim_amount", "total_amount", "amount", "bill_amount"],
    }

    def _map_columns(self, headers: list) -> dict:
        """Map actual CSV headers → canonical field names."""
        mapping = {}
        normalized_headers = {h.strip().lower(): h for h in headers}
        for canonical, aliases in self.COLUMN_ALIASES.items():
            for alias in aliases:
                if alias in normalized_headers:
                    mapping[canonical] = normalized_headers[alias]
                    break
        return mapping

    def parse(self, filepath: str) -> dict:
        """
        Parse a CSV file and return a list of canonical patient records.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"CSV not found: {filepath}")

        result = {
            "source_file": path.name,
            "source_type": "csv",
            "records": [],
            "errors": [],
            "row_count": 0,
            "parsed_count": 0,
        }

        try:
            raw = path.read_text(encoding="utf-8-sig", errors="replace")
        except Exception as e:
            result["errors"].append(f"Read error: {e}")
            return result

        delimiter = _detect_delimiter(raw[:2000])
        reader = csv.DictReader(io.StringIO(raw), delimiter=delimiter)

        if not reader.fieldnames:
            result["errors"].append("CSV has no headers")
            return result

        col_map = self._map_columns(list(reader.fieldnames))

        for i, row in enumerate(reader):
            result["row_count"] += 1
            try:
                record = self._parse_row(row, col_map, i + 2)
                result["records"].append(record)
                result["parsed_count"] += 1
            except Exception as e:
                result["errors"].append(f"Row {i + 2}: {e}")

        return result

    def _parse_row(self, row: dict, col_map: dict, row_num: int) -> dict:
        def get(field):
            col = col_map.get(field)
            return row.get(col, "").strip() if col else ""

        diag_raw = get("diagnosis")
        diag_normalised = _normalize_hindi(diag_raw) if diag_raw else ""

        return {
            "patient": {
                "id": get("patient_id") or f"row-{row_num}",
                "name": get("name"),
                "age": _safe_int(get("age")),
                "gender": _normalize_gender(get("gender")),
                "address": get("address"),
                "phone": get("phone"),
            },
            "encounter": {
                "date": _parse_date(get("date")),
                "facility_name": get("hospital_name"),
                "type": "AMB",
            },
            "diagnoses": [{"text": diag_normalised, "raw": diag_raw, "code": None, "system": None}]
            if diag_normalised else [],
            "medications": [{"text": get("drug_name"), "code": None, "system": None}]
            if get("drug_name") else [],
            "coverage": {
                "scheme_name": get("insurance_scheme"),
                "claim_amount": _safe_float(get("claim_amount")),
            },
        }

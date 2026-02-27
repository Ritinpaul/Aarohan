"""
PDF Parser — Aarohan++ Phase 1
Extracts structured data from digital and scanned PDF documents (Diagnostic Reports & Discharge Summaries).
Strategy:
  1. Try PyMuPDF (fitz) for native text extraction (digital PDFs)
  2. If text yield is < 50 chars/page, fall back to pytesseract OCR (scanned PDFs)
  3. Apply regex + keyword heuristics to extract clinical entities
"""

import re
import fitz  # PyMuPDF
import logging
from pathlib import Path
from typing import Optional
from datetime import date, datetime

logger = logging.getLogger(__name__)


# ─── Regex Patterns ────────────────────────────────────────────────────────────

DATE_PATTERNS = [
    r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b",           # DD/MM/YYYY or DD-MM-YYYY
    r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{4})\b",   # 15 Nov 2024
    r"\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b",              # YYYY-MM-DD
]

NAME_PATTERN = re.compile(
    r"(?:Patient\s*Name|Name of Patient|Patient)[:\s]+([A-Za-z\s\.]+?)(?:\n|,|Age|D\.?O\.?B|Gender|Sex|Mr\.|Mrs\.)",
    re.IGNORECASE,
)

AGE_PATTERN = re.compile(r"\bAge[:\s]+(\d{1,3})\s*(?:Years?|Yrs?|Y)?", re.IGNORECASE)

GENDER_PATTERN = re.compile(r"\b(?:Sex|Gender)[:\s]+(Male|Female|M|F|Other)\b", re.IGNORECASE)

ABHA_PATTERN = re.compile(r"\bABHA\s*(?:No|Number|ID)?[:\s]+(\d{2}-\d{4}-\d{4}-\d{4})\b", re.IGNORECASE)

PHONE_PATTERN = re.compile(r"\b(?:Mobile|Phone|Contact|Tel)[:\s]+([\d\s\-\+]{10,13})\b", re.IGNORECASE)

DIAGNOSIS_PATTERN = re.compile(
    r"(?:Diagnosis|Final Diagnosis|Provisional Diagnosis|Impression|Assessment)[:\s]+([^\n]{5,200})",
    re.IGNORECASE,
)

DISCHARGE_DATE_PATTERN = re.compile(
    r"(?:Discharge Date|Date of Discharge|DOD)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)

ADMISSION_DATE_PATTERN = re.compile(
    r"(?:Admission Date|Date of Admission|DOA)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)

FACILITY_PATTERN = re.compile(
    r"(?:Hospital|Medical|Health|Institute|Centre|Center|Clinic|AIIMS|NIMHANS|PGI)[^\n]{0,60}",
    re.IGNORECASE,
)

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_date(text: str) -> Optional[date]:
    """Try multiple date formats to extract a valid date."""
    # DD/MM/YYYY or DD-MM-YYYY
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d)
        except ValueError:
            pass
    # YYYY-MM-DD
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    return None


def _extract_text_digital(pdf_path: str) -> str:
    """Extract text using PyMuPDF (fast, no GPU needed)."""
    text_parts = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


def _extract_text_ocr(pdf_path: str) -> str:
    """
    OCR fallback for scanned PDFs using pytesseract.
    Only invoked when digital extraction yields < 50 chars/page.
    """
    try:
        import pytesseract
        from PIL import Image
        import io

        text_parts = []
        with fitz.open(pdf_path) as doc:
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes))
                text_parts.append(pytesseract.image_to_string(img, lang="eng"))
        return "\n".join(text_parts)
    except ImportError:
        logger.warning("pytesseract not available — OCR fallback skipped")
        return ""
    except Exception as e:
        logger.error(f"OCR extraction failed for {pdf_path}: {e}")
        return ""


def _is_scanned(text: str, page_count: int) -> bool:
    return (len(text) / max(1, page_count)) < 50


class PDFParser:
    """
    Multi-strategy PDF parser for Indian hospital documents.
    Extracts: patient demographics, diagnoses, medications, dates, facility name.
    """

    def parse(self, filepath: str) -> dict:
        """
        Parse a PDF and return a structured extraction dict.
        Returns a canonical-ready dict with lists of extracted entities.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {filepath}")

        result = {
            "source_file": path.name,
            "source_type": "pdf",
            "patient": {},
            "encounters": [],
            "diagnoses": [],
            "medications": [],
            "observations": [],
            "facility_name": None,
            "raw_text_length": 0,
            "is_scanned": False,
            "extraction_confidence": 0.0,
            "errors": [],
        }

        try:
            with fitz.open(filepath) as doc:
                page_count = len(doc)

            digital_text = _extract_text_digital(filepath)

            if _is_scanned(digital_text, page_count):
                result["is_scanned"] = True
                logger.info(f"{path.name}: scanned PDF — using OCR")
                text = _extract_text_ocr(filepath)
            else:
                text = digital_text

            result["raw_text_length"] = len(text)

            # ── Patient Demographics ──────────────────────────────────────────
            patient = {}

            name_m = NAME_PATTERN.search(text)
            if name_m:
                patient["name"] = name_m.group(1).strip()

            age_m = AGE_PATTERN.search(text)
            if age_m:
                patient["age"] = int(age_m.group(1))

            gender_m = GENDER_PATTERN.search(text)
            if gender_m:
                raw_gender = gender_m.group(1).strip().lower()
                patient["gender"] = "male" if raw_gender in ("male", "m") else \
                                    "female" if raw_gender in ("female", "f") else "other"

            abha_m = ABHA_PATTERN.search(text)
            if abha_m:
                patient["abha_id"] = abha_m.group(1).strip()

            phone_m = PHONE_PATTERN.search(text)
            if phone_m:
                patient["phone"] = re.sub(r"\s", "", phone_m.group(1))

            result["patient"] = patient

            # ── Facility ─────────────────────────────────────────────────────
            fac_m = FACILITY_PATTERN.search(text)
            if fac_m:
                result["facility_name"] = fac_m.group(0).strip()

            # ── Encounters (Admission / Discharge dates) ──────────────────────
            encounter = {}
            adm_m = ADMISSION_DATE_PATTERN.search(text)
            if adm_m:
                encounter["admission_date"] = _parse_date(adm_m.group(1))

            dis_m = DISCHARGE_DATE_PATTERN.search(text)
            if dis_m:
                encounter["discharge_date"] = _parse_date(dis_m.group(1))

            if encounter:
                encounter["type"] = "IMP"  # Inpatient
                result["encounters"].append(encounter)

            # ── Diagnoses ────────────────────────────────────────────────────
            for diag_m in DIAGNOSIS_PATTERN.finditer(text):
                diag_text = diag_m.group(1).strip()
                if diag_text:
                    result["diagnoses"].append({
                        "text": diag_text,
                        "code": None,
                        "system": None,
                        "confidence": 0.6,
                    })

            # ── Medications (basic keyword extraction) ────────────────────────
            med_pattern = re.compile(
                r"(?:Tab|Cap|Inj|Syp|Liquid|Drops?|Ointment)[.\s]+([A-Za-z0-9\s\-/]+?)(?:\d|mg|ml|units|daily|BD|TDS|OD|\n)",
                re.IGNORECASE,
            )
            for med_m in med_pattern.finditer(text):
                med_text = med_m.group(1).strip()
                if med_text and len(med_text) > 2:
                    result["medications"].append({
                        "text": med_text,
                        "code": None,
                        "system": None,
                        "confidence": 0.5,
                    })

            # ── Confidence ────────────────────────────────────────────────────
            fields_found = sum([
                bool(patient.get("name")),
                bool(patient.get("gender")),
                bool(patient.get("age")),
                bool(result["diagnoses"]),
                bool(result["facility_name"]),
            ])
            result["extraction_confidence"] = round(fields_found / 5, 2)

        except Exception as e:
            logger.error(f"PDFParser failed for {filepath}: {e}")
            result["errors"].append(str(e))

        return result

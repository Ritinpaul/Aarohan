"""
PDF Parser — Aarohan++ Phase 1 (v3 — 3-Layer Cascade)
Strategy:
  Layer 1: pdfplumber   → Best for digital PDFs, forms, tables
  Layer 2: PyMuPDF      → Fallback for simple digital PDFs
  Layer 3: Tesseract    → OCR for scanned/image-only PDFs
"""
import re
import logging
import os
from pathlib import Path
from typing import Optional
from datetime import date

logger = logging.getLogger(__name__)


# ─── Tesseract Auto-Detection ─────────────────────────────────────────────────

def _configure_tesseract() -> bool:
    try:
        import pytesseract
        windows_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Users\ritin\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        ]
        for p in windows_paths:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                return True
        import shutil
        if shutil.which("tesseract"):
            return True
        logger.warning("Tesseract not installed. OCR unavailable for scanned PDFs. Install: https://github.com/UB-Mannheim/tesseract/wiki")
        return False
    except ImportError:
        return False


TESSERACT_AVAILABLE = _configure_tesseract()


# ─── Regex Patterns (tuned for Indian hospital PDFs) ─────────────────────────

# Matches compact "CRNo.:x Name:John Age" and standard "Patient Name: John"
NAME_PATTERN = re.compile(
    r"(?:Patient\s*Name|Name of Patient|Pt\.?\s*Name)[:\s]+([A-Za-z\s\.]+?)(?:\n|,|Age|D\.?O\.?B|Gender|Sex|Ph|Mob)"
    r"|Name[:\s]+([A-Za-z][A-Za-z\s\.]{2,30})(?:\s*Age|/Gender|\n)",
    re.IGNORECASE,
)

# Compact "Age/Gender:48Yr/F" — very common in Indian HIS exports
AGE_GENDER_PATTERN = re.compile(
    r"Age[\s/]*Gender[:\s]+(\d{1,3})\s*(?:Yr|Years?|Yrs?|Y)?\s*/\s*(M(?:ale)?|F(?:emale)?)",
    re.IGNORECASE,
)
AGE_PATTERN = re.compile(r"\bAge[:\s]+(\d{1,3})\s*(?:Years?|Yrs?|Y)?", re.IGNORECASE)
GENDER_PATTERN = re.compile(r"\b(?:Sex|Gender)[:\s]+(Male|Female|M|F|Other)\b", re.IGNORECASE)
ABHA_PATTERN = re.compile(r"\bABHA\s*(?:No|Number|ID)?[:\s]+(\d{2}-\d{4}-\d{4}-\d{4})\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"\b(?:Mobile|Phone|Contact|Tel|ContactNo)[.:\s]+(\d[\d\s\-\+]{9,12})(?:\s|$)", re.IGNORECASE)

DIAGNOSIS_PATTERN = re.compile(
    r"(?:Diagnosis|Final\s*Diagnosis|Provisional\s*Diagnosis|Impression|Assessment"
    r"|CHRONICDISEASES|Chronic\s*Diseases|CASE\s*SUMMARY|Case\s*Summary)[:\s]+([^\n]{5,200})",
    re.IGNORECASE,
)
CHIEF_COMPLAINT_PATTERN = re.compile(
    r"(?:CHIEF\s*COMPLAINTS?|Chief\s*Complaints?)[:\s]*\n((?:[^\n]+\n?){1,10})",
    re.IGNORECASE,
)

# DOA/DOD compact: "D.O.A.:08-Sep-2022 16:08" or "D.O.D.:22-Dec-2023"
ADMISSION_DATE_PATTERN = re.compile(
    r"(?:D\.O\.A\.|DOA|Admission\s*Date|Date\s*of\s*Admission)[.:\s]+"
    r"(\d{1,2}[-/]\w{2,9}[-/]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
    re.IGNORECASE,
)
DISCHARGE_DATE_PATTERN = re.compile(
    r"(?:D\.O\.D\.|DOD|Discharge\s*Date|Date\s*of\s*Discharge)[.:\s]+"
    r"(\d{1,2}[-/]\w{2,9}[-/]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
    re.IGNORECASE,
)
FACILITY_PATTERN = re.compile(
    r"(?:Department|Hospital|Medical|Health|Institute|Centre|Center|Clinic|AIIMS|PGI|Govt)[A-Za-z\s]{0,60}",
    re.IGNORECASE,
)
MED_PATTERN = re.compile(
    r"(?:Tab|Cap|Inj|Syp|Liquid|Drops?|Ointment|Cream)[.\s]+([A-Za-z0-9\s\-/]+?)(?:\d|mg|ml|units|daily|BD|TDS|OD|\n)",
    re.IGNORECASE,
)

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_date(text: str) -> Optional[date]:
    # handles "08-Sep-2022" style
    m = re.search(r"(\d{1,2})[-/]([A-Za-z]{3})[-/](\d{2,4})", text)
    if m:
        d, mon, y = int(m.group(1)), m.group(2).lower()[:3], int(m.group(3))
        if y < 100:
            y += 2000
        month = MONTH_MAP.get(mon)
        if month:
            try:
                return date(y, month, d)
            except ValueError:
                pass
    # handles "DD/MM/YYYY"
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d)
        except ValueError:
            pass
    # handles "YYYY-MM-DD"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    return None


# ─── Extraction Layers ────────────────────────────────────────────────────────

def _extract_pdfplumber(filepath: str) -> str:
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                for table in (page.extract_tables() or []):
                    for row in table:
                        row_text = "  ".join(cell or "" for cell in row if cell)
                        if row_text.strip():
                            text += "\n" + row_text
                pages.append(text)
        return "\n".join(pages)
    except Exception as e:
        logger.debug(f"pdfplumber failed: {e}")
        return ""


def _extract_pymupdf(filepath: str) -> str:
    try:
        import fitz
        parts = []
        with fitz.open(filepath) as doc:
            for page in doc:
                parts.append(page.get_text())
        return "\n".join(parts)
    except Exception as e:
        logger.debug(f"PyMuPDF failed: {e}")
        return ""


def _extract_tesseract(filepath: str) -> str:
    if not TESSERACT_AVAILABLE:
        return ""
    try:
        import pytesseract
        import fitz
        from PIL import Image
        import io
        parts = []
        with fitz.open(filepath) as doc:
            for page in doc:
                pix = page.get_pixmap(dpi=250)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                try:
                    text = pytesseract.image_to_string(img, lang="eng+hin")
                except Exception:
                    text = pytesseract.image_to_string(img, lang="eng")
                parts.append(text)
        return "\n".join(parts)
    except Exception as e:
        logger.warning(f"Tesseract OCR failed: {e}")
        return ""


def _text_quality(text: str, page_count: int) -> float:
    if not text or page_count == 0:
        return 0.0
    chars_per_page = len(text.strip()) / page_count
    real_words = len(re.findall(r"\b[A-Za-z\u0900-\u097F]{3,}\b", text))
    return min(1.0, (chars_per_page / 200) * 0.5 + (real_words / 50) * 0.5)


# ─── Main Parser ──────────────────────────────────────────────────────────────

class PDFParser:
    """
    3-layer competitive PDF parser for Indian hospital documents.
    Runs pdfplumber + PyMuPDF, picks best, falls back to Tesseract for scanned PDFs.
    """

    def parse(self, filepath: str) -> dict:
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
            "extraction_layer": "none",
            "extraction_confidence": 0.0,
            "errors": [],
        }

        try:
            import fitz
            with fitz.open(filepath) as doc:
                page_count = max(1, len(doc))

            candidates = {}
            t1 = _extract_pdfplumber(filepath)
            candidates["pdfplumber"] = (t1, _text_quality(t1, page_count))

            t2 = _extract_pymupdf(filepath)
            candidates["pymupdf"] = (t2, _text_quality(t2, page_count))

            best_so_far = max(candidates.values(), key=lambda x: x[1])
            if best_so_far[1] < 0.3:
                result["is_scanned"] = True
                t3 = _extract_tesseract(filepath)
                if t3:
                    candidates["tesseract"] = (t3, _text_quality(t3, page_count))

            best_name = max(candidates, key=lambda k: candidates[k][1])
            text, quality = candidates[best_name]
            result["extraction_layer"] = best_name
            result["raw_text_length"] = len(text)

            logger.info(f"{path.name}: layer={best_name} quality={quality:.2f} chars={len(text)}")

            if not text.strip():
                result["errors"].append(
                    "No text extracted. PDF may be image-only. Install Tesseract for OCR support."
                )
                return result

            # ── Patient Demographics ──────────────────────────────────────────
            patient = {}

            # Try compact "Age/Gender:48Yr/F" first (common in Indian HIS)
            ag_m = AGE_GENDER_PATTERN.search(text)
            if ag_m:
                patient["age"] = int(ag_m.group(1))
                patient["gender"] = "male" if ag_m.group(2).lower().startswith("m") else "female"
            else:
                age_m = AGE_PATTERN.search(text)
                if age_m:
                    patient["age"] = int(age_m.group(1))
                gender_m = GENDER_PATTERN.search(text)
                if gender_m:
                    raw_g = gender_m.group(1).strip().lower()
                    patient["gender"] = "male" if raw_g in ("male", "m") else \
                                        "female" if raw_g in ("female", "f") else "other"

            name_m = NAME_PATTERN.search(text)
            if name_m:
                # Pattern has 2 alternating groups; pick whichever matched
                raw_name = next((g for g in name_m.groups() if g is not None), "").strip()
                if raw_name and len(raw_name) > 2 and raw_name.lower() not in ("anonymous",):
                    patient["name"] = raw_name

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
                result["facility_name"] = fac_m.group(0).strip()[:80]

            # ── Encounters ───────────────────────────────────────────────────
            encounter = {}
            adm_m = ADMISSION_DATE_PATTERN.search(text)
            if adm_m:
                encounter["admission_date"] = _parse_date(adm_m.group(1))
            dis_m = DISCHARGE_DATE_PATTERN.search(text)
            if dis_m:
                encounter["discharge_date"] = _parse_date(dis_m.group(1))
            if encounter:
                encounter["type"] = "IMP"
                result["encounters"].append(encounter)

            # ── Diagnoses ────────────────────────────────────────────────────
            for diag_m in DIAGNOSIS_PATTERN.finditer(text):
                diag_text = diag_m.group(1).strip()
                if diag_text and len(diag_text) > 3:
                    result["diagnoses"].append({
                        "text": diag_text, "code": None, "system": None, "confidence": 0.6,
                    })

            # Fallback: parse Chief Complaints block as diagnoses
            if not result["diagnoses"]:
                cc_m = CHIEF_COMPLAINT_PATTERN.search(text)
                if cc_m:
                    for c in cc_m.group(1).splitlines():
                        c = c.strip()
                        if c and len(c) > 2:
                            result["diagnoses"].append({
                                "text": c, "code": None, "system": "chief_complaint", "confidence": 0.4,
                            })

            # ── Medications ──────────────────────────────────────────────────
            for med_m in MED_PATTERN.finditer(text):
                med_text = med_m.group(1).strip()
                if med_text and len(med_text) > 2:
                    result["medications"].append({
                        "text": med_text, "code": None, "system": None, "confidence": 0.5,
                    })

            # ── Confidence score (out of 5 key fields) ────────────────────
            fields_found = sum([
                bool(patient.get("name")),
                bool(patient.get("gender")),
                bool(patient.get("age")),
                bool(result["diagnoses"]),
                bool(result["facility_name"]),
            ])
            result["extraction_confidence"] = round(fields_found / 5, 2)

        except Exception as e:
            logger.error(f"PDFParser failed for {filepath}: {e}", exc_info=True)
            result["errors"].append(str(e))

        return result

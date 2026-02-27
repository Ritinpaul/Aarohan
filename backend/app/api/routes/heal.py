"""
Heal Route — Aarohan++ Phase 4
POST /api/v1/heal/

Accepts a file upload (PDF / CSV / HL7 / XML) and applies the full
Phase 4 resilience healing pipeline:
  - Date normalisation → ISO 8601
  - Name cleaning + gender inference
  - ABHA placeholder generation
  - Diagnosis → ICD-10/SNOMED code mapping
  - Drug healing (brand→generic, multi-drug split, dosage extraction)
  - Confidence scoring for every healed field

Returns:
  - healed JSON, HealReport, score_before/after, score_delta
"""

import logging
import uuid
import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from app.parsers.pdf_parser import PDFParser
from app.parsers.csv_parser import CSVParser
from app.parsers.hl7_parser import HL7Parser
from app.parsers.xml_parser import XMLParser
from app.resilience.heal_orchestrator import heal

logger = logging.getLogger(__name__)
router = APIRouter()

_PARSERS = {
    "pdf":   PDFParser(),
    "csv":   CSVParser(),
    "hl7v2": HL7Parser(),
    "xml":   XMLParser(),
}


def _detect_format(filename: str, content_type: str = "") -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":    return "pdf"
    if ext == ".csv":    return "csv"
    if ext == ".hl7":    return "hl7v2"
    if ext == ".xml":    return "xml"
    if "xml" in content_type:  return "xml"
    return "unknown"


@router.post(
    "/",
    summary="Heal a legacy healthcare file using the Phase 4 Resilience Engine",
    response_description=(
        "Healed JSON with ICD-10 codes, normalised dates, "
        "ABHA placeholder, gender inference, and confidence scores"
    ),
)
async def heal_file(
    file: UploadFile = File(..., description="Raw healthcare data file (PDF, CSV, HL7v2, XML)"),
    format: Optional[str] = Form(None, description="Force format: pdf|csv|hl7v2|xml"),
    run_readiness: bool = Form(True, description="Compute before/after readiness score (adds ~50ms)"),
):
    """
    Full healing pipeline:
    Upload → Parse → Heal (Phase 4) → Confidence Score → Return HealResult
    """
    run_id = str(uuid.uuid4())
    logger.info(f"[{run_id}] Heal request — file: {file.filename}")

    suffix = Path(file.filename or "upload").suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        shutil.copyfileobj(file.file, tmp)
        tmp.close()

        detected_format = format or _detect_format(file.filename or "", file.content_type or "")
        if detected_format == "unknown":
            raise HTTPException(400, f"Cannot detect format for '{file.filename}'")

        parser = _PARSERS.get(detected_format)
        if not parser:
            raise HTTPException(400, f"No parser for format: {detected_format}")

        try:
            parsed = parser.parse(tmp.name)
        except Exception as e:
            raise HTTPException(422, f"Parse error: {e}")

        result = heal(parsed, run_readiness=run_readiness)

        response = {
            "run_id": run_id,
            "filename": file.filename,
            "format_detected": detected_format,
            "heal_applied": result.heal_applied,
            "score_before": result.score_before,
            "score_after": result.score_after,
            "score_delta": result.score_delta,
            "report": result.report.model_dump(),
            "healed": result.healed,
        }
        return JSONResponse(status_code=200, content=response)

    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


@router.post(
    "/parsed",
    summary="Heal a pre-parsed dict using the Phase 4 Resilience Engine",
)
async def heal_parsed(
    payload: dict,
    run_readiness: bool = True,
):
    """Heal a pre-parsed dict directly (for internal pipeline use)."""
    result = heal(payload, run_readiness=run_readiness)
    return {
        "heal_applied": result.heal_applied,
        "score_before": result.score_before,
        "score_after": result.score_after,
        "score_delta": result.score_delta,
        "report": result.report.model_dump(),
        "healed": result.healed,
    }

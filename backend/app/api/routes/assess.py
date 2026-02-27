"""
Assess Route — Aarohan++ Phase 2
POST /api/v1/assess/
Accepts file upload OR pre-parsed JSON → runs NHCX Readiness Score → returns scoring report.
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
from app.quality.readiness_engine import compute_readiness_score

logger = logging.getLogger(__name__)
router = APIRouter()

_PARSERS = {
    "pdf": PDFParser(),
    "csv": CSVParser(),
    "hl7v2": HL7Parser(),
    "xml": XMLParser(),
}


def _detect_format(filename: str, content_type: str = "") -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":    return "pdf"
    if ext in (".csv",): return "csv"
    if ext in (".hl7",): return "hl7v2"
    if ext in (".xml",): return "xml"
    if "xml" in content_type: return "xml"
    return "unknown"


@router.post(
    "/",
    summary="Compute NHCX Readiness Score for a healthcare file",
    response_description="Readiness score, dimension breakdown, gaps, and rejection risk",
)
async def assess_file(
    file: UploadFile = File(..., description="Legacy data file (PDF, CSV, HL7v2, XML)"),
    format: Optional[str] = Form(None),
    target_profile: str = Form("ClaimBundle", description="NRCeS profile target: ClaimBundle | CoverageEligibilityRequestBundle"),
    hospital_name: Optional[str] = Form(None),
):
    """
    Full assessment pipeline:
    Upload → Parse → Score (4 dimensions) → Gap Analysis → Readiness Score → Return
    """
    run_id = str(uuid.uuid4())
    logger.info(f"[{run_id}] Assess request — file: {file.filename}")

    suffix = Path(file.filename).suffix if file.filename else ""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        shutil.copyfileobj(file.file, tmp)
        tmp.close()
        tmp_path = tmp.name

        detected_format = format or _detect_format(file.filename or "", file.content_type or "")
        if detected_format == "unknown":
            raise HTTPException(400, f"Cannot detect format for '{file.filename}'")

        parser = _PARSERS.get(detected_format)
        if not parser:
            raise HTTPException(400, f"No parser for format: {detected_format}")

        try:
            parsed = parser.parse(tmp_path)
        except Exception as e:
            raise HTTPException(422, f"Parse error: {e}")

        score_result = compute_readiness_score(parsed, target_profile=target_profile)

        return JSONResponse(
            status_code=200,
            content={
                "run_id": run_id,
                "filename": file.filename,
                "format_detected": detected_format,
                "target_profile": target_profile,
                "readiness_score": score_result.model_dump(),
                "next_step": "POST /api/v1/convert/ to transform and heal the data",
            }
        )
    finally:
        os.unlink(tmp_path)


@router.post(
    "/parsed",
    summary="Assess pre-parsed JSON data",
    response_description="Readiness score for a pre-parsed dict",
)
async def assess_parsed(payload: dict, target_profile: str = "ClaimBundle"):
    """Assess an already-parsed dict (for internal pipeline use)."""
    score_result = compute_readiness_score(payload, target_profile)
    return score_result.model_dump()

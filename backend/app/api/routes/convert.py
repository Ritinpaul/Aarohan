"""
Convert Route — Aarohan++ Phase 1
POST /api/v1/convert/
Accepts a file upload, detects format, parses, runs context engine, returns structured result.
"""

import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from app.parsers.pdf_parser import PDFParser
from app.parsers.csv_parser import CSVParser
from app.parsers.hl7_parser import HL7Parser
from app.parsers.xml_parser import XMLParser
from app.context.engine import ContextEngine

logger = logging.getLogger(__name__)
router = APIRouter()

_context_engine = ContextEngine()


def _detect_format(filename: str, content_type: str) -> str:
    """Detect file format from extension and MIME type."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext in (".csv", ".tsv"):
        return "csv"
    if ext in (".hl7", ".txt") or "hl7" in content_type.lower():
        return "hl7v2"
    if ext in (".xml",) or "xml" in content_type.lower():
        return "xml"
    if ext in (".json",) or "json" in content_type.lower():
        return "json"
    return "unknown"


def _get_parser(fmt: str):
    parsers = {
        "pdf": PDFParser(),
        "csv": CSVParser(),
        "hl7v2": HL7Parser(),
        "xml": XMLParser(),
    }
    return parsers.get(fmt)


@router.post(
    "/",
    summary="Convert legacy healthcare data to NHCX-aligned FHIR",
    response_description="Parsed data, context detection, and readiness pre-check",
)
async def convert_file(
    file: UploadFile = File(..., description="Legacy data file (PDF, CSV, HL7v2, XML)"),
    format: Optional[str] = Form(None, description="Override format detection: pdf|csv|hl7v2|xml"),
    target_network: str = Form("nhcx", description="Target network: nhcx|openhcx"),
    target_profile: str = Form("ClaimBundle", description="NRCeS profile: ClaimBundle|CoverageEligibilityRequestBundle"),
    hospital_name: Optional[str] = Form(None, description="Override hospital name for context detection"),
    auto_heal: bool = Form(True, description="Enable Resilience Healer for missing field inference"),
):
    """
    Phase 1 pipeline: Upload → Detect Format → Parse → Context Detection → Return.
    FHIR transformation (Phase 3) and healing (Phase 4) will be added in subsequent phases.
    """
    pipeline_id = str(uuid.uuid4())
    logger.info(f"[{pipeline_id}] Convert request — file: {file.filename}, target: {target_network}/{target_profile}")

    # ── 1. Save upload to temp ────────────────────────────────────────────────
    import tempfile, shutil, os
    suffix = Path(file.filename).suffix if file.filename else ""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        shutil.copyfileobj(file.file, tmp)
        tmp.close()
        tmp_path = tmp.name

        # ── 2. Detect format ─────────────────────────────────────────────────
        detected_format = format or _detect_format(file.filename or "", file.content_type or "")
        if detected_format == "unknown":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot detect file format for '{file.filename}'. Specify 'format' parameter.",
            )

        # ── 3. Parse ─────────────────────────────────────────────────────────
        parser = _get_parser(detected_format)
        if not parser:
            raise HTTPException(status_code=400, detail=f"No parser available for format: {detected_format}")

        try:
            parsed = parser.parse(tmp_path)
        except Exception as e:
            logger.error(f"[{pipeline_id}] Parse error: {e}")
            raise HTTPException(status_code=422, detail=f"Parse failed: {str(e)}")

        # ── 4. Context Detection ──────────────────────────────────────────────
        # Extract useful fields from parsed output for context engine
        facility = (
            hospital_name
            or parsed.get("facility_name")
            or parsed.get("facility", {}).get("name", "")
            or ""
        )

        records = parsed.get("records", [])
        first_record = records[0] if records else {}
        address = (
            first_record.get("patient", {}).get("address", "")
            or parsed.get("patient", {}).get("address", "")
            or ""
        )
        raw_text = parsed.get("raw_text_length", "")

        context = _context_engine.detect(
            hospital_name=facility,
            address_text=address,
            raw_text=address,
            state_hint="",
        )

        # ── 5. Return structured response ─────────────────────────────────────
        return JSONResponse(
            status_code=200,
            content={
                "pipeline_id": pipeline_id,
                "status": "parsed",
                "format_detected": detected_format,
                "target_network": target_network,
                "target_profile": target_profile,
                "context": context.model_dump(),
                "parsed_summary": {
                    "source_file": parsed.get("source_file", file.filename),
                    "diagnoses_count": len(parsed.get("diagnoses", [])),
                    "medications_count": len(parsed.get("medications", [])),
                    "records_count": len(parsed.get("records", [])),
                    "is_scanned": parsed.get("is_scanned", False),
                    "extraction_confidence": parsed.get("extraction_confidence"),
                    "errors": parsed.get("errors", []),
                },
                "next_step": "POST /api/v1/assess/ to get NHCX Readiness Score",
                "phases_remaining": ["assess", "transform", "heal", "validate", "deliver"],
            },
        )

    finally:
        os.unlink(tmp_path)

"""
Transform Route — Aarohan++ Phase 3
POST /api/v1/transform/
Accepts file upload → parses → runs context engine → builds NHCX/OpenHCX FHIR Bundle.
Returns the full FHIR Bundle JSON plus pipeline metadata.
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
from app.context.engine import ContextEngine
from app.fhir.bundle_packager import BundlePackager
from app.quality.readiness_engine import compute_readiness_score

logger = logging.getLogger(__name__)
router = APIRouter()

_PARSERS = {
    "pdf": PDFParser(),
    "csv": CSVParser(),
    "hl7v2": HL7Parser(),
    "xml": XMLParser(),
}
_CONTEXT_ENGINE = ContextEngine()


def _detect_format(filename: str, content_type: str = "") -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":    return "pdf"
    if ext in (".csv",): return "csv"
    if ext in (".hl7",): return "hl7v2"
    if ext in (".xml",): return "xml"
    return "unknown"


@router.post(
    "/",
    summary="Transform legacy data to a NRCeS/NHCX FHIR Bundle",
    response_description="FHIR Bundle (ClaimBundle or CoverageEligibilityRequestBundle) plus metadata",
)
async def transform_file(
    file: UploadFile = File(...),
    format: Optional[str] = Form(None),
    target_profile: str = Form("ClaimBundle"),
    target_network: str = Form("nhcx"),
    hospital_name: Optional[str] = Form(None),
    insurer_name: Optional[str] = Form(None),
    include_score: bool = Form(True, description="Include NHCX Readiness Score in response"),
):
    """
    Full Phase 3 pipeline:
    Upload → Detect Format → Parse → Context Detection → Drug Code Enrichment
    → FHIR Resource Building → Bundle Packaging → Return
    """
    run_id = str(uuid.uuid4())
    logger.info(f"[{run_id}] Transform: file={file.filename} profile={target_profile} net={target_network}")

    suffix = Path(file.filename).suffix if file.filename else ""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)

    try:
        shutil.copyfileobj(file.file, tmp)
        tmp.close()
        tmp_path = tmp.name

        # 1) Format detection
        detected_format = format or _detect_format(file.filename or "", file.content_type or "")
        if detected_format == "unknown":
            raise HTTPException(400, f"Cannot detect format for '{file.filename}'")

        # 2) Parse
        parser = _PARSERS.get(detected_format)
        if not parser:
            raise HTTPException(400, f"No parser for format: {detected_format}")

        try:
            parsed = parser.parse(tmp_path)
        except Exception as e:
            raise HTTPException(422, f"Parse error: {e}")

        # 3) Context Detection
        facility = (
            hospital_name
            or parsed.get("facility_name")
            or parsed.get("facility", {}).get("name", "")
        )
        records = parsed.get("records", [])
        address = (
            records[0].get("patient", {}).get("address", "") if records
            else parsed.get("patient", {}).get("address", "")
        )
        context = _CONTEXT_ENGINE.detect(
            hospital_name=facility,
            address_text=address,
            raw_text=address,
        )
        context_dict = context.model_dump()

        # Use context to pick network if not explicitly set
        effective_network = target_network or context.network

        # 4) Bundle Packaging
        packager = BundlePackager(network=effective_network)
        if target_profile == "CoverageEligibilityRequestBundle":
            bundle = packager.pack_coverage_eligibility_bundle(parsed, context_dict)
        else:
            bundle = packager.pack_claim_bundle(
                parsed, context_dict, hospital_name=facility, insurer_name=insurer_name
            )

        # 5) Optionally compute readiness score
        score_summary = None
        if include_score:
            score_result = compute_readiness_score(parsed, target_profile)
            score_summary = {
                "overall_score": score_result.overall_score,
                "grade": score_result.grade,
                "rejection_risk": score_result.rejection_risk,
                "blocking_count": score_result.blocking_count,
                "critical_count": score_result.critical_count,
                "auto_fixable_count": score_result.auto_fixable_count,
                "top_gaps": [g.model_dump() for g in score_result.gaps[:5]],
            }

        # 6) Build response
        entry_count = len(bundle.get("entry", []))
        return JSONResponse(
            status_code=200,
            content={
                "run_id": run_id,
                "filename": file.filename,
                "format_detected": detected_format,
                "target_profile": target_profile,
                "network": effective_network,
                "bundle": bundle,
                "bundle_summary": {
                    "bundle_id": bundle.get("id"),
                    "bundle_type": bundle.get("type"),
                    "entry_count": entry_count,
                    "resource_types": list({
                        e["resource"]["resourceType"] for e in bundle.get("entry", [])
                    }),
                },
                "context": context_dict,
                "readiness": score_summary,
                "next_step": "POST /api/v1/validate/ to validate with HAPI FHIR R4",
            }
        )
    finally:
        os.unlink(tmp_path)

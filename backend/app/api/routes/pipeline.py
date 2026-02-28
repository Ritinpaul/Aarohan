"""
Pipeline Route — Aarohan++ Phase 5
POST /api/v1/pipeline/

Full end-to-end pipeline: Upload → Parse → Context → Assess → Heal → Transform → Validate → Sign.
Returns all stage results, bundle, validation report, JWS token, and readiness score delta.
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

from app.network.pipeline_orchestrator import PipelineOrchestrator
from app.network.audit_trail import log_run

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/",
    summary="Full Aarohan++ Pipeline — Parse → Heal → FHIR → Validate → Sign",
    response_description="Complete pipeline result with bundle, validation report, and audit trail entry",
)
async def run_pipeline(
    file: UploadFile = File(..., description="Source file: PDF, CSV, HL7v2, or XML"),
    format: Optional[str] = Form(None),
    profile: str = Form("ClaimBundle"),
    network: str = Form("nhcx", description="Target network: nhcx | openhcx"),
    hospital_name: Optional[str] = Form(None),
    insurer_name: Optional[str] = Form(None),
    sign: bool = Form(True, description="Sign the final bundle with JWS RS256"),
):
    """
    The single unified endpoint for the complete Aarohan++ pipeline.
    All 7 stages are executed in sequence, isolated from each other.
    Any stage failure is captured without crashing the entire pipeline.
    """
    run_id = str(uuid.uuid4())
    logger.info(f"[{run_id}] Pipeline request — {file.filename}")

    suffix = Path(file.filename or "upload").suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        shutil.copyfileobj(file.file, tmp)
        tmp.close()

        orchestrator = PipelineOrchestrator(network=network)
        run = orchestrator.run(
            file_path=tmp.name,
            format=format,
            profile=profile,
            hospital_name=hospital_name,
            insurer_name=insurer_name,
            sign=sign,
        )
        run.source_file = file.filename or run.source_file

        # Persist to audit trail
        audit_id = log_run(run)

        # Build response
        stages_summary = [
            {
                "stage": s.stage,
                "success": s.success,
                "duration_ms": s.duration_ms,
                "error": s.error,
            }
            for s in run.stages
        ]

        response_body = {
            "run_id": run.run_id,
            "audit_id": audit_id,
            "filename": file.filename,
            "format_detected": run.format_detected,
            "network": run.network,
            "profile": run.profile,
            "success": run.success,
            "total_ms": run.total_ms,
            "readiness_before": run.readiness_before,
            "readiness_after": run.readiness_after,
            "readiness_delta": run.readiness_delta,
            "stages": stages_summary,
            "bundle_summary": {
                "bundle_id": (run.bundle or {}).get("id"),
                "bundle_type": (run.bundle or {}).get("type"),
                "entry_count": len((run.bundle or {}).get("entry", [])),
                "resource_types": list({
                    e["resource"]["resourceType"]
                    for e in (run.bundle or {}).get("entry", [])
                    if e.get("resource")
                }),
            } if run.bundle else None,
            "validation": run.validation_report,
            "jws_digest": run.jws_digest,
            "jws_token": run.jws_token if hasattr(run, 'jws_token') else None,
            "bundle": run.bundle,
            "error": run.error,
        }

        status_code = 200 if run.success else 207  # 207 Multi-Status if some stages failed
        return JSONResponse(status_code=status_code, content=response_body)

    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


@router.get(
    "/audit",
    summary="Return recent pipeline audit trail entries",
)
async def audit_log(n: int = 20):
    """Return the N most recent pipeline run audit entries."""
    from app.network.audit_trail import get_recent_runs, audit_stats
    return {
        "stats": audit_stats(),
        "recent_runs": get_recent_runs(n),
    }

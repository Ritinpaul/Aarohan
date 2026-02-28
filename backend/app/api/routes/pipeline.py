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

# Resolve backend root directory (backend/) relative to this file
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent


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


@router.get(
    "/eval_reports",
    summary="Return a list of available evaluation reports",
)
async def list_eval_reports():
    """Returns all available evaluation reports from data/eval_reports directory."""
    import json
    import re
    
    # Path to evaluation reports
    reports_dir = _BACKEND_DIR / "data" / "eval_reports"
    if not reports_dir.exists():
        return []

    reports = []
    for filepath in reports_dir.glob("*.json"):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            
            # Extract timestamp from filename (eval_YYYYMMDD_HHMMSS.json)
            ts_match = re.search(r'eval_(\d{8})_(\d{6})', filepath.stem)
            timestamp = ""
            if ts_match:
                d, t = ts_match.group(1), ts_match.group(2)
                timestamp = f"{d[:4]}-{d[4:6]}-{d[6:8]}T{t[:2]}:{t[2:4]}:{t[4:6]}"

            # Extract metrics from the actual structure
            m3 = data.get("M3", {})
            m4 = data.get("M4", {})
            m5 = data.get("M5", {})
            
            pass_rate = m3.get("pass_rate", 0) * 100  # Convert to percentage
            total_bundles = m3.get("passed", 0) + m3.get("warned", 0) + m3.get("failed", 0)
            fidelity = m4.get("fidelity", 0) * 100
            avg_lift = m5.get("avg_lift", 0)

            reports.append({
                "filename": filepath.name,
                "timestamp": timestamp,
                "total_documents": total_bundles,
                "success_rate": pass_rate,
                "fidelity": fidelity,
                "avg_lift": avg_lift,
                "avg_score_before": m4.get("csv_real_score", 0),
                "avg_score_after": m4.get("csv_real_score", 0) + avg_lift,
            })
        except Exception as e:
            logger.error(f"Failed to read report {filepath}: {e}")

    # Sort reports newest first
    reports.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return reports


@router.get(
    "/eval_reports/{filename}",
    summary="Return a specific evaluation report",
)
async def get_eval_report(filename: str):
    """Returns the full JSON content of a specific evaluation report."""
    import json
    
    filepath = _BACKEND_DIR / "data" / "eval_reports" / filename
    if not filepath.exists() or filepath.suffix != ".json":
        raise HTTPException(status_code=404, detail="Report not found")
        
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/eval_reports/{filename}/summary",
    summary="Return a printable HTML summary for an evaluation report",
    response_class=None,
)
async def get_eval_report_summary(filename: str):
    """Generates a human-readable HTML summary report for a given eval report JSON."""
    import json
    import re
    from fastapi.responses import HTMLResponse

    filepath = _BACKEND_DIR / "data" / "eval_reports" / filename
    if not filepath.exists() or filepath.suffix != ".json":
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Extract timestamp from filename
    ts_match = re.search(r'eval_(\d{8})_(\d{6})', filepath.stem)
    timestamp = ""
    if ts_match:
        d, t = ts_match.group(1), ts_match.group(2)
        timestamp = f"{d[:4]}-{d[4:6]}-{d[6:8]} {t[:2]}:{t[2:4]}:{t[4:6]}"

    m1_csv = data.get("M1_csv", {})
    m1_xml = data.get("M1_xml", {})
    m1_hl7 = data.get("M1_hl7", {})
    m2 = data.get("M2", {})
    m3 = data.get("M3", {})
    m4 = data.get("M4", {})
    m5 = data.get("M5", {})

    pass_rate = m3.get("pass_rate", 0) * 100
    fidelity = m4.get("fidelity", 0) * 100
    avg_lift = m5.get("avg_lift", 0)
    total = m3.get("passed", 0) + m3.get("warned", 0) + m3.get("failed", 0)

    def badge(val, good=True):
        color = "#059669" if good else "#dc2626"
        return f'<span style="background:{color}22;color:{color};padding:2px 10px;border-radius:999px;font-size:0.8rem;font-weight:600">{val}</span>'

    def metric_row(label, value, is_good=True):
        return f"<tr><td style='padding:8px 12px;color:#374151'>{label}</td><td style='padding:8px 12px'>{badge(value, is_good)}</td></tr>"

    m3_details_rows = ""
    for d in m3.get("details", []):
        status = d.get("status", "")
        color = "#059669" if status == "PASS" else "#d97706" if status == "WARN" else "#dc2626"
        warns = ", ".join(d.get("warnings", [])) or "None"
        errors = ", ".join(d.get("errors", [])) or "None"
        m3_details_rows += f"""
        <tr style='border-bottom:1px solid #f3f4f6'>
            <td style='padding:10px 12px;font-weight:500'>{d.get("label","")}</td>
            <td style='padding:10px 12px'><span style='background:{color}22;color:{color};padding:2px 10px;border-radius:999px;font-size:0.8rem;font-weight:600'>{status}</span></td>
            <td style='padding:10px 12px;font-size:0.82rem;color:#6b7280'>{warns}</td>
            <td style='padding:10px 12px;font-size:0.82rem;color:#dc2626'>{errors}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Aarohan++ Evaluation Report — {timestamp}</title>
  <style>
    body {{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;margin:0;padding:2rem;background:#f8fafc;color:#0f172a;line-height:1.5}}
    .page {{max-width:850px;margin:0 auto;background:#fff;border-radius:16px;box-shadow:0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);padding:3rem}}
    .header {{border-bottom:2px solid #e2e8f0;padding-bottom:1.5rem;margin-bottom:2.5rem}}
    h1 {{margin:0 0 0.5rem;font-size:1.875rem;color:#0f172a;letter-spacing:-0.025em}}
    .subtitle {{color:#64748b;font-size:1rem;margin:0}}
    
    h2 {{font-size:1.25rem;color:#0f172a;margin:2.5rem 0 1rem;padding-bottom:0.5rem;border-bottom:1px solid #f1f5f9;display:flex;align-items:center;gap:0.5rem}}
    .section-desc {{font-size:0.9rem;color:#64748b;margin-bottom:1.25rem;line-height:1.6}}
    
    .kpi-grid {{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:3rem}}
    .kpi {{background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:1.25rem;text-align:center}}
    .kpi .val {{font-size:1.875rem;font-weight:700;color:#059669;letter-spacing:-0.025em}} 
    .kpi .lbl {{font-size:0.75rem;color:#475569;text-transform:uppercase;letter-spacing:0.05em;margin-top:0.5rem;font-weight:600}}
    
    table {{width:100%;border-collapse:separate;border-spacing:0;font-size:0.9rem;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden}}
    thead th {{background:#f8fafc;padding:12px 16px;text-align:left;font-size:0.75rem;color:#475569;text-transform:uppercase;letter-spacing:0.05em;border-bottom:1px solid #e2e8f0}}
    tbody tr td {{padding:12px 16px;border-bottom:1px solid #f1f5f9;color:#334155}}
    tbody tr:last-child td {{border-bottom:none}}
    tbody tr:hover {{background:#f8fafc}}
    
    .footer {{margin-top:4rem;font-size:0.8rem;color:#94a3b8;text-align:center;padding-top:1.5rem;border-top:1px solid #e2e8f0}}
    @media print {{body{{background:white;padding:0}} .page{{box-shadow:none;padding:0;max-width:100%}}}}
  </style>
</head>
<body>
<div class="page">
  <div class="header">
    <h1>Aarohan++ Quality Assessment Report</h1>
    <p class="subtitle">Generated on {timestamp} for file: <strong>{filename}</strong></p>
  </div>

  <div class="kpi-grid">
    <div class="kpi"><div class="val">{total}</div><div class="lbl">Total Records Processed</div></div>
    <div class="kpi"><div class="val">{pass_rate:.0f}%</div><div class="lbl">Regulatory Pass Rate</div></div>
    <div class="kpi"><div class="val">{fidelity:.0f}%</div><div class="lbl">Data Accuracy</div></div>
    <div class="kpi"><div class="val">+{avg_lift:.1f}</div><div class="lbl">Average Quality Lift</div></div>
  </div>

  <h2>1. Patient Data Extraction</h2>
  <p class="section-desc">We analyzed how accurately our AI models extracted crucial patient information (like names, diagnoses, and medications) from your raw healthcare files.</p>
  <table>
    <thead><tr><th>Document Origin</th><th>Extracted Field</th><th>Accuracy Confidence</th></tr></thead>
    <tbody>
      {"".join(f"<tr><td style='font-weight:500;color:#0f172a'>CSV Data</td><td>{k.replace('_recall',' Identification Rate').replace('_precision',' Precision').replace('_f1',' Overall Reliability').title()}</td><td>{badge(f'{v*100:.0f}%' if isinstance(v, float) else str(v), v >= 0.9 if isinstance(v, float) else v)}</td></tr>" for k, v in m1_csv.items())}
      {"".join(f"<tr><td style='font-weight:500;color:#0f172a'>XML Data</td><td>{k.replace('_recall',' Identification Rate').replace('_precision',' Precision').replace('_f1',' Overall Reliability').title()}</td><td>{badge(f'{v*100:.0f}%' if isinstance(v, float) else str(v), v >= 0.9 if isinstance(v, float) else v)}</td></tr>" for k, v in m1_xml.items())}
    </tbody>
  </table>

  <h2>2. Medical Terminology Understanding</h2>
  <p class="section-desc">This checks if non-standard doctor notes and local drug names were correctly translated into universally recognized medical codes (SNOMED, RxNorm).</p>
  <table>
    <thead><tr><th>Assessment Metric</th><th>Result</th></tr></thead>
    <tbody>
      <tr><td>First-Choice Diagnosis Accuracy</td><td>{badge(f"{m2.get('top1_accuracy',0)*100:.0f}%", m2.get('top1_accuracy',0)>=0.9)}</td></tr>
      <tr><td>Top-3 Diagnosis Accuracy</td><td>{badge(f"{m2.get('top3_accuracy',0)*100:.0f}%", m2.get('top3_accuracy',0)>=0.9)}</td></tr>
      <tr><td>Total Clinical Terms Processed</td><td style='font-weight:500'>{m2.get('total_probes',0)}</td></tr>
      <tr><td>Unmapped Terms (Gaps)</td><td>{badge(str(len(m2.get('gaps',[]))) + ' unmapped terms', len(m2.get('gaps',[]))==0)}</td></tr>
    </tbody>
  </table>

  <h2>3. Regulatory Compliance Health</h2>
  <p class="section-desc">A breakdown of whether the final converted data meets the strict FHIR standards required by the national health network. Warnings indicate minor missing context but not critical failure.</p>
  <table>
    <thead><tr><th>Hospital / Record Group</th><th>Approval Status</th><th>Advisories (Warnings)</th><th>Critical Errors</th></tr></thead>
    <tbody>{m3_details_rows}</tbody>
  </table>

  <h2>4. Overall Quality Improvement</h2>
  <p class="section-desc">Comparing the quality of your raw data before processing versus the final, enhanced, FHIR-compliant data. Higher lifts mean Aarohan++ automatically fixed more underlying data issues.</p>
  <table>
    <thead><tr><th>Metric</th><th>Score</th></tr></thead>
    <tbody>
      <tr><td>Average Quality Point Increase</td><td>{badge(f"+{avg_lift:.2f} points", avg_lift>0)}</td></tr>
      <tr><td>Original Data Score (CSV format)</td><td style='font-weight:500'>{m4.get('csv_real_score','—')} / 100</td></tr>
      <tr><td>Original Data Score (XML format)</td><td style='font-weight:500'>{m4.get('xml_real_score','—')} / 100</td></tr>
    </tbody>
  </table>

  <div class="footer">
    Aarohan++ AI pipeline execution report. This is an auto-generated summary.
  </div>
</div>
</body>
</html>"""

    return HTMLResponse(content=html)

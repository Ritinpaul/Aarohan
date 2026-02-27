"""
Pipeline Orchestrator — Aarohan++ Phase 5
Full end-to-end pipeline: Parse → Context → Assess → Heal → Transform → Validate → Sign → Package.

This is the single entry-point for the complete Aarohan++ pipeline.
Every stage result is captured in a PipelineRun for audit trail.
"""

import uuid
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Literal
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class StageResult:
    stage: str
    success: bool
    duration_ms: float
    output: Optional[dict] = None
    error: Optional[str] = None


@dataclass
class PipelineRun:
    run_id: str
    source_file: str
    format_detected: str
    network: str
    profile: str
    stages: list[StageResult] = field(default_factory=list)
    parsed: Optional[dict] = None
    healed: Optional[dict] = None
    bundle: Optional[dict] = None
    validation_report: Optional[dict] = None
    jws_token: Optional[str] = None
    jws_digest: Optional[str] = None
    readiness_before: Optional[float] = None
    readiness_after: Optional[float] = None
    readiness_delta: Optional[float] = None
    total_ms: float = 0.0
    success: bool = False
    error: Optional[str] = None


class PipelineOrchestrator:
    """
    Full Aarohan++ end-to-end pipeline orchestrator.

    Stages:
      1. Parse          — format detection + parsing
      2. Context        — hospital tier, state scheme, language detection
      3. Assess         — pre-heal readiness score
      4. Heal           — Phase 4 resilience engine
      5. Transform      — FHIR bundle assembly (Phase 3)
      6. Validate       — NRCeS validation gate (Phase 5)
      7. Sign           — JWS RS256 signing (Phase 5)
    """

    def __init__(self, network: str = "nhcx"):
        from app.parsers.pdf_parser import PDFParser
        from app.parsers.csv_parser import CSVParser
        from app.parsers.hl7_parser import HL7Parser
        from app.parsers.xml_parser import XMLParser
        from app.context.engine import ContextEngine
        from app.fhir.bundle_packager import BundlePackager
        from app.network.fhir_validator import validate_bundle
        from app.network.jws_signer import sign_bundle
        from app.resilience.heal_orchestrator import heal
        from app.quality.readiness_engine import compute_readiness_score

        self.parsers = {
            "pdf": PDFParser(), "csv": CSVParser(),
            "hl7v2": HL7Parser(), "xml": XMLParser(),
        }
        self.context_engine = ContextEngine()
        self.packager = BundlePackager(network=network)
        self.validate_bundle = validate_bundle
        self.sign_bundle = sign_bundle
        self.heal = heal
        self.compute_readiness = compute_readiness_score
        self.network = network

    def _detect_format(self, filename: str) -> str:
        ext = Path(filename).suffix.lower()
        return {"pdf": "pdf", ".csv": "csv", ".hl7": "hl7v2", ".xml": "xml"}.get(ext, {
            ".pdf": "pdf", ".csv": "csv", ".hl7": "hl7v2", ".xml": "xml",
        }.get(ext, "unknown"))

    def _time_stage(self, name: str, fn, *args, **kwargs):
        t0 = time.time()
        try:
            result = fn(*args, **kwargs)
            return StageResult(
                stage=name,
                success=True,
                duration_ms=round((time.time() - t0) * 1000, 1),
                output={"ok": True},
            ), result
        except Exception as e:
            return StageResult(
                stage=name,
                success=False,
                duration_ms=round((time.time() - t0) * 1000, 1),
                error=str(e),
            ), None

    def run(
        self,
        file_path: str,
        format: Optional[str] = None,
        profile: str = "ClaimBundle",
        hospital_name: Optional[str] = None,
        insurer_name: Optional[str] = None,
        sign: bool = True,
    ) -> PipelineRun:
        """
        Execute the full pipeline for a given file.

        Returns PipelineRun with all stage results and final outputs.
        """
        t_total = time.time()
        run = PipelineRun(
            run_id=str(uuid.uuid4()),
            source_file=Path(file_path).name,
            format_detected=format or self._detect_format(Path(file_path).name),
            network=self.network,
            profile=profile,
        )

        # ── Stage 1: Parse ──────────────────────────────────────────────────
        parser = self.parsers.get(run.format_detected)
        if not parser:
            run.error = f"No parser for format: {run.format_detected}"
            return run

        stage, parsed = self._time_stage("parse", parser.parse, file_path)
        run.stages.append(stage)
        if not stage.success:
            run.error = f"Parse failed: {stage.error}"
            return run
        run.parsed = parsed

        # ── Stage 2: Context Detection ──────────────────────────────────────
        def _context():
            records = parsed.get("records", [])
            facility = hospital_name or parsed.get("facility_name", "") or ""
            address = records[0].get("patient", {}).get("address", "") if records else ""
            ctx = self.context_engine.detect(
                hospital_name=facility, address_text=address, raw_text=address
            )
            return ctx.model_dump()

        stage, context = self._time_stage("context", _context)
        run.stages.append(stage)
        context = context or {}

        # ── Stage 3: Assess (pre-heal) ──────────────────────────────────────
        def _assess():
            score = self.compute_readiness(parsed, profile)
            return {"score": score.overall_score, "grade": score.grade, "risk": score.rejection_risk}

        stage, pre_score = self._time_stage("assess", _assess)
        run.stages.append(stage)
        run.readiness_before = (pre_score or {}).get("score")

        # ── Stage 4: Heal ───────────────────────────────────────────────────
        stage, heal_result = self._time_stage("heal", self.heal, parsed, False)
        run.stages.append(stage)
        healed = heal_result.healed if heal_result else parsed
        run.healed = healed

        # Post-heal score
        try:
            post_score = self.compute_readiness(healed, profile)
            run.readiness_after = post_score.overall_score
            if run.readiness_before is not None:
                run.readiness_delta = round(run.readiness_after - run.readiness_before, 1)
        except Exception:
            pass

        # ── Stage 5: Transform → Bundle ────────────────────────────────────
        _network = self.network
        _packager = self.packager
        _profile = profile
        _hospital = hospital_name
        _insurer = insurer_name
        _healed = healed
        _context = context

        def _transform():
            from app.fhir.bundle_packager import BundlePackager as BP
            p = BP(network=_network)
            if _profile == "CoverageEligibilityRequestBundle":
                return p.pack_coverage_eligibility_bundle(_healed, _context)
            return p.pack_claim_bundle(_healed, _context, hospital_name=_hospital, insurer_name=_insurer)


        stage, bundle = self._time_stage("transform", _transform)
        run.stages.append(stage)
        if not stage.success or not bundle:
            run.error = f"Transform failed: {stage.error}"
            run.total_ms = round((time.time() - t_total) * 1000, 1)
            return run
        run.bundle = bundle

        # ── Stage 6: Validate ───────────────────────────────────────────────
        def _validate():
            report = self.validate_bundle(bundle, profile)
            return report.model_dump()

        stage, val_report = self._time_stage("validate", _validate)
        run.stages.append(stage)
        run.validation_report = val_report

        # ── Stage 7: Sign ────────────────────────────────────────────────────
        if sign:
            def _sign():
                result = self.sign_bundle(bundle)
                return {"token": result.token[:80] + "...", "digest": result.bundle_digest, "demo": result.demo_mode}

            stage, sig = self._time_stage("sign", _sign)
            run.stages.append(stage)
            if sig:
                run.jws_token = sig.get("token")
                run.jws_digest = sig.get("digest")

        run.success = all(s.success for s in run.stages)
        run.total_ms = round((time.time() - t_total) * 1000, 1)
        logger.info(
            f"[{run.run_id}] Pipeline complete — {run.total_ms}ms "
            f"score {run.readiness_before}→{run.readiness_after} "
            f"(+{run.readiness_delta})"
        )
        return run

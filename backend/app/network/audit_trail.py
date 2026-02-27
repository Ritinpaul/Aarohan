"""
Audit Trail — Aarohan++ Phase 5
PostgreSQL-backed or in-memory event sourcing for pipeline run tracking.

Stores every PipelineRun as a structured JSONB log entry.
Falls back gracefully to an in-memory deque if PostgreSQL is unavailable.

Schema (PostgreSQL):
  CREATE TABLE audit_trail (
    id          SERIAL PRIMARY KEY,
    run_id      UUID NOT NULL,
    timestamp   TIMESTAMPTZ DEFAULT NOW(),
    source_file TEXT,
    format      TEXT,
    network     TEXT,
    profile     TEXT,
    success     BOOLEAN,
    score_before FLOAT,
    score_after  FLOAT,
    score_delta  FLOAT,
    error       TEXT,
    stages      JSONB,
    metadata    JSONB
  );
"""

import json
import logging
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_MAX_IN_MEMORY = 500                # Cap in-memory audit log size
_audit_store: deque = deque(maxlen=_MAX_IN_MEMORY)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_run(run) -> str:
    """
    Persist a PipelineRun to the audit trail.
    Falls back to in-memory if DB unavailable.
    Returns the audit entry ID.
    """
    entry_id = str(uuid.uuid4())
    entry = {
        "id": entry_id,
        "run_id": run.run_id,
        "timestamp": _now(),
        "source_file": run.source_file,
        "format": run.format_detected,
        "network": run.network,
        "profile": run.profile,
        "success": run.success,
        "score_before": run.readiness_before,
        "score_after": run.readiness_after,
        "score_delta": run.readiness_delta,
        "total_ms": run.total_ms,
        "error": run.error,
        "stages": [
            {
                "stage": s.stage,
                "success": s.success,
                "duration_ms": s.duration_ms,
                "error": s.error,
            }
            for s in run.stages
        ],
        "jws_digest": run.jws_digest,
    }

    # Try PostgreSQL first
    if _try_db_insert(entry):
        logger.debug(f"AuditTrail: Persisted run {run.run_id} to PostgreSQL")
    else:
        _audit_store.append(entry)
        logger.debug(f"AuditTrail: Stored run {run.run_id} in memory ({len(_audit_store)} total)")

    return entry_id


def _try_db_insert(entry: dict) -> bool:
    """
    Attempt to insert into PostgreSQL. Returns True on success.
    Silently fails and returns False if DB is unavailable.
    """
    try:
        import asyncio
        from app.core.database import get_db

        # Try async insert in a sync context (best-effort)
        async def _insert():
            async for db in get_db():
                await db.execute(
                    """
                    INSERT INTO audit_trail
                        (run_id, source_file, format, network, profile, success,
                         score_before, score_after, score_delta, total_ms, error, stages, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    """,
                    entry["run_id"], entry["source_file"], entry["format"],
                    entry["network"], entry["profile"], entry["success"],
                    entry["score_before"], entry["score_after"], entry["score_delta"],
                    entry["total_ms"], entry["error"],
                    json.dumps(entry["stages"]),
                    json.dumps({"jws_digest": entry.get("jws_digest")}),
                )

        loop = asyncio.get_event_loop()
        if loop.is_running():
            return False  # Can't block inside async context — use fallback
        loop.run_until_complete(_insert())
        return True
    except Exception:
        return False


def get_recent_runs(n: int = 20) -> list[dict]:
    """Return the N most recent audit trail entries (in-memory store)."""
    entries = list(_audit_store)
    return entries[-n:]


def get_run(run_id: str) -> Optional[dict]:
    """Look up a specific run by ID from in-memory store."""
    for entry in _audit_store:
        if entry.get("run_id") == run_id or entry.get("id") == run_id:
            return entry
    return None


def audit_stats() -> dict:
    """Return summary statistics from in-memory audit trail."""
    entries = list(_audit_store)
    if not entries:
        return {"total": 0}

    successes = sum(1 for e in entries if e.get("success"))
    failures  = len(entries) - successes
    deltas = [e["score_delta"] for e in entries if e.get("score_delta") is not None]
    avg_lift = round(sum(deltas) / len(deltas), 1) if deltas else 0.0
    avg_ms = round(sum(e.get("total_ms", 0) for e in entries) / len(entries), 1)

    return {
        "total": len(entries),
        "success": successes,
        "failed": failures,
        "success_rate": round(successes / len(entries), 3),
        "avg_score_lift": avg_lift,
        "avg_processing_ms": avg_ms,
        "formats": {fmt: sum(1 for e in entries if e.get("format") == fmt)
                    for fmt in set(e.get("format", "") for e in entries)},
    }

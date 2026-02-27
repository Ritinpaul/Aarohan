"""
Validate Route — Aarohan++ Phase 5
POST /api/v1/validate/

Validates a pre-built FHIR bundle against NRCeS profile constraints.
Returns a ValidationReport with errors, warnings, and compliance status.
"""

import logging
from fastapi import APIRouter
from app.network.fhir_validator import validate_bundle, ValidationReport

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/",
    summary="Validate a FHIR bundle against NRCeS profile constraints",
    response_model=ValidationReport,
)
async def validate(
    payload: dict,
    profile: str = "ClaimBundle",
) -> ValidationReport:
    """
    Accepts a raw FHIR bundle dict and validates it against:
      - FHIR R4 structural rules
      - NRCeS required resource presence
      - NRCeS coding system constraints
      - Profile URL compliance
    """
    report = validate_bundle(payload, profile=profile)
    logger.info(
        f"Validate: profile={profile} valid={report.valid} "
        f"errors={report.error_count} warnings={report.warning_count}"
    )
    return report

"""
Payer Route — Aarohan++ Phase 5
POST /api/v1/payer/{flow}

Simulates NHCX payer gateway flows:
  - /payer/eligibility — CoverageEligibilityRequest check
  - /payer/preauth    — Pre-Authorization submission
  - /payer/claim      — Full claim adjudication
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.network.payer_simulator import check_eligibility, request_preauth, submit_claim, PayerResponse

logger = logging.getLogger(__name__)
router = APIRouter()


class PayerRequest(BaseModel):
    bundle: dict
    claim_amount: float = 50000.0
    subscriber_id: str = "SUB-0001"


@router.post(
    "/eligibility",
    summary="Simulate a NHCX CoverageEligibilityRequest",
    response_model=PayerResponse,
)
async def eligibility(req: PayerRequest) -> PayerResponse:
    """Check patient eligibility under their scheme."""
    result = check_eligibility(req.bundle, req.subscriber_id)
    logger.info(f"Payer/eligibility: scheme={result.scheme_name} status={result.status}")
    return result


@router.post(
    "/preauth",
    summary="Simulate a NHCX Pre-Authorization request",
    response_model=PayerResponse,
)
async def preauth(req: PayerRequest) -> PayerResponse:
    """Submit a pre-authorization for a planned claim."""
    result = request_preauth(req.bundle, req.claim_amount, req.subscriber_id)
    logger.info(f"Payer/preauth: scheme={result.scheme_name} status={result.status}")
    return result


@router.post(
    "/claim",
    summary="Simulate a NHCX full claim submission",
    response_model=PayerResponse,
)
async def claim(req: PayerRequest) -> PayerResponse:
    """Submit a full claim for adjudication."""
    result = submit_claim(req.bundle, req.claim_amount, req.subscriber_id)
    logger.info(f"Payer/claim: scheme={result.scheme_name} amount={result.benefit_amount} status={result.status}")
    return result

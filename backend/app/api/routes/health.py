"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "service": "aarohan-api",
        "layers": {
            "context_engine": "ready",
            "quality_assessment": "ready",
            "mapping_studio": "ready",
            "resilience_engine": "ready",
            "compliance_enforcement": "ready",
        },
    }


@router.get("/ready")
async def readiness_check():
    """Readiness probe for Docker/K8s."""
    # TODO: Check DB, Redis, FHIR server connectivity
    return {"ready": True}

"""
Aarohan++ — NHCX Compliance Intelligence Platform
FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.core.seed_loader import load_seed_data
from app.api.routes import health, assess, convert, map as map_routes
from app.api.routes import transform
from app.api.routes import heal
from app.api.routes import validate, payer, pipeline

settings = get_settings()

# ─── Logging ──────────────────────────────────────────────────────
logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("🚀 Starting Aarohan++ v%s", settings.APP_VERSION)
    await init_db()
    logger.info("✅ Database initialized")
    seed_stats = await load_seed_data()
    logger.info("✅ Seed data loaded — %s", seed_stats)
    yield
    await close_db()
    logger.info("👋 Aarohan++ shutdown complete")



# ─── Application ──────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "An open-source NHCX Compliance Intelligence Platform that transforms "
        "legacy healthcare data into NHCX-aligned FHIR bundles with India-specific "
        "contextual awareness, quality scoring, and zero-code configurability."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ───────────────────────────────────────────────────────
app.include_router(
    health.router,
    prefix=f"{settings.API_PREFIX}/health",
    tags=["Health"],
)
app.include_router(
    assess.router,
    prefix=f"{settings.API_PREFIX}/assess",
    tags=["Quality Assessment"],
)
app.include_router(
    convert.router,
    prefix=f"{settings.API_PREFIX}/convert",
    tags=["Conversion"],
)
app.include_router(
    map_routes.router,
    prefix=f"{settings.API_PREFIX}/map",
    tags=["Mapping"],
)
app.include_router(
    transform.router,
    prefix=f"{settings.API_PREFIX}/transform",
    tags=["FHIR Transform"],
)
app.include_router(
    heal.router,
    prefix=f"{settings.API_PREFIX}/heal",
    tags=["Phase 4 — Resilience Healer"],
)
app.include_router(
    validate.router,
    prefix=f"{settings.API_PREFIX}/validate",
    tags=["Phase 5 — FHIR Validation"],
)
app.include_router(
    payer.router,
    prefix=f"{settings.API_PREFIX}/payer",
    tags=["Phase 5 — Payer Gateway"],
)
app.include_router(
    pipeline.router,
    prefix=f"{settings.API_PREFIX}/pipeline",
    tags=["Phase 5 — End-to-End Pipeline"],
)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with platform info."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs",
        "endpoints": {
            "health": f"{settings.API_PREFIX}/health",
            "assess": f"{settings.API_PREFIX}/assess",
            "convert": f"{settings.API_PREFIX}/convert",
            "transform": f"{settings.API_PREFIX}/transform",
            "map": f"{settings.API_PREFIX}/map",
            "heal":     f"{settings.API_PREFIX}/heal",
            "validate": f"{settings.API_PREFIX}/validate",
            "payer":    f"{settings.API_PREFIX}/payer",
            "pipeline": f"{settings.API_PREFIX}/pipeline",
        },
    }

"""
Aarohan++ Configuration Module
Centralized settings using Pydantic BaseSettings with .env support.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # ─── Application ───────────────────────────────────────────────
    APP_NAME: str = "Aarohan++ NHCX Compliance Intelligence Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # ─── Database ──────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://aarohan:aarohan_dev@localhost:5432/aarohan_db",
        description="PostgreSQL connection string",
    )

    # ─── Redis ─────────────────────────────────────────────────────
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection for terminology caching",
    )
    REDIS_TERMINOLOGY_TTL: int = Field(
        default=86400,
        description="TTL for cached terminology lookups (seconds)",
    )

    # ─── HAPI FHIR Server ─────────────────────────────────────────
    FHIR_SERVER_URL: str = Field(
        default="http://localhost:8080/fhir",
        description="HAPI FHIR JPA Server base URL",
    )

    # ─── NRCeS Snowstorm API ──────────────────────────────────────
    SNOWSTORM_BASE_URL: str = Field(
        default="https://snowstorm.nrces.in/fhir",
        description="NRCeS Snowstorm terminology server",
    )
    SNOWSTORM_API_KEY: Optional[str] = Field(
        default=None,
        description="API key for Snowstorm (if required)",
    )

    # ─── NHCX / HCX Network ───────────────────────────────────────
    NHCX_BASE_URL: str = Field(
        default="https://staging-hcx.swasth.app/api/v0.8",
        description="NHCX network gateway URL",
    )
    NHCX_PARTICIPANT_CODE: Optional[str] = Field(
        default=None,
        description="Registered HCX participant code",
    )
    NHCX_AUTH_TOKEN: Optional[str] = Field(
        default=None,
        description="Bearer token for NHCX API authentication",
    )
    NHCX_ENCRYPTION_CERT_PATH: Optional[str] = Field(
        default=None,
        description="Path to X.509 certificate for JWE encryption",
    )
    NHCX_SIGNING_KEY_PATH: Optional[str] = Field(
        default=None,
        description="Path to private key for JWS signing",
    )

    # ─── OpenHCX Network ──────────────────────────────────────────
    OPENHCX_BASE_URL: str = Field(
        default="https://api.openhcx.io/v0.9",
        description="OpenHCX network gateway URL",
    )

    # ─── Dummy Payer API ──────────────────────────────────────────
    DUMMY_PAYER_URL: str = Field(
        default="http://localhost:8090/payer",
        description="Dummy Payer API for testing end-to-end flows",
    )
    USE_MOCK_PAYER: bool = Field(
        default=True,
        description="Use mock payer responses when real API is unavailable",
    )

    # ─── NLP Configuration ────────────────────────────────────────
    SPACY_MODEL: str = Field(
        default="en_core_sci_lg",
        description="scispaCy model for medical NER",
    )
    NLP_CONFIDENCE_THRESHOLD: float = Field(
        default=0.75,
        description="Minimum confidence for NLP-inferred codes",
    )

    # ─── Quality Assessment ───────────────────────────────────────
    QUALITY_WEIGHTS: dict = Field(
        default={
            "structural_completeness": 0.30,
            "terminology_coverage": 0.25,
            "profile_compliance": 0.30,
            "consent_readiness": 0.15,
        },
        description="Weights for NHCX Readiness Score dimensions",
    )

    # ─── NRCeS Profiles ──────────────────────────────────────────
    NRCES_PROFILES_DIR: str = Field(
        default="profiles",
        description="Directory containing NRCeS FHIR profiles",
    )
    CORE_PROFILES: list = Field(
        default=[
            "NRCeSPatient",
            "NRCeSClaimBundle",
            "NRCeSCoverageEligibilityRequestBundle",
            "NRCeSCoverage",
            "NRCeSOrganization",
        ],
        description="Core NRCeS profiles to validate against",
    )

    # ─── Logging ──────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()

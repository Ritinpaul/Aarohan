"""
Mapping template CRUD endpoint.
Manages saved field-to-FHIR mapping configurations.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class MappingTemplate(BaseModel):
    """A saved field mapping configuration."""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    source_format: str  # csv | hl7v2 | xml | json
    target_profile: str  # NRCeSClaimBundle, NRCeSPatient, etc.
    mappings: list  # List of field-to-field mappings
    created_at: Optional[str] = None


@router.get("/")
async def list_templates():
    """List all saved mapping templates."""
    # TODO: Phase 3 — load from PostgreSQL
    return {"templates": [], "total": 0}


@router.post("/")
async def create_template(template: MappingTemplate):
    """Save a new mapping template."""
    # TODO: Phase 3
    return {"status": "stub", "message": "Mapping template save not yet implemented."}


@router.get("/{template_id}")
async def get_template(template_id: str):
    """Get a specific mapping template."""
    # TODO: Phase 3
    return {"status": "stub", "template_id": template_id}


@router.put("/{template_id}")
async def update_template(template_id: str, template: MappingTemplate):
    """Update an existing mapping template."""
    # TODO: Phase 3
    return {"status": "stub", "template_id": template_id}


@router.delete("/{template_id}")
async def delete_template(template_id: str):
    """Delete a mapping template."""
    # TODO: Phase 3
    return {"status": "stub", "template_id": template_id}

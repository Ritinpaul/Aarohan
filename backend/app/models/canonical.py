from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime

class InternalIdentifier(BaseModel):
    system: Optional[str] = None
    value: str

class InternalPatient(BaseModel):
    id: str
    identifiers: List[InternalIdentifier] = Field(default_factory=list)
    name: str
    gender: str
    birth_date: Optional[date] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

class InternalDiagnosis(BaseModel):
    id: str
    patient_id: str
    text: str
    code: Optional[str] = None
    system: Optional[str] = None
    recorded_date: Optional[datetime] = None

class InternalMedication(BaseModel):
    id: str
    patient_id: str
    text: str
    code: Optional[str] = None
    system: Optional[str] = None
    dosage_instruction: Optional[str] = None
    duration_days: Optional[int] = None
    start_date: Optional[date] = None

class InternalObservation(BaseModel):
    id: str
    patient_id: str
    text: str
    code: Optional[str] = None
    system: Optional[str] = None
    value: Optional[str] = None
    unit: Optional[str] = None
    issued_date: Optional[datetime] = None

class InternalEncounter(BaseModel):
    id: str
    patient_id: str
    facility_name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    class_type: str = "AMB" # AMB, IMP, EMR
    
class InternalCoverage(BaseModel):
    id: str
    patient_id: str
    subscriber_id: Optional[str] = None
    network: str
    scheme_name: str
    status: str = "active"

class InternalClaim(BaseModel):
    id: str
    patient_id: str
    encounter_id: str
    coverage_id: str
    provider_facility: str
    total_amount: float
    currency: str = "INR"
    type: str = "institutional"

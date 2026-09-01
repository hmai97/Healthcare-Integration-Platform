"""Patient validation schema placeholder for later implementation."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_patient_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    created_at: datetime
    updated_at: datetime

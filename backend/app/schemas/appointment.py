"""Appointment validation schema placeholder for later implementation."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_appointment_id: str
    patient_id: int
    appointment_date: date
    appointment_type: str
    provider: str
    status: str
    created_at: datetime

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EventType(str, Enum):
    PATIENT_CREATED = "PATIENT_CREATED"
    PATIENT_UPDATED = "PATIENT_UPDATED"
    APPOINTMENT_CREATED = "APPOINTMENT_CREATED"
    APPOINTMENT_UPDATED = "APPOINTMENT_UPDATED"
    BILLING_CREATED = "BILLING_CREATED"
    BILLING_UPDATED = "BILLING_UPDATED"


class EventSource(str, Enum):
    EMR = "EMR"
    APPOINTMENT_SYSTEM = "APPOINTMENT_SYSTEM"
    BILLING_SYSTEM = "BILLING_SYSTEM"


class PatientStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class AppointmentStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class BillingStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    DENIED = "DENIED"


class PatientPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_patient_id: str = Field(..., min_length=1)
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    date_of_birth: date

    @field_validator("external_patient_id", "first_name", "last_name")
    @classmethod
    def ensure_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value cannot be blank")
        return value.strip()

    @field_validator("date_of_birth")
    @classmethod
    def date_not_in_future(cls, value: date) -> date:
        today = date.today()
        if value > today:
            raise ValueError("date_of_birth cannot be in the future")
        return value


class AppointmentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_appointment_id: str = Field(..., min_length=1)
    patient_id: str = Field(..., min_length=1)
    appointment_date: date
    appointment_type: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)
    status: AppointmentStatus

    @field_validator("external_appointment_id", "patient_id", "appointment_type", "provider")
    @classmethod
    def ensure_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value cannot be blank")
        return value.strip()


class BillingPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_billing_id: str = Field(..., min_length=1)
    patient_id: str = Field(..., min_length=1)
    amount: float = Field(..., ge=0)
    insurance_provider: str = Field(..., min_length=1)
    billing_status: BillingStatus
    service_date: date

    @field_validator("external_billing_id", "patient_id", "insurance_provider")
    @classmethod
    def ensure_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value cannot be blank")
        return value.strip()


class HealthcareEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(..., min_length=1)
    event_type: EventType
    source: EventSource
    timestamp: datetime
    entity_id: str = Field(..., min_length=1)
    payload: dict[str, Any]

    @field_validator("event_id", "entity_id")
    @classmethod
    def ensure_required_strings(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value cannot be blank")
        return value.strip()

    @model_validator(mode="after")
    def validate_payload_for_event_type(self) -> "HealthcareEvent":
        if not isinstance(self.payload, dict):
            raise ValueError("payload must be an object")

        if self.event_type in {EventType.PATIENT_CREATED, EventType.PATIENT_UPDATED}:
            PatientPayload.model_validate(self.payload)
        elif self.event_type in {EventType.APPOINTMENT_CREATED, EventType.APPOINTMENT_UPDATED}:
            AppointmentPayload.model_validate(self.payload)
        elif self.event_type in {EventType.BILLING_CREATED, EventType.BILLING_UPDATED}:
            BillingPayload.model_validate(self.payload)

        return self


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    event_type: str
    source: str
    entity_id: str
    payload: dict[str, Any]
    status: str
    validation_error: str | None = None
    processing_time_ms: int | None = None
    created_at: datetime
    processed_at: datetime | None = None


class PaginatedEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[EventRead]
    page: int
    page_size: int
    total: int
    total_pages: int


class HealthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str = "healthy"


class MonitoringSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_events: int
    processed_events: int
    failed_events: int
    processing_rate: float
    events_last_minute: int


class EventTypeCountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_type: str
    count: int


class StatusCountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    count: int

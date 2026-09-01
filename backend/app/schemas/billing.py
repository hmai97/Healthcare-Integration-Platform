"""Billing validation schema placeholder for later implementation."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class BillingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_billing_id: str
    patient_id: int
    amount: float
    insurance_provider: str
    billing_status: str
    service_date: date
    created_at: datetime

"""Appointment API routes will be implemented in a later phase."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.appointment import AppointmentRead
from app.services.data_service import AppointmentService

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


def get_appointment_service(db: Session = Depends(get_db)) -> AppointmentService:
    return AppointmentService(db)


@router.get("", response_model=list[AppointmentRead])
def list_appointments(
    limit: int = Query(100, ge=1, le=500),
    service: AppointmentService = Depends(get_appointment_service),
) -> list[AppointmentRead]:
    return service.list_appointments(limit=limit)

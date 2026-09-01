"""Patient API routes will be implemented in a later phase."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.patient import PatientRead
from app.services.data_service import PatientService

router = APIRouter(prefix="/api/patients", tags=["patients"])


def get_patient_service(db: Session = Depends(get_db)) -> PatientService:
    return PatientService(db)


@router.get("", response_model=list[PatientRead])
def list_patients(
    limit: int = Query(100, ge=1, le=500),
    service: PatientService = Depends(get_patient_service),
) -> list[PatientRead]:
    return service.list_patients(limit=limit)

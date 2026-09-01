from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.billing_repository import BillingRepository
from app.repositories.patient_repository import PatientRepository
from app.schemas.appointment import AppointmentRead
from app.schemas.billing import BillingRead
from app.schemas.patient import PatientRead


class PatientService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = PatientRepository()

    def list_patients(self, *, limit: int = 100) -> list[PatientRead]:
        limit = max(min(limit, 500), 1)
        patients = self.repository.list_patients(self.db, limit=limit)
        return [PatientRead.model_validate(patient) for patient in patients]


class AppointmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = AppointmentRepository()

    def list_appointments(self, *, limit: int = 100) -> list[AppointmentRead]:
        limit = max(min(limit, 500), 1)
        appointments = self.repository.list_appointments(self.db, limit=limit)
        return [AppointmentRead.model_validate(appointment) for appointment in appointments]


class BillingService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = BillingRepository()

    def list_billing(self, *, limit: int = 100) -> list[BillingRead]:
        limit = max(min(limit, 500), 1)
        billing_records = self.repository.list_billing_records(self.db, limit=limit)
        return [BillingRead.model_validate(record) for record in billing_records]

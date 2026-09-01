"""Patient repository placeholder for later implementation."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.patient import Patient


class PatientRepository:
    def get_by_external_patient_id(self, db: Session, external_patient_id: str) -> Patient | None:
        return db.query(Patient).filter(Patient.external_patient_id == external_patient_id).first()

    def list_patients(self, db: Session, *, limit: int = 100, offset: int = 0) -> list[Patient]:
        return db.query(Patient).order_by(Patient.created_at.desc()).offset(offset).limit(limit).all()

    def count_patients(self, db: Session) -> int:
        return db.query(Patient).count()

    def create_patient(self, db: Session, payload: dict) -> Patient:
        external_patient_id = str(payload["external_patient_id"]).strip()
        existing = self.get_by_external_patient_id(db, external_patient_id)
        if existing is not None:
            return existing

        patient = Patient(
            external_patient_id=external_patient_id,
            first_name=str(payload["first_name"]).strip(),
            last_name=str(payload["last_name"]).strip(),
            date_of_birth=date.fromisoformat(str(payload["date_of_birth"])),
        )
        db.add(patient)
        db.flush()
        return patient

    def update_patient(self, db: Session, external_patient_id: str, payload: dict) -> Patient:
        patient = self.get_by_external_patient_id(db, external_patient_id)
        if patient is None:
            raise ValueError(f"Patient {external_patient_id} not found")

        if "first_name" in payload and str(payload["first_name"]).strip():
            patient.first_name = str(payload["first_name"]).strip()
        if "last_name" in payload and str(payload["last_name"]).strip():
            patient.last_name = str(payload["last_name"]).strip()
        if "date_of_birth" in payload and payload["date_of_birth"] is not None:
            patient.date_of_birth = date.fromisoformat(str(payload["date_of_birth"]))

        db.add(patient)
        db.flush()
        return patient

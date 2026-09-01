"""Appointment repository placeholder for later implementation."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.patient import Patient


class AppointmentRepository:
    def get_by_external_appointment_id(self, db: Session, external_appointment_id: str) -> Appointment | None:
        return db.query(Appointment).filter(Appointment.external_appointment_id == external_appointment_id).first()

    def list_appointments(self, db: Session, *, limit: int = 100, offset: int = 0) -> list[Appointment]:
        return db.query(Appointment).order_by(Appointment.created_at.desc()).offset(offset).limit(limit).all()

    def count_appointments(self, db: Session) -> int:
        return db.query(Appointment).count()

    def create_appointment(self, db: Session, payload: dict) -> Appointment:
        external_appointment_id = str(payload["external_appointment_id"]).strip()
        existing = self.get_by_external_appointment_id(db, external_appointment_id)
        if existing is not None:
            return existing

        patient_external_id = str(payload["patient_id"]).strip()
        patient = db.query(Patient).filter(Patient.external_patient_id == patient_external_id).first()
        if patient is None:
            raise ValueError(f"Patient {patient_external_id} not found for appointment {external_appointment_id}")

        appointment = Appointment(
            external_appointment_id=external_appointment_id,
            patient_id=patient.id,
            appointment_date=date.fromisoformat(str(payload["appointment_date"])),
            appointment_type=str(payload["appointment_type"]).strip(),
            provider=str(payload["provider"]).strip(),
            status=str(payload["status"]).strip(),
        )
        db.add(appointment)
        db.flush()
        return appointment

    def update_appointment(self, db: Session, external_appointment_id: str, payload: dict) -> Appointment:
        appointment = self.get_by_external_appointment_id(db, external_appointment_id)
        if appointment is None:
            raise ValueError(f"Appointment {external_appointment_id} not found")

        if "appointment_date" in payload and payload["appointment_date"] is not None:
            appointment.appointment_date = date.fromisoformat(str(payload["appointment_date"]))
        if "appointment_type" in payload and str(payload["appointment_type"]).strip():
            appointment.appointment_type = str(payload["appointment_type"]).strip()
        if "provider" in payload and str(payload["provider"]).strip():
            appointment.provider = str(payload["provider"]).strip()
        if "status" in payload and str(payload["status"]).strip():
            appointment.status = str(payload["status"]).strip()
        if "patient_id" in payload and payload["patient_id"] is not None:
            patient_external_id = str(payload["patient_id"]).strip()
            patient = db.query(Patient).filter(Patient.external_patient_id == patient_external_id).first()
            if patient is None:
                raise ValueError(f"Patient {patient_external_id} not found for appointment {external_appointment_id}")
            appointment.patient_id = patient.id

        db.add(appointment)
        db.flush()
        return appointment

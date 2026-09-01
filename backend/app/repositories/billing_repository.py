"""Billing repository placeholder for later implementation."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.billing import BillingRecord
from app.models.patient import Patient


class BillingRepository:
    def get_by_external_billing_id(self, db: Session, external_billing_id: str) -> BillingRecord | None:
        return db.query(BillingRecord).filter(BillingRecord.external_billing_id == external_billing_id).first()

    def list_billing_records(self, db: Session, *, limit: int = 100, offset: int = 0) -> list[BillingRecord]:
        return db.query(BillingRecord).order_by(BillingRecord.created_at.desc()).offset(offset).limit(limit).all()

    def count_billing_records(self, db: Session) -> int:
        return db.query(BillingRecord).count()

    def create_billing_record(self, db: Session, payload: dict) -> BillingRecord:
        external_billing_id = str(payload["external_billing_id"]).strip()
        existing = self.get_by_external_billing_id(db, external_billing_id)
        if existing is not None:
            return existing

        patient_external_id = str(payload["patient_id"]).strip()
        patient = db.query(Patient).filter(Patient.external_patient_id == patient_external_id).first()
        if patient is None:
            raise ValueError(f"Patient {patient_external_id} not found for billing {external_billing_id}")

        billing_record = BillingRecord(
            external_billing_id=external_billing_id,
            patient_id=patient.id,
            amount=float(payload["amount"]),
            insurance_provider=str(payload["insurance_provider"]).strip(),
            billing_status=str(payload["billing_status"]).strip(),
            service_date=date.fromisoformat(str(payload["service_date"])),
        )
        db.add(billing_record)
        db.flush()
        return billing_record

    def update_billing_record(self, db: Session, external_billing_id: str, payload: dict) -> BillingRecord:
        billing_record = self.get_by_external_billing_id(db, external_billing_id)
        if billing_record is None:
            raise ValueError(f"Billing record {external_billing_id} not found")

        if "amount" in payload and payload["amount"] is not None:
            billing_record.amount = float(payload["amount"])
        if "insurance_provider" in payload and str(payload["insurance_provider"]).strip():
            billing_record.insurance_provider = str(payload["insurance_provider"]).strip()
        if "billing_status" in payload and str(payload["billing_status"]).strip():
            billing_record.billing_status = str(payload["billing_status"]).strip()
        if "service_date" in payload and payload["service_date"] is not None:
            billing_record.service_date = date.fromisoformat(str(payload["service_date"]))
        if "patient_id" in payload and payload["patient_id"] is not None:
            patient_external_id = str(payload["patient_id"]).strip()
            patient = db.query(Patient).filter(Patient.external_patient_id == patient_external_id).first()
            if patient is None:
                raise ValueError(f"Patient {patient_external_id} not found for billing {external_billing_id}")
            billing_record.patient_id = patient.id

        db.add(billing_record)
        db.flush()
        return billing_record

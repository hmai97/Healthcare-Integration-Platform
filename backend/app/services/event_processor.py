"""Event processing service placeholder for later implementation."""
from __future__ import annotations

import time
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.event import EventStatus
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.billing_repository import BillingRepository
from app.repositories.event_repository import EventRepository
from app.repositories.patient_repository import PatientRepository
from app.utils.logger import logger


class EventProcessingService:
    def __init__(
        self,
        event_repository: EventRepository | None = None,
        patient_repository: PatientRepository | None = None,
        appointment_repository: AppointmentRepository | None = None,
        billing_repository: BillingRepository | None = None,
    ) -> None:
        self.event_repository = event_repository or EventRepository()
        self.patient_repository = patient_repository or PatientRepository()
        self.appointment_repository = appointment_repository or AppointmentRepository()
        self.billing_repository = billing_repository or BillingRepository()

    def _event_payload(self, event: Mapping[str, Any] | Any) -> dict[str, Any]:
        if hasattr(event, "model_dump"):
            return dict(event.model_dump(mode="json"))
        if isinstance(event, Mapping):
            return dict(event)
        raise TypeError("Event must be a mapping or Pydantic model")

    def _processing_start(self) -> float:
        return time.perf_counter()

    def _processing_duration_ms(self, start: float) -> int:
        return max(0, int(round((time.perf_counter() - start) * 1000)))

    def process(self, event: Mapping[str, Any] | Any, db: Session | None = None) -> dict[str, Any]:
        event_data = self._event_payload(event)
        event_id = str(event_data.get("event_id", "")).strip()
        event_type = str(event_data.get("event_type", "")).strip()
        payload = dict(event_data.get("payload", {}))

        if not event_id:
            raise ValueError("event_id is required")

        # If no db session provided, create one and manage its lifecycle
        owns_session = db is None
        if owns_session:
            db = SessionLocal()

        started_at = self._processing_start()

        try:
            # Check idempotency - this may auto-start transaction
            existing_event = self.event_repository.get_by_event_id(db, event_id)
            if existing_event is not None and existing_event.status == EventStatus.PROCESSED.value:
                logger.info("EVENT_ALREADY_PROCESSED event_id=%s", event_id)
                return {"event_id": event_id, "status": EventStatus.PROCESSED.value, "duplicate": True}

            if existing_event is not None and existing_event.status == EventStatus.FAILED.value:
                logger.warning("EVENT_RETRYING_FAILED_EVENT event_id=%s", event_id)

            # Process based on event type within the existing transaction
            # (no explicit with db.begin() - transaction already started by query above)
            if event_type in {"PATIENT_CREATED", "PATIENT_UPDATED"}:
                if event_type == "PATIENT_CREATED":
                    self.patient_repository.create_patient(db, payload)
                elif event_type == "PATIENT_UPDATED":
                    self.patient_repository.update_patient(db, str(payload.get("external_patient_id", "")).strip(), payload)

            elif event_type in {"APPOINTMENT_CREATED", "APPOINTMENT_UPDATED"}:
                if event_type == "APPOINTMENT_CREATED":
                    self.appointment_repository.create_appointment(db, payload)
                elif event_type == "APPOINTMENT_UPDATED":
                    self.appointment_repository.update_appointment(db, str(payload.get("external_appointment_id", "")).strip(), payload)

            elif event_type in {"BILLING_CREATED", "BILLING_UPDATED"}:
                if event_type == "BILLING_CREATED":
                    self.billing_repository.create_billing_record(db, payload)
                elif event_type == "BILLING_UPDATED":
                    self.billing_repository.update_billing_record(db, str(payload.get("external_billing_id", "")).strip(), payload)
            else:
                raise ValueError(f"Unsupported event_type for processing: {event_type}")

            # Mark as processed within the same transaction
            self.event_repository.update_status(
                db,
                event_id,
                EventStatus.PROCESSED.value,
                processing_time_ms=self._processing_duration_ms(started_at),
                processed_at=datetime.now(timezone.utc),
            )

            # Only commit if we own the session; otherwise caller manages
            if owns_session:
                db.commit()

            logger.info(
                "EVENT_PROCESSED event_id=%s event_type=%s processing_time_ms=%s",
                event_id,
                event_type,
                self._processing_duration_ms(started_at),
            )
            return {"event_id": event_id, "status": EventStatus.PROCESSED.value, "duplicate": False}

        except Exception as exc:
            # If we own the session, mark FAILED and rollback
            if owns_session:
                try:
                    # Start a fresh transaction to mark FAILED (the current one failed)
                    db.rollback()
                    self.event_repository.update_status(
                        db,
                        event_id,
                        EventStatus.FAILED.value,
                        validation_error=str(exc),
                        processed_at=datetime.now(timezone.utc),
                    )
                    db.commit()
                except Exception as exc_failed:
                    db.rollback()
                    logger.error("EVENT_FAILED_STATUS_UPDATE_FAILED event_id=%s error=%s", event_id, exc_failed)
            else:
                # If session is passed by caller, let them handle FAILED marking
                pass

            logger.error("EVENT_PROCESSING_FAILED event_id=%s event_type=%s error=%s", event_id, event_type, exc)
            raise
        finally:
            if owns_session:
                db.close()


processing_service = EventProcessingService()

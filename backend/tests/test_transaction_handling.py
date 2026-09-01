"""Regression tests for SQLAlchemy transaction handling fix.

These tests expose and verify the fix for:
InvalidRequestError: A transaction is already begun on this Session.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.core.config import settings
from app.models.event import Event, EventStatus
from app.models.patient import Patient
from app.repositories.event_repository import EventRepository
from app.repositories.patient_repository import PatientRepository
from app.services.event_processor import EventProcessingService


class TestTransactionHandlingRegression:
    """Regression tests for transaction conflict bug: 'A transaction is already begun'."""

    def test_processor_accepts_session_with_active_transaction(self):
        """Verify that processor doesn't fail when passed a session with active transaction."""
        # This reproduces the actual issue: a session query auto-starts transaction,
        # then passing to processor should NOT cause InvalidRequestError
        db = SessionLocal()
        try:
            # Simulate consumer creating event (auto-starts transaction)
            patient_data = {
                "event_id": "evt-123-transaction",
                "event_type": "PATIENT_CREATED",
                "source": "test",
                "entity_id": "pat-001",
                "payload": {
                    "external_patient_id": "ext-pat-001",
                    "first_name": "John",
                    "last_name": "Doe",
                    "date_of_birth": "1990-01-15",
                },
            }

            event_repo = EventRepository()
            patient_repo = PatientRepository()
            processor = EventProcessingService(
                event_repository=event_repo,
                patient_repository=patient_repo,
            )

            # Create event to simulate consumer flow (auto-starts transaction)
            event_repo.create_event(db, patient_data)
            db.commit()

            # Mark as validated (another transaction)
            event_repo.update_status(db, "evt-123-transaction", EventStatus.VALIDATED.value)
            db.commit()

            # Now pass the session to processor - should NOT raise InvalidRequestError
            # This is where the bug would occur: processor calls get_by_event_id (queries),
            # which auto-starts a transaction, then tries with db.begin() -> InvalidRequestError
            result = processor.process(patient_data, db=db)

            # Should succeed and return PROCESSED
            assert result["status"] == EventStatus.PROCESSED.value
            assert result["duplicate"] is False

            db.commit()
        finally:
            db.close()

    def test_processor_with_session_doesnt_nest_transactions(self):
        """Verify that processor doesn't attempt to nest transactions when session provided."""
        db = SessionLocal()
        try:
            appointment_data = {
                "event_id": "evt-456-no-nest",
                "event_type": "APPOINTMENT_CREATED",
                "source": "test",
                "entity_id": "apt-001",
                "payload": {
                    "external_appointment_id": "ext-apt-001",
                    "patient_id": "ext-pat-002",  # external patient ID
                    "appointment_date": "2026-09-01",
                    "appointment_type": "FOLLOW_UP",
                    "provider": "Dr. Test",
                    "status": "SCHEDULED",
                },
            }

            # First create the patient (required foreign key)
            patient_data = {
                "event_id": "evt-patient-prereq",
                "event_type": "PATIENT_CREATED",
                "source": "test",
                "entity_id": "pat-002",
                "payload": {
                    "external_patient_id": "ext-pat-002",
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "date_of_birth": "1985-06-20",
                },
            }

            event_repo = EventRepository()
            processor = EventProcessingService()

            # Create patient first
            event_repo.create_event(db, patient_data)
            db.commit()
            
            event_repo.update_status(db, "evt-patient-prereq", EventStatus.VALIDATED.value)
            db.commit()
            
            processor.process(patient_data, db=db)
            db.commit()

            # Now process appointment (requires session to already have transaction context)
            event_repo.create_event(db, appointment_data)
            db.commit()

            event_repo.update_status(db, "evt-456-no-nest", EventStatus.VALIDATED.value)
            db.commit()

            # This should work without InvalidRequestError
            result = processor.process(appointment_data, db=db)
            assert result["status"] == EventStatus.PROCESSED.value

            db.commit()
        finally:
            db.close()

    def test_processor_rollback_on_failure_with_passed_session(self):
        """Verify that processor doesn't cause InvalidRequestError in exception handler."""
        db = SessionLocal()
        try:
            invalid_patient_data = {
                "event_id": "evt-789-rollback",
                "event_type": "PATIENT_UPDATED",
                "source": "test",
                "entity_id": "pat-003",
                "payload": {
                    "external_patient_id": "ext-pat-nonexistent",  # Patient doesn't exist
                    "first_name": "Invalid",
                    "last_name": "Update",
                },
            }

            event_repo = EventRepository()
            processor = EventProcessingService()

            # Create event
            event_repo.create_event(db, invalid_patient_data)
            db.commit()

            event_repo.update_status(db, "evt-789-rollback", EventStatus.VALIDATED.value)
            db.commit()

            # This should fail (patient doesn't exist) but NOT raise InvalidRequestError
            with pytest.raises(ValueError, match="not found"):
                processor.process(invalid_patient_data, db=db)

            # Verify we can still use the session to check/update status
            # (the bug would prevent this from working)
            db.rollback()
            event = event_repo.get_by_event_id(db, "evt-789-rollback")
            assert event is not None
            assert event.status == EventStatus.VALIDATED.value

        finally:
            db.close()

    def test_processor_marks_failed_after_rollback(self):
        """Verify that FAILED status can be persisted after a processing failure."""
        db = SessionLocal()
        try:
            invalid_data = {
                "event_id": "evt-999-failed",
                "event_type": "PATIENT_CREATED",
                "source": "test",
                "entity_id": "pat-004",
                "payload": {
                    "external_patient_id": "ext-pat-fail",
                    "first_name": "Test",
                    "last_name": "Failure",
                    # Missing date_of_birth - will cause validation error
                },
            }

            event_repo = EventRepository()
            processor = EventProcessingService()

            # Create event
            event_repo.create_event(db, invalid_data)
            db.commit()

            event_repo.update_status(db, "evt-999-failed", EventStatus.VALIDATED.value)
            db.commit()

            # Processing will fail
            with pytest.raises(Exception):
                processor.process(invalid_data, db=db)

            # Rollback the failed processing
            db.rollback()

            # Now mark as FAILED (this was failing in the bug)
            error_msg = "Missing required field: date_of_birth"
            event_repo.update_status(
                db,
                "evt-999-failed",
                EventStatus.FAILED.value,
                validation_error=error_msg,
            )
            db.commit()

            # Verify FAILED status persisted
            final_event = event_repo.get_by_event_id(db, "evt-999-failed")
            assert final_event is not None
            assert final_event.status == EventStatus.FAILED.value
            assert error_msg in final_event.validation_error

        finally:
            db.close()

    def test_processor_preserves_idempotency_with_session(self):
        """Verify that idempotency check works correctly when session is passed."""
        db = SessionLocal()
        try:
            patient_data = {
                "event_id": "evt-idem-001",
                "event_type": "PATIENT_CREATED",
                "source": "test",
                "entity_id": "pat-005",
                "payload": {
                    "external_patient_id": "ext-pat-idem",
                    "first_name": "Idempotent",
                    "last_name": "Test",
                    "date_of_birth": "1980-05-10",
                },
            }

            event_repo = EventRepository()
            processor = EventProcessingService()

            # Process once
            event_repo.create_event(db, patient_data)
            db.commit()

            event_repo.update_status(db, "evt-idem-001", EventStatus.VALIDATED.value)
            db.commit()

            result1 = processor.process(patient_data, db=db)
            db.commit()

            assert result1["status"] == EventStatus.PROCESSED.value
            assert result1["duplicate"] is False

            # Process again (should return duplicate=True due to idempotency)
            result2 = processor.process(patient_data, db=db)

            assert result2["status"] == EventStatus.PROCESSED.value
            assert result2["duplicate"] is True

        finally:
            db.close()

    def test_consecutive_events_dont_conflict(self):
        """Verify that processing multiple events in sequence doesn't cause transaction conflicts."""
        success_count = 0

        for i in range(3):
            db = SessionLocal()
            try:
                event_data = {
                    "event_id": f"evt-seq-00{i}",
                    "event_type": "PATIENT_CREATED",
                    "source": "test",
                    "entity_id": f"pat-seq-{i:03d}",
                    "payload": {
                        "external_patient_id": f"ext-pat-seq-{i:03d}",
                        "first_name": f"Sequential{i}",
                        "last_name": f"Patient{i}",
                        "date_of_birth": "1990-01-01",
                    },
                }

                event_repo = EventRepository()
                processor = EventProcessingService()

                event_repo.create_event(db, event_data)
                db.commit()

                event_repo.update_status(db, event_data["event_id"], EventStatus.VALIDATED.value)
                db.commit()

                # Should not raise InvalidRequestError even though we're
                # now on the Nth event being processed
                result = processor.process(event_data, db=db)
                db.commit()

                assert result["status"] == EventStatus.PROCESSED.value
                success_count += 1

            finally:
                db.close()

        assert success_count == 3, "All three consecutive events should process successfully"

    def test_processor_owns_session_when_none_provided(self):
        """Verify that processor still manages its own session when not provided."""
        # First, create the event in the database (simulating consumer behavior)
        db_init = SessionLocal()
        try:
            patient_data = {
                "event_id": "evt-own-001",
                "event_type": "PATIENT_CREATED",
                "source": "test",
                "entity_id": "pat-own-001",
                "payload": {
                    "external_patient_id": "ext-pat-own",
                    "first_name": "OwnsSession",
                    "last_name": "Processor",
                    "date_of_birth": "1975-12-25",
                },
            }

            event_repo = EventRepository()
            event_repo.create_event(db_init, patient_data)
            db_init.commit()

            event_repo.update_status(db_init, "evt-own-001", EventStatus.VALIDATED.value)
            db_init.commit()
        finally:
            db_init.close()

        # Now process without passing db; processor should create and manage its own
        processor = EventProcessingService()
        result = processor.process(patient_data)  # No db parameter

        assert result["status"] == EventStatus.PROCESSED.value
        assert result["duplicate"] is False

        # Verify data was persisted
        db = SessionLocal()
        try:
            event = EventRepository().get_by_event_id(db, "evt-own-001")
            assert event is not None
            assert event.status == EventStatus.PROCESSED.value
        finally:
            db.close()

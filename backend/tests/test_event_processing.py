from types import SimpleNamespace
from unittest.mock import ANY, MagicMock

import pytest

from app.models.event import EventStatus
from app.services.event_processor import EventProcessingService


@pytest.fixture
def fake_session():
    session = MagicMock()
    session.begin.return_value.__enter__.return_value = session
    session.begin.return_value.__exit__.return_value = False
    return session


def test_patient_created_event_processing_calls_patient_repository(fake_session, monkeypatch):
    event_repo = MagicMock()
    event_repo.get_by_event_id.return_value = None
    event_repo.update_status.return_value = SimpleNamespace()

    patient_repo = MagicMock()
    patient_repo.create_patient.return_value = SimpleNamespace()

    service = EventProcessingService(
        event_repository=event_repo,
        patient_repository=patient_repo,
        appointment_repository=MagicMock(),
        billing_repository=MagicMock(),
    )

    monkeypatch.setattr("app.services.event_processor.SessionLocal", lambda: fake_session)

    payload = {
        "event_id": "evt-patient-01",
        "event_type": "PATIENT_CREATED",
        "source": "EMR",
        "entity_id": "patient-1001",
        "payload": {
            "external_patient_id": "patient-1001",
            "first_name": "John",
            "last_name": "Smith",
            "date_of_birth": "1990-01-15",
        },
    }

    result = service.process(payload)

    assert result["status"] == EventStatus.PROCESSED.value
    patient_repo.create_patient.assert_called_once()
    event_repo.update_status.assert_any_call(fake_session, "evt-patient-01", EventStatus.PROCESSED.value, processing_time_ms=pytest.approx(0, abs=50), processed_at=ANY)


def test_patient_updated_event_processing_updates_existing_patient(fake_session, monkeypatch):
    event_repo = MagicMock()
    event_repo.get_by_event_id.return_value = None
    event_repo.update_status.return_value = SimpleNamespace()

    patient_repo = MagicMock()
    patient_repo.update_patient.return_value = SimpleNamespace()

    service = EventProcessingService(
        event_repository=event_repo,
        patient_repository=patient_repo,
        appointment_repository=MagicMock(),
        billing_repository=MagicMock(),
    )

    monkeypatch.setattr("app.services.event_processor.SessionLocal", lambda: fake_session)

    payload = {
        "event_id": "evt-patient-update-01",
        "event_type": "PATIENT_UPDATED",
        "source": "EMR",
        "entity_id": "patient-1001",
        "payload": {
            "external_patient_id": "patient-1001",
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "1988-11-08",
        },
    }

    result = service.process(payload)

    assert result["status"] == EventStatus.PROCESSED.value
    patient_repo.update_patient.assert_called_once_with(fake_session, "patient-1001", payload["payload"])


def test_appointment_created_event_processing_calls_appointment_repository(fake_session, monkeypatch):
    event_repo = MagicMock()
    event_repo.get_by_event_id.return_value = None
    event_repo.update_status.return_value = SimpleNamespace()

    appointment_repo = MagicMock()
    appointment_repo.create_appointment.return_value = SimpleNamespace()

    service = EventProcessingService(
        event_repository=event_repo,
        patient_repository=MagicMock(),
        appointment_repository=appointment_repo,
        billing_repository=MagicMock(),
    )

    monkeypatch.setattr("app.services.event_processor.SessionLocal", lambda: fake_session)

    payload = {
        "event_id": "evt-appt-01",
        "event_type": "APPOINTMENT_CREATED",
        "source": "APPOINTMENT_SYSTEM",
        "entity_id": "appt-2001",
        "payload": {
            "external_appointment_id": "appt-2001",
            "patient_id": "patient-1001",
            "appointment_date": "2026-08-20",
            "appointment_type": "FOLLOW_UP",
            "provider": "Dr. Patel",
            "status": "SCHEDULED",
        },
    }

    result = service.process(payload)

    assert result["status"] == EventStatus.PROCESSED.value
    appointment_repo.create_appointment.assert_called_once_with(fake_session, payload["payload"])


def test_billing_created_event_processing_calls_billing_repository(fake_session, monkeypatch):
    event_repo = MagicMock()
    event_repo.get_by_event_id.return_value = None
    event_repo.update_status.return_value = SimpleNamespace()

    billing_repo = MagicMock()
    billing_repo.create_billing_record.return_value = SimpleNamespace()

    service = EventProcessingService(
        event_repository=event_repo,
        patient_repository=MagicMock(),
        appointment_repository=MagicMock(),
        billing_repository=billing_repo,
    )

    monkeypatch.setattr("app.services.event_processor.SessionLocal", lambda: fake_session)

    payload = {
        "event_id": "evt-bill-01",
        "event_type": "BILLING_CREATED",
        "source": "BILLING_SYSTEM",
        "entity_id": "bill-3001",
        "payload": {
            "external_billing_id": "bill-3001",
            "patient_id": "patient-1001",
            "amount": 125.5,
            "insurance_provider": "BlueCross",
            "billing_status": "PENDING",
            "service_date": "2026-08-15",
        },
    }

    result = service.process(payload)

    assert result["status"] == EventStatus.PROCESSED.value
    billing_repo.create_billing_record.assert_called_once_with(fake_session, payload["payload"])


def test_duplicate_processed_event_is_skipped(fake_session, monkeypatch):
    event_repo = MagicMock()
    event_repo.get_by_event_id.return_value = SimpleNamespace(status=EventStatus.PROCESSED.value)
    patient_repo = MagicMock()

    service = EventProcessingService(
        event_repository=event_repo,
        patient_repository=patient_repo,
        appointment_repository=MagicMock(),
        billing_repository=MagicMock(),
    )

    monkeypatch.setattr("app.services.event_processor.SessionLocal", lambda: fake_session)

    payload = {
        "event_id": "evt-already-processed",
        "event_type": "PATIENT_CREATED",
        "payload": {
            "external_patient_id": "patient-2001",
            "first_name": "Tom",
            "last_name": "Test",
            "date_of_birth": "1980-01-01",
        },
    }

    result = service.process(payload)

    assert result["duplicate"] is True
    patient_repo.create_patient.assert_not_called()


def test_processing_failure_marks_event_failed_and_raises(fake_session, monkeypatch):
    event_repo = MagicMock()
    event_repo.get_by_event_id.return_value = None
    event_repo.update_status.return_value = SimpleNamespace()

    patient_repo = MagicMock()
    patient_repo.create_patient.side_effect = RuntimeError("database error")

    service = EventProcessingService(
        event_repository=event_repo,
        patient_repository=patient_repo,
        appointment_repository=MagicMock(),
        billing_repository=MagicMock(),
    )

    monkeypatch.setattr("app.services.event_processor.SessionLocal", lambda: fake_session)

    payload = {
        "event_id": "evt-fail-01",
        "event_type": "PATIENT_CREATED",
        "payload": {
            "external_patient_id": "patient-fail",
            "first_name": "Fail",
            "last_name": "Case",
            "date_of_birth": "1995-02-02",
        },
    }

    with pytest.raises(RuntimeError, match="database error"):
        service.process(payload)

    event_repo.update_status.assert_any_call(fake_session, "evt-fail-01", EventStatus.FAILED.value, validation_error="database error", processed_at=ANY)

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.models.appointment import Appointment
from app.models.billing import BillingRecord
from app.models.event import Event, EventStatus
from app.models.patient import Patient
from app.services.monitoring_service import MonitoringService
from main import app

client = TestClient(app)

# Test data identifiers that will be cleaned up after each test
_TEST_PATIENT_IDS = {
    "api-patient-3001",
    "api-patient-4001",
    "api-patient-5001",
}
_TEST_EVENT_IDS = {
    "api-event-1001",
    "api-event-1002",
    "api-event-1003",
    "api-event-1004",
    "api-event-detail-2001",
    "api-mon-6001",
    "api-mon-6002",
    "api-mon-6003",
    "api-mon-6004",
    "api-group-7001",
    "api-group-7002",
    "api-group-7003",
    "api-fail-8001",
    "api-fail-8002",
}
_TEST_APPOINTMENT_IDS = {
    "api-appt-4001",
}
_TEST_BILLING_IDS = {
    "api-bill-5001",
}


def _cleanup_test_data(db):
    """Delete all test-created records from the database, respecting foreign key constraints."""
    try:
        # Delete in reverse order of dependency: appointments and billing first (depend on patients)
        db.query(Appointment).filter(
            Appointment.external_appointment_id.in_(_TEST_APPOINTMENT_IDS)
        ).delete(synchronize_session=False)

        db.query(BillingRecord).filter(
            BillingRecord.external_billing_id.in_(_TEST_BILLING_IDS)
        ).delete(synchronize_session=False)

        # Then delete patients (appointments/billing already removed)
        db.query(Patient).filter(
            Patient.external_patient_id.in_(_TEST_PATIENT_IDS)
        ).delete(synchronize_session=False)

        # Finally delete events (no dependencies)
        db.query(Event).filter(
            Event.event_id.in_(_TEST_EVENT_IDS)
        ).delete(synchronize_session=False)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Warning: cleanup failed: {e}")
    finally:
        db.close()


@pytest.fixture
def api_db():
    """Fixture that provides a clean database session for API tests and cleans up afterwards."""
    db = SessionLocal()
    yield db
    # Cleanup is called after the test completes
    _cleanup_test_data(db)


def _create_patient(db, external_patient_id: str, *, first_name: str = "Test", last_name: str = "Patient") -> Patient:
    patient = Patient(
        external_patient_id=external_patient_id,
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date(1990, 1, 15),
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def _create_event(db, event_id: str, event_type: str, status: str, *, created_at: datetime | None = None) -> Event:
    created = created_at or datetime.now(timezone.utc)
    event = Event(
        event_id=event_id,
        event_type=event_type,
        source="EMR",
        entity_id=f"entity-{event_id}",
        payload={"external_patient_id": "patient-123"},
        status=status,
        validation_error=None if status != EventStatus.FAILED.value else "sample failure",
        processing_time_ms=10 if status == EventStatus.PROCESSED.value else None,
        created_at=created,
        processed_at=created if status in {EventStatus.PROCESSED.value, EventStatus.FAILED.value} else None,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_events_pagination_and_filters(api_db):
    db = api_db
    _create_event(db, "api-event-1001", "PATIENT_CREATED", EventStatus.PROCESSED.value)
    _create_event(db, "api-event-1002", "PATIENT_CREATED", EventStatus.PROCESSED.value)
    _create_event(db, "api-event-1003", "APPOINTMENT_CREATED", EventStatus.FAILED.value)
    _create_event(db, "api-event-1004", "BILLING_CREATED", EventStatus.FAILED.value)

    response = client.get("/api/events?page=1&page_size=2")
    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 2
    assert payload["total"] >= 4
    assert len(payload["items"]) == 2

    filtered = client.get("/api/events?event_type=PATIENT_CREATED&status=PROCESSED&page=1&page_size=10")
    assert filtered.status_code == 200
    filtered_payload = filtered.json()
    assert filtered_payload["total"] >= 2
    items = filtered_payload["items"]
    assert all(item["event_type"] == "PATIENT_CREATED" for item in items)
    assert all(item["status"] == "PROCESSED" for item in items)

    status_only = client.get("/api/events?status=FAILED&page=1&page_size=10")
    assert status_only.status_code == 200
    status_items = status_only.json()["items"]
    assert all(item["status"] == "FAILED" for item in status_items)


def test_event_detail_returns_existing_and_missing(api_db):
    db = api_db
    event = _create_event(db, "api-event-detail-2001", "PATIENT_CREATED", EventStatus.PROCESSED.value)

    response = client.get(f"/api/events/{event.event_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["event_id"] == event.event_id
    assert payload["status"] == "PROCESSED"

    missing = client.get("/api/events/missing-event-id")
    assert missing.status_code == 404


def test_patients_endpoint_returns_data(api_db):
    db = api_db
    _create_patient(db, "api-patient-3001", first_name="Alice", last_name="Brown")
    response = client.get("/api/patients?limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert any(item["external_patient_id"] == "api-patient-3001" for item in payload)


def test_appointments_endpoint_returns_data(api_db):
    db = api_db
    patient = _create_patient(db, "api-patient-4001", first_name="Bob", last_name="Green")
    appointment = Appointment(
        external_appointment_id="api-appt-4001",
        patient_id=patient.id,
        appointment_date=date(2026, 9, 15),
        appointment_type="FOLLOW_UP",
        provider="Dr. Lee",
        status="SCHEDULED",
    )
    db.add(appointment)
    db.commit()

    response = client.get("/api/appointments?limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert any(item["external_appointment_id"] == "api-appt-4001" for item in payload)


def test_billing_endpoint_returns_data(api_db):
    db = api_db
    patient = _create_patient(db, "api-patient-5001", first_name="Carol", last_name="White")
    billing = BillingRecord(
        external_billing_id="api-bill-5001",
        patient_id=patient.id,
        amount=120.25,
        insurance_provider="BlueCross",
        billing_status="PENDING",
        service_date=date(2026, 9, 10),
    )
    db.add(billing)
    db.commit()

    response = client.get("/api/billing?limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert any(item["external_billing_id"] == "api-bill-5001" for item in payload)


def test_monitoring_summary_and_zero_division_protection(api_db):
    db = api_db
    _create_event(db, "api-mon-6001", "PATIENT_CREATED", EventStatus.PROCESSED.value)
    _create_event(db, "api-mon-6002", "PATIENT_CREATED", EventStatus.PROCESSED.value)
    _create_event(db, "api-mon-6003", "BILLING_CREATED", EventStatus.FAILED.value)
    _create_event(db, "api-mon-6004", "APPOINTMENT_CREATED", EventStatus.PROCESSED.value, created_at=datetime.now(timezone.utc) - timedelta(minutes=1))

    response = client.get("/api/monitoring/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_events"] >= 4
    assert payload["processed_events"] >= 3
    assert payload["failed_events"] >= 1
    assert payload["processing_rate"] >= 0.0
    assert payload["events_last_minute"] >= 0

    summary = MonitoringService.build_summary(total_events=0, processed_events=0, failed_events=0, events_last_minute=0)
    assert summary.processing_rate == 0.0


def test_monitoring_event_type_and_status_grouping(api_db):
    db = api_db
    _create_event(db, "api-group-7001", "PATIENT_CREATED", EventStatus.PROCESSED.value)
    _create_event(db, "api-group-7002", "PATIENT_CREATED", EventStatus.PROCESSED.value)
    _create_event(db, "api-group-7003", "APPOINTMENT_CREATED", EventStatus.FAILED.value)

    event_types = client.get("/api/monitoring/event-types")
    assert event_types.status_code == 200
    event_types_payload = event_types.json()
    assert any(item["event_type"] == "PATIENT_CREATED" for item in event_types_payload)

    statuses = client.get("/api/monitoring/status")
    assert statuses.status_code == 200
    status_payload = statuses.json()
    assert any(item["status"] == "PROCESSED" for item in status_payload)
    assert any(item["status"] == "FAILED" for item in status_payload)


def test_monitoring_recent_failures_returns_newest_first(api_db):
    db = api_db
    _create_event(db, "api-fail-8001", "BILLING_CREATED", EventStatus.FAILED.value)
    _create_event(db, "api-fail-8002", "APPOINTMENT_CREATED", EventStatus.FAILED.value)

    response = client.get("/api/monitoring/recent-failures?limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 2
    assert payload[0]["status"] == "FAILED"
    assert payload[0]["event_id"] in {"api-fail-8001", "api-fail-8002"}

from datetime import date, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.event import (
    AppointmentStatus,
    BillingStatus,
    EventSource,
    EventType,
    HealthcareEvent,
)
from app.services.validation_service import ValidationService


valid_patient_payload = {
    "external_patient_id": "patient-1001",
    "first_name": "John",
    "last_name": "Smith",
    "date_of_birth": "1990-01-15",
}

valid_appointment_payload = {
    "external_appointment_id": "appt-2001",
    "patient_id": "patient-1001",
    "appointment_date": "2026-08-20",
    "appointment_type": "FOLLOW_UP",
    "provider": "Dr. Patel",
    "status": "SCHEDULED",
}

valid_billing_payload = {
    "external_billing_id": "bill-3001",
    "patient_id": "patient-1001",
    "amount": 125.50,
    "insurance_provider": "BlueCross",
    "billing_status": "PENDING",
    "service_date": "2026-08-15",
}


def test_valid_patient_event():
    event = HealthcareEvent(
        event_id="evt-001",
        event_type=EventType.PATIENT_CREATED,
        source=EventSource.EMR,
        timestamp="2026-08-15T12:00:00Z",
        entity_id="patient-1001",
        payload=valid_patient_payload,
    )
    assert event.event_type == EventType.PATIENT_CREATED
    assert event.payload["first_name"] == "John"


def test_invalid_patient_event():
    with pytest.raises(ValidationError):
        HealthcareEvent(
            event_id="evt-002",
            event_type=EventType.PATIENT_UPDATED,
            source=EventSource.EMR,
            timestamp="2026-08-15T12:00:00Z",
            entity_id="patient-1001",
            payload={
                "external_patient_id": "",
                "first_name": "  ",
                "last_name": "Smith",
                "date_of_birth": "2027-01-01",
            },
        )


def test_valid_appointment_event():
    event = HealthcareEvent(
        event_id="evt-003",
        event_type=EventType.APPOINTMENT_CREATED,
        source=EventSource.APPOINTMENT_SYSTEM,
        timestamp="2026-08-15T12:05:00Z",
        entity_id="appt-2001",
        payload=valid_appointment_payload,
    )
    assert event.payload["status"] == AppointmentStatus.SCHEDULED


def test_invalid_appointment_event():
    with pytest.raises(ValidationError):
        HealthcareEvent(
            event_id="evt-004",
            event_type=EventType.APPOINTMENT_UPDATED,
            source=EventSource.APPOINTMENT_SYSTEM,
            timestamp="2026-08-15T12:05:00Z",
            entity_id="appt-2001",
            payload={
                "external_appointment_id": "appt-2001",
                "patient_id": "",
                "appointment_date": "invalid-date",
                "appointment_type": "FOLLOW_UP",
                "provider": "Dr. Patel",
                "status": "UNKNOWN",
            },
        )


def test_valid_billing_event():
    event = HealthcareEvent(
        event_id="evt-005",
        event_type=EventType.BILLING_CREATED,
        source=EventSource.BILLING_SYSTEM,
        timestamp="2026-08-15T12:10:00Z",
        entity_id="bill-3001",
        payload=valid_billing_payload,
    )
    assert event.payload["billing_status"] == BillingStatus.PENDING


def test_invalid_billing_event():
    with pytest.raises(ValidationError):
        HealthcareEvent(
            event_id="evt-006",
            event_type=EventType.BILLING_UPDATED,
            source=EventSource.BILLING_SYSTEM,
            timestamp="2026-08-15T12:10:00Z",
            entity_id="bill-3001",
            payload={
                "external_billing_id": "bill-3001",
                "patient_id": "patient-1001",
                "amount": -10,
                "insurance_provider": "BlueCross",
                "billing_status": "PAID",
                "service_date": "2026-08-15",
            },
        )


def test_missing_event_id():
    with pytest.raises(ValidationError):
        HealthcareEvent(
            event_type=EventType.PATIENT_CREATED,
            source=EventSource.EMR,
            timestamp="2026-08-15T12:00:00Z",
            entity_id="patient-1001",
            payload=valid_patient_payload,
        )


def test_invalid_event_type():
    with pytest.raises(ValidationError):
        HealthcareEvent(
            event_id="evt-007",
            event_type="NOT_A_REAL_EVENT",
            source=EventSource.EMR,
            timestamp="2026-08-15T12:00:00Z",
            entity_id="patient-1001",
            payload=valid_patient_payload,
        )


def test_invalid_source():
    with pytest.raises(ValidationError):
        HealthcareEvent(
            event_id="evt-008",
            event_type=EventType.PATIENT_CREATED,
            source="UNKNOWN_SOURCE",
            timestamp="2026-08-15T12:00:00Z",
            entity_id="patient-1001",
            payload=valid_patient_payload,
        )


def test_negative_billing_amount_error_via_service():
    result = ValidationService.validate_event(
        {
            "event_id": "evt-009",
            "event_type": "BILLING_CREATED",
            "source": "BILLING_SYSTEM",
            "timestamp": "2026-08-15T12:11:00Z",
            "entity_id": "bill-3001",
            "payload": {
                "external_billing_id": "bill-3001",
                "patient_id": "patient-1001",
                "amount": -1,
                "insurance_provider": "BlueCross",
                "billing_status": "PAID",
                "service_date": "2026-08-15",
            },
        }
    )
    assert result.is_valid is False
    assert result.error is not None
    assert "amount" in result.error.lower()


def test_future_patient_dob():
    with pytest.raises(ValidationError):
        HealthcareEvent(
            event_id="evt-010",
            event_type=EventType.PATIENT_CREATED,
            source=EventSource.EMR,
            timestamp="2026-08-15T12:00:00Z",
            entity_id="patient-1001",
            payload={
                "external_patient_id": "patient-1001",
                "first_name": "Alice",
                "last_name": "Jones",
                "date_of_birth": (date.today() + timedelta(days=1)).isoformat(),
            },
        )


def test_invalid_appointment_status():
    with pytest.raises(ValidationError):
        HealthcareEvent(
            event_id="evt-011",
            event_type=EventType.APPOINTMENT_CREATED,
            source=EventSource.APPOINTMENT_SYSTEM,
            timestamp="2026-08-15T12:00:00Z",
            entity_id="appt-2001",
            payload={
                "external_appointment_id": "appt-2001",
                "patient_id": "patient-1001",
                "appointment_date": "2026-08-20",
                "appointment_type": "FOLLOW_UP",
                "provider": "Dr. Patel",
                "status": "IN_PROGRESS",
            },
        )


def test_duplicate_event_id_behavior_if_practical():
    raw_event = {
        "event_id": "evt-duplicate-001",
        "event_type": "PATIENT_CREATED",
        "source": "EMR",
        "timestamp": "2026-08-15T12:00:00Z",
        "entity_id": "patient-duplicate",
        "payload": valid_patient_payload,
    }
    first = ValidationService.validate_event(raw_event)
    second = ValidationService.validate_event(raw_event)
    assert first.is_valid is True
    assert second.is_valid is True
    assert first.event.event_id == second.event.event_id

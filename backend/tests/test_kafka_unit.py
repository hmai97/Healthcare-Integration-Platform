import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.kafka.producer import KafkaProducerClient, serialize_event
from app.kafka.topics import TOPICS, resolve_topic


def test_patient_event_topic_mapping():
    assert resolve_topic("PATIENT_CREATED") == TOPICS["patients"]
    assert resolve_topic("PATIENT_UPDATED") == TOPICS["patients"]


def test_appointment_event_topic_mapping():
    assert resolve_topic("APPOINTMENT_CREATED") == TOPICS["appointments"]
    assert resolve_topic("APPOINTMENT_UPDATED") == TOPICS["appointments"]


def test_billing_event_topic_mapping():
    assert resolve_topic("BILLING_CREATED") == TOPICS["billing"]
    assert resolve_topic("BILLING_UPDATED") == TOPICS["billing"]


def test_event_serialization():
    event = {
        "event_id": "evt-123",
        "event_type": "PATIENT_CREATED",
        "source": "EMR",
        "timestamp": "2026-08-15T12:00:00Z",
        "entity_id": "patient-1001",
        "payload": {"external_patient_id": "patient-1001", "first_name": "John", "last_name": "Smith"},
    }
    serialized = serialize_event(event)
    payload = json.loads(serialized.decode("utf-8"))
    assert payload["event_id"] == "evt-123"
    assert payload["event_type"] == "PATIENT_CREATED"


def test_event_deserialization_round_trip():
    event = {
        "event_id": "evt-456",
        "event_type": "BILLING_CREATED",
        "source": "BILLING_SYSTEM",
        "timestamp": "2026-08-15T12:00:00Z",
        "entity_id": "bill-3001",
        "payload": {
            "external_billing_id": "bill-3001",
            "patient_id": "patient-1001",
            "amount": 75.5,
            "insurance_provider": "BlueCross",
            "billing_status": "PAID",
            "service_date": "2026-08-15",
        },
    }
    serialized = serialize_event(event)
    assert json.loads(serialized.decode("utf-8"))["event_id"] == "evt-456"


def test_invalid_event_handling_via_consumer(monkeypatch):
    from app.kafka.consumer import HealthcareKafkaConsumer

    consumer = HealthcareKafkaConsumer(bootstrap_servers="localhost:9092", group_id="test-group")
    consumer.producer = SimpleNamespace(publish_deadletter=AsyncMock())

    message = SimpleNamespace(
        topic=TOPICS["billing"],
        value=json.dumps({
            "event_id": "evt-bad",
            "event_type": "BILLING_CREATED",
            "source": "BILLING_SYSTEM",
            "timestamp": "2026-08-15T12:30:00Z",
            "entity_id": "bill-999",
            "payload": {
                "external_billing_id": "bill-999",
                "patient_id": "patient-1001",
                "amount": -5,
                "insurance_provider": "BlueCross",
                "billing_status": "PENDING",
                "service_date": "2026-08-15",
            },
        }).encode("utf-8"),
    )

    asyncio.run(consumer._handle_message(message))
    consumer.producer.publish_deadletter.assert_awaited_once()


def test_deadletter_message_creation():
    from app.kafka.producer import build_deadletter_message

    message = build_deadletter_message({
        "event_id": "evt-789",
        "event_type": "BILLING_CREATED",
        "source": "BILLING_SYSTEM",
        "entity_id": "bill-789",
        "payload": {"amount": -1},
    }, "amount must be greater than or equal to 0")

    assert message["error"] == "amount must be greater than or equal to 0"
    assert message["event"]["event_id"] == "evt-789"


def test_producer_failure_handling():
    client = KafkaProducerClient(bootstrap_servers="localhost:9092")
    client._producer = SimpleNamespace(send_and_wait=AsyncMock(side_effect=RuntimeError("broker unavailable")))

    event = {
        "event_id": "evt-fail",
        "event_type": "PATIENT_CREATED",
        "source": "EMR",
        "timestamp": "2026-08-15T12:00:00Z",
        "entity_id": "patient-1001",
        "payload": {
            "external_patient_id": "patient-1001",
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "1991-05-01",
        },
    }

    with pytest.raises(RuntimeError, match="broker unavailable"):
        asyncio.run(client.publish_event(event))

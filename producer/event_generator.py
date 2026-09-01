"""Event generator for the simulated healthcare data producer."""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from faker import Faker

root_dir = Path(__file__).resolve().parents[1]
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.kafka.config import settings
from app.kafka.producer import KafkaProducerClient

faker = Faker()


def _iso_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_patient_event(invalid: bool = False) -> dict:
    if invalid:
        return {
            "event_id": f"evt-{faker.uuid4()}",
            "event_type": "PATIENT_CREATED",
            "source": "EMR",
            "timestamp": _iso_timestamp(),
            "entity_id": "patient-invalid",
            "payload": {
                "external_patient_id": "",
                "first_name": "",
                "last_name": "",
                "date_of_birth": (date.today() + timedelta(days=365)).isoformat(),
            },
        }

    external_id = f"patient-{faker.random_int(min=1000, max=9999)}"
    return {
        "event_id": f"evt-{faker.uuid4()}",
        "event_type": "PATIENT_CREATED",
        "source": "EMR",
        "timestamp": _iso_timestamp(),
        "entity_id": external_id,
        "payload": {
            "external_patient_id": external_id,
            "first_name": faker.first_name(),
            "last_name": faker.last_name(),
            "date_of_birth": faker.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
        },
    }


def build_appointment_event(invalid: bool = False, patient_id: str | None = None) -> dict:
    if invalid:
        return {
            "event_id": f"evt-{faker.uuid4()}",
            "event_type": "APPOINTMENT_CREATED",
            "source": "APPOINTMENT_SYSTEM",
            "timestamp": _iso_timestamp(),
            "entity_id": "appt-invalid",
            "payload": {
                "external_appointment_id": "",
                "patient_id": patient_id or "patient-1001",
                "appointment_date": "2026-08-15",
                "appointment_type": "FOLLOW_UP",
                "provider": "Dr. Test",
                "status": "INVALID_STATUS",
            },
        }

    external_id = f"appt-{faker.random_int(min=1000, max=9999)}"
    target_patient_id = patient_id or f"patient-{faker.random_int(min=1000, max=9999)}"
    return {
        "event_id": f"evt-{faker.uuid4()}",
        "event_type": "APPOINTMENT_CREATED",
        "source": "APPOINTMENT_SYSTEM",
        "timestamp": _iso_timestamp(),
        "entity_id": external_id,
        "payload": {
            "external_appointment_id": external_id,
            "patient_id": target_patient_id,
            "appointment_date": (date.today() + timedelta(days=3)).isoformat(),
            "appointment_type": random.choice(["FOLLOW_UP", "CONSULTATION", "LAB_REVIEW"]),
            "provider": faker.name(),
            "status": "SCHEDULED",
        },
    }


def build_billing_event(invalid: bool = False, patient_id: str | None = None) -> dict:
    if invalid:
        return {
            "event_id": f"evt-{faker.uuid4()}",
            "event_type": "BILLING_CREATED",
            "source": "BILLING_SYSTEM",
            "timestamp": _iso_timestamp(),
            "entity_id": "bill-invalid",
            "payload": {
                "external_billing_id": "",
                "patient_id": patient_id or "patient-1001",
                "amount": -50,
                "insurance_provider": "TestInsurance",
                "billing_status": "INVALID_STATUS",
                "service_date": "2026-08-15",
            },
        }

    external_id = f"bill-{faker.random_int(min=1000, max=9999)}"
    target_patient_id = patient_id or f"patient-{faker.random_int(min=1000, max=9999)}"
    return {
        "event_id": f"evt-{faker.uuid4()}",
        "event_type": "BILLING_CREATED",
        "source": "BILLING_SYSTEM",
        "timestamp": _iso_timestamp(),
        "entity_id": external_id,
        "payload": {
            "external_billing_id": external_id,
            "patient_id": target_patient_id,
            "amount": round(random.uniform(25, 500), 2),
            "insurance_provider": random.choice(["BlueCross", "Aetna", "Cigna", "Medicare"]),
            "billing_status": "PENDING",
            "service_date": date.today().isoformat(),
        },
    }


def random_event(invalid: bool = False, known_patient_ids: list[str] | None = None) -> dict:
    known_patient_ids = known_patient_ids or []
    if not known_patient_ids:
        return build_patient_event(invalid=invalid)

    event_type = random.choice(["PATIENT_CREATED", "APPOINTMENT_CREATED", "BILLING_CREATED"])
    if event_type == "PATIENT_CREATED":
        return build_patient_event(invalid=invalid)
    if event_type == "APPOINTMENT_CREATED":
        return build_appointment_event(invalid=invalid, patient_id=random.choice(known_patient_ids))
    return build_billing_event(invalid=invalid, patient_id=random.choice(known_patient_ids))


async def generate_events(count: int, interval_seconds: int, invalid_percentage: int) -> None:
    producer = KafkaProducerClient()
    await producer.start()
    known_patient_ids: list[str] = []
    try:
        for index in range(count):
            should_invalidate = random.randint(1, 100) <= invalid_percentage

            if not known_patient_ids or index % 3 == 0:
                event = build_patient_event(invalid=should_invalidate)
                if not should_invalidate:
                    known_patient_ids.append(event["payload"]["external_patient_id"])
            else:
                patient_id = random.choice(known_patient_ids)
                event_type = random.choice(["APPOINTMENT_CREATED", "BILLING_CREATED"])
                if event_type == "APPOINTMENT_CREATED":
                    event = build_appointment_event(invalid=should_invalidate, patient_id=patient_id)
                else:
                    event = build_billing_event(invalid=should_invalidate, patient_id=patient_id)

            await producer.publish_event(event)
            if index < count - 1 and interval_seconds > 0:
                await asyncio.sleep(interval_seconds)
    finally:
        await producer.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate healthcare events to Kafka.")
    parser.add_argument("--count", type=int, default=20, help="Approximate number of events to generate.")
    parser.add_argument("--interval", type=int, default=settings.event_interval_seconds, help="Seconds between published events.")
    parser.add_argument("--invalid-percentage", type=int, default=settings.invalid_event_percentage, help="Percent of events to intentionally invalidate.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    await generate_events(args.count, args.interval, args.invalid_percentage)


if __name__ == "__main__":
    asyncio.run(main())

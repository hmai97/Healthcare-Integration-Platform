from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class KafkaSettings:
    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    group_id: str = os.getenv("KAFKA_GROUP_ID", "healthcare-event-processor")
    patient_topic: str = "healthcare.patient"
    appointment_topic: str = "healthcare.appointment"
    billing_topic: str = "healthcare.billing"
    deadletter_topic: str = "healthcare.deadletter"
    event_interval_seconds: int = int(os.getenv("EVENT_INTERVAL_SECONDS", "2"))
    invalid_event_percentage: int = int(os.getenv("INVALID_EVENT_PERCENTAGE", "5"))


settings = KafkaSettings()

"""Kafka topic names for the healthcare integration platform."""

TOPICS = {
    "patients": "healthcare.patient",
    "appointments": "healthcare.appointment",
    "billing": "healthcare.billing",
    "deadletter": "healthcare.deadletter",
}


def resolve_topic(event_type: str | None) -> str:
    if not event_type:
        return TOPICS["patients"]

    event_name = str(event_type).upper()
    if event_name in {"PATIENT_CREATED", "PATIENT_UPDATED"}:
        return TOPICS["patients"]
    if event_name in {"APPOINTMENT_CREATED", "APPOINTMENT_UPDATED"}:
        return TOPICS["appointments"]
    if event_name in {"BILLING_CREATED", "BILLING_UPDATED"}:
        return TOPICS["billing"]
    return TOPICS["deadletter"]

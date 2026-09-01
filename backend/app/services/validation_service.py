"""Validation service placeholder for later implementation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from pydantic import ValidationError

from app.schemas.event import HealthcareEvent


@dataclass
class ValidationResult:
    is_valid: bool
    event: HealthcareEvent | None = None
    event_id: str | None = None
    event_type: str | None = None
    error: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "error": self.error,
            "details": self.details,
        }


class ValidationService:
    @staticmethod
    def validate_event(raw_event: Mapping[str, Any]) -> ValidationResult:
        event_id = str(raw_event.get("event_id", "")).strip() if raw_event.get("event_id") is not None else ""
        event_type = str(raw_event.get("event_type", "")).strip() if raw_event.get("event_type") is not None else ""

        try:
            event = HealthcareEvent.model_validate(raw_event)
            return ValidationResult(
                is_valid=True,
                event=event,
                event_id=event.event_id,
                event_type=event.event_type.value,
            )
        except ValidationError as exc:
            details = exc.errors(include_url=False)
            message = "; ".join(
                f"{'.'.join(str(part) for part in err.get('loc', [])) or 'value'}: {err.get('msg', 'invalid value')}"
                for err in details
            )
            return ValidationResult(
                is_valid=False,
                event_id=event_id or None,
                event_type=event_type or None,
                error=message,
                details={"validation_errors": details},
            )
        except Exception as exc:  # pragma: no cover - defensive fallback for unexpected validation failures
            return ValidationResult(
                is_valid=False,
                event_id=event_id or None,
                event_type=event_type or None,
                error=str(exc),
                details={"exception": exc.__class__.__name__},
            )


validate_event = ValidationService.validate_event

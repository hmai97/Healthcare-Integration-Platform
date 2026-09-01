"""Event repository placeholder for later implementation."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.event import Event, EventStatus


class EventRepository:
    def create_event(self, db: Session, event_data: Mapping[str, Any]) -> Event:
        event_id = str(event_data.get("event_id", "")).strip()
        if not event_id:
            raise ValueError("event_id is required")

        existing = self.get_by_event_id(db, event_id)
        if existing is not None:
            return existing

        event = Event(
            event_id=event_id,
            event_type=str(event_data.get("event_type", "")).strip(),
            source=str(event_data.get("source", "")).strip(),
            entity_id=str(event_data.get("entity_id", "")).strip(),
            payload=dict(event_data.get("payload", {})),
            status=EventStatus.RECEIVED.value,
            validation_error=None,
            processing_time_ms=None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(event)
        db.flush()
        return event

    def get_by_event_id(self, db: Session, event_id: str) -> Event | None:
        return db.query(Event).filter(Event.event_id == event_id).first()

    def list_events(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 20,
        event_type: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Event], int]:
        query = db.query(Event)
        if event_type:
            query = query.filter(Event.event_type == event_type)
        if status:
            query = query.filter(Event.status == status)

        total = query.count()
        items = query.order_by(Event.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def count_total(self, db: Session) -> int:
        return db.query(Event).count()

    def count_by_status(self, db: Session, status: str) -> int:
        return db.query(Event).filter(Event.status == status).count()

    def count_by_event_type(self, db: Session, event_type: str) -> int:
        return db.query(Event).filter(Event.event_type == event_type).count()

    def get_event_type_counts(self, db: Session) -> list[tuple[str, int]]:
        return db.query(Event.event_type, func.count(Event.id)).group_by(Event.event_type).order_by(func.count(Event.id).desc()).all()

    def get_status_counts(self, db: Session) -> list[tuple[str, int]]:
        return db.query(Event.status, func.count(Event.id)).group_by(Event.status).order_by(func.count(Event.id).desc()).all()

    def get_recent_failures(self, db: Session, *, limit: int = 20) -> list[Event]:
        return (
            db.query(Event)
            .filter(Event.status == EventStatus.FAILED.value)
            .order_by(Event.created_at.desc())
            .limit(limit)
            .all()
        )

    def count_events_last_minute(self, db: Session) -> int:
        since = datetime.now(timezone.utc) - timedelta(minutes=1)
        return db.query(Event).filter(Event.created_at >= since).count()

    def update_status(
        self,
        db: Session,
        event_id: str,
        status: str,
        *,
        validation_error: str | None = None,
        processing_time_ms: int | None = None,
        processed_at: datetime | None = None,
    ) -> Event:
        event = self.get_by_event_id(db, event_id)
        if event is None:
            raise ValueError(f"Event {event_id} not found")

        event.status = status
        if validation_error is not None:
            event.validation_error = validation_error
        elif status != EventStatus.FAILED.value:
            event.validation_error = None

        if processing_time_ms is not None:
            event.processing_time_ms = processing_time_ms

        if status == EventStatus.PROCESSED.value and event.processed_at is None:
            event.processed_at = processed_at or datetime.now(timezone.utc)
        elif status == EventStatus.FAILED.value and event.processed_at is None:
            event.processed_at = processed_at or datetime.now(timezone.utc)

        db.add(event)
        db.flush()
        return event

    def mark_failed(self, db: Session, event_id: str, error: str) -> Event:
        return self.update_status(db, event_id, EventStatus.FAILED.value, validation_error=error)

    def mark_processed(self, db: Session, event_id: str, processing_time_ms: int | None = None) -> Event:
        return self.update_status(db, event_id, EventStatus.PROCESSED.value, processing_time_ms=processing_time_ms)

"""Monitoring service placeholder for later implementation."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.event_repository import EventRepository
from app.schemas.event import EventRead, EventTypeCountResponse, MonitoringSummaryResponse, StatusCountResponse


class MonitoringService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = EventRepository()

    @staticmethod
    def build_summary(*, total_events: int, processed_events: int, failed_events: int, events_last_minute: int) -> MonitoringSummaryResponse:
        if total_events == 0:
            processing_rate = 0.0
        else:
            processing_rate = round((processed_events / total_events) * 100, 2)

        return MonitoringSummaryResponse(
            total_events=total_events,
            processed_events=processed_events,
            failed_events=failed_events,
            processing_rate=processing_rate,
            events_last_minute=events_last_minute,
        )

    def get_summary(self) -> MonitoringSummaryResponse:
        total_events = self.repository.count_total(self.db)
        processed_events = self.repository.count_by_status(self.db, "PROCESSED")
        failed_events = self.repository.count_by_status(self.db, "FAILED")
        events_last_minute = self.repository.count_events_last_minute(self.db)
        return self.build_summary(
            total_events=total_events,
            processed_events=processed_events,
            failed_events=failed_events,
            events_last_minute=events_last_minute,
        )

    def get_event_type_counts(self) -> list[EventTypeCountResponse]:
        rows = self.repository.get_event_type_counts(self.db)
        return [EventTypeCountResponse(event_type=event_type, count=count) for event_type, count in rows]

    def get_status_counts(self) -> list[StatusCountResponse]:
        rows = self.repository.get_status_counts(self.db)
        return [StatusCountResponse(status=status, count=count) for status, count in rows]

    def get_recent_failures(self, limit: int = 20) -> list[EventRead]:
        limit = max(min(limit, 100), 1)
        failures = self.repository.get_recent_failures(self.db, limit=limit)
        return [EventRead.model_validate(event) for event in failures]

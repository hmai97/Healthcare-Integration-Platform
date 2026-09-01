from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.event_repository import EventRepository
from app.schemas.event import EventRead, PaginatedEventResponse


class EventService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = EventRepository()

    def list_events(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        event_type: str | None = None,
        status: str | None = None,
    ) -> PaginatedEventResponse:
        page = max(page, 1)
        page_size = max(min(page_size, 100), 1)

        items, total = self.repository.list_events(
            self.db,
            page=page,
            page_size=page_size,
            event_type=event_type,
            status=status,
        )
        total_pages = (total + page_size - 1) // page_size if total else 0

        return PaginatedEventResponse(
            items=[EventRead.model_validate(item) for item in items],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    def get_event(self, event_id: str) -> EventRead | None:
        event = self.repository.get_by_event_id(self.db, event_id)
        if event is None:
            return None
        return EventRead.model_validate(event)

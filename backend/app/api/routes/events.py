"""Event API routes will be implemented in a later phase."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.event import EventRead, PaginatedEventResponse
from app.services.event_service import EventService

router = APIRouter(prefix="/api/events", tags=["events"])


def get_event_service(db: Session = Depends(get_db)) -> EventService:
    return EventService(db)


@router.get("", response_model=PaginatedEventResponse)
def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    event_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    service: EventService = Depends(get_event_service),
) -> PaginatedEventResponse:
    return service.list_events(page=page, page_size=page_size, event_type=event_type, status=status)


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: str, service: EventService = Depends(get_event_service)) -> EventRead:
    event = service.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    return event

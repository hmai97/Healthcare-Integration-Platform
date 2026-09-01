"""Monitoring API routes will be implemented in a later phase."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.event import EventRead, EventTypeCountResponse, MonitoringSummaryResponse, StatusCountResponse
from app.services.monitoring_service import MonitoringService

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


def get_monitoring_service(db: Session = Depends(get_db)) -> MonitoringService:
    return MonitoringService(db)


@router.get("/summary", response_model=MonitoringSummaryResponse)
def get_monitoring_summary(service: MonitoringService = Depends(get_monitoring_service)) -> MonitoringSummaryResponse:
    return service.get_summary()


@router.get("/event-types", response_model=list[EventTypeCountResponse])
def get_event_type_counts(service: MonitoringService = Depends(get_monitoring_service)) -> list[EventTypeCountResponse]:
    return service.get_event_type_counts()


@router.get("/status", response_model=list[StatusCountResponse])
def get_status_counts(service: MonitoringService = Depends(get_monitoring_service)) -> list[StatusCountResponse]:
    return service.get_status_counts()


@router.get("/recent-failures", response_model=list[EventRead])
def get_recent_failures(
    limit: int = Query(20, ge=1, le=100),
    service: MonitoringService = Depends(get_monitoring_service),
) -> list[EventRead]:
    return service.get_recent_failures(limit=limit)

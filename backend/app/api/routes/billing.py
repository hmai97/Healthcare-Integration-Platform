"""Billing API routes will be implemented in a later phase."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.billing import BillingRead
from app.services.data_service import BillingService

router = APIRouter(prefix="/api/billing", tags=["billing"])


def get_billing_service(db: Session = Depends(get_db)) -> BillingService:
    return BillingService(db)


@router.get("", response_model=list[BillingRead])
def list_billing(
    limit: int = Query(100, ge=1, le=500),
    service: BillingService = Depends(get_billing_service),
) -> list[BillingRead]:
    return service.list_billing(limit=limit)

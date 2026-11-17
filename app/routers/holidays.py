from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_manager
from app.clients.holiday_client import (
    HolidayClient,
    HolidayServiceError,
    get_holiday_client,
)
from app.clock import get_today
from app.db import get_db
from app.models import Employee, Holiday
from app.schemas import HolidayOut, HolidaySyncOut

router = APIRouter(tags=["holidays"])


@router.get("/holidays", response_model=list[HolidayOut])
def list_holidays(
    year: int | None = Query(default=None, ge=2000, le=2100),
    _: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
    today: date = Depends(get_today),
):
    year = year or today.year
    return db.scalars(
        select(Holiday)
        .where(extract("year", Holiday.holiday_date) == year)
        .order_by(Holiday.holiday_date)
    ).all()


@router.post("/holidays/sync", response_model=HolidaySyncOut)
def sync_holidays(
    year: int | None = Query(default=None, ge=2000, le=2100),
    _: Employee = Depends(require_manager),
    db: Session = Depends(get_db),
    today: date = Depends(get_today),
    client: HolidayClient = Depends(get_holiday_client),
):
    year = year or today.year
    try:
        fetched = client.fetch_holidays(year)
    except HolidayServiceError:
        raise HTTPException(status_code=502, detail="holiday service unavailable")

    existing = set(
        db.scalars(
            select(Holiday.holiday_date).where(
                extract("year", Holiday.holiday_date) == year
            )
        )
    )
    added = 0
    for holiday_date, name in fetched:
        if holiday_date not in existing:
            db.add(Holiday(holiday_date=holiday_date, name=name))
            existing.add(holiday_date)
            added += 1
    db.commit()
    return HolidaySyncOut(year=year, fetched=len(fetched), added=added)
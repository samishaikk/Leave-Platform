from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.auth import require_manager
from app.clock import get_today
from app.db import get_db
from app.models import Employee
from app.queries import reports
from app.schemas import (
    CalendarEntryOut,
    MonthlyAttendanceOut,
    OverlapOut,
    TeamBalanceOut,
)

router = APIRouter(prefix="/reports", tags=["reports"])

MAX_CALENDAR_DAYS = 62


@router.get("/team-balances", response_model=list[TeamBalanceOut])
def team_balances_report(
    year: int | None = Query(default=None, ge=2000, le=2100),
    manager: Employee = Depends(require_manager),
    db: Session = Depends(get_db),
    today: date = Depends(get_today),
):
    return reports.team_balances(db, manager.id, year or today.year)


@router.get("/team-overlaps", response_model=list[OverlapOut])
def team_overlaps_report(
    manager: Employee = Depends(require_manager), db: Session = Depends(get_db)
):
    return reports.team_overlaps(db, manager.id)


@router.get("/team-calendar", response_model=list[CalendarEntryOut])
def team_calendar_report(
    start: date,
    end: date,
    manager: Employee = Depends(require_manager),
    db: Session = Depends(get_db),
):
    if end < start:
        raise HTTPException(status_code=422, detail="end date is before start date")
    if (end - start).days > MAX_CALENDAR_DAYS:
        raise HTTPException(
            status_code=422,
            detail=f"range cannot be longer than {MAX_CALENDAR_DAYS} days",
        )
    return reports.team_calendar(db, manager.id, start, end)


@router.get("/monthly-attendance", response_model=list[MonthlyAttendanceOut])
def monthly_attendance_report(
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    manager: Employee = Depends(require_manager),
    db: Session = Depends(get_db),
    today: date = Depends(get_today),
):
    return reports.monthly_attendance(
        db, manager.id, year or today.year, month or today.month
    )
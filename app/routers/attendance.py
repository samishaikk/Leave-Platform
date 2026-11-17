from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.clock import get_now, get_today
from app.db import get_db
from app.models import Attendance, Employee, LeaveRequest, LeaveStatus
from app.schemas import AttendanceOut

router = APIRouter(tags=["attendance"])


def serialize_attendance(row: Attendance) -> AttendanceOut:
    hours = None
    if row.check_out is not None:
        hours = round((row.check_out - row.check_in).total_seconds() / 3600, 2)
    return AttendanceOut(
        id=row.id,
        employee_id=row.employee_id,
        work_date=row.work_date,
        check_in=row.check_in,
        check_out=row.check_out,
        hours_worked=hours,
    )


@router.post("/attendance/check-in", response_model=AttendanceOut, status_code=201)
def check_in(
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
    today: date = Depends(get_today),
    now: datetime = Depends(get_now),
):
    on_leave = db.scalar(
        select(LeaveRequest.id)
        .where(
            LeaveRequest.employee_id == user.id,
            LeaveRequest.status == LeaveStatus.approved,
            LeaveRequest.start_date <= today,
            LeaveRequest.end_date >= today,
        )
        .limit(1)
    )
    if on_leave is not None:
        raise HTTPException(status_code=409, detail="you are on approved leave today")

    record = Attendance(employee_id=user.id, work_date=today, check_in=now)
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        # the unique (employee, day) constraint stops a second check-in
        db.rollback()
        raise HTTPException(status_code=409, detail="you have already checked in today")
    db.refresh(record)
    return serialize_attendance(record)


@router.post("/attendance/check-out", response_model=AttendanceOut)
def check_out(
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
    today: date = Depends(get_today),
    now: datetime = Depends(get_now),
):
    record = db.scalar(
        select(Attendance).where(
            Attendance.employee_id == user.id, Attendance.work_date == today
        )
    )
    if record is None:
        raise HTTPException(status_code=409, detail="you have not checked in today")

    result = db.execute(
        update(Attendance)
        .where(Attendance.id == record.id, Attendance.check_out.is_(None))
        .values(check_out=now)
    )
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=409, detail="you have already checked out today")
    db.commit()
    db.refresh(record)
    return serialize_attendance(record)


@router.get("/attendance/mine", response_model=list[AttendanceOut])
def my_attendance(
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
    today: date = Depends(get_today),
):
    year = year or today.year
    month = month or today.month
    first_day = date(year, month, 1)
    next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    rows = db.scalars(
        select(Attendance)
        .where(
            Attendance.employee_id == user.id,
            Attendance.work_date >= first_day,
            Attendance.work_date < next_month,
        )
        .order_by(Attendance.work_date)
    ).all()
    return [serialize_attendance(row) for row in rows]
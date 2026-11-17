from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.clock import get_today
from app.db import get_db
from app.models import (
    AuditLog,
    Employee,
    Holiday,
    LeaveRequest,
    LeaveStatus,
    LeaveType,
)
from app.schemas import (
    BalanceOut,
    LeaveRequestCreate,
    LeaveRequestOut,
    LeaveTypeOut,
)
from app.services.balance import days_by_status, remaining_balance
from app.services.policies import LeaveContext, PolicyError, get_policy
from app.services.working_days import count_working_days

router = APIRouter(tags=["leave"])


def serialize(leave_request: LeaveRequest) -> LeaveRequestOut:
    return LeaveRequestOut(
        id=leave_request.id,
        employee_id=leave_request.employee_id,
        employee_name=leave_request.employee.name,
        leave_type=leave_request.leave_type.name,
        start_date=leave_request.start_date,
        end_date=leave_request.end_date,
        days=leave_request.days,
        reason=leave_request.reason,
        status=leave_request.status,
        decided_by=leave_request.decided_by,
        decided_at=leave_request.decided_at,
        decision_comment=leave_request.decision_comment,
        created_at=leave_request.created_at,
    )


@router.get("/leave-types", response_model=list[LeaveTypeOut])
def list_leave_types(
    _: Employee = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.scalars(select(LeaveType).order_by(LeaveType.id)).all()


@router.post("/leave-requests", response_model=LeaveRequestOut, status_code=201)
def apply_for_leave(
    payload: LeaveRequestCreate,
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
    today: date = Depends(get_today),
):
    leave_type = db.get(LeaveType, payload.leave_type_id)
    if leave_type is None:
        raise HTTPException(status_code=404, detail="leave type not found")

    holidays = set(
        db.scalars(
            select(Holiday.holiday_date).where(
                Holiday.holiday_date.between(payload.start_date, payload.end_date)
            )
        )
    )
    working_days = count_working_days(payload.start_date, payload.end_date, holidays)

    context = LeaveContext(
        start_date=payload.start_date,
        end_date=payload.end_date,
        working_days=working_days,
        today=today,
        remaining_balance=remaining_balance(
            db, user.id, leave_type, payload.start_date.year
        ),
    )
    try:
        get_policy(leave_type.name).validate(context)
    except PolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    overlapping = db.scalar(
        select(LeaveRequest.id)
        .where(
            LeaveRequest.employee_id == user.id,
            LeaveRequest.status.in_([LeaveStatus.pending, LeaveStatus.approved]),
            LeaveRequest.start_date <= payload.end_date,
            LeaveRequest.end_date >= payload.start_date,
        )
        .limit(1)
    )
    if overlapping is not None:
        raise HTTPException(
            status_code=409, detail="you already have a leave request on these dates"
        )

    leave_request = LeaveRequest(
        employee_id=user.id,
        leave_type_id=leave_type.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        days=working_days,
        reason=payload.reason,
        status=LeaveStatus.pending,
    )
    db.add(leave_request)
    db.flush()  # gives the new request its id before we write the audit row
    db.add(
        AuditLog(
            actor_id=user.id,
            action="leave_requested",
            entity_type="leave_request",
            entity_id=leave_request.id,
            old_status=None,
            new_status=LeaveStatus.pending.value,
            comment=payload.reason,
        )
    )
    db.commit()
    db.refresh(leave_request)
    return serialize(leave_request)


@router.get("/leave-requests/mine", response_model=list[LeaveRequestOut])
def my_leave_requests(
    user: Employee = Depends(get_current_user), db: Session = Depends(get_db)
):
    rows = db.scalars(
        select(LeaveRequest)
        .options(
            joinedload(LeaveRequest.employee), joinedload(LeaveRequest.leave_type)
        )
        .where(LeaveRequest.employee_id == user.id)
        .order_by(LeaveRequest.start_date.desc(), LeaveRequest.id.desc())
    ).all()
    return [serialize(row) for row in rows]


@router.get("/leave-balance", response_model=list[BalanceOut])
def leave_balance(
    year: int | None = None,
    user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
    today: date = Depends(get_today),
):
    year = year or today.year
    totals = days_by_status(db, user.id, year)
    result = []
    for leave_type in db.scalars(select(LeaveType).order_by(LeaveType.id)):
        approved = totals.get((leave_type.id, LeaveStatus.approved), 0)
        pending = totals.get((leave_type.id, LeaveStatus.pending), 0)
        remaining = (
            None
            if leave_type.annual_quota is None
            else leave_type.annual_quota - approved - pending
        )
        result.append(
            BalanceOut(
                leave_type=leave_type.name,
                annual_quota=leave_type.annual_quota,
                approved_days=approved,
                pending_days=pending,
                remaining_days=remaining,
            )
        )
    return result
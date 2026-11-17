from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.models import LeaveRequest, LeaveStatus, LeaveType


def days_by_status(
    db: Session, employee_id: int, year: int
) -> dict[tuple[int, LeaveStatus], int]:
    """Pending and approved working days, keyed by (leave_type_id, status)."""
    rows = db.execute(
        select(
            LeaveRequest.leave_type_id,
            LeaveRequest.status,
            func.sum(LeaveRequest.days),
        )
        .where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_([LeaveStatus.pending, LeaveStatus.approved]),
            extract("year", LeaveRequest.start_date) == year,
        )
        .group_by(LeaveRequest.leave_type_id, LeaveRequest.status)
    ).all()
    return {(type_id, status): int(total) for type_id, status, total in rows}


def remaining_balance(
    db: Session, employee_id: int, leave_type: LeaveType, year: int
) -> int | None:
    """Days left for this leave type this year. None means unlimited."""
    if leave_type.annual_quota is None:
        return None
    totals = days_by_status(db, employee_id, year)
    used = totals.get((leave_type.id, LeaveStatus.pending), 0) + totals.get(
        (leave_type.id, LeaveStatus.approved), 0
    )
    return leave_type.annual_quota - used
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from itertools import count

import bcrypt

from app.models import (
    Attendance,
    Employee,
    Holiday,
    LeaveRequest,
    LeaveStatus,
    LeaveType,
    Role,
)

_counter = count(1)


@lru_cache(maxsize=None)
def _fast_hash(password: str) -> str:
    """Cheap bcrypt hash (4 rounds) so tests stay fast. Test data only."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=4)).decode()


# Factories commit (not just flush) so that a rollback inside the app code
# cannot undo the data a test set up.
def make_employee(
    db, name="Test User", role=Role.employee, manager=None, password=None, email=None
):
    n = next(_counter)
    employee = Employee(
        name=name,
        email=email or f"user{n}@example.com",
        password_hash=_fast_hash(password) if password else "not-a-real-hash",
        role=role,
        manager_id=manager.id if manager else None,
    )
    db.add(employee)
    db.commit()
    return employee


def make_leave_types(db) -> dict[str, LeaveType]:
    types = {}
    for name, quota in [("Annual", 18), ("Sick", 10), ("Unpaid", None)]:
        leave_type = LeaveType(name=name, annual_quota=quota)
        db.add(leave_type)
        types[name] = leave_type
    db.commit()
    return types


def make_leave_request(
    db,
    employee,
    leave_type,
    start,
    end,
    days=1,
    status=LeaveStatus.pending,
    reason=None,
):
    leave_request = LeaveRequest(
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        start_date=start,
        end_date=end,
        days=days,
        status=status,
        reason=reason,
    )
    db.add(leave_request)
    db.commit()
    return leave_request


def make_attendance(db, employee, work_date: date, hours: float | None = 8):
    check_in = datetime(
        work_date.year, work_date.month, work_date.day, 9, 0, tzinfo=timezone.utc
    )
    record = Attendance(
        employee_id=employee.id,
        work_date=work_date,
        check_in=check_in,
        check_out=None if hours is None else check_in + timedelta(hours=hours),
    )
    db.add(record)
    db.commit()
    return record


def make_holiday(db, holiday_date: date, name="Test Holiday"):
    holiday = Holiday(holiday_date=holiday_date, name=name)
    db.add(holiday)
    db.commit()
    return holiday
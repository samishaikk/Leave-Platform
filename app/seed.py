from datetime import date
from sqlalchemy import select
from app.db import SessionLocal
from app.init_db import init_db
from app.models import Employee, Holiday, LeaveType, Role
from app.security import hash_password

DEMO_PASSWORD = "Password123!"  # demo data only

LEAVE_TYPES = [
    ("Annual", 18),
    ("Sick", 10),
    ("Unpaid", None),  # None = unlimited
]

HOLIDAYS = [
    (date(2026, 12, 25), "Christmas Day"),
    (date(2027, 1, 1), "New Year's Day"),
    (date(2027, 1, 26), "Republic Day"),
    (date(2027, 3, 29), "Holi"),
    (date(2027, 8, 15), "Independence Day"),
]


PEOPLE = [
    ("Meera Rao", "meera@example.com", Role.manager, None),
    ("Suresh Nair", "suresh@example.com", Role.manager, None),
    ("Ravi Kumar", "ravi@example.com", Role.employee, "meera@example.com"),
    ("Anita Sharma", "anita@example.com", Role.employee, "meera@example.com"),
    ("Karan Mehta", "karan@example.com", Role.employee, "meera@example.com"),
    ("Divya Iyer", "divya@example.com", Role.employee, "suresh@example.com"),
]


def seed() -> dict:
    init_db()
    added = {"leave_types": 0, "holidays": 0, "employees": 0}
    db = SessionLocal()
    try:
        for name, quota in LEAVE_TYPES:
            exists = db.scalar(select(LeaveType).where(LeaveType.name == name))
            if exists is None:
                db.add(LeaveType(name=name, annual_quota=quota))
                added["leave_types"] += 1

        for holiday_date, holiday_name in HOLIDAYS:
            exists = db.scalar(select(Holiday).where(Holiday.holiday_date == holiday_date))
            if exists is None:
                db.add(Holiday(holiday_date=holiday_date, name=holiday_name))
                added["holidays"] += 1

        db.flush()

        by_email: dict[str, Employee] = {}
        for name, email, role, manager_email in PEOPLE:
            employee = db.scalar(select(Employee).where(Employee.email == email))
            if employee is None:
                manager_id = by_email[manager_email].id if manager_email else None
                employee = Employee(
                    name=name,
                    email=email,
                    password_hash=hash_password(DEMO_PASSWORD),
                    role=role,
                    manager_id=manager_id,
                )
                db.add(employee)
                db.flush()
                added["employees"] += 1
            by_email[email] = employee

        db.commit()
    finally:
        db.close()
    return added


if __name__ == "__main__":
    print("added:", seed())
from datetime import date
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.orm import Session

SQL_DIR = Path(__file__).parent


def _run(db: Session, name: str, params: dict) -> list[dict]:
    sql = text((SQL_DIR / f"{name}.sql").read_text(encoding="utf-8"))
    return [dict(row) for row in db.execute(sql, params).mappings().all()]


def team_balances(db: Session, manager_id: int, year: int) -> list[dict]:
    return _run(db, "team_balances", {"manager_id": manager_id, "year": year})


def team_overlaps(db: Session, manager_id: int) -> list[dict]:
    return _run(db, "team_overlaps", {"manager_id": manager_id})


def team_calendar(
    db: Session, manager_id: int, range_start: date, range_end: date
) -> list[dict]:
    return _run(
        db,
        "team_calendar",
        {"manager_id": manager_id, "range_start": range_start, "range_end": range_end},
    )


def monthly_attendance(
    db: Session, manager_id: int, year: int, month: int
) -> list[dict]:
    first_day = date(year, month, 1)
    next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return _run(
        db,
        "monthly_attendance",
        {"manager_id": manager_id, "first_day": first_day, "next_month": next_month},
    )
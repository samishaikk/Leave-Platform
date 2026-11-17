from datetime import date
from types import SimpleNamespace

import pytest
from app.models import LeaveStatus, Role
from app.queries import reports
from tests.factories import (
    make_attendance,
    make_employee,
    make_holiday,
    make_leave_request,
    make_leave_types,
)


@pytest.fixture()
def team(db):
    manager = make_employee(db, "Meera", Role.manager)
    other_manager = make_employee(db, "Suresh", Role.manager)
    return SimpleNamespace(
        manager=manager,
        ravi=make_employee(db, "Ravi", manager=manager),
        anita=make_employee(db, "Anita", manager=manager),
        karan=make_employee(db, "Karan", manager=manager),
        outsider=make_employee(db, "Divya", manager=other_manager),
        types=make_leave_types(db),
    )


def test_team_balances_count_only_open_leave_of_that_year(db, team):
    annual, sick = team.types["Annual"], team.types["Sick"]
    approved, pending, rejected = (
        LeaveStatus.approved,
        LeaveStatus.pending,
        LeaveStatus.rejected,
    )
    make_leave_request(db, team.ravi, annual, date(2026, 3, 2), date(2026, 3, 4), 3, approved)
    make_leave_request(db, team.ravi, annual, date(2026, 4, 6), date(2026, 4, 7), 2, pending)
    make_leave_request(db, team.ravi, annual, date(2026, 5, 4), date(2026, 5, 8), 5, rejected)
    make_leave_request(db, team.ravi, annual, date(2025, 12, 1), date(2025, 12, 4), 4, approved)
    make_leave_request(db, team.ravi, sick, date(2026, 2, 9), date(2026, 2, 9), 1, approved)
    make_leave_request(db, team.outsider, annual, date(2026, 3, 2), date(2026, 3, 4), 3, approved)

    rows = reports.team_balances(db, team.manager.id, 2026)
    by_key = {(row["employee_name"], row["leave_type"]): row for row in rows}

    assert len(rows) == 9  # 3 team members x 3 leave types, the other team is excluded
    ravi_annual = by_key[("Ravi", "Annual")]
    assert (
        ravi_annual["annual_quota"],
        ravi_annual["approved_days"],
        ravi_annual["pending_days"],
        ravi_annual["remaining_days"],
    ) == (18, 3, 2, 13)
    ravi_sick = by_key[("Ravi", "Sick")]
    assert (ravi_sick["approved_days"], ravi_sick["remaining_days"]) == (1, 9)
    ravi_unpaid = by_key[("Ravi", "Unpaid")]
    assert ravi_unpaid["annual_quota"] is None
    assert ravi_unpaid["remaining_days"] is None
    assert by_key[("Anita", "Annual")]["remaining_days"] == 18
    assert ("Divya", "Annual") not in by_key


def test_team_overlaps_only_between_teammates_with_open_requests(db, team):
    annual = team.types["Annual"]
    approved, pending, rejected = (
        LeaveStatus.approved,
        LeaveStatus.pending,
        LeaveStatus.rejected,
    )
    make_leave_request(db, team.ravi, annual, date(2026, 6, 1), date(2026, 6, 5), 5, approved)
    # same person overlapping himself must not be reported
    make_leave_request(db, team.ravi, annual, date(2026, 6, 2), date(2026, 6, 3), 2, pending)
    make_leave_request(db, team.anita, annual, date(2026, 6, 4), date(2026, 6, 10), 5, pending)
   
    make_leave_request(db, team.karan, annual, date(2026, 6, 3), date(2026, 6, 4), 2, rejected)

    make_leave_request(db, team.karan, annual, date(2026, 6, 22), date(2026, 6, 23), 2, approved)
    # other team is ignored
    make_leave_request(db, team.outsider, annual, date(2026, 6, 1), date(2026, 6, 5), 5, approved)

    rows = reports.team_overlaps(db, team.manager.id)

    assert len(rows) == 1
    row = rows[0]
    assert {row["employee_a"], row["employee_b"]} == {"Ravi", "Anita"}
    assert row["overlap_start"] == date(2026, 6, 4)
    assert row["overlap_end"] == date(2026, 6, 5)


def test_team_calendar_skips_weekends_holidays_and_unapproved_leave(db, team):
    annual = team.types["Annual"]
   
    make_leave_request(
        db, team.ravi, annual, date(2026, 6, 4), date(2026, 6, 9), 3, LeaveStatus.approved
    )
    make_holiday(db, date(2026, 6, 8), "Test Holiday")
    make_leave_request(
        db, team.anita, annual, date(2026, 6, 4), date(2026, 6, 9), 3, LeaveStatus.pending
    )
    make_leave_request(
        db, team.outsider, annual, date(2026, 6, 4), date(2026, 6, 9), 3, LeaveStatus.approved
    )

    rows = reports.team_calendar(db, team.manager.id, date(2026, 6, 1), date(2026, 6, 30))

    assert [(row["day"], row["employee_name"]) for row in rows] == [
        (date(2026, 6, 4), "Ravi"),
        (date(2026, 6, 5), "Ravi"),
        (date(2026, 6, 9), "Ravi"),
    ]


def test_monthly_attendance_summary_and_ranking(db, team):
    for work_date, hours in [
        (date(2026, 6, 1), 8),
        (date(2026, 6, 2), 8),
        (date(2026, 6, 3), 6),
    ]:
        make_attendance(db, team.ravi, work_date, hours)
    make_attendance(db, team.ravi, date(2026, 5, 29), 8)  
    make_attendance(db, team.ravi, date(2026, 6, 4), None)  
    make_attendance(db, team.anita, date(2026, 6, 1), 9)
    make_attendance(db, team.anita, date(2026, 6, 2), 9)
    make_attendance(db, team.outsider, date(2026, 6, 1), 10)  

    rows = reports.monthly_attendance(db, team.manager.id, 2026, 6)

    assert [row["employee_name"] for row in rows] == ["Ravi", "Anita", "Karan"]
    ravi, anita, karan = rows

    assert ravi["days_present"] == 3
    assert float(ravi["total_hours"]) == pytest.approx(22.0)
    assert float(ravi["avg_hours_per_day"]) == pytest.approx(7.33)
    assert ravi["hours_rank"] == 1

    assert anita["days_present"] == 2
    assert float(anita["total_hours"]) == pytest.approx(18.0)
    assert anita["hours_rank"] == 2

    assert karan["days_present"] == 0
    assert float(karan["total_hours"]) == 0
    assert karan["avg_hours_per_day"] is None
    assert karan["hours_rank"] == 3
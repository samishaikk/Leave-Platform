from datetime import date
import pytest
from app.models import LeaveStatus
from tests.factories import make_holiday, make_leave_request
from tests.helpers import apply


def test_apply_for_leave_happy_path(client, world, auth):
    response = apply(
        client, auth(world.ravi), world.types["Annual"], "2026-11-25", "2026-11-27", "trip"
    )
    assert response.status_code == 201
    body = response.json()
    assert body["employee_name"] == "Ravi"
    assert body["leave_type"] == "Annual"
    assert body["days"] == 3
    assert body["status"] == "pending"


def test_apply_requires_login(client, world):
    response = client.post(
        "/leave-requests",
        json={"leave_type_id": 1, "start_date": "2026-11-25", "end_date": "2026-11-27"},
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "type_name, start, end, expected_text",
    [
        ("Annual", "2026-11-19", "2026-11-19", "cannot start before 2026-11-21"),
        ("Sick", "2026-11-02", "2026-11-03", "cannot start before 2026-11-11"),
        ("Unpaid", "2026-11-10", "2026-11-10", "cannot start before 2026-11-18"),
        ("Annual", "2026-11-28", "2026-11-29", "no working days"),
    ],
)
def test_policy_violations_are_422(
    client, world, auth, type_name, start, end, expected_text
):
    response = apply(client, auth(world.ravi), world.types[type_name], start, end)
    assert response.status_code == 422
    assert expected_text in response.json()["detail"]


@pytest.mark.parametrize(
    "start, end",
    [("2026-12-02", "2026-12-01"), ("2026-12-30", "2027-01-04")],
)
def test_invalid_date_ranges_are_422(client, world, auth, start, end):
    response = apply(client, auth(world.ravi), world.types["Annual"], start, end)
    assert response.status_code == 422


def test_unknown_leave_type_is_404(client, world, auth):
    response = client.post(
        "/leave-requests",
        json={"leave_type_id": 9999, "start_date": "2026-11-25", "end_date": "2026-11-26"},
        headers=auth(world.ravi),
    )
    assert response.status_code == 404


def test_holidays_are_not_counted_as_working_days(client, db, world, auth):
    make_holiday(db, date(2026, 12, 25), "Christmas Day")
   
    response = apply(
        client, auth(world.ravi), world.types["Annual"], "2026-12-24", "2026-12-28"
    )
    assert response.status_code == 201
    assert response.json()["days"] == 2


def test_overlapping_request_is_409(client, world, auth):
    first = apply(client, auth(world.ravi), world.types["Annual"], "2026-11-25", "2026-11-27")
    assert first.status_code == 201
    second = apply(client, auth(world.ravi), world.types["Annual"], "2026-11-26", "2026-11-28")
    assert second.status_code == 409


def test_rejected_request_does_not_block_the_same_dates(client, db, world, auth):
    make_leave_request(
        db, world.ravi, world.types["Annual"],
        date(2026, 11, 25), date(2026, 11, 27), 3, LeaveStatus.rejected,
    )
    response = apply(client, auth(world.ravi), world.types["Annual"], "2026-11-25", "2026-11-27")
    assert response.status_code == 201


def test_pending_days_reserve_balance(client, db, world, auth):
    annual = world.types["Annual"]
    make_leave_request(
        db, world.ravi, annual, date(2026, 12, 1), date(2026, 12, 14), 10, LeaveStatus.approved
    )
    make_leave_request(
        db, world.ravi, annual, date(2026, 12, 15), date(2026, 12, 24), 8, LeaveStatus.pending
    )

    # 10 approved + 8 pending = the whole quota of 18
    response = apply(client, auth(world.ravi), annual, "2026-12-28", "2026-12-31")
    assert response.status_code == 422
    assert "not enough Annual leave balance" in response.json()["detail"]


def test_balance_endpoint_reports_approved_pending_and_remaining(client, db, world, auth):
    annual = world.types["Annual"]
    make_leave_request(
        db, world.ravi, annual, date(2026, 12, 1), date(2026, 12, 14), 10, LeaveStatus.approved
    )
    make_leave_request(
        db, world.ravi, annual, date(2026, 12, 15), date(2026, 12, 24), 8, LeaveStatus.pending
    )

    response = client.get("/leave-balance", headers=auth(world.ravi))
    assert response.status_code == 200
    rows = {row["leave_type"]: row for row in response.json()}
    assert rows["Annual"]["approved_days"] == 10
    assert rows["Annual"]["pending_days"] == 8
    assert rows["Annual"]["remaining_days"] == 0
    assert rows["Unpaid"]["remaining_days"] is None


def test_mine_returns_only_my_requests(client, db, world, auth):
    annual = world.types["Annual"]
    make_leave_request(db, world.ravi, annual, date(2026, 12, 1), date(2026, 12, 2), 2)
    make_leave_request(db, world.anita, annual, date(2026, 12, 8), date(2026, 12, 9), 2)

    response = client.get("/leave-requests/mine", headers=auth(world.ravi))
    assert response.status_code == 200
    assert [row["employee_name"] for row in response.json()] == ["Ravi"]


def test_leave_types_are_listed(client, world, auth):
    response = client.get("/leave-types", headers=auth(world.ravi))
    assert response.status_code == 200
    assert [row["name"] for row in response.json()] == ["Annual", "Sick", "Unpaid"]
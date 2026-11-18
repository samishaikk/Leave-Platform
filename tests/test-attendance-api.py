from datetime import date, timedelta
import pytest
from app.models import LeaveStatus
from tests.factories import make_leave_request


def test_check_in_then_check_out_records_hours(client, clock, world, auth):
    headers = auth(world.ravi)
    check_in = client.post("/attendance/check-in", headers=headers)
    assert check_in.status_code == 201
    assert check_in.json()["check_out"] is None

    clock.now += timedelta(hours=8)
    check_out = client.post("/attendance/check-out", headers=headers)
    assert check_out.status_code == 200
    assert check_out.json()["hours_worked"] == 8.0


def test_second_check_in_is_409(client, world, auth):
    headers = auth(world.ravi)
    assert client.post("/attendance/check-in", headers=headers).status_code == 201
    assert client.post("/attendance/check-in", headers=headers).status_code == 409


def test_check_out_without_check_in_is_409(client, world, auth):
    assert client.post("/attendance/check-out", headers=auth(world.ravi)).status_code == 409


def test_second_check_out_is_409(client, clock, world, auth):
    headers = auth(world.ravi)
    client.post("/attendance/check-in", headers=headers)
    clock.now += timedelta(hours=1)
    assert client.post("/attendance/check-out", headers=headers).status_code == 200
    assert client.post("/attendance/check-out", headers=headers).status_code == 409


def test_cannot_check_in_on_approved_leave(client, db, world, auth):
    make_leave_request(
        db, world.ravi, world.types["Annual"],
        date(2026, 11, 18), date(2026, 11, 18), 1, LeaveStatus.approved,
    )
    response = client.post("/attendance/check-in", headers=auth(world.ravi))
    assert response.status_code == 409
    assert "approved leave" in response.json()["detail"]


def test_pending_leave_does_not_block_check_in(client, db, world, auth):
    make_leave_request(
        db, world.ravi, world.types["Annual"],
        date(2026, 11, 18), date(2026, 11, 18), 1, LeaveStatus.pending,
    )
    assert client.post("/attendance/check-in", headers=auth(world.ravi)).status_code == 201


def test_my_attendance_lists_the_month(client, world, auth):
    headers = auth(world.ravi)
    client.post("/attendance/check-in", headers=headers)

    this_month = client.get("/attendance/mine", headers=headers)
    assert [row["work_date"] for row in this_month.json()] == ["2026-11-18"]

    other_month = client.get("/attendance/mine?year=2026&month=10", headers=headers)
    assert other_month.json() == []


@pytest.mark.parametrize("query", ["month=13", "month=0", "year=1999"])
def test_my_attendance_validates_the_month_and_year(client, world, auth, query):
    response = client.get(f"/attendance/mine?{query}", headers=auth(world.ravi))
    assert response.status_code == 422
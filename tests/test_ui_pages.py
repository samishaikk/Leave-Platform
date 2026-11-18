from datetime import date
import pytest
from app.models import LeaveStatus
from tests.factories import make_leave_request
from tests.helpers import PASSWORD


def ui_login(client, employee):
    response = client.post(
        "/login",
        data={"email": employee.email, "password": PASSWORD},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return response


def test_dashboard_redirects_to_login_when_logged_out(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "Log in" in response.text


def test_wrong_password_shows_an_error(client, world):
    response = client.post(
        "/login", data={"email": world.ravi.email, "password": "nope"}
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.text


def test_login_sets_a_cookie_and_redirects(client, world):
    response = ui_login(client, world.ravi)
    assert response.headers["location"] == "/"
    assert client.cookies.get("access_token")


def test_dashboard_shows_name_and_balances(client, world):
    ui_login(client, world.ravi)
    page = client.get("/")
    assert page.status_code == 200
    assert "Hello, Ravi" in page.text
    assert "Annual" in page.text and "Sick" in page.text


def test_apply_through_the_form(client, world):
    ui_login(client, world.ravi)
    response = client.post(
        "/leave",
        data={
            "leave_type_id": world.types["Annual"].id,
            "start_date": "2026-11-25",
            "end_date": "2026-11-27",
            "reason": "trip",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "submitted (3 working days)" in response.text
    assert "pending" in response.text


def test_form_shows_policy_errors(client, world):
    ui_login(client, world.ravi)
    response = client.post(
        "/leave",
        data={
            "leave_type_id": world.types["Annual"].id,
            "start_date": "2026-11-19",
            "end_date": "2026-11-19",
            "reason": "",
        },
        follow_redirects=True,
    )
    assert "cannot start before 2026-11-21" in response.text


def test_employee_is_sent_away_from_approvals(client, world):
    ui_login(client, world.ravi)
    response = client.get("/approvals", follow_redirects=True)
    assert "Manager access only" in response.text


def test_manager_approvals_flow(client, db, world):
    pending = make_leave_request(
        db, world.ravi, world.types["Annual"], date(2026, 11, 25), date(2026, 11, 27), 3
    )
    ui_login(client, world.manager)

    page = client.get("/approvals")
    assert page.status_code == 200
    assert "Ravi" in page.text

    no_comment = client.post(
        f"/approvals/{pending.id}",
        data={"decision": "rejected", "comment": ""},
        follow_redirects=True,
    )
    assert "a comment is required when rejecting" in no_comment.text

    approved = client.post(
        f"/approvals/{pending.id}",
        data={"decision": "approved", "comment": ""},
        follow_redirects=True,
    )
    assert f"Request #{pending.id} approved" in approved.text

    db.refresh(pending)
    assert pending.status == LeaveStatus.approved


def test_logout_clears_the_session(client, world):
    ui_login(client, world.ravi)
    client.post("/logout", follow_redirects=False)
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
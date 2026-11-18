from datetime import date
import pytest
from sqlalchemy import select

from app.models import AuditLog, LeaveStatus
from tests.factories import make_leave_request
from tests.helpers import decide


@pytest.fixture()
def pending(db, world):
    """A pending Annual request from Ravi."""
    return make_leave_request(
        db, world.ravi, world.types["Annual"], date(2026, 11, 25), date(2026, 11, 27), 3
    )


def test_employee_cannot_decide(client, world, auth, pending):
    response = decide(client, auth(world.ravi), pending.id, "approved")
    assert response.status_code == 403


def test_employee_cannot_list_team_requests(client, world, auth):
    assert client.get("/leave-requests/team", headers=auth(world.ravi)).status_code == 403


def test_manager_can_approve_and_it_is_audited(client, db, world, auth, pending):
    response = decide(client, auth(world.manager), pending.id, "approved")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["decided_by"] == world.manager.id
    assert body["decided_at"] is not None

    audit = db.scalars(
        select(AuditLog).where(
            AuditLog.entity_id == pending.id, AuditLog.action == "leave_approved"
        )
    ).all()
    assert len(audit) == 1
    assert (audit[0].old_status, audit[0].new_status) == ("pending", "approved")
    assert audit[0].actor_id == world.manager.id


def test_rejecting_needs_a_comment(client, world, auth, pending):
    response = decide(client, auth(world.manager), pending.id, "rejected")
    assert response.status_code == 422


def test_reject_with_comment_is_saved(client, world, auth, pending):
    response = decide(client, auth(world.manager), pending.id, "rejected", "team is short")
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["decision_comment"] == "team is short"


@pytest.mark.regression
def test_second_decision_is_409_and_changes_nothing(client, db, world, auth, pending):
    first = decide(client, auth(world.manager), pending.id, "approved")
    assert first.status_code == 200

    second = decide(client, auth(world.manager), pending.id, "rejected", "changed my mind")
    assert second.status_code == 409

    db.refresh(pending)
    assert pending.status == LeaveStatus.approved
    audit = db.scalars(select(AuditLog).where(AuditLog.entity_id == pending.id)).all()
    assert [row.action for row in audit] == ["leave_approved"]


def test_other_teams_manager_gets_404(client, world, auth, pending):
    response = decide(client, auth(world.other_manager), pending.id, "approved")
    assert response.status_code == 404


def test_unknown_request_is_404(client, world, auth):
    assert decide(client, auth(world.manager), 99999, "approved").status_code == 404


def test_manager_cannot_decide_their_own_request(client, db, world, auth):
    own = make_leave_request(
        db, world.manager, world.types["Annual"], date(2026, 12, 1), date(2026, 12, 2), 2
    )
    response = decide(client, auth(world.manager), own.id, "approved")
    assert response.status_code == 404


def test_team_list_only_shows_direct_reports_and_can_filter(client, db, world, auth):
    annual = world.types["Annual"]
    make_leave_request(db, world.ravi, annual, date(2026, 12, 1), date(2026, 12, 2), 2)
    make_leave_request(
        db, world.anita, annual, date(2026, 12, 8), date(2026, 12, 9), 2, LeaveStatus.approved
    )
    make_leave_request(db, world.outsider, annual, date(2026, 12, 1), date(2026, 12, 2), 2)

    everything = client.get("/leave-requests/team", headers=auth(world.manager))
    assert {row["employee_name"] for row in everything.json()} == {"Ravi", "Anita"}

    only_pending = client.get(
        "/leave-requests/team?status=pending", headers=auth(world.manager)
    )
    assert [row["employee_name"] for row in only_pending.json()] == ["Ravi"]


def test_decisions_need_login(client, pending):
    response = client.post(
        f"/leave-requests/{pending.id}/decision", json={"decision": "approved"}
    )
    assert response.status_code == 401
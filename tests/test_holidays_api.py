from datetime import date
from app.clients.holiday_client import HolidayServiceError, get_holiday_client
from app.main import app as fastapi_app
from tests.helpers import apply


class FakeHolidayClient:
    def __init__(self, items=None, fail=False):
        self.items = items or []
        self.fail = fail

    def fetch_holidays(self, year):
        if self.fail:
            raise HolidayServiceError("service down")
        return [item for item in self.items if item[0].year == year]


def use_fake(fake):
    fastapi_app.dependency_overrides[get_holiday_client] = lambda: fake


def test_sync_adds_new_holidays_and_is_idempotent(client, world, auth):
    use_fake(
        FakeHolidayClient(
            [(date(2027, 2, 1), "Founders Day"), (date(2027, 2, 2), "Rest Day")]
        )
    )
    headers = auth(world.manager)

    first = client.post("/holidays/sync?year=2027", headers=headers)
    assert first.json() == {"year": 2027, "fetched": 2, "added": 2}

    second = client.post("/holidays/sync?year=2027", headers=headers)
    assert second.json() == {"year": 2027, "fetched": 2, "added": 0}

    listed = client.get("/holidays?year=2027", headers=headers)
    assert [row["name"] for row in listed.json()] == ["Founders Day", "Rest Day"]


def test_sync_reports_502_when_the_service_is_down(client, world, auth):
    use_fake(FakeHolidayClient(fail=True))
    response = client.post("/holidays/sync?year=2027", headers=auth(world.manager))
    assert response.status_code == 502
    assert response.json()["detail"] == "holiday service unavailable"


def test_employee_cannot_sync(client, world, auth):
    use_fake(FakeHolidayClient())
    assert client.post("/holidays/sync", headers=auth(world.ravi)).status_code == 403


def test_synced_holiday_changes_the_working_day_count(client, world, auth):
    use_fake(FakeHolidayClient([(date(2026, 12, 25), "Christmas Day")]))
    client.post("/holidays/sync?year=2026", headers=auth(world.manager))

    
    response = apply(
        client, auth(world.ravi), world.types["Annual"], "2026-12-24", "2026-12-28"
    )
    assert response.status_code == 201
    assert response.json()["days"] == 2
import pytest
REPORT_URLS = [
    "/reports/team-balances",
    "/reports/team-overlaps",
    "/reports/team-calendar?start=2026-11-01&end=2026-11-30",
    "/reports/monthly-attendance",
]


@pytest.mark.parametrize("url", REPORT_URLS)
def test_employees_cannot_read_reports(client, world, auth, url):
    assert client.get(url, headers=auth(world.ravi)).status_code == 403


@pytest.mark.parametrize("url", REPORT_URLS)
def test_reports_need_login(client, url):
    assert client.get(url).status_code == 401


def test_team_balances_cover_only_the_managers_team(client, world, auth):
    response = client.get("/reports/team-balances", headers=auth(world.manager))
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 9  
    assert {row["employee_name"] for row in rows} == {"Ravi", "Anita", "Karan"}


def test_monthly_attendance_lists_the_whole_team(client, world, auth):
    response = client.get("/reports/monthly-attendance", headers=auth(world.manager))
    assert response.status_code == 200
    assert {row["employee_name"] for row in response.json()} == {"Ravi", "Anita", "Karan"}


@pytest.mark.parametrize(
    "url",
    [
        "/reports/team-calendar?start=2026-11-30&end=2026-11-01",
        "/reports/team-calendar?start=2026-01-01&end=2026-12-31",
        "/reports/monthly-attendance?month=13",
        "/reports/team-balances?year=1999",
    ],
)
def test_report_parameters_are_validated(client, world, auth, url):
    assert client.get(url, headers=auth(world.manager)).status_code == 422


def test_team_calendar_accepts_a_normal_range(client, world, auth):
    response = client.get(
        "/reports/team-calendar?start=2026-11-01&end=2026-11-30",
        headers=auth(world.manager),
    )
    assert response.status_code == 200
    assert response.json() == []
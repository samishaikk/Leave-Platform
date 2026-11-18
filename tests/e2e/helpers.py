from datetime import date, timedelta
from tests.e2e.pages import LoginPage
from tests.helpers import PASSWORD



def next_weekday(days_ahead: int) -> date:
    """First Monday-Friday on or after today + days_ahead (the app uses the real clock)."""
    day = date.today() + timedelta(days=days_ahead)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


def login_as(page, employee) -> None:
    LoginPage(page).open().login(employee.email, PASSWORD)
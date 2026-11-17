import os
from datetime import date

import httpx

# Used when no HOLIDAY_API_URL is set (simulated calendar for local use).
SAMPLE_HOLIDAYS: list[tuple[date, str]] = [
    (date(2026, 12, 25), "Christmas Day"),
    (date(2027, 1, 1), "New Year's Day"),
    (date(2027, 1, 26), "Republic Day"),
    (date(2027, 8, 15), "Independence Day"),
    (date(2027, 10, 2), "Gandhi Jayanti"),
]


class HolidayServiceError(Exception):
    """Raised when the holiday service cannot be reached or returns bad data."""


class HolidayClient:
    """Fetches public holidays for a year.

    With a base URL it calls GET {base_url}/{year}, expecting JSON like
    [{"date": "2027-01-26", "name": "Republic Day"}]. Without one it returns
    the built-in sample calendar.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 5.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url if base_url is not None else os.getenv("HOLIDAY_API_URL")
        self.timeout = timeout
        self.transport = transport

    def fetch_holidays(self, year: int) -> list[tuple[date, str]]:
        if not self.base_url:
            return [item for item in SAMPLE_HOLIDAYS if item[0].year == year]

        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                response = client.get(f"{self.base_url.rstrip('/')}/{year}")
                response.raise_for_status()
                items = response.json()
            return [(date.fromisoformat(item["date"]), item["name"]) for item in items]
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise HolidayServiceError(f"could not fetch holidays for {year}") from exc


def get_holiday_client() -> HolidayClient:
    return HolidayClient()
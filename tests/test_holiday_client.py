from datetime import date
import httpx
import pytest

from app.clients.holiday_client import HolidayClient, HolidayServiceError


def make_client(handler):
    return HolidayClient(
        base_url="http://holidays.test/api",
        transport=httpx.MockTransport(handler),
    )


def test_fetch_parses_the_response():
    def handler(request):
        assert request.url.path == "/api/2027"
        return httpx.Response(200, json=[{"date": "2027-01-26", "name": "Republic Day"}])

    result = make_client(handler).fetch_holidays(2027)
    assert result == [(date(2027, 1, 26), "Republic Day")]


def test_server_error_becomes_holiday_service_error():
    client = make_client(lambda request: httpx.Response(500))
    with pytest.raises(HolidayServiceError):
        client.fetch_holidays(2027)


def test_bad_payload_becomes_holiday_service_error():
    client = make_client(lambda request: httpx.Response(200, json=[{"when": "tomorrow"}]))
    with pytest.raises(HolidayServiceError):
        client.fetch_holidays(2027)


def test_timeout_becomes_holiday_service_error():
    def handler(request):
        raise httpx.ConnectTimeout("too slow")

    with pytest.raises(HolidayServiceError):
        make_client(handler).fetch_holidays(2027)


def test_without_a_url_the_built_in_calendar_is_used(monkeypatch):
    monkeypatch.delenv("HOLIDAY_API_URL", raising=False)
    result = HolidayClient().fetch_holidays(2027)
    assert (date(2027, 1, 26), "Republic Day") in result
    assert all(holiday_date.year == 2027 for holiday_date, _ in result)
from datetime import date

import pytest

from app.services.working_days import count_working_days

# 2026-11-16 is a Monday
MON = date(2026, 11, 16)
WED = date(2026, 11, 18)
FRI = date(2026, 11, 20)
SAT = date(2026, 11, 21)
SUN = date(2026, 11, 22)
NEXT_MON = date(2026, 11, 23)


@pytest.mark.parametrize(
    "start, end, holidays, expected",
    [
        (MON, FRI, set(), 5),  # full working week
        (MON, MON, set(), 1),  # single day
        (FRI, NEXT_MON, set(), 2),  # Friday + Monday, weekend skipped
        (SAT, SUN, set(), 0),  # weekend only
        (MON, FRI, {WED}, 4),  # holiday on a working day
        (MON, SUN, {SAT}, 5),  # holiday on a weekend is not subtracted twice
    ],
)
def test_count_working_days(start, end, holidays, expected):
    assert count_working_days(start, end, holidays) == expected


def test_end_before_start_raises():
    with pytest.raises(ValueError):
        count_working_days(FRI, MON, set())
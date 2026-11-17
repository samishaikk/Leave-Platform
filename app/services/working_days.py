from datetime import date, timedelta


def count_working_days(start: date, end: date, holidays: set[date]) -> int:
    """Count Monday-Friday days from start to end (both included), skipping holidays."""
    if end < start:
        raise ValueError("end date is before start date")

    days = 0
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in holidays:
            days += 1
        current += timedelta(days=1)
    return days
from datetime import date

import pytest

from app.services.policies import (
    AnnualPolicy,
    LeaveContext,
    PolicyError,
    SickPolicy,
    UnpaidPolicy,
    get_policy,
)

TODAY = date(2026, 11, 18)


def make_ctx(start, end, days, balance=10):
    return LeaveContext(
        start_date=start,
        end_date=end,
        working_days=days,
        today=TODAY,
        remaining_balance=balance,
    )


#  Annual 
def test_annual_valid_request_passes():
    ctx = make_ctx(date(2026, 11, 25), date(2026, 11, 27), 3)
    AnnualPolicy().validate(ctx)  # no error


def test_annual_needs_three_days_notice():
    ctx = make_ctx(date(2026, 11, 19), date(2026, 11, 19), 1)
    with pytest.raises(PolicyError, match="cannot start before 2026-11-21"):
        AnnualPolicy().validate(ctx)


def test_annual_cannot_exceed_balance():
    ctx = make_ctx(date(2026, 11, 25), date(2026, 12, 1), 5, balance=3)
    with pytest.raises(PolicyError, match="not enough Annual leave balance"):
        AnnualPolicy().validate(ctx)


def test_annual_max_ten_days_per_request():
    ctx = make_ctx(date(2026, 12, 1), date(2026, 12, 16), 11, balance=18)
    with pytest.raises(PolicyError, match="at most 10"):
        AnnualPolicy().validate(ctx)


#  Sick 
def test_sick_can_be_backdated_within_seven_days():
    ctx = make_ctx(date(2026, 11, 16), date(2026, 11, 17), 2)
    SickPolicy().validate(ctx)  


def test_sick_cannot_be_backdated_too_far():
    ctx = make_ctx(date(2026, 11, 1), date(2026, 11, 2), 1)
    with pytest.raises(PolicyError, match="cannot start before 2026-11-11"):
        SickPolicy().validate(ctx)


def test_sick_max_five_days_per_request():
    ctx = make_ctx(date(2026, 11, 16), date(2026, 11, 23), 6)
    with pytest.raises(PolicyError, match="at most 5"):
        SickPolicy().validate(ctx)


#  Unpaid 
def test_unpaid_ignores_balance():
    ctx = make_ctx(date(2026, 11, 23), date(2026, 11, 27), 5, balance=0)
    UnpaidPolicy().validate(ctx)  


def test_unpaid_cannot_start_in_the_past():
    ctx = make_ctx(date(2026, 11, 10), date(2026, 11, 11), 2, balance=None)
    with pytest.raises(PolicyError, match="cannot start before 2026-11-18"):
        UnpaidPolicy().validate(ctx)


# rules shared by all types ----------
@pytest.mark.parametrize("policy", [AnnualPolicy(), SickPolicy(), UnpaidPolicy()])
def test_dates_with_no_working_days_are_rejected(policy):
    ctx = make_ctx(date(2026, 11, 28), date(2026, 11, 29), 0)  # Sat + Sun
    with pytest.raises(PolicyError, match="no working days"):
        policy.validate(ctx)


@pytest.mark.parametrize("policy", [AnnualPolicy(), SickPolicy(), UnpaidPolicy()])
def test_end_before_start_is_rejected(policy):
    ctx = make_ctx(date(2026, 12, 2), date(2026, 12, 1), 1)
    with pytest.raises(PolicyError, match="end date is before start date"):
        policy.validate(ctx)


#  lookup 
def test_get_policy_returns_the_right_class():
    assert isinstance(get_policy("Annual"), AnnualPolicy)
    assert isinstance(get_policy("Sick"), SickPolicy)
    assert isinstance(get_policy("Unpaid"), UnpaidPolicy)


def test_get_policy_unknown_type_raises():
    with pytest.raises(PolicyError, match="unknown leave type"):
        get_policy("Sabbatical")
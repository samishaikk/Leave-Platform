from dataclasses import dataclass
from datetime import date, timedelta


class PolicyError(Exception):
    """Raised when a leave request breaks a rule."""


@dataclass
class LeaveContext:
    start_date: date
    end_date: date
    working_days: int
    today: date
    remaining_balance: int | None  # None means unlimited


class LeavePolicy:
    """Base rules. Each leave type overrides the settings below."""

    name = "base"
    earliest_start_offset_days = 0  
    max_working_days = 10
    uses_balance = True

    def validate(self, ctx: LeaveContext) -> None:
        if ctx.end_date < ctx.start_date:
            raise PolicyError("end date is before start date")

        earliest = ctx.today + timedelta(days=self.earliest_start_offset_days)
        if ctx.start_date < earliest:
            raise PolicyError(
                f"{self.name} leave cannot start before {earliest.isoformat()}"
            )

        if ctx.working_days < 1:
            raise PolicyError("the selected dates contain no working days")

        if ctx.working_days > self.max_working_days:
            raise PolicyError(
                f"{self.name} leave allows at most {self.max_working_days} "
                "working days per request"
            )

        if (
            self.uses_balance
            and ctx.remaining_balance is not None
            and ctx.working_days > ctx.remaining_balance
        ):
            raise PolicyError(
                f"not enough {self.name} leave balance "
                f"(remaining: {ctx.remaining_balance})"
            )


class AnnualPolicy(LeavePolicy):
    name = "Annual"
    earliest_start_offset_days = 3  # needs 3 days notice
    max_working_days = 10


class SickPolicy(LeavePolicy):
    name = "Sick"
    earliest_start_offset_days = -7  
    max_working_days = 5


class UnpaidPolicy(LeavePolicy):
    name = "Unpaid"
    earliest_start_offset_days = 0
    max_working_days = 30
    uses_balance = False


POLICIES: dict[str, LeavePolicy] = {
    policy.name: policy for policy in (AnnualPolicy(), SickPolicy(), UnpaidPolicy())
}


def get_policy(leave_type_name: str) -> LeavePolicy:
    try:
        return POLICIES[leave_type_name]
    except KeyError:
        raise PolicyError(f"unknown leave type: {leave_type_name}")
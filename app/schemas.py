from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import LeaveStatus, Role


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: Role
    manager_id: int | None


class LeaveTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    annual_quota: int | None


class LeaveRequestCreate(BaseModel):
    leave_type_id: int
    start_date: date
    end_date: date
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def check_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end date is before start date")
        if self.start_date.year != self.end_date.year:
            raise ValueError(
                "a request cannot span two calendar years; split it into two requests"
            )
        return self


class LeaveRequestOut(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    leave_type: str
    start_date: date
    end_date: date
    days: int
    reason: str | None
    status: LeaveStatus
    decided_by: int | None
    decided_at: datetime | None
    decision_comment: str | None
    created_at: datetime


class BalanceOut(BaseModel):
    leave_type: str
    annual_quota: int | None
    approved_days: int
    pending_days: int
    remaining_days: int | None


class LeaveDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    comment: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def comment_required_on_reject(self):
        if self.decision == "rejected" and not (self.comment and self.comment.strip()):
            raise ValueError("a comment is required when rejecting")
        return self


class AttendanceOut(BaseModel):
    id: int
    employee_id: int
    work_date: date
    check_in: datetime
    check_out: datetime | None
    hours_worked: float | None


class HolidayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    holiday_date: date
    name: str


class HolidaySyncOut(BaseModel):
    year: int
    fetched: int
    added: int
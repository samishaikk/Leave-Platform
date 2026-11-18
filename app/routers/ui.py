from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import get_today
from app.db import get_db
from app.models import Employee, LeaveStatus, LeaveType, Role
from app.routers.approvals import decide_leave_request, team_leave_requests
from app.routers.leave import apply_for_leave, leave_balance, my_leave_requests
from app.schemas import LeaveDecision, LeaveRequestCreate
from app.security import (
    ACCESS_TOKEN_MINUTES,
    create_access_token,
    decode_access_token,
    verify_password,
)

router = APIRouter(include_in_schema=False)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

COOKIE_NAME = "access_token"


def get_ui_user(request: Request, db: Session = Depends(get_db)) -> Employee | None:
    """Like get_current_user, but reads the cookie and returns None instead of 401."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    employee_id = decode_access_token(token)
    if employee_id is None:
        return None
    employee = db.get(Employee, employee_id)
    if employee is not None:
        request.state.user_id = employee.id
        request.state.user_role = employee.role.value
    return employee


def redirect(path: str, msg: str | None = None, error: str | None = None):
    params = {}
    if msg:
        params["msg"] = msg
    if error:
        params["error"] = error
    url = f"{path}?{urlencode(params)}" if params else path
    return RedirectResponse(url, status_code=303)


def validation_message(exc: ValidationError) -> str:
    return exc.errors()[0]["msg"].removeprefix("Value error, ")


# login / logout 
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: Employee | None = Depends(get_ui_user)):
    if user is not None:
        return redirect("/")
    return templates.TemplateResponse(request, "login.html", {})


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    employee = db.scalar(select(Employee).where(Employee.email == email))
    if employee is None or not verify_password(password, employee.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Incorrect email or password"},
            status_code=401,
        )
    response = redirect("/")
    response.set_cookie(
        COOKIE_NAME,
        create_access_token(employee.id),
        httponly=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_MINUTES * 60,
    )
    return response


@router.post("/logout")
def logout():
    response = redirect("/login")
    response.delete_cookie(COOKIE_NAME)
    return response


#  dashboard 
@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    msg: str | None = None,
    error: str | None = None,
    user: Employee | None = Depends(get_ui_user),
    db: Session = Depends(get_db),
    today: date = Depends(get_today),
):
    if user is None:
        return redirect("/login")
    context = {
        "user": user,
        "today": today,
        "msg": msg,
        "error": error,
        "balances": leave_balance(year=None, user=user, db=db, today=today),
        "requests": my_leave_requests(user=user, db=db),
        "leave_types": db.scalars(select(LeaveType).order_by(LeaveType.id)).all(),
    }
    return templates.TemplateResponse(request, "dashboard.html", context)


@router.post("/leave")
def submit_leave(
    leave_type_id: int = Form(...),
    start_date: date = Form(...),
    end_date: date = Form(...),
    reason: str = Form(""),
    user: Employee | None = Depends(get_ui_user),
    db: Session = Depends(get_db),
    today: date = Depends(get_today),
):
    if user is None:
        return redirect("/login")
    try:
        payload = LeaveRequestCreate(
            leave_type_id=leave_type_id,
            start_date=start_date,
            end_date=end_date,
            reason=reason.strip() or None,
        )
        created = apply_for_leave(payload, user, db, today)
    except ValidationError as exc:
        return redirect("/", error=validation_message(exc))
    except HTTPException as exc:
        return redirect("/", error=str(exc.detail))
    return redirect(
        "/", msg=f"Leave request #{created.id} submitted ({created.days} working days)"
    )


#  manager approvals 
@router.get("/approvals", response_class=HTMLResponse)
def approvals_page(
    request: Request,
    msg: str | None = None,
    error: str | None = None,
    user: Employee | None = Depends(get_ui_user),
    db: Session = Depends(get_db),
):
    if user is None:
        return redirect("/login")
    if user.role != Role.manager:
        return redirect("/", error="Manager access only")
    context = {
        "user": user,
        "msg": msg,
        "error": error,
        "requests": team_leave_requests(
            status=LeaveStatus.pending, manager=user, db=db
        ),
    }
    return templates.TemplateResponse(request, "approvals.html", context)


@router.post("/approvals/{request_id}")
def submit_decision(
    request_id: int,
    decision: str = Form(...),
    comment: str = Form(""),
    user: Employee | None = Depends(get_ui_user),
    db: Session = Depends(get_db),
):
    if user is None:
        return redirect("/login")
    if user.role != Role.manager:
        return redirect("/", error="Manager access only")
    try:
        payload = LeaveDecision(decision=decision, comment=comment.strip() or None)
        decided = decide_leave_request(request_id, payload, user, db)
    except ValidationError as exc:
        return redirect("/approvals", error=validation_message(exc))
    except HTTPException as exc:
        return redirect("/approvals", error=str(exc.detail))
    return redirect("/approvals", msg=f"Request #{decided.id} {decided.status.value}")
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from app.auth import require_manager
from app.db import get_db
from app.models import AuditLog, Employee, LeaveRequest, LeaveStatus
from app.routers.leave import serialize
from app.schemas import LeaveDecision, LeaveRequestOut

router = APIRouter(tags=["approvals"])


def get_team_request_or_404(
    db: Session, manager: Employee, request_id: int
) -> LeaveRequest:
    """Only requests from the manager's direct reports are visible."""
    leave_request = db.scalar(
        select(LeaveRequest)
        .join(Employee, LeaveRequest.employee_id == Employee.id)
        .where(LeaveRequest.id == request_id, Employee.manager_id == manager.id)
    )
    if leave_request is None:
        raise HTTPException(status_code=404, detail="leave request not found")
    return leave_request


@router.get("/leave-requests/team", response_model=list[LeaveRequestOut])
def team_leave_requests(
    status: LeaveStatus | None = None,
    manager: Employee = Depends(require_manager),
    db: Session = Depends(get_db),
):
    query = (
        select(LeaveRequest)
        .join(Employee, LeaveRequest.employee_id == Employee.id)
        .options(
            joinedload(LeaveRequest.employee), joinedload(LeaveRequest.leave_type)
        )
        .where(Employee.manager_id == manager.id)
        .order_by(LeaveRequest.created_at, LeaveRequest.id)
    )
    if status is not None:
        query = query.where(LeaveRequest.status == status)
    return [serialize(row) for row in db.scalars(query).all()]


@router.post("/leave-requests/{request_id}/decision", response_model=LeaveRequestOut)
def decide_leave_request(
    request_id: int,
    payload: LeaveDecision,
    manager: Employee = Depends(require_manager),
    db: Session = Depends(get_db),
):
    leave_request = get_team_request_or_404(db, manager, request_id)
    new_status = LeaveStatus(payload.decision)

    # One atomic statement: it only changes the row if it is still pending.
    result = db.execute(
        update(LeaveRequest)
        .where(
            LeaveRequest.id == request_id,
            LeaveRequest.status == LeaveStatus.pending,
        )
        .values(
            status=new_status,
            decided_by=manager.id,
            decided_at=func.now(),
            decision_comment=payload.comment,
        )
    )
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="this request has already been decided"
        )

    db.add(
        AuditLog(
            actor_id=manager.id,
            action=f"leave_{payload.decision}",
            entity_type="leave_request",
            entity_id=request_id,
            old_status=LeaveStatus.pending.value,
            new_status=new_status.value,
            comment=payload.comment,
        )
    )
    db.commit()
    db.refresh(leave_request)
    return serialize(leave_request)
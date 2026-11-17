from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Employee, Role
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Employee:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    employee_id = decode_access_token(token)
    if employee_id is None:
        raise credentials_error

    employee = db.get(Employee, employee_id)
    if employee is None:
        raise credentials_error

    # saved so request logging can record who made the call
    request.state.user_id = employee.id
    request.state.user_role = employee.role.value
    return employee


def require_manager(user: Employee = Depends(get_current_user)) -> Employee:
    if user.role != Role.manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="manager role required"
        )
    return user
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.db import get_db
from app.routers import approvals, attendance, auth, holidays, leave, reports, ui

app = FastAPI(title="Leave & Attendance Platform")

app.include_router(auth.router)
app.include_router(leave.router)
app.include_router(approvals.router)
app.include_router(attendance.router)
app.include_router(holidays.router)
app.include_router(reports.router)
app.include_router(ui.router)


@app.get("/health")
def health():
    """Liveness: the process is up."""
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    """Readiness: the app can reach its database."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ready"}
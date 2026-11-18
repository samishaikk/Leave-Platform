from fastapi import FastAPI

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
    return {"status": "ok"}
from fastapi import FastAPI

from app.routers import approvals, auth, leave

app = FastAPI(title="Leave & Attendance Platform")

app.include_router(auth.router)
app.include_router(leave.router)
app.include_router(approvals.router)


@app.get("/health")
def health():
    return {"status": "ok"}
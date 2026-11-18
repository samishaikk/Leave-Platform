import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app import models  # noqa: F401  (registers the tables)
from app.db import Base
from app.models import Role
from tests.conftest import TEST_DATABASE_URL
from tests.factories import make_employee, make_leave_types
from tests.helpers import PASSWORD

ROOT = Path(__file__).resolve().parents[2]
E2E_DB_NAME = "leave_e2e_db"

_test_url = make_url(TEST_DATABASE_URL)
ADMIN_URL = _test_url.set(database="postgres")
E2E_URL = _test_url.set(database=E2E_DB_NAME)


def _ensure_database() -> None:
    admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": E2E_DB_NAME},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{E2E_DB_NAME}"'))
    admin.dispose()


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def e2e_engine():
    _ensure_database()
    engine = create_engine(E2E_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def live_server(e2e_engine):
    """Runs the real app (uvicorn) against the E2E database on a free port."""
    port = _free_port()
    env = {
        **os.environ,
        "DATABASE_URL": E2E_URL.render_as_string(hide_password=False),
    }
    process = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning",
        ],
        cwd=ROOT,
        env=env,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError("the test server stopped during startup")
            try:
                if httpx.get(f"{base}/health", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.5)
        else:
            raise RuntimeError("the test server did not start in time")
        yield base
    finally:
        process.terminate()
        process.wait(timeout=10)


@pytest.fixture(scope="session")
def base_url(live_server):
    """Overrides pytest-playwright's base_url so page.goto('/login') works."""
    return live_server


@pytest.fixture()
def seeded(e2e_engine):
    """Wipe the E2E database and add Meera (manager) with Ravi and Anita."""
    with e2e_engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE audit_log, attendance, leave_requests, holidays, "
                "leave_types, employees RESTART IDENTITY CASCADE"
            )
        )
    with Session(e2e_engine, expire_on_commit=False) as session:
        manager = make_employee(
            session, "Meera", Role.manager, password=PASSWORD, email="meera@e2e.test"
        )
        yield SimpleNamespace(
            db=session,
            manager=manager,
            ravi=make_employee(
                session, "Ravi", manager=manager, password=PASSWORD, email="ravi@e2e.test"
            ),
            anita=make_employee(
                session, "Anita", manager=manager, password=PASSWORD, email="anita@e2e.test"
            ),
            types=make_leave_types(session),
        )
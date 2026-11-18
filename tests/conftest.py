import os
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models  # noqa: F401  (registers the tables)
from app.clock import get_now, get_today
from app.db import Base, get_db
from app.main import app as fastapi_app
from app.models import Role
from tests.factories import make_employee, make_leave_types
from tests.helpers import PASSWORD, login_headers

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://leave_user:leave_pass@localhost:5434/leave_test_db",
)


@pytest.fixture(scope="session")
def engine():
    test_engine = create_engine(TEST_DATABASE_URL)
    
    if "test" not in (test_engine.url.database or ""):
        raise RuntimeError("TEST_DATABASE_URL must point at a test database")
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture()
def db(engine):
    """Every test runs inside a transaction that is rolled back afterwards."""
    connection = engine.connect()
    outer = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    yield session
    session.close()
    outer.rollback()
    connection.close()


class FakeClock:
    """Tests control time. Default is Wednesday 2026-11-18, 09:00 UTC."""

    def __init__(self):
        self.now = datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc)

    @property
    def today(self):
        return self.now.date()


@pytest.fixture()
def clock():
    return FakeClock()


@pytest.fixture()
def client(db, clock):
    def override_get_db():
        yield db

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_today] = lambda: clock.today
    fastapi_app.dependency_overrides[get_now] = lambda: clock.now
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture()
def world(db):
    """Two managers; Meera has Ravi, Anita and Karan; Suresh has Divya."""
    manager = make_employee(db, "Meera", Role.manager, password=PASSWORD)
    other_manager = make_employee(db, "Suresh", Role.manager, password=PASSWORD)
    return SimpleNamespace(
        manager=manager,
        other_manager=other_manager,
        ravi=make_employee(db, "Ravi", manager=manager, password=PASSWORD),
        anita=make_employee(db, "Anita", manager=manager, password=PASSWORD),
        karan=make_employee(db, "Karan", manager=manager, password=PASSWORD),
        outsider=make_employee(db, "Divya", manager=other_manager, password=PASSWORD),
        types=make_leave_types(db),
    )


@pytest.fixture()
def auth(client):
    """auth(employee) returns Authorization headers for that employee."""
    cache = {}

    def _auth(employee):
        if employee.id not in cache:
            cache[employee.id] = login_headers(client, employee)
        return cache[employee.id]

    return _auth
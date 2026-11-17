import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers the tables)
from app.db import Base

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://leave_user:leave_pass@localhost:5434/leave_test_db",
)


@pytest.fixture(scope="session")
def engine():
    test_engine = create_engine(TEST_DATABASE_URL)
    # safety check so a wrong URL can never wipe the real database
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
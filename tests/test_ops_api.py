from sqlalchemy.exc import OperationalError
from app.db import get_db
from app.main import app as fastapi_app

def test_health_is_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_is_ok_when_the_database_answers(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_is_503_when_the_database_is_down(client):
    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    def broken_db():
        yield BrokenSession()

    fastapi_app.dependency_overrides[get_db] = broken_db

    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["detail"] == "database unavailable"
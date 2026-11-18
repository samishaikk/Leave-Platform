from datetime import datetime, timedelta, timezone
import jwt
import pytest

from app.security import ALGORITHM, SECRET_KEY
from tests.helpers import PASSWORD


def test_login_returns_a_token_that_works(client, world):
    response = client.post(
        "/auth/login", data={"username": world.ravi.email, "password": PASSWORD}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["name"] == "Ravi"
    assert me.json()["role"] == "employee"
    assert me.json()["manager_id"] == world.manager.id


@pytest.mark.parametrize(
    "who, password",
    [("ravi", "wrong-password"), ("nobody@example.com", PASSWORD)],
)
def test_bad_credentials_get_the_same_401(client, world, who, password):
    email = world.ravi.email if who == "ravi" else who
    response = client.post("/auth/login", data={"username": email, "password": password})
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"
    assert response.headers["www-authenticate"] == "Bearer"


def test_overlong_password_is_a_401_not_a_crash(client, world):
    response = client.post(
        "/auth/login", data={"username": world.ravi.email, "password": "x" * 200}
    )
    assert response.status_code == 401


def test_missing_token_is_401(client):
    assert client.get("/auth/me").status_code == 401


@pytest.mark.regression
def test_invalid_token_is_401_with_bearer_header(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_expired_token_is_401(client, world):
    expired = jwt.encode(
        {
            "sub": str(world.ravi.id),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_token_for_an_unknown_employee_is_401(client):
    token = jwt.encode(
        {"sub": "999999", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
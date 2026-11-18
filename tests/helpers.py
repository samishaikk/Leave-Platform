PASSWORD = "Password123!"
def login_headers(client, employee) -> dict:
    response = client.post(
        "/auth/login", data={"username": employee.email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def apply(client, headers, leave_type, start, end, reason=None):
    body = {"leave_type_id": leave_type.id, "start_date": start, "end_date": end}
    if reason:
        body["reason"] = reason
    return client.post("/leave-requests", json=body, headers=headers)


def decide(client, headers, request_id, decision, comment=None):
    body = {"decision": decision}
    if comment is not None:
        body["comment"] = comment
    return client.post(
        f"/leave-requests/{request_id}/decision", json=body, headers=headers
    )
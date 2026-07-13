from tests import factories
from tests.conftest import auth_headers


# --- GET /users/me ---
async def test_get_own_profile(client, user_headers, regular_user):
    response = await client.get("/api/v1/users/me", headers=user_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == regular_user.email
    assert data["role"] == "user"


async def test_get_profile_of_deleted_user(client, db_session):
    ghost = await factories.create_user(
        db_session, "ghost@test.com", is_active=False
    )

    response = await client.get(
        "/api/v1/users/me", headers=auth_headers(ghost.id)
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


# --- PATCH /users/me ---
async def test_update_profile_partial(client, user_headers):
    response = await client.patch(
        "/api/v1/users/me",
        json={"first_name": "Jaymin", "mobile_no": "9999999999"},
        headers=user_headers,
    )

    assert response.status_code == 200
    detail = response.json()["data"]["user_detail"]
    assert detail["first_name"] == "Jaymin"
    assert detail["mobile_no"] == "9999999999"

    # persisted, not just echoed
    response = await client.get("/api/v1/users/me", headers=user_headers)
    assert response.json()["data"]["user_detail"]["first_name"] == "Jaymin"


async def test_update_profile_empty_body_is_noop(client, user_headers):
    response = await client.patch(
        "/api/v1/users/me", json={}, headers=user_headers
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Profile updated successfully"


# --- DELETE /users/user/delete ---
async def test_delete_own_account_soft_deletes(
    client, user_headers, regular_user, db_session
):
    response = await client.delete(
        "/api/v1/users/user/delete", headers=user_headers
    )

    assert response.status_code == 200
    assert response.json()["message"] == "User deleted successfully"

    await db_session.refresh(regular_user)
    assert regular_user.is_active is False

    # the account is gone from the API's point of view
    response = await client.get("/api/v1/users/me", headers=user_headers)
    assert response.status_code == 404


async def test_delete_account_twice(client, user_headers, regular_user):
    first = await client.delete("/api/v1/users/user/delete", headers=user_headers)
    assert first.status_code == 200

    second = await client.delete(
        "/api/v1/users/user/delete", headers=user_headers
    )
    assert second.status_code == 404
    assert second.json()["detail"] == "User not found"

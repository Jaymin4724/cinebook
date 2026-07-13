from tests.conftest import auth_headers


# --- RBAC VIA permission_required ---
async def test_regular_user_cannot_access_admin_route(client, user_headers):
    response = await client.get("/api/v1/admin/theatres", headers=user_headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


async def test_theatre_admin_cannot_access_admin_route(
    client, theatre_admin_headers
):
    response = await client.get("/api/v1/admin/users", headers=theatre_admin_headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


async def test_admin_can_access_admin_route(client, admin_headers):
    response = await client.get("/api/v1/admin/users", headers=admin_headers)

    assert response.status_code == 200


async def test_regular_user_cannot_access_theatre_admin_route(client, user_headers):
    response = await client.get(
        "/api/v1/theatre-admin/my-theatres", headers=user_headers
    )

    assert response.status_code == 403


async def test_theatre_admin_can_access_theatre_admin_route(
    client, theatre_admin_headers
):
    response = await client.get(
        "/api/v1/theatre-admin/my-theatres", headers=theatre_admin_headers
    )

    assert response.status_code == 200


async def test_admin_has_theatre_admin_permissions_too(client, admin_headers):
    response = await client.get(
        "/api/v1/theatre-admin/my-screens", headers=admin_headers
    )

    assert response.status_code == 200


async def test_regular_user_can_read_movies(client, user_headers):
    # "read-movies" is the only permission the user role holds
    response = await client.get("/api/v1/admin/movies", headers=user_headers)

    assert response.status_code == 200


async def test_permission_check_requires_authentication(client):
    response = await client.get("/api/v1/admin/users")

    assert response.status_code == 401

import pytest
from fastapi import status
from tests.conftest import global_fake_redis
from tests.test_utils import assert_response_structure


@pytest.fixture
async def auth_client(client):
    email = "jaymin.dave@armakuni.com"
    await client.post("/api/v1/auth/send-otp", json={"email": email})

    otp = await global_fake_redis.hget(email, "otp")

    response = await client.post(
        "/api/v1/auth/signin", json={"email": email, "otp": otp}
    )
    token = response.json()["data"]["access_token"]

    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.mark.asyncio(loop_scope="session")
class TestAdmin:

    async def test_create_user_success(self, auth_client):
        new_email = "newuser@example.com"

        await auth_client.post("/api/v1/auth/send-otp", json={"email": new_email})
        otp = await global_fake_redis.hget(new_email, "otp")

        payload = {"email": new_email, "otp": otp, "role": "user"}
        response = await auth_client.post("/api/v1/admin/create-user", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert_response_structure(body)
        assert "created" in body["message"].lower()

    async def test_get_all_users_success(self, auth_client):
        response = await auth_client.get(
            "/api/v1/admin/users", params={"page": 1, "size": 10}
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert_response_structure(body)
        assert isinstance(body["data"], list)
        assert len(body["data"]) >= 1

    async def test_get_all_theatres_success(self, auth_client):
        response = await auth_client.get(
            "/api/v1/admin/theatres", params={"page": 1, "size": 10}
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert_response_structure(body)
        assert isinstance(body["data"], list)

    async def test_get_all_movies_success(self, auth_client):
        response = await auth_client.get(
            "/api/v1/admin/movies", params={"page": 1, "size": 10}
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert_response_structure(body)
        assert isinstance(body["data"], list)

    async def test_create_movie_success(self, auth_client):
        payload = {"imdb_id": "tt0111161"}

        response = await auth_client.post("/api/v1/admin/create-movie", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert_response_structure(body)
        assert "successfully" in body["message"].lower()

    async def test_create_theatre_success(self, auth_client):
        payload = {
            "name": "PVR Cinemas",
            "area": "Thaltej",
            "city": "Ahmedabad",
            "operator_email": "jaymin4724@gmail.com",
        }

        response = await auth_client.post("/api/v1/admin/create-theatre", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert_response_structure(body)
        assert "successfully" in body["message"].lower()

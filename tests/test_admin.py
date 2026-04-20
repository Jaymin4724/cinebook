import pytest
from fastapi import status
from unittest.mock import patch, AsyncMock
from tests.conftest import global_fake_redis
from tests.test_utils import assert_response_structure, assert_list_response


async def signin_as_admin(client):
    email = "jaymin.dave@armakuni.com"
    await client.post("/api/v1/auth/send-otp", json={"email": email})
    otp = await global_fake_redis.hget(email, "otp")
    response = await client.post(
        "/api/v1/auth/signin", json={"email": email, "otp": otp}
    )
    token = response.json()["data"]["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})


MOCK_OMDB_RESPONSE = {
    "Response": "True",
    "Title": "The Shawshank Redemption",
    "Runtime": "142 min",
    "Plot": "Two imprisoned men bond over a number of years.",
    "Genre": "Drama",
    "imdbRating": "9.3",
    "imdbID": "tt0111161",
}


@pytest.mark.asyncio(loop_scope="session")
class TestAdmin:

    async def test_create_user_success(self, client):
        await signin_as_admin(client)

        new_email = "newuser@example.com"
        await client.post("/api/v1/auth/send-otp", json={"email": new_email})
        otp = await global_fake_redis.hget(new_email, "otp")

        payload = {"email": new_email, "otp": otp, "role": "user"}
        response = await client.post("/api/v1/admin/create-user", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert_response_structure(body)
        assert "created" in body["message"].lower()
        assert body["data"]["email"] == new_email

    async def test_create_theatre_success(self, client):
        await signin_as_admin(client)

        payload = {
            "name": "PVR Cinemas",
            "area": "Thaltej",
            "city": "Ahmedabad",
            "operator_email": "jaymin4724@gmail.com",
        }
        response = await client.post("/api/v1/admin/create-theatre", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert_response_structure(body)
        assert "successfully" in body["message"].lower()
        assert body["data"]["name"] == "pvr cinemas"

    async def test_create_movie_success(self, client):
        await signin_as_admin(client)

        mock_omdb = AsyncMock()
        mock_omdb.json = lambda: MOCK_OMDB_RESPONSE

        with patch("httpx.AsyncClient.get", return_value=mock_omdb):
            response = await client.post(
                "/api/v1/admin/create-movie", json={"imdb_id": "tt0111161"}
            )

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert_response_structure(body)
        assert "successfully" in body["message"].lower()
        assert body["data"]["name"] == "the shawshank redemption"

    async def test_get_all_users_success(self, client):
        await signin_as_admin(client)

        response = await client.get(
            "/api/v1/admin/users", params={"page": 1, "size": 10}
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert_list_response(body)
        assert len(body["data"]) >= 1

    async def test_get_all_theatres_success(self, client):
        await signin_as_admin(client)

        response = await client.get(
            "/api/v1/admin/theatres", params={"page": 1, "size": 10}
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert_list_response(body)

    async def test_get_all_movies_success(self, client):
        await signin_as_admin(client)

        response = await client.get(
            "/api/v1/admin/movies", params={"page": 1, "size": 10}
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert_list_response(body)

    async def test_delete_theatre_success(self, client):
        await signin_as_admin(client)

        create_resp = await client.post(
            "/api/v1/admin/create-theatre",
            json={
                "name": "Temp Theatre",
                "area": "Satellite",
                "city": "Ahmedabad",
                "operator_email": "jaymin4724@gmail.com",
            },
        )
        theatre_id = create_resp.json()["data"]["id"]

        response = await client.delete(f"/api/v1/admin/theatre/delete/{theatre_id}")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert_response_structure(body)
        assert "deleted" in body["message"].lower()

    async def test_delete_movie_success(self, client):
        await signin_as_admin(client)

        mock_omdb = AsyncMock()
        mock_omdb.json = lambda: MOCK_OMDB_RESPONSE

        with patch("httpx.AsyncClient.get", return_value=mock_omdb):
            create_resp = await client.post(
                "/api/v1/admin/create-movie", json={"imdb_id": "tt0068646"}
            )
        movie_id = create_resp.json()["data"]["id"]

        response = await client.delete(f"/api/v1/admin/movie/delete/{movie_id}")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert_response_structure(body)
        assert "deleted" in body["message"].lower()

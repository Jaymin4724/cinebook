import pytest
from fastapi import status
from datetime import datetime, timedelta, timezone
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


async def signin_as_theatre_admin(client):
    email = "jaymin4724@gmail.com"
    await client.post("/api/v1/auth/send-otp", json={"email": email})
    otp = await global_fake_redis.hget(email, "otp")
    response = await client.post(
        "/api/v1/auth/signin", json={"email": email, "otp": otp}
    )
    token = response.json()["data"]["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})


async def signin_as_user(client) -> str:
    email = "regularuser@example.com"
    await client.post("/api/v1/auth/send-otp", json={"email": email})
    otp = await global_fake_redis.hget(email, "otp")
    response = await client.post(
        "/api/v1/auth/signin", json={"email": email, "otp": otp}
    )
    token = response.json()["data"]["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return token


LAYOUT_PAYLOAD = {
    "layout": [
        [
            {"grid_type": "wall", "category": None},
            {"grid_type": "seat", "category": "recliner"},
            {"grid_type": "seat", "category": "recliner"},
            {"grid_type": "seat", "category": "recliner"},
            {"grid_type": "wall", "category": None},
        ],
        [
            {"grid_type": "seat", "category": "premium"},
            {"grid_type": "wall", "category": None},
            {"grid_type": "seat", "category": "premium"},
            {"grid_type": "wall", "category": None},
            {"grid_type": "seat", "category": "premium"},
        ],
        [
            {"grid_type": "wall", "category": None},
            {"grid_type": "wall", "category": None},
            {"grid_type": "wall", "category": None},
            {"grid_type": "wall", "category": None},
            {"grid_type": "wall", "category": None},
        ],
        [
            {"grid_type": "wall", "category": None},
            {"grid_type": "seat", "category": "recliner"},
            {"grid_type": "seat", "category": "recliner"},
            {"grid_type": "seat", "category": "recliner"},
            {"grid_type": "wall", "category": None},
        ],
    ],
    "metadata": {"grid_rows": 4, "grid_columns": 5},
}

CATEGORY_PRICE = {"recliner": 300, "premium": 250}

MOCK_OMDB_RESPONSE = {
    "Response": "True",
    "Title": "The Shawshank Redemption",
    "Runtime": "142 min",
    "Plot": "Two imprisoned men bond over a number of years.",
    "Genre": "Drama",
    "imdbRating": "9.3",
    "imdbID": "tt0111161",
}


def show_start_time(hours_ahead: int = 3) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours_ahead)).isoformat()


async def build_full_chain(client) -> dict:
    await signin_as_admin(client)

    theatre_resp = await client.post(
        "/api/v1/admin/create-theatre",
        json={
            "name": "PVR Cinemas",
            "area": "Thaltej",
            "city": "Ahmedabad",
            "operator_email": "jaymin4724@gmail.com",
        },
    )
    theatre_id = theatre_resp.json()["data"]["id"]

    from unittest.mock import Mock

    mock_omdb = AsyncMock()
    mock_omdb.json = Mock(return_value=MOCK_OMDB_RESPONSE)
    with patch("httpx.AsyncClient.get", return_value=mock_omdb):
        movie_resp = await client.post(
            "/api/v1/admin/create-movie", json={"imdb_id": "tt0111161"}
        )
    movie_id = movie_resp.json()["data"]["id"]

    await signin_as_theatre_admin(client)

    layout_resp = await client.post(
        "/api/v1/theatre-admin/create-layout",
        json={
            "name": "Screen A Layout",
            "theatre_id": theatre_id,
            "layout": LAYOUT_PAYLOAD,
        },
    )
    layout_id = layout_resp.json()["data"]["id"]

    screen_resp = await client.post(
        "/api/v1/theatre-admin/create-screen",
        json={
            "name": "Screen 1",
            "theatre_id": theatre_id,
            "layout_id": layout_id,
        },
    )
    screen_id = screen_resp.json()["data"]["id"]

    show_resp = await client.post(
        "/api/v1/theatre-admin/create-show",
        json={
            "screen_id": screen_id,
            "movie_id": movie_id,
            "start_time": show_start_time(hours_ahead=3),
            "category_price": CATEGORY_PRICE,
        },
    )
    show_id = show_resp.json()["data"]["id"]

    return {
        "theatre_id": theatre_id,
        "movie_id": movie_id,
        "layout_id": layout_id,
        "screen_id": screen_id,
        "show_id": show_id,
    }


@pytest.mark.asyncio(loop_scope="session")
class TestUser:

    async def test_get_movies_by_theatre_success(self, client):
        ids = await build_full_chain(client)
        client.headers.pop("Authorization", None)

        response = await client.get(
            f"/api/v1/users/theatre/{str(ids['theatre_id'])}/movies",
            params={"page": 1, "size": 10},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert_list_response(body)

    async def test_get_theatres_by_movie_success(self, client):
        ids = await build_full_chain(client)
        client.headers.pop("Authorization", None)

        response = await client.get(
            f"/api/v1/users/movie/{str(ids['movie_id'])}/theatres",
            params={"page": 1, "size": 10},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert_list_response(body)

    async def test_get_shows_success(self, client):
        ids = await build_full_chain(client)
        print(ids)
        client.headers.pop("Authorization", None)

        response = await client.get(
            f"/api/v1/users/theatre/{ids['theatre_id']}/movie/{ids['movie_id']}",
            params={"page": 1, "size": 10},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert_list_response(body)
        assert any(s["id"] == ids["show_id"] for s in body["data"])

    async def test_get_show_by_id_success(self, client):
        ids = await build_full_chain(client)
        client.headers.pop("Authorization", None)

        response = await client.get(f"/api/v1/users/show/{ids['show_id']}")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert_response_structure(body)
        assert "layout" in body["data"]
        assert "seat_mapping" in body["data"]
        assert "metadata" in body["data"]
        assert "category_pricing" in body["data"]

    async def test_lock_seat_success(self, client):
        ids = await build_full_chain(client)
        await signin_as_user(client)

        response = await client.post(
            f"/api/v1/users/show/{ids['show_id']}/seat-lock",
            json={"seat_array": ["A1"]},
        )

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert_response_structure(body)
        assert "locked" in body["message"].lower()

    async def test_book_seat_success(self, client):
        ids = await build_full_chain(client)
        await signin_as_user(client)

        await client.post(
            f"/api/v1/users/show/{ids['show_id']}/seat-lock",
            json={"seat_array": ["A2"]},
        )

        response = await client.post(
            f"/api/v1/users/show/{ids['show_id']}/seat-book",
            json={"seat_array": ["A2"]},
        )

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert_response_structure(body)
        assert "booked" in body["message"].lower()
        assert "booking_id" in body["data"]
        assert "total_paid" in body["data"]
        assert body["data"]["total_paid"] == 300

    async def test_delete_user_success(self, client):
        await signin_as_user(client)

        response = await client.delete("/api/v1/users/user/delete")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert_response_structure(body)
        assert "deleted" in body["message"].lower()

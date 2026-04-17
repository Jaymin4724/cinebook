import pytest
from fastapi import status
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
from tests.conftest import global_fake_redis
from tests.test_utils import assert_response_structure


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


async def build_theatre_chain(client):
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

    mock_omdb = AsyncMock()
    from unittest.mock import Mock

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

    return {
        "theatre_id": theatre_id,
        "movie_id": movie_id,
        "layout_id": layout_id,
        "screen_id": screen_id,
    }


@pytest.mark.asyncio(loop_scope="session")
class TestTheatreAdmin:

    async def test_create_layout_success(self, client):
        await signin_as_admin(client)

        theatre_resp = await client.post(
            "/api/v1/admin/create-theatre",
            json={
                "name": "Layout Test Theatre",
                "area": "Bodakdev",
                "city": "Ahmedabad",
                "operator_email": "jaymin4724@gmail.com",
            },
        )
        theatre_id = theatre_resp.json()["data"]["id"]

        await signin_as_theatre_admin(client)

        payload = {
            "name": "Screen A Layout",
            "theatre_id": theatre_id,
            "layout": LAYOUT_PAYLOAD,
        }
        response = await client.post(
            "/api/v1/theatre-admin/create-layout", json=payload
        )

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()

        assert "successfully" in body["message"].lower()

    async def test_create_screen_success(self, client):
        ids = await build_theatre_chain(client)

        payload = {
            "name": "Screen 2",
            "theatre_id": ids["theatre_id"],
            "layout_id": ids["layout_id"],
        }
        response = await client.post(
            "/api/v1/theatre-admin/create-screen", json=payload
        )

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert_response_structure(body)
        assert "successfully" in body["message"].lower()

    async def test_create_show_success(self, client):
        ids = await build_theatre_chain(client)

        payload = {
            "screen_id": ids["screen_id"],
            "movie_id": ids["movie_id"],
            "start_time": show_start_time(hours_ahead=3),
            "category_price": CATEGORY_PRICE,
        }
        response = await client.post("/api/v1/theatre-admin/create-show", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert_response_structure(body)
        assert "successfully" in body["message"].lower()

    async def test_delete_screen_success(self, client):
        ids = await build_theatre_chain(client)

        create_resp = await client.post(
            "/api/v1/theatre-admin/create-screen",
            json={
                "name": "Screen To Delete",
                "theatre_id": ids["theatre_id"],
                "layout_id": ids["layout_id"],
            },
        )
        screen_id = create_resp.json()["data"]["id"]

        response = await client.delete(
            "/api/v1/theatre-admin/screen/delete", params={"screen_id": screen_id}
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert_response_structure(body)
        assert "deleted" in body["message"].lower()

    async def test_delete_show_success(self, client):
        ids = await build_theatre_chain(client)

        create_resp = await client.post(
            "/api/v1/theatre-admin/create-show",
            json={
                "screen_id": ids["screen_id"],
                "movie_id": ids["movie_id"],
                "start_time": show_start_time(hours_ahead=3),
                "category_price": CATEGORY_PRICE,
            },
        )
        show_id = create_resp.json()["data"]["id"]

        response = await client.delete(
            "/api/v1/theatre-admin/show/delete", params={"show_id": show_id}
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert_response_structure(body)
        assert "deleted" in body["message"].lower()

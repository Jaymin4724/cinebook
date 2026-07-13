import uuid

from sqlalchemy import select

from app.models import (
    UserModel,
    TheatreModel,
    TheatreOperatorMapModel,
    MovieModel,
)

from tests import factories


# --- OMDB STUBBING ---
class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json


class _FakeOMDBClient:
    """Stands in for the httpx.AsyncClient the admin service opens for OMDB."""

    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, **kwargs):
        return self._response


def _omdb_payload(**overrides):
    payload = {
        "Response": "True",
        "Title": "inception",
        "Runtime": "148 min",
        "Plot": "a mind-bending heist",
        "Genre": "sci-fi",
        "imdbRating": "8.8",
        "imdbID": "tt1375666",
    }
    payload.update(overrides)
    return payload


def _patch_omdb(monkeypatch, json_data, status_code=200):
    fake = _FakeOMDBClient(_FakeResponse(json_data, status_code=status_code))
    monkeypatch.setattr(
        "app.services.admin_service.httpx.AsyncClient", lambda: fake
    )


# --- CREATE USER ---
async def test_admin_creates_theatre_admin_user(
    client, fake_redis, admin_headers, db_session
):
    await client.post("/api/v1/auth/send-otp", json={"email": "newop@test.com"})
    otp = (await fake_redis.hgetall("newop@test.com"))["otp"]

    response = await client.post(
        "/api/v1/admin/create-user",
        json={"email": "newop@test.com", "otp": otp, "role": "theatre_admin"},
        headers=admin_headers,
    )

    assert response.status_code == 201
    assert response.json()["data"]["role"] == "theatre_admin"

    user = (
        await db_session.execute(
            select(UserModel).where(UserModel.email == "newop@test.com")
        )
    ).scalar_one()
    assert user.is_active


async def test_admin_create_user_requires_valid_otp(client, admin_headers):
    response = await client.post(
        "/api/v1/admin/create-user",
        json={"email": "newop@test.com", "otp": "000000", "role": "user"},
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "OTP not found or expired"


# --- CREATE THEATRE ---
async def test_create_theatre_links_operator_and_syncs_es(
    client, admin_headers, theatre_admin_user, db_session, es_sync_calls
):
    response = await client.post(
        "/api/v1/admin/create-theatre",
        json={
            "name": "PVR Cinemas",
            "area": "Satellite",
            "city": "Ahmedabad",
            "operator_email": theatre_admin_user.email,
        },
        headers=admin_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "pvr cinemas"  # lowercased

    theatre = (
        await db_session.execute(
            select(TheatreModel).where(TheatreModel.name == "pvr cinemas")
        )
    ).scalar_one()

    operator_map = (
        await db_session.execute(
            select(TheatreOperatorMapModel).where(
                TheatreOperatorMapModel.theatre_id == theatre.id
            )
        )
    ).scalar_one()
    assert operator_map.user_id == theatre_admin_user.id

    assert len(es_sync_calls) == 1
    assert es_sync_calls[0]["type"] == "theatre"
    assert es_sync_calls[0]["name"] == "pvr cinemas"


async def test_create_theatre_unknown_operator_rolls_back(
    client, admin_headers, db_session, es_sync_calls
):
    response = await client.post(
        "/api/v1/admin/create-theatre",
        json={
            "name": "orphan theatre",
            "area": "satellite",
            "city": "ahmedabad",
            "operator_email": "nobody@test.com",
        },
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Theatre operator not found"

    # the whole transaction rolled back: no theatre row was persisted
    theatre = (
        await db_session.execute(
            select(TheatreModel).where(TheatreModel.name == "orphan theatre")
        )
    ).scalar_one_or_none()
    assert theatre is None
    assert es_sync_calls == []


# --- CREATE MOVIE (OMDB) ---
async def test_create_movie_from_omdb(
    client, admin_headers, db_session, es_sync_calls, monkeypatch
):
    _patch_omdb(monkeypatch, _omdb_payload())

    response = await client.post(
        "/api/v1/admin/create-movie",
        json={"imdb_id": "tt1375666"},
        headers=admin_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "inception"
    assert data["rating"] == 8.8

    movie = (
        await db_session.execute(
            select(MovieModel).where(MovieModel.imdb_id == "tt1375666")
        )
    ).scalar_one()
    assert movie.duration.total_seconds() == 148 * 60

    assert len(es_sync_calls) == 1
    assert es_sync_calls[0]["type"] == "movie"


async def test_create_movie_duplicate_imdb_id(
    client, admin_headers, db_session, monkeypatch
):
    await factories.create_movie(db_session, imdb_id="tt1375666")
    _patch_omdb(monkeypatch, _omdb_payload())

    response = await client.post(
        "/api/v1/admin/create-movie",
        json={"imdb_id": "tt1375666"},
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Movie already exist"


async def test_create_movie_invalid_runtime_not_persisted(
    client, admin_headers, db_session, monkeypatch
):
    _patch_omdb(monkeypatch, _omdb_payload(Runtime="N/A"))

    response = await client.post(
        "/api/v1/admin/create-movie",
        json={"imdb_id": "tt1375666"},
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "OMDB did not return a valid runtime for this movie"
    )

    movie = (
        await db_session.execute(
            select(MovieModel).where(MovieModel.imdb_id == "tt1375666")
        )
    ).scalar_one_or_none()
    assert movie is None


async def test_create_movie_omdb_not_found(client, admin_headers, monkeypatch):
    _patch_omdb(
        monkeypatch, {"Response": "False", "Error": "Movie not found!"}
    )

    response = await client.post(
        "/api/v1/admin/create-movie",
        json={"title": "does not exist"},
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Movie not found!"


async def test_create_movie_missing_rating_defaults_to_zero(
    client, admin_headers, monkeypatch
):
    _patch_omdb(monkeypatch, _omdb_payload(imdbRating="N/A"))

    response = await client.post(
        "/api/v1/admin/create-movie",
        json={"imdb_id": "tt1375666"},
        headers=admin_headers,
    )

    assert response.status_code == 201
    assert response.json()["data"]["rating"] == 0.0


async def test_create_movie_rejects_both_imdb_id_and_title(client, admin_headers):
    # rejected by the request schema's model_validator before the service runs
    response = await client.post(
        "/api/v1/admin/create-movie",
        json={"imdb_id": "tt1375666", "title": "inception"},
        headers=admin_headers,
    )

    assert response.status_code == 422


async def test_create_movie_rejects_neither_imdb_id_nor_title(
    client, admin_headers
):
    response = await client.post(
        "/api/v1/admin/create-movie", json={}, headers=admin_headers
    )

    assert response.status_code == 422


# --- UPDATES ---
async def test_update_theatre_partial(
    client, admin_headers, db_session, es_sync_calls
):
    theatre = await factories.create_theatre(db_session)

    response = await client.patch(
        f"/api/v1/admin/theatre/update/{theatre.id}",
        json={"area": "Bopal"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["area"] == "bopal"
    assert data["name"] == theatre.name  # untouched
    assert len(es_sync_calls) == 1


async def test_update_theatre_not_found(client, admin_headers):
    response = await client.patch(
        f"/api/v1/admin/theatre/update/{uuid.uuid4()}",
        json={"area": "bopal"},
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Theatre not found"


async def test_update_movie_partial(
    client, admin_headers, db_session, es_sync_calls
):
    movie = await factories.create_movie(db_session)

    response = await client.patch(
        f"/api/v1/admin/movie/update/{movie.id}",
        json={"rating": 9.1},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["rating"] == 9.1
    assert len(es_sync_calls) == 1


async def test_update_movie_not_found(client, admin_headers):
    response = await client.patch(
        f"/api/v1/admin/movie/update/{uuid.uuid4()}",
        json={"rating": 9.1},
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


# --- LIST ENDPOINTS ---
async def test_get_all_users_paginated(client, admin_headers, db_session):
    for i in range(3):
        await factories.create_user(db_session, f"listed{i}@test.com")

    response = await client.get(
        "/api/v1/admin/users?page=1&size=2", headers=admin_headers
    )

    assert response.status_code == 200
    assert len(response.json()["data"]) == 2


async def test_get_all_theatres_excludes_deleted(
    client, admin_headers, db_session
):
    await factories.create_theatre(db_session, name="active theatre")
    await factories.create_theatre(db_session, name="dead theatre", is_active=False)

    response = await client.get("/api/v1/admin/theatres", headers=admin_headers)

    assert response.status_code == 200
    names = [t["name"] for t in response.json()["data"]]
    assert names == ["active theatre"]


async def test_get_all_movies_excludes_deleted(client, admin_headers, db_session):
    await factories.create_movie(db_session, name="visible movie")
    await factories.create_movie(db_session, name="hidden movie", is_deleted=True)

    response = await client.get("/api/v1/admin/movies", headers=admin_headers)

    assert response.status_code == 200
    names = [m["name"] for m in response.json()["data"]]
    assert names == ["visible movie"]


# --- DELETES (SOFT) ---
async def test_delete_theatre_soft_deletes_and_hides_from_es(
    client, admin_headers, db_session, es_sync_calls
):
    theatre = await factories.create_theatre(db_session)

    response = await client.delete(
        f"/api/v1/admin/theatre/delete/{theatre.id}", headers=admin_headers
    )

    assert response.status_code == 200

    await db_session.refresh(theatre)
    assert theatre.is_active is False

    assert len(es_sync_calls) == 1
    assert es_sync_calls[0]["is_hidden"] is True

    # already soft-deleted -> gone for a second delete
    response = await client.delete(
        f"/api/v1/admin/theatre/delete/{theatre.id}", headers=admin_headers
    )
    assert response.status_code == 404


async def test_delete_movie_soft_deletes_and_hides_from_es(
    client, admin_headers, db_session, es_sync_calls
):
    movie = await factories.create_movie(db_session)

    response = await client.delete(
        f"/api/v1/admin/movie/delete/{movie.id}", headers=admin_headers
    )

    assert response.status_code == 200

    await db_session.refresh(movie)
    assert movie.is_deleted is True

    assert len(es_sync_calls) == 1
    assert es_sync_calls[0]["is_hidden"] is True

    response = await client.delete(
        f"/api/v1/admin/movie/delete/{movie.id}", headers=admin_headers
    )
    assert response.status_code == 404

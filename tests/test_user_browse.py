import uuid
from datetime import datetime, timedelta, timezone

from tests import factories


# --- MOVIES BY THEATRE ---
async def test_get_movies_by_theatre(client, bookable_show):
    response = await client.get(
        f"/api/v1/users/theatre/{bookable_show.theatre.id}/movies"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert [m["name"] for m in data] == [bookable_show.movie.name]


async def test_get_movies_by_theatre_ignores_past_shows(
    client, db_session, theatre_admin_user
):
    past = await factories.create_bookable_show(
        db_session,
        operator=theatre_admin_user,
        start_time=datetime.now(timezone.utc) - timedelta(days=1),
    )

    response = await client.get(f"/api/v1/users/theatre/{past.theatre.id}/movies")

    assert response.status_code == 200
    assert response.json()["data"] == []


# --- THEATRES BY MOVIE ---
async def test_get_theatres_by_movie(client, bookable_show):
    response = await client.get(
        f"/api/v1/users/movie/{bookable_show.movie.id}/theatres"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert [t["name"] for t in data] == [bookable_show.theatre.name]


# --- SHOWS FOR MOVIE + THEATRE ---
async def test_get_shows_for_movie_and_theatre(client, bookable_show):
    response = await client.get(
        f"/api/v1/users/theatre/{bookable_show.theatre.id}"
        f"/movie/{bookable_show.movie.id}"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    show = data[0]
    assert show["id"] == str(bookable_show.show.id)
    assert show["movie_name"] == bookable_show.movie.name
    assert show["theatre_name"] == bookable_show.theatre.name
    assert show["screen_name"] == bookable_show.screen.name


async def test_get_shows_reverse_route_matches(client, bookable_show):
    response = await client.get(
        f"/api/v1/users/movie/{bookable_show.movie.id}"
        f"/theatre/{bookable_show.theatre.id}"
    )

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


async def test_get_shows_empty_for_unrelated_movie(
    client, bookable_show, db_session
):
    other_movie = await factories.create_movie(db_session, name="other movie")

    response = await client.get(
        f"/api/v1/users/theatre/{bookable_show.theatre.id}"
        f"/movie/{other_movie.id}"
    )

    assert response.status_code == 200
    assert response.json()["data"] == []


# --- SHOW DETAIL (SEAT LAYOUT) ---
async def test_get_show_detail_returns_seat_layout(client, bookable_show):
    response = await client.get(f"/api/v1/users/show/{bookable_show.show.id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["category_pricing"] == factories.CATEGORY_PRICING
    assert data["metadata"]["total_seats"] == 5

    row, col = data["seat_mapping"]["A1"]
    seat = data["layout"][row][col]
    assert seat["status"] == "Available"
    assert seat["price"] == 300.0  # gold pricing applied


async def test_get_show_detail_marks_booked_seats(
    client, db_session, regular_user, bookable_show
):
    await factories.create_booking(
        db_session, regular_user, bookable_show.show, ["A1"], total_bill=300
    )

    response = await client.get(f"/api/v1/users/show/{bookable_show.show.id}")

    assert response.status_code == 200
    data = response.json()["data"]
    row, col = data["seat_mapping"]["A1"]
    assert data["layout"][row][col]["status"] == "Booked"
    assert data["metadata"]["booked_seats"] == 1


async def test_get_show_detail_marks_locked_seats(
    client, user_headers, bookable_show
):
    lock = await client.post(
        f"/api/v1/users/show/{bookable_show.show.id}/seat-lock",
        json={"seat_array": ["B1"]},
        headers=user_headers,
    )
    assert lock.status_code == 201

    response = await client.get(f"/api/v1/users/show/{bookable_show.show.id}")

    assert response.status_code == 200
    data = response.json()["data"]
    row, col = data["seat_mapping"]["B1"]
    assert data["layout"][row][col]["status"] == "Locked"


async def test_get_show_detail_handles_null_gap_cells(
    client, db_session, theatre_admin_user
):
    """Layouts stored with null gap cells must not crash layout generation."""
    grid = {
        "layout": [
            [
                {"grid_type": "seat", "category": "standard"},
                None,
                {"grid_type": "seat", "category": "standard"},
            ],
        ],
        "metadata": {"grid_rows": 1, "grid_columns": 3},
    }
    theatre = await factories.create_theatre(db_session, operator=theatre_admin_user)
    layout = await factories.create_layout(db_session, theatre, raw_grid=grid)
    screen = await factories.create_screen(db_session, theatre, layout)
    movie = await factories.create_movie(db_session)
    show = await factories.create_show(
        db_session, screen, movie, category_pricing={"standard": 150.0}
    )

    response = await client.get(f"/api/v1/users/show/{show.id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["layout"][0][1] is None
    row, col = data["seat_mapping"]["A1"]
    assert data["layout"][row][col]["status"] == "Available"


async def test_get_show_detail_unknown_show(client):
    response = await client.get(f"/api/v1/users/show/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Show not found"

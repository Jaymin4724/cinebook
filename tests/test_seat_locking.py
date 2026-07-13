from tests import factories
from tests.conftest import auth_headers


def _lock_url(show) -> str:
    return f"/api/v1/users/show/{show.id}/seat-lock"


async def test_lock_seats_success(
    client, fake_redis, user_headers, regular_user, bookable_show
):
    response = await client.post(
        _lock_url(bookable_show.show),
        json={"seat_array": ["A1", "B1"]},
        headers=user_headers,
    )

    assert response.status_code == 201
    assert response.json()["message"] == "Seats Locked Successfully"

    lock_key = f"show_seat_locked_{bookable_show.show.id}"
    locks = await fake_redis.hgetall(lock_key)
    assert locks == {
        "A1": str(regular_user.id),
        "B1": str(regular_user.id),
    }
    assert await fake_redis.ttl(lock_key) > 0


async def test_lock_conflict_writes_nothing(
    client, fake_redis, user_headers, db_session, bookable_show
):
    other_user = await factories.create_user(db_session, "rival@test.com")
    response = await client.post(
        _lock_url(bookable_show.show),
        json={"seat_array": ["B1"]},
        headers=auth_headers(other_user.id),
    )
    assert response.status_code == 201

    # B1 is taken, so the whole request must fail atomically
    response = await client.post(
        _lock_url(bookable_show.show),
        json={"seat_array": ["B1", "B2"]},
        headers=user_headers,
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "One or more seats were just locked by another user"
    )

    locks = await fake_redis.hgetall(f"show_seat_locked_{bookable_show.show.id}")
    assert locks == {"B1": str(other_user.id)}  # no partial B2 write


async def test_lock_already_booked_seat(
    client, user_headers, db_session, regular_user, bookable_show
):
    await factories.create_booking(
        db_session, regular_user, bookable_show.show, seats=["A1"], total_bill=300
    )

    response = await client.post(
        _lock_url(bookable_show.show),
        json={"seat_array": ["A1"]},
        headers=user_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Seat A1 is unavailable"


async def test_lock_unknown_seat(client, user_headers, bookable_show):
    response = await client.post(
        _lock_url(bookable_show.show),
        json={"seat_array": ["Z9"]},
        headers=user_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Seat Z9 not found"


async def test_lock_empty_seat_array_rejected(client, user_headers, bookable_show):
    response = await client.post(
        _lock_url(bookable_show.show),
        json={"seat_array": []},
        headers=user_headers,
    )

    assert response.status_code == 422


async def test_lock_requires_authentication(client, bookable_show):
    response = await client.post(
        _lock_url(bookable_show.show), json={"seat_array": ["A1"]}
    )

    assert response.status_code == 401

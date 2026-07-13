import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import BookingModel, BookedSeatMapModel, BookedTicketModel

from tests import factories
from tests.conftest import auth_headers


def _lock_url(show) -> str:
    return f"/api/v1/users/show/{show.id}/seat-lock"


def _book_url(show) -> str:
    return f"/api/v1/users/show/{show.id}/seat-book"


async def _lock_and_book(client, show, headers, seats):
    lock = await client.post(
        _lock_url(show), json={"seat_array": seats}, headers=headers
    )
    assert lock.status_code == 201

    return await client.post(
        _book_url(show), json={"seat_array": seats}, headers=headers
    )


# --- BOOKING HAPPY PATH ---
async def test_book_tickets_full_flow(
    client,
    fake_redis,
    fake_email_service,
    user_headers,
    regular_user,
    bookable_show,
    db_session,
):
    show = bookable_show.show

    response = await _lock_and_book(client, show, user_headers, ["A1", "B1"])

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["total_paid"] == 450.0  # gold 300 + standard 150

    booking = (
        await db_session.execute(
            select(BookingModel).where(BookingModel.id == data["booking_id"])
        )
    ).scalar_one()
    assert booking.user_id == regular_user.id
    assert booking.number_of_seats == 2
    assert booking.total_bill == 450.0

    seats = (
        (
            await db_session.execute(
                select(BookedSeatMapModel.seats_number).where(
                    BookedSeatMapModel.booking_id == booking.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert sorted(seats) == ["A1", "B1"]

    ticket = (
        await db_session.execute(
            select(BookedTicketModel).where(
                BookedTicketModel.booking_id == booking.id
            )
        )
    ).scalar_one()
    assert ticket.is_used is False

    # QR ticket email is sent in the background
    assert len(fake_email_service.qr_tickets) == 1
    assert fake_email_service.qr_tickets[0]["email_to"] == regular_user.email

    # Redis locks are cleared and the cached layout is marked Booked
    locks = await fake_redis.hgetall(f"show_seat_locked_{show.id}")
    assert locks == {}

    layout_body = await fake_redis.json().get(f"show_seat_layout_{show.id}")
    row, col = layout_body["seat_mapping"]["A1"]
    assert layout_body["layout"][row][col]["status"] == "Booked"


# --- BOOKING LOCK GUARDS ---
async def test_book_empty_seat_array_rejected(client, user_headers, bookable_show):
    response = await client.post(
        _book_url(bookable_show.show),
        json={"seat_array": []},
        headers=user_headers,
    )

    assert response.status_code == 422


async def test_book_without_lock(client, user_headers, bookable_show):
    response = await client.post(
        _book_url(bookable_show.show),
        json={"seat_array": ["A1"]},
        headers=user_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Seat A1 lock expired or invalid"


async def test_book_with_another_users_lock(
    client, user_headers, db_session, bookable_show
):
    other_user = await factories.create_user(db_session, "rival@test.com")
    lock = await client.post(
        _lock_url(bookable_show.show),
        json={"seat_array": ["A1"]},
        headers=auth_headers(other_user.id),
    )
    assert lock.status_code == 201

    response = await client.post(
        _book_url(bookable_show.show),
        json={"seat_array": ["A1"]},
        headers=user_headers,
    )

    assert response.status_code == 403


async def test_book_seat_already_booked_in_db(
    client, user_headers, db_session, bookable_show
):
    """A valid Redis lock does not bypass the DB re-check inside the booking tx."""
    show = bookable_show.show

    lock = await client.post(
        _lock_url(show), json={"seat_array": ["A1"]}, headers=user_headers
    )
    assert lock.status_code == 201

    # simulate a race: the seat lands in Postgres between lock and book
    racer = await factories.create_user(db_session, "racer@test.com")
    await factories.create_booking(db_session, racer, show, ["A1"], total_bill=300)

    response = await client.post(
        _book_url(show), json={"seat_array": ["A1"]}, headers=user_headers
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Seat(s) A1 already booked"


# --- DB BACKSTOP: PARTIAL UNIQUE INDEX ---
async def test_partial_unique_index_blocks_double_booking(
    db_session, regular_user, bookable_show
):
    await factories.create_booking(
        db_session, regular_user, bookable_show.show, ["A1"], total_bill=300
    )

    with pytest.raises(IntegrityError):
        await factories.create_booking(
            db_session, regular_user, bookable_show.show, ["A1"], total_bill=300
        )
    await db_session.rollback()


async def test_cancelled_seat_can_be_booked_again(
    db_session, regular_user, bookable_show
):
    await factories.create_booking(
        db_session,
        regular_user,
        bookable_show.show,
        ["A1"],
        total_bill=300,
        is_cancelled=True,
    )

    # the partial index only guards non-cancelled rows
    booking = await factories.create_booking(
        db_session, regular_user, bookable_show.show, ["A1"], total_bill=300
    )
    assert booking.id is not None


# --- BOOKING HISTORY & DETAIL ---
async def test_booking_history_newest_first(
    client, user_headers, regular_user, bookable_show, db_session
):
    first = await factories.create_booking(
        db_session, regular_user, bookable_show.show, ["A1"], total_bill=300
    )
    second = await factories.create_booking(
        db_session, regular_user, bookable_show.show, ["B1"], total_bill=150
    )

    response = await client.get("/api/v1/users/bookings", headers=user_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert [b["id"] for b in data] == [str(second.id), str(first.id)]
    assert data[0]["movie_name"] == bookable_show.movie.name
    assert data[0]["theatre_name"] == bookable_show.theatre.name


async def test_booking_history_pagination(
    client, user_headers, regular_user, bookable_show, db_session
):
    for seat in ("A1", "B1", "B2"):
        await factories.create_booking(
            db_session, regular_user, bookable_show.show, [seat], total_bill=150
        )

    response = await client.get(
        "/api/v1/users/bookings?page=1&size=2", headers=user_headers
    )

    assert response.status_code == 200
    assert len(response.json()["data"]) == 2


async def test_booking_detail_includes_seats(
    client, user_headers, regular_user, bookable_show, db_session
):
    booking = await factories.create_booking(
        db_session, regular_user, bookable_show.show, ["A1", "B1"], total_bill=450
    )

    response = await client.get(
        f"/api/v1/users/bookings/{booking.id}", headers=user_headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_bill"] == 450.0
    assert sorted(s["seats_number"] for s in data["seats"]) == ["A1", "B1"]


async def test_booking_detail_of_another_user(
    client, user_headers, db_session, bookable_show
):
    other_user = await factories.create_user(db_session, "rival@test.com")
    booking = await factories.create_booking(
        db_session, other_user, bookable_show.show, ["A1"], total_bill=300
    )

    response = await client.get(
        f"/api/v1/users/bookings/{booking.id}", headers=user_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Booking not found"


async def test_booking_detail_unknown_id(client, user_headers):
    response = await client.get(
        f"/api/v1/users/bookings/{uuid.uuid4()}", headers=user_headers
    )

    assert response.status_code == 404


# --- CANCELLATION ---
async def test_cancel_booking_releases_seats(
    client, fake_redis, user_headers, db_session, bookable_show
):
    show = bookable_show.show

    book = await _lock_and_book(client, show, user_headers, ["A1"])
    booking_id = book.json()["data"]["booking_id"]

    response = await client.post(
        f"/api/v1/users/bookings/{booking_id}/cancel", headers=user_headers
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Booking cancelled successfully"

    booking = (
        await db_session.execute(
            select(BookingModel).where(BookingModel.id == booking_id)
        )
    ).scalar_one()
    assert booking.is_cancelled is True

    seat = (
        await db_session.execute(
            select(BookedSeatMapModel).where(
                BookedSeatMapModel.booking_id == booking.id
            )
        )
    ).scalar_one()
    assert seat.is_cancelled is True

    # cached layout is refreshed immediately
    layout_body = await fake_redis.json().get(f"show_seat_layout_{show.id}")
    row, col = layout_body["seat_mapping"]["A1"]
    assert layout_body["layout"][row][col]["status"] == "Available"

    # and the seat is genuinely re-bookable by someone else
    other_user = await factories.create_user(db_session, "rival@test.com")
    rebook = await _lock_and_book(
        client, show, auth_headers(other_user.id), ["A1"]
    )
    assert rebook.status_code == 201


async def test_cancel_booking_twice(
    client, user_headers, regular_user, bookable_show, db_session
):
    booking = await factories.create_booking(
        db_session,
        regular_user,
        bookable_show.show,
        ["A1"],
        total_bill=300,
        is_cancelled=True,
    )

    response = await client.post(
        f"/api/v1/users/bookings/{booking.id}/cancel", headers=user_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Booking is already cancelled"


async def test_cancel_booking_within_six_hours_of_show(
    client, user_headers, regular_user, theatre_admin_user, db_session
):
    from datetime import datetime, timedelta, timezone

    soon = await factories.create_bookable_show(
        db_session,
        operator=theatre_admin_user,
        start_time=datetime.now(timezone.utc) + timedelta(hours=3),
    )
    booking = await factories.create_booking(
        db_session, regular_user, soon.show, ["A1"], total_bill=300
    )

    response = await client.post(
        f"/api/v1/users/bookings/{booking.id}/cancel", headers=user_headers
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Booking can only be cancelled at least 6 hours before the show"
    )

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models import LayoutModel, BookedTicketModel
from app.utils.helper import encrypt_data

from tests import factories
from tests.conftest import auth_headers


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _in(hours: float = 0, days: float = 0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=hours, days=days)


async def _other_operator(db_session):
    user = await factories.create_user(
        db_session, "other-operator@test.com", role="theatre_admin"
    )
    return user, auth_headers(user.id)


# --- CREATE LAYOUT ---
async def test_create_layout_stores_polished_layout(
    client, theatre_admin_headers, theatre_admin_user, db_session
):
    theatre = await factories.create_theatre(db_session, operator=theatre_admin_user)

    response = await client.post(
        "/api/v1/theatre-admin/create-layout",
        json={
            "name": "gold layout",
            "layout": factories.raw_layout_grid(),
            "theatre_id": str(theatre.id),
        },
        headers=theatre_admin_headers,
    )

    assert response.status_code == 201
    polished = response.json()["data"]["layout"]
    assert polished["metadata"]["total_seats"] == 5
    assert polished["seat_mapping"]["A1"] == [0, 0]
    assert polished["seat_mapping"]["A2"] == [0, 2]  # aisle gap skipped
    assert polished["category"] == ["gold", "standard"]

    layout = (
        await db_session.execute(
            select(LayoutModel).where(LayoutModel.theatre_id == theatre.id)
        )
    ).scalar_one()
    assert layout.layout["metadata"]["total_seats"] == 5


async def test_create_layout_for_theatre_not_owned(
    client, theatre_admin_headers, db_session
):
    theatre = await factories.create_theatre(db_session)  # no operator mapping

    response = await client.post(
        "/api/v1/theatre-admin/create-layout",
        json={
            "name": "gold layout",
            "layout": factories.raw_layout_grid(),
            "theatre_id": str(theatre.id),
        },
        headers=theatre_admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Theatre not found"


async def test_create_layout_invalid_format(
    client, theatre_admin_headers, theatre_admin_user, db_session
):
    theatre = await factories.create_theatre(db_session, operator=theatre_admin_user)

    response = await client.post(
        "/api/v1/theatre-admin/create-layout",
        json={
            "name": "broken layout",
            "layout": {"layout": [], "metadata": {}},  # no grid_rows/grid_columns
            "theatre_id": str(theatre.id),
        },
        headers=theatre_admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Layout format is not valid"


# --- UPDATE LAYOUT ---
async def test_update_layout_renames(
    client, theatre_admin_headers, bookable_show
):
    response = await client.patch(
        f"/api/v1/theatre-admin/layout/update/{bookable_show.layout.id}",
        json={"name": "renamed layout"},
        headers=theatre_admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "renamed layout"


async def test_update_layout_of_other_admin(client, bookable_show, db_session):
    _, other_headers = await _other_operator(db_session)

    response = await client.patch(
        f"/api/v1/theatre-admin/layout/update/{bookable_show.layout.id}",
        json={"name": "hijacked"},
        headers=other_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Layout not found"


# --- CREATE SCREEN ---
async def test_create_screen(
    client, theatre_admin_headers, theatre_admin_user, db_session
):
    theatre = await factories.create_theatre(db_session, operator=theatre_admin_user)
    layout = await factories.create_layout(db_session, theatre)

    response = await client.post(
        "/api/v1/theatre-admin/create-screen",
        json={
            "name": "Audi 1",
            "theatre_id": str(theatre.id),
            "layout_id": str(layout.id),
        },
        headers=theatre_admin_headers,
    )

    assert response.status_code == 201
    assert response.json()["data"]["name"] == "audi 1"


async def test_create_screen_with_cross_theatre_layout(
    client, theatre_admin_headers, theatre_admin_user, db_session
):
    my_theatre = await factories.create_theatre(
        db_session, operator=theatre_admin_user, name="mine"
    )
    other_theatre = await factories.create_theatre(db_session, name="theirs")
    other_layout = await factories.create_layout(db_session, other_theatre)

    response = await client.post(
        "/api/v1/theatre-admin/create-screen",
        json={
            "name": "audi 1",
            "theatre_id": str(my_theatre.id),
            "layout_id": str(other_layout.id),
        },
        headers=theatre_admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Layout not found"


# --- UPDATE SCREEN ---
async def test_update_screen_renames(client, theatre_admin_headers, bookable_show):
    response = await client.patch(
        f"/api/v1/theatre-admin/screen/update/{bookable_show.screen.id}",
        json={"name": "renamed screen"},
        headers=theatre_admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "renamed screen"


async def test_update_screen_of_other_admin(client, bookable_show, db_session):
    _, other_headers = await _other_operator(db_session)

    response = await client.patch(
        f"/api/v1/theatre-admin/screen/update/{bookable_show.screen.id}",
        json={"name": "hijacked"},
        headers=other_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Screen not found"


# --- CREATE SHOW ---
async def _screen_without_shows(db_session, operator):
    theatre = await factories.create_theatre(db_session, operator=operator)
    layout = await factories.create_layout(db_session, theatre)
    screen = await factories.create_screen(db_session, theatre, layout)
    movie = await factories.create_movie(db_session)
    return screen, movie


async def test_create_show(
    client, theatre_admin_headers, theatre_admin_user, db_session
):
    screen, movie = await _screen_without_shows(db_session, theatre_admin_user)

    response = await client.post(
        "/api/v1/theatre-admin/create-show",
        json={
            "start_time": _iso(_in(days=1)),
            "screen_id": str(screen.id),
            "movie_id": str(movie.id),
            "category_price": factories.CATEGORY_PRICING,
        },
        headers=theatre_admin_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["screen_id"] == str(screen.id)
    assert data["category_pricing"] == factories.CATEGORY_PRICING


async def test_create_show_less_than_two_hours_away(
    client, theatre_admin_headers, theatre_admin_user, db_session
):
    screen, movie = await _screen_without_shows(db_session, theatre_admin_user)

    response = await client.post(
        "/api/v1/theatre-admin/create-show",
        json={
            "start_time": _iso(_in(hours=1)),
            "screen_id": str(screen.id),
            "movie_id": str(movie.id),
            "category_price": factories.CATEGORY_PRICING,
        },
        headers=theatre_admin_headers,
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Show must be scheduled at least 2 hours from now."
    )


async def test_create_show_more_than_three_days_away(
    client, theatre_admin_headers, theatre_admin_user, db_session
):
    screen, movie = await _screen_without_shows(db_session, theatre_admin_user)

    response = await client.post(
        "/api/v1/theatre-admin/create-show",
        json={
            "start_time": _iso(_in(days=4)),
            "screen_id": str(screen.id),
            "movie_id": str(movie.id),
            "category_price": factories.CATEGORY_PRICING,
        },
        headers=theatre_admin_headers,
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Show date cannot be more than 3 days in the future."
    )


async def test_create_show_overlapping_previous_show(
    client, theatre_admin_headers, bookable_show
):
    # existing show starts at +1 day and runs 120 min; +1h is mid-show
    overlapping_start = bookable_show.show.start_time.replace(
        tzinfo=timezone.utc
    ) + timedelta(hours=1)

    response = await client.post(
        "/api/v1/theatre-admin/create-show",
        json={
            "start_time": _iso(overlapping_start),
            "screen_id": str(bookable_show.screen.id),
            "movie_id": str(bookable_show.movie.id),
            "category_price": factories.CATEGORY_PRICING,
        },
        headers=theatre_admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Show is overlapping with previous show"


async def test_create_show_overlapping_next_show(
    client, theatre_admin_headers, bookable_show
):
    # starting 1h before the existing show, the 120-min movie would swallow it
    overlapping_start = bookable_show.show.start_time.replace(
        tzinfo=timezone.utc
    ) - timedelta(hours=1)

    response = await client.post(
        "/api/v1/theatre-admin/create-show",
        json={
            "start_time": _iso(overlapping_start),
            "screen_id": str(bookable_show.screen.id),
            "movie_id": str(bookable_show.movie.id),
            "category_price": factories.CATEGORY_PRICING,
        },
        headers=theatre_admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Show is overlapping with next movie"


async def test_create_show_missing_category_price(
    client, theatre_admin_headers, theatre_admin_user, db_session
):
    screen, movie = await _screen_without_shows(db_session, theatre_admin_user)

    response = await client.post(
        "/api/v1/theatre-admin/create-show",
        json={
            "start_time": _iso(_in(days=1)),
            "screen_id": str(screen.id),
            "movie_id": str(movie.id),
            "category_price": {"standard": 150.0},  # gold missing
        },
        headers=theatre_admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Category not found in price list"


async def test_create_show_unknown_movie(
    client, theatre_admin_headers, theatre_admin_user, db_session
):
    screen, _ = await _screen_without_shows(db_session, theatre_admin_user)

    response = await client.post(
        "/api/v1/theatre-admin/create-show",
        json={
            "start_time": _iso(_in(days=1)),
            "screen_id": str(screen.id),
            "movie_id": str(uuid.uuid4()),
            "category_price": factories.CATEGORY_PRICING,
        },
        headers=theatre_admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


async def test_create_show_on_screen_not_owned(
    client, bookable_show, db_session
):
    _, other_headers = await _other_operator(db_session)

    response = await client.post(
        "/api/v1/theatre-admin/create-show",
        json={
            "start_time": _iso(_in(days=1)),
            "screen_id": str(bookable_show.screen.id),
            "movie_id": str(bookable_show.movie.id),
            "category_price": factories.CATEGORY_PRICING,
        },
        headers=other_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Screen not found"


# --- UPDATE SHOW ---
async def test_update_show_pricing(client, theatre_admin_headers, bookable_show):
    new_pricing = {"gold": 350.0, "standard": 200.0}

    response = await client.patch(
        f"/api/v1/theatre-admin/show/update/{bookable_show.show.id}",
        json={"category_price": new_pricing},
        headers=theatre_admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["category_pricing"] == new_pricing


async def test_update_show_pricing_missing_category(
    client, theatre_admin_headers, bookable_show
):
    response = await client.patch(
        f"/api/v1/theatre-admin/show/update/{bookable_show.show.id}",
        json={"category_price": {"standard": 200.0}},
        headers=theatre_admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Category not found in price list"


async def test_update_show_empty_body_is_noop(
    client, theatre_admin_headers, bookable_show
):
    response = await client.patch(
        f"/api/v1/theatre-admin/show/update/{bookable_show.show.id}",
        json={},
        headers=theatre_admin_headers,
    )

    assert response.status_code == 200
    assert (
        response.json()["data"]["category_pricing"]
        == bookable_show.show.category_pricing
    )


async def test_update_show_of_other_admin(client, bookable_show, db_session):
    _, other_headers = await _other_operator(db_session)

    response = await client.patch(
        f"/api/v1/theatre-admin/show/update/{bookable_show.show.id}",
        json={"category_price": factories.CATEGORY_PRICING},
        headers=other_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Show not found"


# --- OWNERSHIP-SCOPED LISTS ---
async def test_my_theatres_only_shows_own(
    client, theatre_admin_headers, theatre_admin_user, db_session
):
    other_user, _ = await _other_operator(db_session)
    await factories.create_theatre(
        db_session, operator=theatre_admin_user, name="my theatre"
    )
    await factories.create_theatre(
        db_session, operator=other_user, name="their theatre"
    )

    response = await client.get(
        "/api/v1/theatre-admin/my-theatres", headers=theatre_admin_headers
    )

    assert response.status_code == 200
    names = [t["name"] for t in response.json()["data"]]
    assert names == ["my theatre"]


async def test_my_screens_includes_details(
    client, theatre_admin_headers, bookable_show
):
    response = await client.get(
        "/api/v1/theatre-admin/my-screens", headers=theatre_admin_headers
    )

    assert response.status_code == 200
    screens = response.json()["data"]
    assert len(screens) == 1
    assert screens[0]["theatre_name"] == bookable_show.theatre.name
    assert screens[0]["layout_name"] == bookable_show.layout.name


# --- DELETES (SOFT) ---
async def test_delete_screen(
    client, theatre_admin_headers, bookable_show, db_session
):
    response = await client.delete(
        f"/api/v1/theatre-admin/screen/delete/{bookable_show.screen.id}",
        headers=theatre_admin_headers,
    )

    assert response.status_code == 200

    await db_session.refresh(bookable_show.screen)
    assert bookable_show.screen.is_active is False


async def test_delete_screen_of_other_admin(client, bookable_show, db_session):
    _, other_headers = await _other_operator(db_session)

    response = await client.delete(
        f"/api/v1/theatre-admin/screen/delete/{bookable_show.screen.id}",
        headers=other_headers,
    )

    assert response.status_code == 404


async def test_delete_show(client, theatre_admin_headers, bookable_show, db_session):
    response = await client.delete(
        f"/api/v1/theatre-admin/show/delete/{bookable_show.show.id}",
        headers=theatre_admin_headers,
    )

    assert response.status_code == 200

    await db_session.refresh(bookable_show.show)
    assert bookable_show.show.is_deleted is True


async def test_delete_show_of_other_admin(client, bookable_show, db_session):
    _, other_headers = await _other_operator(db_session)

    response = await client.delete(
        f"/api/v1/theatre-admin/show/delete/{bookable_show.show.id}",
        headers=other_headers,
    )

    assert response.status_code == 404


# --- VERIFY TICKET ---
async def _create_ticket(db_session, booking, show):
    """Create a QR ticket row the way book_ticket_service does."""
    ticket_hash = await encrypt_data(str(booking.id))
    db_session.add(
        BookedTicketModel(
            booking_id=booking.id,
            ticket_hash=ticket_hash,
            expired_time=show.start_time + timedelta(hours=2),
        )
    )
    await db_session.commit()
    return ticket_hash.decode()


async def test_verify_ticket_marks_it_used(
    client, theatre_admin_headers, bookable_show, regular_user, db_session
):
    booking = await factories.create_booking(
        db_session, regular_user, bookable_show.show, seats=["A1"], total_bill=300
    )
    ticket_hash = await _create_ticket(db_session, booking, bookable_show.show)

    response = await client.post(
        "/api/v1/theatre-admin/verify-ticket",
        json={"ticket_hash": ticket_hash},
        headers=theatre_admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Ticket verified successfully"

    ticket = (
        await db_session.execute(
            select(BookedTicketModel).where(
                BookedTicketModel.booking_id == booking.id
            )
        )
    ).scalar_one()
    assert ticket.is_used is True


async def test_verify_ticket_cannot_be_reused(
    client, theatre_admin_headers, bookable_show, regular_user, db_session
):
    booking = await factories.create_booking(
        db_session, regular_user, bookable_show.show, seats=["A1"], total_bill=300
    )
    ticket_hash = await _create_ticket(db_session, booking, bookable_show.show)

    first = await client.post(
        "/api/v1/theatre-admin/verify-ticket",
        json={"ticket_hash": ticket_hash},
        headers=theatre_admin_headers,
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/theatre-admin/verify-ticket",
        json={"ticket_hash": ticket_hash},
        headers=theatre_admin_headers,
    )
    assert second.status_code == 404
    assert second.json()["detail"] == "Ticket is not valid"


async def test_verify_ticket_of_cancelled_booking(
    client, theatre_admin_headers, bookable_show, regular_user, db_session
):
    booking = await factories.create_booking(
        db_session,
        regular_user,
        bookable_show.show,
        seats=["A1"],
        total_bill=300,
        is_cancelled=True,
    )
    ticket_hash = await _create_ticket(db_session, booking, bookable_show.show)

    response = await client.post(
        "/api/v1/theatre-admin/verify-ticket",
        json={"ticket_hash": ticket_hash},
        headers=theatre_admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket is not valid"


async def test_verify_ticket_from_other_operators_theatre(
    client, bookable_show, regular_user, db_session
):
    _, other_headers = await _other_operator(db_session)
    booking = await factories.create_booking(
        db_session, regular_user, bookable_show.show, seats=["A1"], total_bill=300
    )
    ticket_hash = await _create_ticket(db_session, booking, bookable_show.show)

    response = await client.post(
        "/api/v1/theatre-admin/verify-ticket",
        json={"ticket_hash": ticket_hash},
        headers=other_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket Not Found"


async def test_verify_ticket_garbage_hash_is_500(client, theatre_admin_headers):
    # Current behavior: an undecryptable hash raises inside Fernet and is
    # swallowed by the global exception middleware as a 500, not a 4xx.
    response = await client.post(
        "/api/v1/theatre-admin/verify-ticket",
        json={"ticket_hash": "not-a-real-ticket"},
        headers=theatre_admin_headers,
    )

    assert response.status_code == 500
    assert response.json()["error"] == "Internal server error"

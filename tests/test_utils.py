from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.services.admin_service import (
    _parse_omdb_runtime_minutes,
    _parse_omdb_rating,
)
from app.utils.helper import (
    generate_otp,
    _generate_token,
    decode_token,
    generate_access_token_and_refresh_token,
    blacklist_token,
    is_token_revoked,
    encrypt_data,
    decrypt_data,
)
from app.utils.polish_seat_layout import polish_seat_layout
from app.utils.seat_lock_script import acquire_seat_locks

from tests import factories


# --- OTP ---
def test_generate_otp_is_six_digits():
    for _ in range(20):
        otp = generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()


# --- JWT ---
def test_token_roundtrip_with_type_enforcement():
    tokens = generate_access_token_and_refresh_token(
        payload={"user_id": "abc-123"}, response=None
    )

    access = decode_token(
        tokens["access_token"],
        settings.JWT_SECRET_ACCESS_KEY,
        expected_type="access",
    )
    assert access["sub"] == "abc-123"
    assert access["jti"]

    # an access token is not accepted where a refresh token is expected
    assert (
        decode_token(
            tokens["access_token"],
            settings.JWT_SECRET_ACCESS_KEY,
            expected_type="refresh",
        )
        is None
    )

    # and each token type is signed with its own secret
    assert (
        decode_token(
            tokens["refresh_token"],
            settings.JWT_SECRET_ACCESS_KEY,
            expected_type="refresh",
        )
        is None
    )


def test_decode_expired_token():
    token = _generate_token(
        data={"user_id": "abc-123"},
        expires_delta=timedelta(seconds=-10),
        secret=settings.JWT_SECRET_ACCESS_KEY,
        token_type="access",
    )

    assert decode_token(token, settings.JWT_SECRET_ACCESS_KEY) is None


def test_decode_garbage_token():
    assert decode_token("not-a-jwt", settings.JWT_SECRET_ACCESS_KEY) is None


def test_every_token_gets_a_unique_jti():
    jtis = set()
    for _ in range(5):
        tokens = generate_access_token_and_refresh_token(
            payload={"user_id": "abc-123"}, response=None
        )
        payload = decode_token(
            tokens["access_token"], settings.JWT_SECRET_ACCESS_KEY
        )
        jtis.add(payload["jti"])
    assert len(jtis) == 5


# --- TOKEN REVOCATION ---
async def test_blacklist_and_check_revocation(fake_redis):
    tokens = generate_access_token_and_refresh_token(
        payload={"user_id": "abc-123"}, response=None
    )
    payload = decode_token(tokens["access_token"], settings.JWT_SECRET_ACCESS_KEY)

    assert await is_token_revoked(fake_redis, payload["jti"]) is False

    await blacklist_token(fake_redis, payload["jti"], payload["exp"])

    assert await is_token_revoked(fake_redis, payload["jti"]) is True
    # the revocation entry expires with the token itself
    assert await fake_redis.ttl(f"revoked_token_{payload['jti']}") > 0


async def test_blacklisting_expired_token_is_noop(fake_redis):
    token = _generate_token(
        data={"user_id": "abc-123"},
        expires_delta=timedelta(seconds=-10),
        secret=settings.JWT_SECRET_ACCESS_KEY,
        token_type="access",
    )
    from jose import jwt

    payload = jwt.decode(
        token,
        settings.JWT_SECRET_ACCESS_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"verify_exp": False},
    )

    await blacklist_token(fake_redis, payload["jti"], payload["exp"])

    assert await is_token_revoked(fake_redis, payload["jti"]) is False


# --- FERNET ENCRYPTION ---
async def test_encrypt_decrypt_roundtrip():
    encrypted = await encrypt_data("some-booking-id")

    assert isinstance(encrypted, bytes)
    assert await decrypt_data(encrypted) == "some-booking-id"


# --- OMDB PARSERS ---
def test_parse_omdb_runtime():
    assert _parse_omdb_runtime_minutes("142 min") == 142


@pytest.mark.parametrize("bad_runtime", ["N/A", None, "", "abc min"])
def test_parse_omdb_runtime_invalid(bad_runtime):
    with pytest.raises(HTTPException) as exc_info:
        _parse_omdb_runtime_minutes(bad_runtime)
    assert exc_info.value.status_code == 400


def test_parse_omdb_rating():
    assert _parse_omdb_rating("8.8") == 8.8
    assert _parse_omdb_rating("N/A") == 0.0
    assert _parse_omdb_rating(None) == 0.0


# --- SEAT LAYOUT POLISHING ---
def test_polish_seat_layout_numbers_seats_and_skips_aisles():
    polished = polish_seat_layout(factories.raw_layout_grid())

    assert polished["metadata"]["total_seats"] == 5
    assert polished["category"] == ["gold", "standard"]
    # the aisle between the two gold seats does not consume a seat number
    assert polished["seat_mapping"] == {
        "A1": [0, 0],
        "A2": [0, 2],
        "B1": [1, 0],
        "B2": [1, 1],
        "B3": [1, 2],
    }
    aisle = polished["layout"][0][1]
    assert aisle["grid_type"] == "aisle"
    assert aisle["seat_number"] is None


def test_polish_seat_layout_preserves_none_gaps():
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

    polished = polish_seat_layout(grid)

    assert polished["layout"][0][1] is None
    assert polished["seat_mapping"] == {"A1": [0, 0], "A2": [0, 2]}


def test_polish_seat_layout_seatless_row_does_not_consume_label():
    grid = {
        "layout": [
            [{"grid_type": "seat", "category": "standard"}],
            [None],  # walkway row
            [{"grid_type": "seat", "category": "standard"}],
        ],
        "metadata": {"grid_rows": 3, "grid_columns": 1},
    }

    polished = polish_seat_layout(grid)

    # the walkway row is skipped, so the third row is B, not C
    assert list(polished["seat_mapping"]) == ["A1", "B1"]


def test_polish_seat_layout_invalid_inputs():
    assert polish_seat_layout({"layout": "not-a-list", "metadata": {}}) is None
    assert polish_seat_layout({"layout": []}) is None
    assert (
        polish_seat_layout({"layout": [], "metadata": {"grid_rows": 2}}) is None
    )


# --- ATOMIC SEAT LOCK SCRIPT ---
async def test_acquire_seat_locks_all_or_nothing(fake_redis):
    acquired = await acquire_seat_locks(
        fake_redis, show_id="show1", user_id="user1", seat_array=["A1", "A2"]
    )
    assert acquired is True

    locks = await fake_redis.hgetall("show_seat_locked_show1")
    assert locks == {"A1": "user1", "A2": "user1"}
    assert await fake_redis.ttl("show_seat_locked_show1") > 0

    # A2 conflicts, so B1 must not be written either
    acquired = await acquire_seat_locks(
        fake_redis, show_id="show1", user_id="user2", seat_array=["A2", "B1"]
    )
    assert acquired is False
    assert await fake_redis.hgetall("show_seat_locked_show1") == {
        "A1": "user1",
        "A2": "user1",
    }


async def test_acquire_seat_locks_isolated_per_show(fake_redis):
    assert await acquire_seat_locks(
        fake_redis, show_id="show1", user_id="user1", seat_array=["A1"]
    )
    # the same seat number in a different show is a different key
    assert await acquire_seat_locks(
        fake_redis, show_id="show2", user_id="user2", seat_array=["A1"]
    )

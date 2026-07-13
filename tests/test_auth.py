from sqlalchemy import select

from app.models import UserModel
from app.core.config import settings
from app.utils.helper import decode_token

from tests import factories
from tests.conftest import auth_headers, make_tokens


# --- SEND OTP ---
async def test_send_otp_stores_otp_and_queues_email(
    client, fake_redis, fake_email_service
):
    response = await client.post(
        "/api/v1/auth/send-otp", json={"email": "new@test.com"}
    )

    assert response.status_code == 200
    assert response.json()["data"] == {"email": "new@test.com"}

    cached = await fake_redis.hgetall("new@test.com")
    assert cached["tries"] == "3"
    assert len(cached["otp"]) == 6
    assert await fake_redis.ttl("new@test.com") > 0

    assert fake_email_service.otp_emails == [
        {"email_to": "new@test.com", "otp": cached["otp"]}
    ]


# --- SIGNIN ---
async def _request_otp(client, fake_redis, email: str) -> str:
    await client.post("/api/v1/auth/send-otp", json={"email": email})
    return (await fake_redis.hgetall(email))["otp"]


async def test_signin_creates_new_user_and_returns_tokens(
    client, fake_redis, db_session
):
    otp = await _request_otp(client, fake_redis, "new@test.com")

    response = await client.post(
        "/api/v1/auth/signin", json={"email": "new@test.com", "otp": otp}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "User created successfully"

    user = (
        await db_session.execute(
            select(UserModel).where(UserModel.email == "new@test.com")
        )
    ).scalar_one()

    access_payload = decode_token(
        body["data"]["access_token"],
        settings.JWT_SECRET_ACCESS_KEY,
        expected_type="access",
    )
    assert access_payload["sub"] == str(user.id)

    refresh_payload = decode_token(
        body["data"]["refresh_token"],
        settings.JWT_SECRET_REFRESH_KEY,
        expected_type="refresh",
    )
    assert refresh_payload["sub"] == str(user.id)

    # OTP is consumed on success
    assert await fake_redis.hgetall("new@test.com") == {}


async def test_signin_existing_user_logs_in(client, fake_redis, regular_user):
    otp = await _request_otp(client, fake_redis, regular_user.email)

    response = await client.post(
        "/api/v1/auth/signin", json={"email": regular_user.email, "otp": otp}
    )

    assert response.status_code == 201
    assert response.json()["message"] == "User login successfully"


async def test_signin_without_requesting_otp(client):
    response = await client.post(
        "/api/v1/auth/signin", json={"email": "ghost@test.com", "otp": "123456"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "OTP not found or expired"


async def test_signin_wrong_otp_decrements_tries(client, fake_redis):
    await _request_otp(client, fake_redis, "new@test.com")

    response = await client.post(
        "/api/v1/auth/signin", json={"email": "new@test.com", "otp": "000000"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect OTP. 2 tries left."
    assert (await fake_redis.hgetall("new@test.com"))["tries"] == "2"


async def test_signin_exhausting_tries_deletes_otp(client, fake_redis):
    otp = await _request_otp(client, fake_redis, "new@test.com")

    for _ in range(2):
        await client.post(
            "/api/v1/auth/signin", json={"email": "new@test.com", "otp": "000000"}
        )

    response = await client.post(
        "/api/v1/auth/signin", json={"email": "new@test.com", "otp": "000000"}
    )

    assert response.status_code == 400
    assert "All tries exhausted" in response.json()["detail"]
    assert await fake_redis.hgetall("new@test.com") == {}

    # even the correct OTP no longer works
    response = await client.post(
        "/api/v1/auth/signin", json={"email": "new@test.com", "otp": otp}
    )
    assert response.status_code == 404


async def test_signin_deleted_account_rejected(client, fake_redis, db_session):
    await factories.create_user(db_session, "gone@test.com", is_active=False)
    otp = await _request_otp(client, fake_redis, "gone@test.com")

    response = await client.post(
        "/api/v1/auth/signin", json={"email": "gone@test.com", "otp": otp}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "User account is deleted"


# --- REFRESH ---
async def test_refresh_rotates_tokens_and_revokes_old(client, regular_user):
    old_refresh = make_tokens(regular_user.id)["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["access_token"]
    assert data["refresh_token"] != old_refresh

    # the old refresh token is single-use
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh token has been revoked"


async def test_refresh_rejects_access_token(client, regular_user):
    access_token = make_tokens(regular_user.id)["access_token"]

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": access_token}
    )

    assert response.status_code == 401


async def test_refresh_rejects_garbage_token(client):
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "not-a-jwt"}
    )

    assert response.status_code == 401


# --- LOGOUT ---
async def test_logout_revokes_access_token(client, regular_user):
    headers = auth_headers(regular_user.id)

    response = await client.post("/api/v1/auth/logout", json={}, headers=headers)
    assert response.status_code == 200

    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Token has been revoked"


async def test_logout_also_revokes_refresh_token(client, regular_user):
    tokens = make_tokens(regular_user.id)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=headers,
    )
    assert response.status_code == 200

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 401


# --- TOKEN VALIDATION ON PROTECTED ROUTES ---
async def test_protected_route_without_token(client):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


async def test_protected_route_with_tampered_token(client, regular_user):
    token = make_tokens(regular_user.id)["access_token"]
    tampered = token[:-4] + "aaaa"

    response = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {tampered}"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


async def test_protected_route_rejects_refresh_token(client, regular_user):
    refresh_token = make_tokens(regular_user.id)["refresh_token"]

    response = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {refresh_token}"}
    )

    assert response.status_code == 401


# --- GOOGLE OAUTH CALLBACK ---
class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json


class _FakeGoogleClient:
    """Stands in for the httpx.AsyncClient the auth service opens for Google."""

    def __init__(self, post_response, get_response=None):
        self._post_response = post_response
        self._get_response = get_response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, **kwargs):
        return self._post_response

    async def get(self, url, **kwargs):
        return self._get_response


async def _seed_oauth_state(fake_redis, state: str = "test-state") -> str:
    await fake_redis.set(f"oauth_state_{state}", "1", ex=600)
    return state


async def test_google_login_redirects_with_state(client, fake_redis):
    response = await client.get("/api/v1/auth/google/login")

    assert response.status_code == 307
    location = response.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/auth?")
    assert "state=" in location

    state = location.split("state=")[1].split("&")[0]
    assert await fake_redis.exists(f"oauth_state_{state}")


async def test_google_callback_creates_user(
    client, fake_redis, db_session, monkeypatch
):
    fake_google = _FakeGoogleClient(
        post_response=_FakeResponse({"access_token": "google-token"}),
        get_response=_FakeResponse(
            {
                "email": "google@test.com",
                "sub": "google-id-123",
                "given_name": "Goo",
                "family_name": "Gle",
            }
        ),
    )
    monkeypatch.setattr(
        "app.services.auth_service.httpx.AsyncClient", lambda: fake_google
    )
    state = await _seed_oauth_state(fake_redis)

    response = await client.get(
        f"/api/v1/auth/google/callback?code=abc&state={state}"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == "google@test.com"
    assert data["access_token"]

    user = (
        await db_session.execute(
            select(UserModel).where(UserModel.email == "google@test.com")
        )
    ).scalar_one()
    assert user.google_id == "google-id-123"


async def test_google_callback_token_exchange_failure(
    client, fake_redis, monkeypatch
):
    fake_google = _FakeGoogleClient(
        post_response=_FakeResponse(
            {"error": "invalid_grant", "error_description": "Bad code"},
            status_code=400,
        )
    )
    monkeypatch.setattr(
        "app.services.auth_service.httpx.AsyncClient", lambda: fake_google
    )
    state = await _seed_oauth_state(fake_redis)

    response = await client.get(
        f"/api/v1/auth/google/callback?code=bad&state={state}"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Bad code"


async def test_google_callback_rejects_unknown_state(client):
    response = await client.get(
        "/api/v1/auth/google/callback?code=abc&state=forged-state"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired OAuth state"


async def test_google_callback_state_is_single_use(
    client, fake_redis, monkeypatch
):
    fake_google = _FakeGoogleClient(
        post_response=_FakeResponse({"access_token": "google-token"}),
        get_response=_FakeResponse(
            {"email": "google@test.com", "sub": "google-id-123"}
        ),
    )
    monkeypatch.setattr(
        "app.services.auth_service.httpx.AsyncClient", lambda: fake_google
    )
    state = await _seed_oauth_state(fake_redis)

    first = await client.get(f"/api/v1/auth/google/callback?code=abc&state={state}")
    assert first.status_code == 200

    second = await client.get(
        f"/api/v1/auth/google/callback?code=abc&state={state}"
    )
    assert second.status_code == 400
    assert second.json()["detail"] == "Invalid or expired OAuth state"


async def test_google_callback_requires_state_param(client):
    response = await client.get("/api/v1/auth/google/callback?code=abc")

    assert response.status_code == 422

import pytest
from fastapi import status
from tests.conftest import global_fake_redis
from tests.test_utils import assert_response_structure


@pytest.mark.asyncio(loop_scope="session")
class TestAuthentication:

    async def test_send_otp_success(self, client):
        email = "jaymin.dave@armakuni.com"

        response = await client.post("/api/v1/auth/send-otp", json={"email": email})

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert_response_structure(body)
        assert body["message"] == "OTP sent to your email"
        assert await global_fake_redis.exists(email)

    async def test_signin_success(self, client):
        email = "jaymin4724@gmail.com"
        await client.post("/api/v1/auth/send-otp", json={"email": email})
        otp = await global_fake_redis.hget(email, "otp")

        response = await client.post(
            "/api/v1/auth/signin", json={"email": email, "otp": otp}
        )

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert_response_structure(body)
        assert "successfully" in body["message"].lower()
        assert "access_token" in body["data"]
        assert "refresh_token" in body["data"]

    async def test_google_login_redirect(self, client):
        response = await client.get("/api/v1/auth/google/login", follow_redirects=False)

        assert response.status_code in [
            status.HTTP_302_FOUND,
            status.HTTP_307_TEMPORARY_REDIRECT,
        ]
        assert "accounts.google.com" in response.headers["location"]

import pytest
from fastapi import status
from tests.conftest import global_fake_redis
from tests.test_utils import assert_response_structure


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

        signin_payload = {"email": email, "otp": otp}
        response = await client.post("/api/v1/auth/signin", json=signin_payload)

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert_response_structure(body)
        
        assert "successfully" in body["message"]

    async def test_google_login_redirect(self, client):
        response = await client.get("/api/v1/auth/google/login", follow_redirects=False)
        assert response.status_code in [
            status.HTTP_302_FOUND,
            status.HTTP_307_TEMPORARY_REDIRECT,
        ]
        assert "accounts.google.com" in response.headers["location"]

    async def test_signin_invalid_otp(self, client):
        email = "jaymin.dave@armakuni.com"
        await client.post("/api/v1/auth/send-otp", json={"email": email})

        signin_payload = {"email": email, "otp": "000000"}
        response = await client.post("/api/v1/auth/signin", json=signin_payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.json()
from fastapi import status
from tests.test_utils import create_user_data


class TestUserFlow:
    async def test_full_booking_workflow(self, client):
        user_data = create_user_data()
        reg_res = await client.post("/auth/signup", json=user_data)
        assert reg_res.status_code == status.HTTP_201_CREATED

        token = reg_res.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        search_res = await client.get("/search?input=Inception&location=Ahmedabad")
        assert search_res.status_code == status.HTTP_200_OK
        movie_id = search_res.json()["data"][0]["id"]

        theatre_res = await client.get(f"/movie/{movie_id}")
        assert theatre_res.status_code == status.HTTP_200_OK
        theatre_id = theatre_res.json()["data"][0]["id"]

        shows_res = await client.get(f"/movie/{movie_id}/{theatre_id}")
        assert shows_res.status_code == status.HTTP_200_OK
        show_id = shows_res.json()["data"][0]["id"]

        layout_res = await client.get(f"/movie/{movie_id}/{theatre_id}/{show_id}")
        assert layout_res.status_code == status.HTTP_200_OK

        reserve_payload = {"row_num": "A", "column_num": 1}
        lock_res = await client.post(
            f"/movie/{movie_id}/{theatre_id}/{show_id}/reserve",
            json=reserve_payload,
            headers=headers,
        )
        assert lock_res.status_code == status.HTTP_201_CREATED
        seat_id = lock_res.json()["data"]["seat_id"]
        assert lock_res.json()["message"] == "Seat locked temporarily"

        payment_payload = {"payment_details": "tok_visa_dummy"}
        pay_res = await client.post(
            f"/movie/{movie_id}/{theatre_id}/{show_id}/{seat_id}/payment",
            json=payment_payload,
            headers=headers,
        )
        assert pay_res.status_code == status.HTTP_200_OK
        assert "ticket_url" in pay_res.json()["data"]

    async def test_magic_link_flow(self, client):
        email_payload = {"email": "magic@example.com"}
        response = await client.post("/auth/verify", json=email_payload)
        assert response.status_code == status.HTTP_200_OK
        assert "Magic Link" in response.json()["message"]

    async def test_double_booking_prevention(self, client):
        show_path = "/movie/1/1/1"
        reserve_data = {"row_num": "A", "column_num": 1}
        await client.post(f"{show_path}/reserve", json=reserve_data)
        response = await client.post(f"{show_path}/reserve", json=reserve_data)
        assert response.status_code == status.HTTP_409_CONFLICT

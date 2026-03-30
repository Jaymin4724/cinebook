from fastapi import status
from tests.test_utils import (
    assert_response_structure,
    create_movie_data,
    create_show_data,
)


class TestAdminFlow:
    async def test_super_admin_create_theatre_admin(self, client):
        headers = {"Authorization": "Bearer super_admin_token"}
        
        admin_payload = {
            "email": "new_owner@cinema.com",
            "name": "John Owner",
            "role": "theatre_admin",
        }

        response = await client.post(
            "/admin/theatre-admins", json=admin_payload, headers=headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["data"]["role"] == "theatre_admin"

    async def test_super_admin_manage_movies(self, client):
        headers = {"Authorization": "Bearer super_admin_token"}
        movie_data = create_movie_data("Interstellar")

        response = await client.post("/admin/movies", json=movie_data, headers=headers)
        assert response.status_code == status.HTTP_201_CREATED
        movie_id = response.json()["data"]["id"]

        update_res = await client.put(
            f"/admin/movies/{movie_id}",
            json={"title": "Interstellar IMAX"},
            headers=headers,
        )
        assert update_res.status_code == status.HTTP_200_OK

    async def test_super_admin_user_oversight(self, client):
        headers = {"Authorization": "Bearer super_admin_token"}
        response = await client.get("/admin/users", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json()["data"], list)

    # --- THEATRE ADMIN PRIVILEGES ---

    async def test_theatre_admin_manage_screens(self, client):
        headers = {"Authorization": "Bearer theatre_admin_token"}
        screen_payload = {"screen_number": 1, "capacity": 100}

        response = await client.post(
            "/theatre-admin/screens", json=screen_payload, headers=headers
        )
        assert response.status_code == status.HTTP_201_CREATED

    async def test_theatre_admin_create_show(self, client):
        headers = {"Authorization": "Bearer theatre_admin_token"}
        show_payload = create_show_data(movie_id=1, screen_id=1)

        response = await client.post(
            "/theatre-admin/shows", json=show_payload, headers=headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert_response_structure(response.json())

    async def test_theatre_admin_cannot_access_super_admin_routes(self, client):
        headers = {"Authorization": "Bearer theatre_admin_token"}
        # Theatre Admin trying to delete another admin
        response = await client.delete("/admin/theatre-admins/2", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_unauthorized_user_cannot_create_shows(self, client):
        headers = {"Authorization": "Bearer regular_user_token"}
        show_payload = create_show_data()

        response = await client.post(
            "/theatre-admin/shows", json=show_payload, headers=headers
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
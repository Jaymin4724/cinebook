def assert_response_structure(body: dict, success: bool = True):
    assert "success" in body
    assert "message" in body
    assert "data" in body
    assert body["success"] is success


def create_user_data(email="test@example.com", name="Test User", role="user"):
    return {"email": email, "name": name, "password": "password123", "role": role}


def create_movie_data(title="Inception"):
    return {
        "title": title,
        "description": "A mind-bending thriller",
        "duration": 148,
        "genre": "Sci-Fi",
    }


def create_theatre_data(name="Grand Cinema"):
    return {"name": name, "location": "Ahmedabad", "owner_id": 1}


def create_show_data(movie_id=1, screen_id=1):
    return {
        "movie_id": movie_id,
        "screen_id": screen_id,
        "start_time": "2024-05-01T20:00:00",
        "price": 15.0,
    }

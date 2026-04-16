def assert_response_structure(body: dict, success: bool = True):
    assert "success" in body
    assert "message" in body
    assert "data" in body
    assert body["success"] is success


def assert_list_response(body: dict):
    assert_response_structure(body)
    assert isinstance(body["data"], list)

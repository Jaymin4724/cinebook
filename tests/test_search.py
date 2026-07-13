import uuid


class StubES:
    """Stands in for the module-level Elasticsearch client in search_service."""

    def __init__(self, hits=None, fail: bool = False):
        self.hits = hits or []
        self.fail = fail

    async def search(self, index, body):
        if self.fail:
            raise ConnectionError("es down")
        return {"hits": {"hits": self.hits}}


def _hit(name: str, doc_type: str, score: float = 1.0):
    return {
        "_score": score,
        "_source": {"name": name, "type": doc_type, "db_id": str(uuid.uuid4())},
    }


async def test_search_returns_mapped_hits(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.search_service.es",
        StubES(hits=[_hit("inception", "movie", 2.5), _hit("inox", "theatre")]),
    )

    response = await client.get("/api/v1/search/?q=in")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 2
    first = data["items"][0]
    assert first["name"] == "inception"
    assert first["type"] == "movie"
    assert first["score"] == 2.5
    assert first["db_id"]


async def test_search_no_results(client, monkeypatch):
    monkeypatch.setattr("app.services.search_service.es", StubES(hits=[]))

    response = await client.get("/api/v1/search/?q=zzz")

    assert response.status_code == 200
    assert response.json()["data"] == {"items": [], "total": 0}


async def test_search_es_failure_returns_503(client, monkeypatch):
    monkeypatch.setattr("app.services.search_service.es", StubES(fail=True))

    response = await client.get("/api/v1/search/?q=inception")

    assert response.status_code == 503
    assert response.json()["detail"] == "Search is temporarily unavailable"


async def test_search_validates_query_params(client):
    # empty q
    response = await client.get("/api/v1/search/?q=")
    assert response.status_code == 422

    # limit above the cap
    response = await client.get("/api/v1/search/?q=inception&limit=51")
    assert response.status_code == 422

    # limit below the floor
    response = await client.get("/api/v1/search/?q=inception&limit=0")
    assert response.status_code == 422

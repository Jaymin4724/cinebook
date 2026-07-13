class StubES:
    def __init__(self, ok: bool = True):
        self.ok = ok

    async def ping(self):
        if not self.ok:
            raise ConnectionError("es down")
        return True


async def test_health_all_ok(client, monkeypatch):
    monkeypatch.setattr("app.main.es", StubES(ok=True))

    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {
        "database": "ok",
        "redis": "ok",
        "elasticsearch": "ok",
    }


async def test_health_degraded_when_es_down(client, monkeypatch):
    monkeypatch.setattr("app.main.es", StubES(ok=False))

    response = await client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["elasticsearch"] == "unavailable"
    assert body["checks"]["database"] == "ok"


async def test_health_degraded_when_redis_down(client, fake_redis, monkeypatch):
    monkeypatch.setattr("app.main.es", StubES(ok=True))

    async def broken_ping(*args, **kwargs):
        raise ConnectionError("redis down")

    monkeypatch.setattr(fake_redis, "ping", broken_ping)

    response = await client.get("/health")

    assert response.status_code == 503
    assert response.json()["checks"]["redis"] == "unavailable"

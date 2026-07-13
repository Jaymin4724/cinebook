import fakeredis.aioredis


def create_fake_redis():
    """Create a fresh fake Redis instance for a single test.

    Uses real `fakeredis` so EVAL/Lua scripts (`lupa`) and RedisJSON
    commands (`jsonpath-ng`) behave like the real server.
    """
    return fakeredis.aioredis.FakeRedis(decode_responses=True)

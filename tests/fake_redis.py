import json
from fakeredis import FakeServer
from fakeredis.aioredis import FakeRedis


class FakeRedisJSON:

    def __init__(self, redis):
        self.redis = redis

    async def get(self, name, *args, **kwargs):
        data = await self.redis.get(name)
        return json.loads(data) if data else None

    async def set(self, name=None, path=None, obj=None, *args, **kwargs):
        await self.redis.set(name, json.dumps(obj))


class FakePipeline:

    def __init__(self, redis):
        self.redis = redis
        self.commands = []

    def json(self):
        return self

    def set(self, name=None, path=None, obj=None, *args, **kwargs):
        self.commands.append(("set", name, obj))

    def expire(self, name, time):
        self.commands.append(("expire", name, time))

    def hsetnx(self, name, key, value):
        self.commands.append(("hsetnx", name, key, value))

    def hdel(self, name, key):
        self.commands.append(("hdel", name, key))

    async def execute(self):
        for cmd in self.commands:
            if cmd[0] == "set":
                await self.redis.set(cmd[1], json.dumps(cmd[2]))

            elif cmd[0] == "expire":
                await self.redis.expire(cmd[1], cmd[2])

            elif cmd[0] == "hsetnx":
                name, key, value = cmd[1], cmd[2], cmd[3]
                exists = await self.redis.hexists(name, key)
                if not exists:
                    await self.redis.hset(name, key, value)

            elif cmd[0] == "hdel":
                name, key = cmd[1], cmd[2]
                await self.redis.hdel(name, key)

        self.commands.clear()
        return []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


def _add_json_support(redis):
    redis.json = lambda: FakeRedisJSON(redis)
    return redis


def _patch_pipeline(redis):
    redis.pipeline = lambda *args, **kwargs: FakePipeline(redis)
    return redis


# Single shared instance used by all tests via import.
_shared_server = FakeServer()
global_fake_redis = FakeRedis(server=_shared_server, decode_responses=True)
global_fake_redis = _add_json_support(global_fake_redis)
global_fake_redis = _patch_pipeline(global_fake_redis)

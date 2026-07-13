from app.core.redis_config import Redis

# How long a user's seat hold lasts before the seats are released. This is
# deliberately much shorter than LAYOUT_CACHE_TTL_SECONDS in
# seat_layout_service: locks represent an in-progress checkout, while the
# layout key is only a cache (locks are re-overlaid on every read and
# Postgres is the durable source of truth for booked seats).
SEAT_LOCK_TTL_SECONDS = 600

ACQUIRE_SEAT_LOCKS_SCRIPT = """
local lock_key = KEYS[1]
local user_id = ARGV[1]
local expiry = tonumber(ARGV[2])

for i = 3, #ARGV do
    if redis.call('HEXISTS', lock_key, ARGV[i]) == 1 then
        return 0
    end
end

for i = 3, #ARGV do
    redis.call('HSET', lock_key, ARGV[i], user_id)
end

redis.call('EXPIRE', lock_key, expiry)
return 1
"""


async def acquire_seat_locks(
    redis: Redis,
    show_id: str,
    user_id: str,
    seat_array: list[str],
    expiry: int = SEAT_LOCK_TTL_SECONDS,
) -> bool:
    """Atomically lock all given seats for a show, or none, in a single round trip."""
    result = await redis.eval(
        ACQUIRE_SEAT_LOCKS_SCRIPT,
        1,
        f"show_seat_locked_{show_id}",
        user_id,
        expiry,
        *seat_array,
    )
    return bool(result)

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

FastAPI backend for a movie ticket booking platform: role-based access, real-time seat locking, Postgres + Redis + Elasticsearch. Async throughout (SQLAlchemy async, async Redis client, async ES client).

## Commands

Dependency manager is `uv`.

```
uv sync                                          # install deps
uv run fastapi dev app/main.py                   # run dev server
uv run alembic revision --autogenerate -m "msg"  # create migration
uv run alembic upgrade head                      # apply migrations
uv run pytest                                     # run all tests
uv run pytest tests/test_auth.py                  # run one test file
uv run pytest tests/test_auth.py::test_name -v    # run a single test
uv run pytest --cov=app                           # run tests with coverage
docker compose up --watch                         # run full stack (api+db+redis+es) with live sync
docker compose build                              # rebuild docker images
```

Equivalent `make` targets exist: `dep-sync`, `fastapi-run`, `db-migration m="msg"`, `db-migrate`, `docker-watch`, `docker-build`.

**`tests/` was deleted (2026-07-12) and is being rebuilt from scratch** — the commands above are the intended way to run tests once it exists again, but there is currently no test suite at all. When rebuilt, follow the previous convention: `asyncio_mode = auto` (pytest.ini) so async test functions need no `@pytest.mark.asyncio` decorator; a fake Redis at `tests/fake_redis.py` (real `fakeredis`, `lupa` installed so `EVAL`/Lua scripts work) and a real test Postgres DB (`tests/database.py`, driven by `TEST_DB_URL`); `app.dependency_overrides` swapping `get_db`, `get_redis`, and `get_email_service` per-test (`tests/conftest.py`).

## Architecture

Strict layered flow: **routes → services → repositories → models**, request-scoped via FastAPI `Depends`.

- `app/api/v1/*_routes.py` — route definitions per domain (auth, admin, theatre_admin, user, search). Wired together in `app/api/v1/routes.py` → `app/api/routes.py` (prefix `/api/v1/...`) → `app/main.py`.
- `app/api/dependencies.py` — the composition root. Every repository and service is built here via `Depends`-based factories (`get_repo(RepoClass)` pattern for repos, `get_*_service` functions for services) and exposed as `Annotated` `*Dep` type aliases (e.g. `UserServiceDep`, `DBDep`, `RedisDep`). When adding a new repo/service, follow this exact pattern rather than instantiating directly in routes.
- `app/services/*.py` — business logic. Each service takes its dependencies (db, redis, repos, other services) via constructor injection, matching the factories in `dependencies.py`.
- `app/repositories/*.py` — one repository per model family, holding all SQLAlchemy queries for that domain. Repo methods are suffixed `_repo` (e.g. `get_user_by_email_repo`). Repos raise `HTTPException` directly for not-found cases rather than returning `None` up the stack.
- `app/models/*.py` — SQLAlchemy ORM models. Soft delete is the norm (`is_active` flag + a `soft_delete(db=...)` method), not hard deletes.
- `app/schemas/*.py` — Pydantic request/response schemas. All API responses are wrapped in the generic `ResponseSchema`/`create_response()` from `app/schemas/standard_schema.py` (`{success, message, data}`).
- `app/core/config.py` — single `Settings` (pydantic-settings) object loaded from `.env`, exported as `settings`. All required env vars are declared here with no defaults (aside from a few), so add new env vars here first.
- `app/core/redis_config.py`, `app/core/es_config.py` — module-level singleton clients (`redis_client`, `es`), exposed via `get_redis()`. Elasticsearch index (`booking_search`) is created on app startup via the `lifespan` handler in `app/main.py`.
- `app/middlewares/` — `GlobalExceptionHandlerMiddleware` catches all unhandled exceptions into a uniform 500 JSON response; `RateLimitingMiddleware` (token bucket) is skipped entirely when `settings.ENV == "TESTING"`.
- Auth: JWT access/refresh tokens (`app/utils/helper.py` for encode/decode) — decoding pins `algorithms=[settings.JWT_ALGORITHM]` and every token carries a `jti`. `HTTPBearer` extracts the token in `get_access_token_payload` (`app/api/dependencies.py`), which also checks `is_token_revoked` against Redis (`revoked_token_{jti}`, TTL'd to the token's own remaining lifetime); `get_user_id` just pulls `sub` from that payload, so every route using `GetUserDep`/`permission_required` gets revocation-awareness automatically. `/auth/refresh` rotates to a new access+refresh pair and revokes the old refresh token; `/auth/logout` revokes the current access token (and refresh token, if supplied). Permission checks are done via `permission_required(permission)` — a dependency factory that queries `PermissionRepo` inside a `db.begin()` transaction and raises 403 if missing.
- Alembic migrations live in `alembic/versions/`; `alembic/env.py` reads DB URL from `app/core/config.py`'s settings, not a hardcoded URL.

### Domain-specific flows worth knowing before touching related code

- **Seat locking**: seat layouts are cached in Redis, generated fresh from Postgres (`app/services/seat_layout_service.py`, `app/utils/polish_seat_layout.py`) when not cached; locking is a single atomic Lua script (`app/utils/seat_lock_script.py`, `acquire_seat_locks`) that checks-and-sets all requested seats in one round trip — all-or-nothing, so a partial lock can never be written. Postgres, not Redis, is the durable backstop against double-booking: `booked_seats_map` has a partial unique index on `(show_id, seats_number) WHERE is_cancelled = false`, and `book_ticket_service` re-checks the DB inside the booking transaction (409 on conflict) before ever inserting, with `IntegrityError` caught as a last-resort race guard. Booking commits then clear the Redis locks.
- **Booking lifecycle**: `GET /users/bookings` (history), `GET /users/bookings/{id}` (detail with per-seat breakdown), `POST /users/bookings/{id}/cancel` — cancellation is rejected if already cancelled or if under 6 hours to showtime; on success it flips `is_cancelled` on both `bookings` and `booked_seats_map` (releasing the DB uniqueness constraint) and updates the cached layout immediately so the seat shows "Available" without waiting for cache expiry. See `app/services/user_service.py`'s `cancel_booking_service`.
- **Search**: movie/theatre data is mirrored into Elasticsearch via `queue_search_sync(background_tasks, target)` (`app/services/search_sync.py`), called explicitly from `admin_service.py` after each `db.begin()` commits (not via SQLAlchemy mapper events — those fire mid-flush, before commit, which risked syncing data that could still roll back). Search reads go to ES, not Postgres, via `app/services/search_service.py`.
- **Theatre admin flow**: layout creation → screen creation (validates layout belongs to theatre) → show creation (validates screen ownership, movie duration/timing, overlapping shows, category pricing) — each step depends on the previous being valid, see `app/services/theatre_admin_service.py`.
- **RBAC**: role → permission mapping is checked per-route via `permission_required(...)`, not via role name checks scattered in services.

## Environment

Requires a `.env` (local) or `.env.docker` (docker-compose) file — see the required fields in `app/core/config.py` (`DB_URL`, `TEST_DB_URL`, Redis, mail/SMTP, JWT secrets, Google OAuth, OMDB API key, Elasticsearch URL, encryption password/salt). `ENV` defaults to `"TESTING"`, which also disables rate limiting.

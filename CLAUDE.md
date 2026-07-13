# CLAUDE.md

Guidance for Claude Code when working in this repo. Purpose: **map any change to the exact file(s) fast**, without re-scanning the tree.

## What this is

`cinebook` — async FastAPI movie ticket booking backend. PostgreSQL (async SQLAlchemy 2.0 + asyncpg), Redis (OTP / seat locks / layout cache), Elasticsearch (search). Managed with `uv`. Runs via Docker Compose.

## Layered request flow (strict)

`Route → Dependency (auth/permission + DI) → Service (business logic) → Repository (DB queries) → Model`

Rules:
- Routes never query the DB directly — always go through a service.
- Services never write raw SQL — always go through a repository.
- Repositories are the ONLY place with SQLAlchemy queries.
- Pydantic schemas validate all input/output.
- DB writes happen inside `async with db.begin():` blocks (see any service).

## Directory map — where to change what

### Config / infra
| Need to change… | File |
|---|---|
| App settings / env vars (add a new one here first) | `app/core/config.py` |
| Redis client | `app/core/redis_config.py` |
| Elasticsearch client + index mapping | `app/core/es_config.py` |
| DB engine / async session / `get_db` | `app/db/session.py` |
| SQLAlchemy declarative base | `app/db/base.py` |
| App entrypoint, middleware registration, lifespan | `app/main.py` |
| Container image | `Dockerfile` |
| Services (db/redis/es) + compose config | `docker-compose.yaml` |
| Startup migrations → server handoff | `entrypoint.sh` |
| Dependencies | `pyproject.toml` (then `uv.lock`) |
| Dev command shortcuts | `Makefile` |
| Env values (Docker) | `.env.docker` · (local) `.env` |

### Routes — `app/api/`
| Domain | File | Prefix |
|---|---|---|
| Router assembly (`/api`) | `app/api/routes.py` | `/api` |
| v1 assembly | `app/api/v1/routes.py` | `/v1` |
| **DI + auth + permission guards** | `app/api/dependencies.py` | — |
| Auth (OTP + Google OAuth) | `app/api/v1/auth_routes.py` | `/auth`, `/auth/google` |
| Admin (users/theatres/movies) | `app/api/v1/admin_routes.py` | `/admin` |
| Theatre admin (layout/screen/show/ticket) | `app/api/v1/theatre_admin_routes.py` | `/theatre-admin` |
| User (browse/lock/book/delete) | `app/api/v1/user_routes.py` | `/users` |
| Search | `app/api/v1/search_route.py` | `/search` |

**`dependencies.py` is the wiring hub.** All `*ServiceDep`, `*RepoDep`, `DBDep`, `RedisDep`, `GetUserDep`, and `permission_required(...)` live here. Adding a new service/repo means registering its factory + `Annotated` alias here.

### Services — `app/services/` (business logic)
| File | Owns |
|---|---|
| `auth_service.py` | OTP send/verify, Google OAuth, token issuance |
| `admin_service.py` | Create user/theatre/movie, listings, soft delete |
| `theatre_admin_service.py` | Layout/screen/show creation, ownership checks, ticket verify |
| `user_service.py` | Browse, seat lock, booking, account delete |
| `seat_layout_service.py` | Build/cache seat layout in Redis, apply pricing + booked/locked state |
| `search_service.py` | Elasticsearch query (`search_movies_and_theatres`) |
| `search_sync.py` | Keep ES in sync on movie/theatre insert/update |
| `email_service.py` | Send emails (OTP, ticket) |

### Repositories — `app/repositories/` (DB queries only)
`user_`, `theatre_`, `movie_`, `layout_`, `screen_`, `show_`, `booking_`, `booked_ticket_`, `permission_` `*_repository.py`. One per domain. `permission_repository.py` powers the `permission_required` guard.

### Models — `app/models/` (SQLAlchemy tables)
Core: `user_model`, `user_detail_model`, `role_model`, `permission_model`, `role_permission_map_model`, `theatre_model`, `theatre_operator_map_model`, `movie_model`, `screen_model`, `layout_model`, `show_model`, `booking_model`, `booked_seat_map_model`, `booked_ticket_model`. Register new models in `app/models/__init__.py`.

### Schemas — `app/schemas/` (Pydantic)
`user_`, `theatre_`, `movie_`, `screen_`, `show_`, `layout_`, `pagination_` `*_schema.py`. `standard_schema.py` = `ResponseSchema` + `create_response()` (the standard API envelope — reuse for all responses).

### Utils — `app/utils/`
| File | Contains |
|---|---|
| `helper.py` | JWT (`_generate_token`, `decode_token`, `generate_access_token_and_refresh_token`), OTP (`generate_otp`, `validate_otp`), Fernet encryption (`encrypt_data`, `decrypt_data`) |
| `polish_seat_layout.py` | Seat layout transformation/polishing |
| `show_create_validation.py` | Show timing / overlap / pricing validation |

### Middleware — `app/middlewares/`
`global_exception_handler_middleware.py`, `rate_limiting_middleware.py` (token bucket; skipped when `ENV=TESTING`). Exported via `__init__.py`, registered in `main.py`.

### Scripts — `app/scripts/`
`seed_db.py` (roles/permissions/admin seed → `python -m app.scripts.seed_db`), `migrate_to_es.py` (backfill Elasticsearch).

### Migrations — `alembic/`
Versions in `alembic/versions/`. Config `alembic.ini`, env `alembic/env.py`. New migration: `make db-migration m="msg"`; apply: `make db-migrate`.

### Tests — `tests/`
`conftest.py` (fixtures), `database.py` (test DB), `fake_redis.py` (fakeredis). Suites: `test_auth.py`, `test_admin.py`, `test_theatre_admin.py`, `test_user.py`, `test_utils.py`. Config: `pytest.ini` (async auto mode). Run: `uv run pytest`.

## Conventions

- **Async everywhere** — services/repos/routes are `async def`; DB uses `AsyncSession`.
- **Response envelope** — return via `create_response(...)` → `ResponseSchema`.
- **Permissions** — protect admin/theatre-admin routes with `dependencies=[Depends(permission_required("<perm>"))]`; roles/permissions seeded in `seed_db.py`.
- **Auth** — `GetUserDep` extracts `user_id` from the bearer access token.
- **Soft deletes** — deletions flag records, not remove them.
- **Roles** — `user`, `admin`, `theatre_admin`.

## Commit messages

Format: `<emoji> <type> : <summary>` — subject line only, lowercase casual summary, no body, no `Co-Authored-By`, no AI mention.

Emoji/type pairs actually used in this repo's history:
| Emoji | Type | Used for |
|---|---|---|
| ✨ | `feat` / `add` | new feature, new endpoint |
| 🐛 | `fix` / `bug` | bug fix |
| 🎨 | `update` / `improve` / `format` / `structure` | tweak output, restructure, formatting |
| ♻️ | `refactor` | refactor without behavior change |
| 🚧 | `wip` | work in progress, not finished |
| 🔒️ | `fix` | security-related fix |
| 🌱 | `add` | seed/init data scripts |
| ✅ | `add` | tests, test coverage |
| 🧹 | `chore` | deps, config, project housekeeping |
| 🎉 | `init` | initial project setup |
| 🔀 | `Merge` | merge commits (git-generated, don't write by hand) |

Example: `🐛 fix : minor bug fix in user repository for UserOutSchema`

## Common tasks → touch order

- **New endpoint:** schema (`schemas/`) → repo method (`repositories/`) → service method (`services/`) → route (`api/v1/`) → register service/repo in `dependencies.py` if new.
- **New DB field:** model (`models/`) → migration (`make db-migration`) → schema (`schemas/`).
- **New env var:** `config.py` → `.env` + `.env.docker`.
- **New searchable entity:** index mapping (`es_config.py`) → `search_sync.py` → `search_service.py`.

# 🎬 CineBook — Movie Ticket Booking Backend

A production-style backend for a movie ticket booking platform, built with **FastAPI**. It handles everything from passwordless login to concurrency-safe seat booking, role-based dashboards for admins and theatre owners, QR-code ticket verification, and full-text search.

Think of it as the engine behind a "BookMyShow"-style app — the part that makes sure two people can never book the same seat.

---

## ✨ Highlights

| Capability                         | What it does                                                                              |
| ---------------------------------- | ----------------------------------------------------------------------------------------- |
| 🔐**Passwordless auth**      | Email + OTP login and Google OAuth 2.0, with JWT access/refresh tokens                    |
| 👥**Role-based access**      | Three roles —`user`, `admin`, `theatre_admin` — each permission checked per route |
| 🪑**Concurrency-safe seats** | Seats are*locked* in Redis (atomic ops) before booking, so no double-booking            |
| 🎟️**QR tickets**           | Bookings generate an encrypted QR code; theatre staff verify it at the gate               |
| 🔎**Full-text search**       | Movies and theatres indexed in Elasticsearch, kept in sync on every write                 |
| 🏢**Theatre management**     | Theatre admins design seat layouts, create screens, and schedule shows                    |
| ⚡**Fully async**            | Async SQLAlchemy + asyncpg, async Redis, async Elasticsearch — top to bottom             |
| 🛡️**Middleware**           | Global exception handling + token-bucket rate limiting                                    |

---

## 🧱 Tech Stack

- **Framework:** FastAPI (Python 3.12)
- **Database:** PostgreSQL 16 via SQLAlchemy 2.0 (async) + `asyncpg`
- **Migrations:** Alembic
- **Cache / locks:** Redis
- **Search:** Elasticsearch 9
- **Package manager:** [`uv`](https://github.com/astral-sh/uv) (fast, modern pip replacement)
- **Containers:** Docker + Docker Compose (optional — for spinning up Postgres/Redis/Elasticsearch only)
- **Tests:** Pytest (async) + coverage

---

## 🏛️ Architecture

The app follows a clean, layered design. A request flows **top to bottom**, and each layer has one job:

```
        HTTP request
             │
   ┌─────────▼─────────┐
   │      Routes       │  app/api/v1/*        → define endpoints, validate input
   ├───────────────────┤
   │    Dependencies   │  app/api/dependencies.py → auth, permissions, DI wiring
   ├───────────────────┤
   │     Services      │  app/services/*      → business logic
   ├───────────────────┤
   │   Repositories    │  app/repositories/*  → all database queries
   ├───────────────────┤
   │      Models       │  app/models/*        → SQLAlchemy tables
   └─────────┬─────────┘
             │
   PostgreSQL │ Redis │ Elasticsearch
```

- **Schemas** (`app/schemas/*`) validate and shape data in and out (Pydantic).
- **Routes never touch the database directly** — they call services, which call repositories.
- **Redis** stores OTPs, cached seat layouts, and seat locks.
- **Elasticsearch** is kept in sync automatically whenever a movie or theatre changes.

---

## 🚀 Getting Started

This app is meant to be run **directly** (not inside the app's Docker container) — a couple of setup scripts (like the DB seed script below) expect you to edit them locally before running, which doesn't fit well with a containerized app image. You'll need Python 3.12, [`uv`](https://github.com/astral-sh/uv), and running PostgreSQL, Redis, and Elasticsearch instances.

> 💡 **Don't have Postgres/Redis/Elasticsearch installed?** You can still use the repo's `docker-compose.yaml` for just the infra, without touching the app container: `docker compose up db redis elasticsearch -d`. The API itself is run with `uv` as shown below.

### 1. Clone

```bash
git clone https://github.com/Jaymin4724/cinebook.git
cd cinebook
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment

Copy the template and fill in your own values:

```bash
cp .env.example .env
```

At minimum you'll want to set your own:

- `DB_URL` / `TEST_DB_URL` — point at your Postgres instance
- `REDIS_HOST` / `REDIS_PORT` / `REDIS_URL` — point at your Redis instance
- `ES_URL` — point at your Elasticsearch instance
- `JWT_SECRET_ACCESS_KEY` / `JWT_SECRET_REFRESH_KEY` — any long random strings
- `MAIL_*` — a Gmail address + [App Password](https://support.google.com/accounts/answer/185833) (needed to send OTP emails)
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — from Google Cloud Console (only for Google login)
- `OMDB_API_KEY` — a free key from [omdbapi.com](https://www.omdbapi.com/apikey.aspx) (used to fetch movie details by IMDB ID)
- `ENCRYPTION_PASSWORD` / `ENCRYPTION_STATIC_SALT` — any strings (used to derive the ticket QR-code encryption key)

> ⚠️ **Security note:** never commit real secrets. Keep `.env` out of version control and rotate any keys that were ever committed.

### 4. Add your email(s) to the seed script

OTP sign-in auto-creates a plain `user` account for any email — it's the seed script that grants `admin` / `theatre_admin` access. Before seeding, open `app/scripts/seed_db.py` and add the email(s) you'll actually sign in with:

```python
# app/scripts/seed_db.py  (inside seed_users)
users_data = [
    # enter your emails here.
    ("your-email@gmail.com", True, roles["admin"].id),
    ("your-other-email@gmail.com", True, roles["theatre_admin"].id),
]
```

### 5. Apply migrations

```bash
uv run alembic upgrade head
```

### 6. Seed the database

Creates the roles, permissions, and the admin/theatre_admin users you just added:

```bash
uv run python -m app.scripts.seed_db
```

### 7. Run the dev server

```bash
uv run fastapi dev app/main.py
```

### 8. Open the API

| URL                         | What                   |
| --------------------------- | ---------------------- |
| http://localhost:8000/docs  | Interactive Swagger UI |
| http://localhost:8000/redoc | ReDoc API reference    |

Handy shortcuts live in the **Makefile**:

| Command                       | Does                                        |
| ----------------------------- | ------------------------------------------- |
| `make dep-sync`             | `uv sync`                                 |
| `make fastapi-run`          | Run the dev server                          |
| `make db-migrate`           | Apply migrations (`alembic upgrade head`) |
| `make db-migration m="msg"` | Autogenerate a new migration                |

---

## 🧪 Running Tests

Tests use an isolated test database and a fake Redis, so they don't touch your real data:

```bash
uv run pytest            # run everything
uv run pytest --cov=app  # with coverage
```

---

## 🗺️ API Overview

All routes are prefixed with `/api/v1`. Full, always-up-to-date docs live at `/docs`.

### Auth — `/auth`

| Method | Path                      | Description                  |
| ------ | ------------------------- | ---------------------------- |
| POST   | `/auth/send-otp`        | Send a login OTP to an email |
| POST   | `/auth/signin`          | Verify OTP, return tokens    |
| GET    | `/auth/google/login`    | Redirect to Google login     |
| GET    | `/auth/google/callback` | Google OAuth callback        |

### User — `/users`

| Method | Path                               | Description                        |
| ------ | ---------------------------------- | ---------------------------------- |
| GET    | `/users/theatre/{id}/movies`     | Movies playing in a theatre        |
| GET    | `/users/movie/{id}/theatres`     | Theatres showing a movie           |
| GET    | `/users/theatre/{id}/movie/{id}` | Shows for a movie in a theatre     |
| GET    | `/users/show/{id}`               | Show details + seat layout         |
| POST   | `/users/show/{id}/seat-lock`     | Lock seats before booking          |
| POST   | `/users/show/{id}/seat-book`     | Confirm booking (issues QR ticket) |
| DELETE | `/users/user/delete`             | Soft-delete own account            |

### Admin — `/admin`

| Method | Path                                                           | Description               |
| ------ | -------------------------------------------------------------- | ------------------------- |
| POST   | `/admin/create-user`                                         | Create a user with a role |
| POST   | `/admin/create-theatre`                                      | Create a theatre          |
| POST   | `/admin/create-movie`                                        | Import a movie by IMDB ID |
| GET    | `/admin/users` · `/admin/theatres` · `/admin/movies`   | Paginated listings        |
| DELETE | `/admin/theatre/delete/{id}` · `/admin/movie/delete/{id}` | Soft delete               |

### Theatre Admin — `/theatre-admin`

| Method | Path                                                           | Description                    |
| ------ | -------------------------------------------------------------- | ------------------------------ |
| POST   | `/theatre-admin/create-layout`                               | Design a seat layout           |
| POST   | `/theatre-admin/create-screen`                               | Create a screen                |
| POST   | `/theatre-admin/create-show`                                 | Schedule a show                |
| GET    | `/theatre-admin/my-theatres` · `/my-screens`              | Owned resources                |
| DELETE | `/theatre-admin/screen/delete/{id}` · `/show/delete/{id}` | Soft delete                    |
| POST   | `/theatre-admin/verify-ticket`                               | Verify a QR ticket at the gate |

### Search — `/search`

| Method | Path                         | Description                             |
| ------ | ---------------------------- | --------------------------------------- |
| GET    | `/search/?q=...&limit=...` | Full-text search over movies & theatres |

---

## 🔒 How Seat Booking Stays Safe

The trickiest part of any booking system is stopping two people from grabbing the same seat. Here's the flow:

1. **View** — the seat layout for a show is built once (pricing + booked seats applied) and cached in Redis.
2. **Lock** — when you select seats, they're locked in Redis using an **atomic** operation with an expiry. If someone else already holds a lock, yours fails.
3. **Book** — booking checks that *you* still hold the locks, writes the booking to Postgres, updates seat status, and clears the locks.
4. **Expire** — if you never finish, the locks expire on their own and the seats free up.

This keeps the fast path in memory (Redis) while Postgres stays the source of truth.

---

## 📁 Project Structure

```
cinebook/
├── app/
│   ├── api/            # Routes (v1) + dependency injection / auth guards
│   ├── core/           # Settings, Redis, Elasticsearch clients
│   ├── db/             # SQLAlchemy base, engine, session
│   ├── middlewares/    # Global exception handler, rate limiter
│   ├── models/         # Database tables (SQLAlchemy)
│   ├── repositories/   # Database queries (one per domain)
│   ├── schemas/        # Pydantic request/response models
│   ├── services/       # Business logic
│   ├── scripts/        # DB seeding, Elasticsearch backfill
│   ├── utils/          # Helpers: JWT, OTP, encryption, seat-layout logic
│   └── main.py         # App entrypoint (FastAPI instance, middleware, lifespan)
├── alembic/            # Migrations
├── tests/              # Pytest suite
├── docker-compose.yaml # Optional: Postgres + Redis + Elasticsearch (+ API image)
├── Dockerfile          # App image (uv-based; not needed for local dev)
├── entrypoint.sh       # Runs migrations, then starts the server (used by the app image)
├── Makefile            # Common dev commands
└── pyproject.toml      # Dependencies (managed by uv)
```

> 🤝 **Contributing / making changes?** See [`CLAUDE.md`](./CLAUDE.md) for a file-by-file map of where each feature lives.

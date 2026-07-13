# 🎬 CineBook — Movie Ticket Booking Backend

A production-style backend for a movie ticket booking platform, built with **FastAPI**. It handles everything from passwordless login to concurrency-safe seat booking, role-based dashboards for admins and theatre owners, QR-code ticket verification, and full-text search.

Think of it as the engine behind a "BookMyShow"-style app — the part that makes sure two people can never book the same seat.

---

## ✨ Highlights

| Capability | What it does |
|---|---|
| 🔐 **Passwordless auth** | Email + OTP login and Google OAuth 2.0, with JWT access/refresh tokens |
| 👥 **Role-based access** | Three roles — `user`, `admin`, `theatre_admin` — each permission checked per route |
| 🪑 **Concurrency-safe seats** | Seats are *locked* in Redis (atomic ops) before booking, so no double-booking |
| 🎟️ **QR tickets** | Bookings generate an encrypted QR code; theatre staff verify it at the gate |
| 🔎 **Full-text search** | Movies and theatres indexed in Elasticsearch, kept in sync on every write |
| 🏢 **Theatre management** | Theatre admins design seat layouts, create screens, and schedule shows |
| ⚡ **Fully async** | Async SQLAlchemy + asyncpg, async Redis, async Elasticsearch — top to bottom |
| 🛡️ **Middleware** | Global exception handling + token-bucket rate limiting |

---

## 🧱 Tech Stack

- **Framework:** FastAPI (Python 3.12)
- **Database:** PostgreSQL 16 via SQLAlchemy 2.0 (async) + `asyncpg`
- **Migrations:** Alembic
- **Cache / locks:** Redis
- **Search:** Elasticsearch 9
- **Package manager:** [`uv`](https://github.com/astral-sh/uv) (fast, modern pip replacement)
- **Containers:** Docker + Docker Compose
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

## 🚀 Quick Start (Docker — recommended)

You only need **Docker Desktop** installed. Everything else (Postgres, Redis, Elasticsearch, the app) runs in containers.

### 1. Clone

```bash
git clone https://github.com/Jaymin4724/cinebook.git
cd cinebook
```

### 2. Configure environment

The app reads its config from `.env.docker`. Copy the template and fill in your own values:

```bash
cp .env.docker.example .env.docker   # then edit .env.docker
```

At minimum you'll want to set your own:

- `JWT_SECRET_ACCESS_KEY` / `JWT_SECRET_REFRESH_KEY` — any long random strings
- `MAIL_*` — a Gmail address + [App Password](https://support.google.com/accounts/answer/185833) (needed to send OTP emails)
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — from Google Cloud Console (only for Google login)
- `OMDB_API_KEY` — a free key from [omdbapi.com](https://www.omdbapi.com/apikey.aspx) (used to fetch movie details by IMDB ID)

> ⚠️ **Security note:** never commit real secrets. Keep `.env.docker` out of version control and rotate any keys that were ever committed.

### 3. Run

```bash
docker compose up --watch
```

That's it. Compose will:

1. Start Postgres, Redis, and Elasticsearch, and wait until each is healthy.
2. Build the app image and run database migrations automatically (`alembic upgrade head`).
3. Start the API server with live reload — edits to `./app` sync into the container instantly.

### 4. Open the API

| URL | What |
|---|---|
| http://localhost:8000/docs | Interactive Swagger UI |
| http://localhost:8000/redoc | ReDoc API reference |
| `localhost:5678` | Attach a debugger (debugpy) |

### 5. (Optional) Seed the database

Roles, permissions, and a starter admin are created by the seed script:

```bash
docker compose exec api python -m app.scripts.seed_db
```

---

## 💻 Local Start (without Docker)

You'll need Python 3.12, `uv`, and running Postgres / Redis / Elasticsearch instances.

```bash
# 1. Install dependencies into a local virtualenv
uv sync

# 2. Create a .env file (see app/core/config.py for every required variable)

# 3. Apply migrations
uv run alembic upgrade head

# 4. Run the dev server
uv run fastapi dev app/main.py
```

Handy shortcuts live in the **Makefile**:

| Command | Does |
|---|---|
| `make dep-sync` | `uv sync` |
| `make fastapi-run` | Run the dev server |
| `make db-migrate` | Apply migrations (`alembic upgrade head`) |
| `make db-migration m="msg"` | Autogenerate a new migration |
| `make docker-watch` | `docker compose up --watch` |
| `make docker-build` | Build the compose images |

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
| Method | Path | Description |
|---|---|---|
| POST | `/auth/send-otp` | Send a login OTP to an email |
| POST | `/auth/signin` | Verify OTP, return tokens |
| GET | `/auth/google/login` | Redirect to Google login |
| GET | `/auth/google/callback` | Google OAuth callback |

### User — `/users`
| Method | Path | Description |
|---|---|---|
| GET | `/users/theatre/{id}/movies` | Movies playing in a theatre |
| GET | `/users/movie/{id}/theatres` | Theatres showing a movie |
| GET | `/users/theatre/{id}/movie/{id}` | Shows for a movie in a theatre |
| GET | `/users/show/{id}` | Show details + seat layout |
| POST | `/users/show/{id}/seat-lock` | Lock seats before booking |
| POST | `/users/show/{id}/seat-book` | Confirm booking (issues QR ticket) |
| DELETE | `/users/user/delete` | Soft-delete own account |

### Admin — `/admin`
| Method | Path | Description |
|---|---|---|
| POST | `/admin/create-user` | Create a user with a role |
| POST | `/admin/create-theatre` | Create a theatre |
| POST | `/admin/create-movie` | Import a movie by IMDB ID |
| GET | `/admin/users` · `/admin/theatres` · `/admin/movies` | Paginated listings |
| DELETE | `/admin/theatre/delete/{id}` · `/admin/movie/delete/{id}` | Soft delete |

### Theatre Admin — `/theatre-admin`
| Method | Path | Description |
|---|---|---|
| POST | `/theatre-admin/create-layout` | Design a seat layout |
| POST | `/theatre-admin/create-screen` | Create a screen |
| POST | `/theatre-admin/create-show` | Schedule a show |
| GET | `/theatre-admin/my-theatres` · `/my-screens` | Owned resources |
| DELETE | `/theatre-admin/screen/delete/{id}` · `/show/delete/{id}` | Soft delete |
| POST | `/theatre-admin/verify-ticket` | Verify a QR ticket at the gate |

### Search — `/search`
| Method | Path | Description |
|---|---|---|
| GET | `/search/?q=...&limit=...` | Full-text search over movies & theatres |

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
├── docker-compose.yaml # Postgres + Redis + Elasticsearch + API
├── Dockerfile          # App image (uv-based)
├── entrypoint.sh       # Runs migrations, then starts the server
├── Makefile            # Common dev commands
└── pyproject.toml      # Dependencies (managed by uv)
```

> 🤝 **Contributing / making changes?** See [`CLAUDE.md`](./CLAUDE.md) for a file-by-file map of where each feature lives.

---

## 📝 License

Add your license here.

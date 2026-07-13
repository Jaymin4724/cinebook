# CineBook — Manual API Testing Guide (Postman)

> **Purpose:** End-to-end QA checklist to verify the entire CineBook backend from the user's perspective before deployment.
> **Audience:** A QA engineer with no knowledge of the codebase should be able to execute this document top-to-bottom.
>
> **Base URL:** `http://localhost:8000` · **Swagger UI:** `http://localhost:8000/docs` · **API prefix:** `/api/v1`
>
> All API responses (except `/health` and validation errors) use the standard envelope:
>
> ```json
> { "success": true, "message": "...", "data": { } }
> ```
>
> Errors raised by the app return `{ "detail": "..." }`. Pydantic validation errors return HTTP `422` with `{ "detail": [ ... ] }`.

---

## ⚠️ Read This First — How CineBook Auth Actually Works

CineBook is **passwordless**. There is **no register / password / forgot-password / reset-password endpoint**.

1. `POST /auth/send-otp` emails a **6-digit OTP** to any email address (valid **10 minutes**, **3 attempts**, single-use).
2. `POST /auth/signin` with `email + otp`:
   - If the user **does not exist** → account is **auto-created** with role `user` (signin *is* registration).
   - If the user exists → normal login.
3. Both cases return an **access token** (Bearer, short-lived — `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` env) and a **refresh token** (long-lived — `JWT_REFRESH_TOKEN_EXPIRE_DAYS` env).
4. Refresh **rotates** tokens: the used refresh token is immediately revoked (jti blacklist in Redis).
5. Google OAuth (`/auth/google/login` → `/auth/google/callback`) is the alternate login path.

**Roles:** `user`, `admin`, `theatre_admin` — permissions are checked per-endpoint via `permission_required(...)`.

### Seed prerequisite (IMPORTANT)

Seed the DB before testing:

```
python -m app.scripts.seed_db
```

(`seed_db.sql` is an equivalent raw-SQL alternative — both create the same roles, permissions, and mappings.)
The seeder is idempotent and **reconciling**: it inserts missing roles/permissions/mappings **and revokes stale role–permission mappings** that are no longer part of a role's permission set, so re-running it brings any existing database's RBAC exactly in line with the matrix below. Re-run it now if the DB was seeded with an older version of the script (older seeds granted `read-movies` to the `user` role and lacked the `update-*`/`verify-ticket` permissions). If any **PATCH** endpoint or **verify-ticket** unexpectedly returns `403 {"detail": "Permission denied"}` for an admin, an out-of-date permission seed is the first thing to check.

Seeded accounts:

| Email                       | Role              |
| --------------------------- | ----------------- |
| `jaymindrive01@gmail.com` | `admin`         |
| `jaymin4724@gmail.com`    | `theatre_admin` |

Permission matrix (seeded):

| Permission                                                    | admin | theatre_admin | user |
| ------------------------------------------------------------- | :---: | :-----------: | :--: |
| create-user, read-users                                       |  ✅  |      ❌      |  ❌  |
| create-theatre, read-theatres, update-theatre, delete-theatre |  ✅  |      ❌      |  ❌  |
| create-movie, read-movies, update-movie, delete-movie         |  ✅  |      ❌      |  ❌  |
| create-layout, update-layout                                  |  ✅  |      ✅      |  ❌  |
| create-screen, update-screen, delete-screen                   |  ✅  |      ✅      |  ❌  |
| read-my-theatres, read-my-screens                             |  ✅  |      ✅      |  ❌  |
| create-show, update-show, delete-show                         |  ✅  |      ✅      |  ❌  |
| verify-ticket                                                 |  ✅  |      ✅      |  ❌  |

### Middleware behavior (applies to every request)

- **Rate limiting** (token bucket per client IP): capacity **10**, refill **0.1 token/sec** (1 request per 10 s sustained). Exceeding it returns `429 {"detail": "Too many requests"}`. **Disabled when `ENV=TESTING`** — check `.env` before testing it.
- **Global exception handler:** any unhandled error returns `500 {"error": "Internal server error", "detail": "Internal server error"}`.
  ⚠️ Passing a **malformed UUID** in a path parameter (e.g. `/users/show/not-a-uuid`) is not caught by validation and surfaces as this generic **500** — expected current behavior, note it in bug reports only if the status differs.
- **Missing `Authorization` header** on a protected route → `401 {"detail": "Not authenticated"}` (FastAPI `HTTPBearer` default).
- **Invalid/expired Bearer token** → `401 {"detail": "Invalid or expired token"}`. **Revoked token** → `401 {"detail": "Token has been revoked"}`.

---

## Postman Environment Variables

Create a Postman environment named **CineBook-Local** with:

| Variable                | Initial Value                 | Set By                              |
| ----------------------- | ----------------------------- | ----------------------------------- |
| `BASE_URL`            | `http://localhost:8000`     | manual                              |
| `OTP`                 | *(from email)*              | manual, each send-otp               |
| `USER_EMAIL`          | `jaymindrive2023@gmail.com` | manual                              |
| `ACCESS_TOKEN`        | —                            | Step 4 (regular user signin)        |
| `REFRESH_TOKEN`       | —                            | Step 4                              |
| `ADMIN_ACCESS_TOKEN`  | —                            | Step 9 (admin signin)               |
| `ADMIN_REFRESH_TOKEN` | —                            | Step 9                              |
| `TA_ACCESS_TOKEN`     | —                            | Step 20 (theatre admin signin)      |
| `TA_REFRESH_TOKEN`    | —                            | Step 20                             |
| `USER_ID`             | —                            | Step 33 (`GET /users/me`)         |
| `MOVIE_ID`            | —                            | Step 11 (create movie)              |
| `MOVIE_ID_2`          | —                            | Step 12                             |
| `THEATRE_ID`          | —                            | Step 14 (create theatre)            |
| `LAYOUT_ID`           | —                            | Step 22 (create layout)             |
| `SCREEN_ID`           | —                            | Step 24 (create screen)             |
| `SHOW_ID`             | —                            | Step 27 (create show)               |
| `SHOW_ID_CANCEL`      | —                            | Step 28 (2nd show, for cancel test) |
| `BOOKING_ID`          | —                            | Step 37 (book seats)                |
| `BOOKING_ID_CANCEL`   | —                            | Step 41                             |
| `TICKET_HASH`         | —                            | Step 40 (from QR ticket email)      |

## Postman Collection Folders

Organize requests as:

1. **00 – Health**
2. **01 – Authentication** (OTP, signin, refresh, logout, Google OAuth, negative cases)
3. **02 – Admin** (users, theatres, movies CRUD + listings)
4. **03 – Theatre Admin** (layouts, screens, shows, verify-ticket)
5. **04 – Search** (Elasticsearch)
6. **05 – Users: Browse** (public discovery endpoints)
7. **06 – Users: Booking** (seat lock → book → history → cancel)
8. **07 – Users: Profile & Account**
9. **08 – Security & RBAC** (cross-role negative tests, rate limit)

---

# PHASE 0 — Environment Sanity

## Step 1

### Objective

Verify the stack (Postgres, Redis, Elasticsearch) is up before testing anything else.

### Endpoint

`GET /health`

### Headers

None.

### Expected Response

**200 OK** (note: this endpoint does **not** use the standard envelope)

```json
{
  "status": "ok",
  "checks": { "database": "ok", "redis": "ok", "elasticsearch": "ok" }
}
```

### Database Verification

✓ None — connectivity check only.

### Next Step

If any check reads `"unavailable"` the response is **503** with `"status": "degraded"` — fix infrastructure (`docker compose up -d`) before continuing. Then move to Step 2.

### Common Failure Cases

| Scenario                         | Status | Body                                                         |
| -------------------------------- | ------ | ------------------------------------------------------------ |
| Postgres/Redis/ES container down | 503    | `{"status": "degraded", "checks": {...one "unavailable"}}` |

---

# PHASE 1 — Authentication (Regular User)

We first create a brand-new regular user: **`jaymindrive2023@gmail.com`**.

## Step 2

### Objective

Request an OTP for a new user's email (this is the entry point for both registration and login).

### Endpoint

`POST /api/v1/auth/send-otp`

### Headers

| Header       | Value                |
| ------------ | -------------------- |
| Content-Type | `application/json` |

### Request Body

```json
{
  "email": "jaymindrive2023@gmail.com"
}
```

### Expected Response

**200 OK**

```json
{
  "success": true,
  "message": "OTP sent to your email",
  "data": { "email": "jaymindrive2023@gmail.com" }
}
```

> The email is sent by a **background task** — the API returns 200 even if SMTP later fails. If no email arrives, check app logs for `Failed to send OTP email`.

### Database Verification

✓ No DB row yet (user is created at signin, not here)
✓ Redis: hash key `jaymindrive2023@gmail.com` with fields `otp` (6 digits) and `tries=3`, TTL 600 s
✓ OTP email received: subject **"Your CineBook Verification Code"**, 6-digit code, "valid for 10 minutes"

### Save

- **OTP** → from the email inbox (`{{OTP}}`)

### Next Step

Step 3 (negative: wrong OTP) or Step 4 (signin).

### Common Failure Cases

| Scenario                             | Status | Body                      |
| ------------------------------------ | ------ | ------------------------- |
| Malformed email (`"not-an-email"`) | 422    | Pydantic validation error |
| Missing`email` field               | 422    | validation error          |
| Wrong content type (form data)       | 422    | validation error          |

---

## Step 3

### Objective

Verify OTP retry counting: a wrong OTP decrements the 3-try budget.

### Endpoint

`POST /api/v1/auth/signin`

### Headers

| Header       | Value                |
| ------------ | -------------------- |
| Content-Type | `application/json` |

### Request Body

```json
{
  "email": "jaymindrive2023@gmail.com",
  "otp": "000000"
}
```

*(use any 6 digits that are NOT the real OTP)*

### Expected Response

**400 Bad Request**

```json
{ "detail": "Incorrect OTP. 2 tries left." }
```

### Database Verification

✓ Redis hash `tries` field decremented to `2`
✓ No user row created

### Next Step

Step 4 — sign in with the **correct** OTP. (Don't fail twice more: the 3rd failure deletes the OTP → `400 "All tries exhausted. Please request a new OTP."` and you'd need to re-run Step 2.)

### Common Failure Cases

| Scenario                                | Status | Body                                                             |
| --------------------------------------- | ------ | ---------------------------------------------------------------- |
| OTP never requested / expired (>10 min) | 404    | `{"detail": "OTP not found or expired"}`                       |
| 3rd consecutive wrong OTP               | 400    | `{"detail": "All tries exhausted. Please request a new OTP."}` |
| Missing`otp` field                    | 422    | validation error                                                 |

---

## Step 4

### Objective

Sign in with the correct OTP. Because this email has never signed in, the account is **auto-created** with role `user`.

### Endpoint

`POST /api/v1/auth/signin`

### Headers

| Header       | Value                |
| ------------ | -------------------- |
| Content-Type | `application/json` |

### Request Body

```json
{
  "email": "jaymindrive2023@gmail.com",
  "otp": "{{OTP}}"
}
```

### Expected Response

**201 Created**

```json
{
  "success": true,
  "message": "User created successfully",
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi..."
  }
}
```

> On subsequent logins for an existing user, the message is `"User login successfully"` instead.

### Database Verification

✓ `users` row created: `email=jaymindrive2023@gmail.com`, `is_active=true`, `role_id` → role `user`
✓ `user_details` row created (empty names)
✓ Redis OTP key deleted (OTP is single-use — replaying Step 4 now must fail with 404)

### Save

- **ACCESS_TOKEN** = `data.access_token`
- **REFRESH_TOKEN** = `data.refresh_token`

### Next Step

Step 5 (refresh flow).

### Common Failure Cases

| Scenario                         | Status | Body                                       |
| -------------------------------- | ------ | ------------------------------------------ |
| Replaying the same OTP           | 404    | `{"detail": "OTP not found or expired"}` |
| Signin to a soft-deleted account | 400    | `{"detail": "User account is deleted"}`  |
| Invalid email format             | 422    | validation error                           |

---

## Step 5

### Objective

Exchange the refresh token for a new token pair, and verify **rotation** (old refresh token is revoked).

### Endpoint

`POST /api/v1/auth/refresh`

### Headers

| Header       | Value                |
| ------------ | -------------------- |
| Content-Type | `application/json` |

### Request Body

```json
{
  "refresh_token": "{{REFRESH_TOKEN}}"
}
```

### Expected Response

**201 Created**

```json
{
  "success": true,
  "message": "Token refreshed successfully",
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi..."
  }
}
```

### Database Verification

✓ Redis: `revoked_token_<old-jti>` key created (old refresh token blacklisted, TTL = its remaining lifetime)

### Save

- **ACCESS_TOKEN** and **REFRESH_TOKEN** → overwrite with the **new** pair

### Next Step

Step 6 — prove rotation worked.

### Common Failure Cases

| Scenario                                     | Status | Body                                               |
| -------------------------------------------- | ------ | -------------------------------------------------- |
| Access token passed instead of refresh token | 401    | `{"detail": "Invalid or expired refresh token"}` |
| Garbage/expired token                        | 401    | `{"detail": "Invalid or expired refresh token"}` |
| Missing body                                 | 422    | validation error                                   |

---

## Step 6

### Objective

Confirm refresh-token **reuse detection**: replay the OLD refresh token from Step 4.

### Endpoint

`POST /api/v1/auth/refresh`

### Request Body

```json
{
  "refresh_token": "<the OLD refresh token from Step 4, before rotation>"
}
```

### Expected Response

**401 Unauthorized**

```json
{ "detail": "Refresh token has been revoked" }
```

### Next Step

Step 7 (logout).

---

## Step 7

### Objective

Log out: revoke the current access token and (optionally) the refresh token in one call.

### Endpoint

`POST /api/v1/auth/logout`

### Headers

| Header        | Value                       |
| ------------- | --------------------------- |
| Authorization | `Bearer {{ACCESS_TOKEN}}` |
| Content-Type  | `application/json`        |

### Request Body

```json
{
  "refresh_token": "{{REFRESH_TOKEN}}"
}
```

*(`refresh_token` is optional — `{}` revokes only the access token)*

### Expected Response

**200 OK**

```json
{ "success": true, "message": "Logged out successfully", "data": null }
```

### Database Verification

✓ Redis: `revoked_token_<jti>` keys for both tokens

### Next Step

Step 8 — verify the revoked token is rejected.

### Common Failure Cases

| Scenario                | Status | Body                                       |
| ----------------------- | ------ | ------------------------------------------ |
| No Authorization header | 401    | `{"detail": "Not authenticated"}`        |
| Expired access token    | 401    | `{"detail": "Invalid or expired token"}` |

---

## Step 8

### Objective

Prove the revoked access token no longer works on a protected endpoint.

### Endpoint

`GET /api/v1/users/me`

### Headers

| Header        | Value                                                     |
| ------------- | --------------------------------------------------------- |
| Authorization | `Bearer {{ACCESS_TOKEN}}` *(the one just logged out)* |

### Expected Response

**401 Unauthorized**

```json
{ "detail": "Token has been revoked" }
```

### Next Step

Re-login the regular user (repeat Steps 2 + 4 for `jaymindrive2023@gmail.com`, message will now be `"User login successfully"`, re-save `ACCESS_TOKEN`/`REFRESH_TOKEN`). Then continue to the Admin phase.

### Google OAuth (manual browser test — cannot be fully driven from Postman)

1. Open `http://localhost:8000/api/v1/auth/google/login` in a **browser** → you must be redirected to Google's consent screen (a CSRF `state` is stored in Redis for 10 min, single-use).
2. Complete consent → Google redirects to `GET /api/v1/auth/google/callback?code=...&state=...` → **200**:
   ```json
   { "success": true, "message": "Login successful", "data": { "email": "...", "access_token": "...", "refresh_token": "..." } }
   ```
3. Verify in DB: user auto-created (or linked) with `google_id` populated and first/last name from the Google profile.
4. Negative: reload the callback URL (state already consumed) → **400** `{"detail": "Invalid or expired OAuth state"}`.
5. Negative: callback for a soft-deleted account → **400** `{"detail": "User account is deleted"}`.

---

# PHASE 2 — Admin Flows

Sign in as the **seeded admin**: `jaymindrive01@gmail.com`.

## Step 9

### Objective

Obtain admin tokens.

### Endpoints (two calls)

1. `POST /api/v1/auth/send-otp` with body `{ "email": "jaymindrive01@gmail.com" }` → **200**, read OTP from that inbox.
2. `POST /api/v1/auth/signin` with body:

```json
{
  "email": "jaymindrive01@gmail.com",
  "otp": "{{OTP}}"
}
```

### Expected Response

**201 Created**, message `"User login successfully"` (user already exists from seeding), with token pair.

### Save

- **ADMIN_ACCESS_TOKEN** = `data.access_token`
- **ADMIN_REFRESH_TOKEN** = `data.refresh_token`

### Next Step

Step 10 — RBAC negative check before using admin powers.

---

## Step 10

### Objective

RBAC negative: a **regular user** token must be rejected on an admin endpoint.

### Endpoint

`GET /api/v1/admin/users?page=1&size=10`

### Headers

| Header        | Value                                          |
| ------------- | ---------------------------------------------- |
| Authorization | `Bearer {{ACCESS_TOKEN}}` *(regular user)* |

### Expected Response

**403 Forbidden**

```json
{ "detail": "Permission denied" }
```

### Next Step

Step 11 — create movies as admin.

---

## Step 11

### Objective

Create a movie by **IMDb ID**. The server fetches title/plot/genre/runtime/rating from OMDB (external API) and syncs Elasticsearch in a background task.

### Endpoint

`POST /api/v1/admin/create-movie`

### Headers

| Header        | Value                             |
| ------------- | --------------------------------- |
| Authorization | `Bearer {{ADMIN_ACCESS_TOKEN}}` |
| Content-Type  | `application/json`              |

### Request Body

```json
{
  "imdb_id": "tt30144839"
}
```

*(One Battle After Another, 2025, 161 min)*

### Expected Response

**201 Created**

```json
{
  "success": true,
  "message": "Movie created successfully",
  "data": {
    "id": "<uuid>",
    "name": "one battle after another",
    "description": "when their enemy resurfaces after 16 years, a group of ex-revolutionaries reunite to rescue the daughter of one of their own.",
    "rating": 7.7,
    "genre": "action, crime, drama",
    "imdb_id": "tt30144839",
    "duration": "PT2H41M",
    "is_deleted": false
  }
}
```

> Text fields are lowercased by the schema. `duration` serializes as ISO-8601 (`PT2H41M` = 161 min).

### Database Verification

✓ `movies` row with `imdb_id=tt30144839`, `duration = 161 min`, `is_deleted=false`
✓ Elasticsearch index `booking_search` gains a doc `{name, type: "movie", db_id}` (verify via Step 30 search)

### Save

- **MOVIE_ID** = `data.id`

### Next Step

Step 12 — create more movies (needed for browsing/booking realism).

### Common Failure Cases

| Scenario                                 | Status | Body                                                                 |
| ---------------------------------------- | ------ | -------------------------------------------------------------------- |
| Same imdb_id again                       | 400    | `{"detail": "Movie already exist"}`                                |
| Both`imdb_id` and `title` given      | 422    | `Provide only one of imdb_id or title`                             |
| Neither field given                      | 422    | `Provide either imdb_id or title`                                  |
| Unknown imdb_id                          | 400    | `{"detail": "Incorrect IMDb ID."}` (OMDB error passthrough)        |
| Unknown title                            | 400    | `{"detail": "Movie not found!"}`                                   |
| OMDB has no runtime (e.g. some series)   | 400    | `{"detail": "OMDB did not return a valid runtime for this movie"}` |
| OMDB HTTP failure / bad API key behavior | 502    | `{"detail": "Failed to fetch movie data"}`                         |
| Regular-user token                       | 403    | `{"detail": "Permission denied"}`                                  |

---

## Step 12

### Objective

Create the remaining test movies — one **by title** to cover the second input mode, the rest by IMDb ID.

### Endpoint

`POST /api/v1/admin/create-movie` (repeat 4×, same headers as Step 11)

### Request Bodies

```json
{ "title": "Train Dreams" }
```

```json
{ "imdb_id": "tt26581740" }
```

*(Weapons, 2025)*

```json
{ "imdb_id": "tt11378946" }
```

*(Michael, 2026)*

```json
{ "imdb_id": "tt12042730" }
```

*(Project Hail Mary, 2026)*

### Expected Response

**201 Created** for each, message `"Movie created successfully"`.

### Save

- **MOVIE_ID_2** = `data.id` of *Train Dreams* (keep the rest if you plan extra shows)

### Next Step

Step 13 — create the second theatre-admin user.

---

## Step 13

### Objective

Admin creates a user **with an explicit role** (`theatre_admin`). Note: this endpoint validates an OTP **for the target user's email** — the target proves email ownership.

### Endpoints (two calls)

1. `POST /api/v1/auth/send-otp` body `{ "email": "jaymindrive2024@gmail.com" }` → read OTP from that inbox.
2. `POST /api/v1/admin/create-user`:

### Headers

| Header        | Value                             |
| ------------- | --------------------------------- |
| Authorization | `Bearer {{ADMIN_ACCESS_TOKEN}}` |
| Content-Type  | `application/json`              |

### Request Body

```json
{
  "email": "jaymindrive2024@gmail.com",
  "otp": "{{OTP}}",
  "role": "theatre_admin"
}
```

### Expected Response

**201 Created**

```json
{
  "success": true,
  "message": "User created successfully with role theatre_admin",
  "data": {
    "id": "<uuid>",
    "email": "jaymindrive2024@gmail.com",
    "is_active": true,
    "role": "theatre_admin",
    "google_id": null,
    "user_detail": null
  }
}
```

### Database Verification

✓ `users` row with role → `theatre_admin`
✓ `user_details` row created

### Next Step

Step 14 — create a theatre and assign an operator.

### Common Failure Cases

| Scenario                              | Status | Body                                                                     |
| ------------------------------------- | ------ | ------------------------------------------------------------------------ |
| Wrong OTP                             | 400    | `{"detail": "Incorrect OTP. 2 tries left."}`                           |
| No OTP requested                      | 404    | `{"detail": "OTP not found or expired"}`                               |
| Invalid role value (`"superadmin"`) | 422    | validation error (enum:`user`, `admin`, `theatre_admin`)           |
| Email already registered              | 500    | unique-constraint violation caught by global handler — known rough edge |
| Non-admin token                       | 403    | `{"detail": "Permission denied"}`                                      |

---

## Step 14

### Objective

Create a theatre and link it to a theatre operator. The operator email **must belong to an existing, active `theatre_admin` user**. ES is synced in the background.

### Endpoint

`POST /api/v1/admin/create-theatre`

### Headers

| Header        | Value                             |
| ------------- | --------------------------------- |
| Authorization | `Bearer {{ADMIN_ACCESS_TOKEN}}` |
| Content-Type  | `application/json`              |

### Request Body

```json
{
  "name": "PVR Acropolis",
  "area": "Thaltej",
  "city": "Ahmedabad",
  "operator_email": "jaymin4724@gmail.com"
}
```

### Expected Response

**201 Created**

```json
{
  "success": true,
  "message": "Theatre created successfully",
  "data": {
    "id": "<uuid>",
    "name": "pvr acropolis",
    "area": "thaltej",
    "city": "ahmedabad",
    "is_active": true
  }
}
```

*(all strings lowercased)*

### Database Verification

✓ `theatres` row (`is_active=true`)
✓ `theatre_operator_map` row linking theatre → `jaymin4724@gmail.com`'s user id
✓ ES doc `{name: "pvr acropolis", type: "theatre"}` (verify via search later)

### Save

- **THEATRE_ID** = `data.id`

### Next Step

Step 15 — update the theatre.

### Common Failure Cases

| Scenario                                                           | Status | Body                                         |
| ------------------------------------------------------------------ | ------ | -------------------------------------------- |
| `operator_email` not a theatre_admin (e.g. regular user's email) | 404    | `{"detail": "Theatre operator not found"}` |
| Missing any field                                                  | 422    | validation error                             |
| Non-admin token                                                    | 403    | `{"detail": "Permission denied"}`          |

---

## Step 15

### Objective

Partially update a theatre (PATCH semantics — send only changed fields).

### Endpoint

`PATCH /api/v1/admin/theatre/update/{{THEATRE_ID}}`

### Headers

| Header        | Value                             |
| ------------- | --------------------------------- |
| Authorization | `Bearer {{ADMIN_ACCESS_TOKEN}}` |
| Content-Type  | `application/json`              |

### Path Parameters

| Param      | Value              |
| ---------- | ------------------ |
| theatre_id | `{{THEATRE_ID}}` |

### Request Body

```json
{
  "area": "Bodakdev"
}
```

### Expected Response

**200 OK**, message `"Theatre updated successfully"`, `data.area = "bodakdev"`, other fields unchanged.

### Database Verification

✓ `theatres.area` updated; `name`/`city` untouched
✓ ES doc re-synced in background

### Next Step

Step 16 — update a movie.

### Common Failure Cases

| Scenario               | Status | Body                                |
| ---------------------- | ------ | ----------------------------------- |
| Random UUID            | 404    | `{"detail": "Theatre not found"}` |
| Malformed UUID in path | 500    | global handler (known behavior)     |
| Non-admin token        | 403    | `{"detail": "Permission denied"}` |

---

## Step 16

### Objective

Partially update a movie (name/description/rating/genre only — `duration` and `imdb_id` are intentionally immutable).

### Endpoint

`PATCH /api/v1/admin/movie/update/{{MOVIE_ID}}`

### Headers

| Header        | Value                             |
| ------------- | --------------------------------- |
| Authorization | `Bearer {{ADMIN_ACCESS_TOKEN}}` |
| Content-Type  | `application/json`              |

### Request Body

```json
{
  "rating": 7.8,
  "genre": "Action, Crime, Drama, Thriller"
}
```

### Expected Response

**200 OK**, message `"Movie updated successfully"`, `data.rating = 7.8`, `data.genre = "action, crime, drama, thriller"`.

### Database Verification

✓ Only the sent fields changed
✓ Sending `{"duration": 90}` or `{"imdb_id": "tt999"}` is silently ignored (schema drops unknown fields)

### Next Step

Step 17 — listings & pagination.

### Common Failure Cases

| Scenario           | Status | Body                              |
| ------------------ | ------ | --------------------------------- |
| Random UUID        | 404    | `{"detail": "Movie not found"}` |
| Non-numeric rating | 422    | validation error                  |

---

## Step 17

### Objective

Verify all three admin listing endpoints and their pagination.

### Endpoints

- `GET /api/v1/admin/users?page=1&size=10`
- `GET /api/v1/admin/theatres?page=1&size=10`
- `GET /api/v1/admin/movies?page=1&size=2`

### Headers

| Header        | Value                             |
| ------------- | --------------------------------- |
| Authorization | `Bearer {{ADMIN_ACCESS_TOKEN}}` |

### Query Parameters

| Param | Rules                      |
| ----- | -------------------------- |
| page  | integer ≥ 1, default 1    |
| size  | integer 1–100, default 10 |

### Expected Response

**200 OK** each. Messages: `"Users fetched successfully"` / `"Theatres fetched successfully"` / `"Movies fetched successfully"`. `data` is an **array** (no total-count wrapper).

Pagination check with `size=2` on movies: page 1 returns 2 movies, `page=2` returns the next 2, `page=99` returns `[]`.

### Database Verification

✓ Users list shows all 4+ accounts with roles; soft-deleted users/theatres/movies never appear.

### Next Step

Phase 3 — theatre admin.

### Common Failure Cases

| Scenario                                                                                | Status | Body                                |
| --------------------------------------------------------------------------------------- | ------ | ----------------------------------- |
| `page=0` or `size=0`                                                                | 422    | validation error (ge=1)             |
| `size=101`                                                                            | 422    | validation error (le=100)           |
| Regular-user token (on**any** of the three listings, including `/admin/movies`) | 403    | `{"detail": "Permission denied"}` |

---

# PHASE 3 — Theatre Admin Flows

Sign in as the seeded theatre operator: **`jaymin4724@gmail.com`** (linked to the theatre in Step 14).

## Step 20

### Objective

Obtain theatre-admin tokens.

### Endpoints (two calls)

1. `POST /api/v1/auth/send-otp` body `{ "email": "jaymin4724@gmail.com" }`
2. `POST /api/v1/auth/signin` body:

```json
{
  "email": "jaymin4724@gmail.com",
  "otp": "{{OTP}}"
}
```

### Expected Response

**201**, `"User login successfully"`, token pair.

### Save

- **TA_ACCESS_TOKEN**, **TA_REFRESH_TOKEN**

### Next Step

Step 21.

---

## Step 21

### Objective

Theatre admin sees the theatres mapped to them.

### Endpoint

`GET /api/v1/theatre-admin/my-theatres?page=1&size=10`

### Headers

| Header        | Value                          |
| ------------- | ------------------------------ |
| Authorization | `Bearer {{TA_ACCESS_TOKEN}}` |

### Expected Response

**200 OK**, message `"Theatres fetched successfully"`, `data` contains the theatre from Step 14 (`pvr acropolis`, `{{THEATRE_ID}}`).

### Next Step

Step 22 — create the seat layout.

### Common Failure Cases

| Scenario                                    | Status                |
| ------------------------------------------- | --------------------- |
| Regular-user token                          | 403 Permission denied |
| Operator with no theatres (jaymindrive2024) | 200 with`data: []`  |

---

## Step 22

### Objective

Create a seat layout for the theatre. The raw grid is "polished" server-side: rows containing seats get letters (A, B, …), seats get numbers per row (A1, A2, …), categories are lowercased, and a `seat_mapping` is generated.

### Endpoint

`POST /api/v1/theatre-admin/create-layout`

### Headers

| Header        | Value                          |
| ------------- | ------------------------------ |
| Authorization | `Bearer {{TA_ACCESS_TOKEN}}` |
| Content-Type  | `application/json`           |

### Request Body

A 3×4 grid: row 1 = premium (2 seats, aisle, 1 seat), row 2 = standard (4 seats), row 3 = a gap row + 2 standard seats:

```json
{
  "name": "Audi 1 Standard Layout",
  "theatre_id": "{{THEATRE_ID}}",
  "layout": {
    "metadata": { "grid_rows": 3, "grid_columns": 4 },
    "layout": [
      [
        { "grid_type": "seat", "category": "premium" },
        { "grid_type": "seat", "category": "premium" },
        null,
        { "grid_type": "seat", "category": "premium" }
      ],
      [
        { "grid_type": "seat", "category": "standard" },
        { "grid_type": "seat", "category": "standard" },
        { "grid_type": "seat", "category": "standard" },
        { "grid_type": "seat", "category": "standard" }
      ],
      [
        { "grid_type": "gap", "category": null },
        null,
        { "grid_type": "seat", "category": "standard" },
        { "grid_type": "seat", "category": "standard" }
      ]
    ]
  }
}
```

### Expected Response

**201 Created**

```json
{
  "success": true,
  "message": "New layout created successfully",
  "data": {
    "id": "<uuid>",
    "layout": {
      "layout": [
        [
          {"grid_type": "seat", "seat_number": "A1", "category": "premium"},
          {"grid_type": "seat", "seat_number": "A2", "category": "premium"},
          null,
          {"grid_type": "seat", "seat_number": "A3", "category": "premium"}
        ],
        [
          {"grid_type": "seat", "seat_number": "B1", "category": "standard"},
          {"grid_type": "seat", "seat_number": "B2", "category": "standard"},
          {"grid_type": "seat", "seat_number": "B3", "category": "standard"},
          {"grid_type": "seat", "seat_number": "B4", "category": "standard"}
        ],
        [
          {"grid_type": "gap", "seat_number": null, "category": null},
          null,
          {"grid_type": "seat", "seat_number": "C1", "category": "standard"},
          {"grid_type": "seat", "seat_number": "C2", "category": "standard"}
        ]
      ],
      "category": ["premium", "standard"],
      "seat_mapping": { "A1": [0,0], "A2": [0,1], "A3": [0,3], "B1": [1,0], "B2": [1,1], "B3": [1,2], "B4": [1,3], "C1": [2,2], "C2": [2,3] },
      "metadata": { "row": 3, "column": 4, "total_seats": 9 }
    }
  }
}
```

### Database Verification

✓ `layouts` row with the polished JSON, `theatre_id` set
✓ `total_seats = 9`, categories = `["premium", "standard"]`

### Save

- **LAYOUT_ID** = `data.id`

### Next Step

Step 23 — rename layout, then Step 24 — screen.

### Common Failure Cases

| Scenario                                                                    | Status | Body                                         |
| --------------------------------------------------------------------------- | ------ | -------------------------------------------- |
| `theatre_id` not owned by this operator                                   | 404    | `{"detail": "Theatre not found"}`          |
| Missing`metadata`/`grid_rows`/`grid_columns` or `layout` not a list | 400    | `{"detail": "Layout format is not valid"}` |
| Regular-user token                                                          | 403    | Permission denied                            |

---

## Step 23

### Objective

Rename the layout (only `name` is editable — the grid is frozen once created).

### Endpoint

`PATCH /api/v1/theatre-admin/layout/update/{{LAYOUT_ID}}`

### Headers

| Header        | Value                          |
| ------------- | ------------------------------ |
| Authorization | `Bearer {{TA_ACCESS_TOKEN}}` |
| Content-Type  | `application/json`           |

### Request Body

```json
{
  "name": "Audi 1 Layout v2"
}
```

### Expected Response

**200 OK**

```json
{
  "success": true,
  "message": "Layout updated successfully",
  "data": { "id": "<uuid>", "name": "audi 1 layout v2" }
}
```

### Common Failure Cases

| Scenario                             | Status | Body                               |
| ------------------------------------ | ------ | ---------------------------------- |
| Layout of another operator's theatre | 404    | `{"detail": "Layout not found"}` |
| Regular-user token                   | 403    | Permission denied                  |

### Next Step

Step 24.

---

## Step 24

### Objective

Create a screen bound to the theatre + layout.

### Endpoint

`POST /api/v1/theatre-admin/create-screen`

### Headers

| Header        | Value                          |
| ------------- | ------------------------------ |
| Authorization | `Bearer {{TA_ACCESS_TOKEN}}` |
| Content-Type  | `application/json`           |

### Request Body

```json
{
  "name": "Audi 1",
  "theatre_id": "{{THEATRE_ID}}",
  "layout_id": "{{LAYOUT_ID}}"
}
```

### Expected Response

**201 Created**

```json
{
  "success": true,
  "message": "Screen created successfully",
  "data": {
    "id": "<uuid>",
    "name": "audi 1",
    "theatre_id": "<THEATRE_ID>",
    "layout_id": "<LAYOUT_ID>"
  }
}
```

### Database Verification

✓ `screens` row, `is_active=true`

### Save

- **SCREEN_ID** = `data.id`

### Next Step

Step 25 — list screens; Step 26 — rename screen.

### Common Failure Cases

| Scenario                                     | Status | Body                                |
| -------------------------------------------- | ------ | ----------------------------------- |
| Theatre not owned by operator                | 404    | `{"detail": "Theatre not found"}` |
| `layout_id` belongs to a different theatre | 404    | `{"detail": "Layout not found"}`  |

---

## Step 25

### Objective

List the operator's screens with theatre/layout names joined.

### Endpoint

`GET /api/v1/theatre-admin/my-screens?page=1&size=10`

### Headers

| Header        | Value                          |
| ------------- | ------------------------------ |
| Authorization | `Bearer {{TA_ACCESS_TOKEN}}` |

### Expected Response

**200 OK**, message `"Screens fetched successfully"`:

```json
{
  "data": [
    {
      "id": "<SCREEN_ID>",
      "name": "audi 1",
      "theatre_id": "<THEATRE_ID>",
      "theatre_name": "pvr acropolis",
      "layout_id": "<LAYOUT_ID>",
      "layout_name": "audi 1 layout v2"
    }
  ]
}
```

### Next Step

Step 26.

---

## Step 26

### Objective

Rename the screen (name only; `layout_id` is immutable).

### Endpoint

`PATCH /api/v1/theatre-admin/screen/update/{{SCREEN_ID}}`

### Headers

| Header        | Value                          |
| ------------- | ------------------------------ |
| Authorization | `Bearer {{TA_ACCESS_TOKEN}}` |
| Content-Type  | `application/json`           |

### Request Body

```json
{
  "name": "Audi 1 IMAX"
}
```

### Expected Response

**200 OK**, `"Screen updated successfully"`, `data.name = "audi 1 imax"`.

### Common Failure Cases

| Scenario                   | Status | Body                               |
| -------------------------- | ------ | ---------------------------------- |
| Screen of another operator | 404    | `{"detail": "Screen not found"}` |
| Regular-user token         | 403    | Permission denied                  |

### Next Step

Step 27 — create shows.

---

## Step 27

### Objective

Create a show. Constraints enforced server-side (all in UTC):

- `start_time` must be **≥ now + 2 hours** and **≤ now + 3 days**
- must not overlap the previous/next show on the same screen (movie runtime is used)
- `category_price` must contain **every** category present in the screen's layout (`premium`, `standard`)

### Endpoint

`POST /api/v1/theatre-admin/create-show`

### Headers

| Header        | Value                          |
| ------------- | ------------------------------ |
| Authorization | `Bearer {{TA_ACCESS_TOKEN}}` |
| Content-Type  | `application/json`           |

### Request Body

> ⚠️ Adjust `start_time` before running: pick a UTC datetime **8–24 hours from now** (8+ hours ahead keeps the later cancellation test valid, which requires ≥ 6 h before showtime). Example assumes today is 2026-07-13:

```json
{
  "start_time": "2026-07-14T14:30:00",
  "screen_id": "{{SCREEN_ID}}",
  "movie_id": "{{MOVIE_ID}}",
  "category_price": {
    "premium": 450.0,
    "standard": 220.0
  }
}
```

### Expected Response

**201 Created**

```json
{
  "success": true,
  "message": "Show created successfully",
  "data": {
    "id": "<uuid>",
    "start_time": "2026-07-14T14:30:00",
    "screen_id": "<SCREEN_ID>",
    "movie_id": "<MOVIE_ID>",
    "category_pricing": { "premium": 450.0, "standard": 220.0 },
    "is_deleted": false
  }
}
```

### Database Verification

✓ `shows` row with `category_pricing` JSON, `is_deleted=false`

### Save

- **SHOW_ID** = `data.id`

### Next Step

Step 28 — second show (for the cancel test) + negative timing cases.

### Common Failure Cases

| Scenario                               | Status | Body                                                                  |
| -------------------------------------- | ------ | --------------------------------------------------------------------- |
| `start_time` < now + 2 h             | 400    | `{"detail": "Show must be scheduled at least 2 hours from now."}`   |
| `start_time` > now + 3 days          | 400    | `{"detail": "Show date cannot be more than 3 days in the future."}` |
| Overlaps previous show on screen       | 400    | `{"detail": "Show is overlapping with previous show"}`              |
| Another show starts during this one    | 400    | `{"detail": "Show is overlapping with next movie"}`                 |
| `category_price` missing `premium` | 400    | `{"detail": "Category not found in price list"}`                    |
| Non-numeric price (`"abc"`)          | 422    | validation error                                                      |
| Screen not owned / inactive            | 404    | `{"detail": "Screen not found"}`                                    |
| Deleted/unknown movie                  | 404    | `{"detail": "Movie not found"}`                                     |

---

## Step 28

### Objective

(a) Create a **second show** on the same screen for the cancellation test (a different time slot, still ≥ 8 h out and non-overlapping — *One Battle After Another* runs 161 min, so leave ≥ 3 h between starts).
(b) Immediately verify the **overlap guard** with a third request.

### Endpoint

`POST /api/v1/theatre-admin/create-show` (same headers)

### Request Body (a) — succeeds

```json
{
  "start_time": "2026-07-14T18:00:00",
  "screen_id": "{{SCREEN_ID}}",
  "movie_id": "{{MOVIE_ID_2}}",
  "category_price": { "premium": 400.0, "standard": 200.0 }
}
```

**Expected:** 201. **Save:** **SHOW_ID_CANCEL** = `data.id`.

### Request Body (b) — overlap, must fail

```json
{
  "start_time": "2026-07-14T15:00:00",
  "screen_id": "{{SCREEN_ID}}",
  "movie_id": "{{MOVIE_ID_2}}",
  "category_price": { "premium": 400.0, "standard": 200.0 }
}
```

**Expected:** 400 `{"detail": "Show is overlapping with previous show"}` (14:30 show runs until ≈17:11).

### Next Step

Step 29 — update show pricing.

---

## Step 29

### Objective

Update a show's category pricing (only pricing is editable; time/screen/movie are frozen).

### Endpoint

`PATCH /api/v1/theatre-admin/show/update/{{SHOW_ID}}`

### Headers

| Header        | Value                          |
| ------------- | ------------------------------ |
| Authorization | `Bearer {{TA_ACCESS_TOKEN}}` |
| Content-Type  | `application/json`           |

### Request Body

```json
{
  "category_price": { "premium": 500.0, "standard": 250.0 }
}
```

### Expected Response

**200 OK**, `"Show updated successfully"`, `data.category_pricing` reflects new prices.

> ⚠️ Note for the booking phase: the cached seat layout in Redis keeps the **old** prices until it expires (100 min TTL) or is regenerated. If you update pricing after someone viewed the show, `GET /users/show/{id}` may still show old prices — acceptable, but bookings compute the bill from the cached layout. Test pricing updates **before** first seat-map view.

### Common Failure Cases

| Scenario                  | Status | Body                                               |
| ------------------------- | ------ | -------------------------------------------------- |
| Missing a layout category | 400    | `{"detail": "Category not found in price list"}` |
| Show of another operator  | 404    | `{"detail": "Show not found"}`                   |
| Regular-user token        | 403    | Permission denied                                  |
| Empty body`{}`          | 200    | no-op, returns current show                        |

### Next Step

Phase 4 — public discovery.

---

# PHASE 4 — Search & Public Browsing (no auth required)

## Step 30

### Objective

Verify Elasticsearch global search (prefix match on movie/theatre names). **Public — no token.**

### Endpoint

`GET /api/v1/search/?q=one&limit=10`

### Query Parameters

| Param | Rules                       |
| ----- | --------------------------- |
| q     | required, min length 1      |
| limit | optional, 1–50, default 10 |

### Expected Response

**200 OK**

```json
{
  "success": true,
  "message": "Search results retrieved successfully",
  "data": {
    "items": [
      { "name": "one battle after another", "type": "movie", "db_id": "<MOVIE_ID>", "score": 1.54 }
    ],
    "total": 1
  }
}
```

Also test `q=pvr` → returns the theatre (`"type": "theatre"`, `db_id = THEATRE_ID`). Search results confirm the **background ES sync** from movie/theatre creation worked.

### Common Failure Cases

| Scenario                    | Status | Body                                                |
| --------------------------- | ------ | --------------------------------------------------- |
| Missing`q`                | 422    | validation error                                    |
| `limit=0` or `limit=51` | 422    | validation error                                    |
| No matches (`q=zzzz`)     | 200    | `{"items": [], "total": 0}`                       |
| Elasticsearch down          | 503    | `{"detail": "Search is temporarily unavailable"}` |

### Next Step

Step 31.

---

## Step 31

### Objective

Browse movies playing in a theatre, and theatres playing a movie. Only movies/theatres with **upcoming, non-deleted shows** appear. **Public.**

### Endpoints

1. `GET /api/v1/users/theatre/{{THEATRE_ID}}/movies?page=1&size=10`
2. `GET /api/v1/users/movie/{{MOVIE_ID}}/theatres?page=1&size=10`

### Expected Responses

**200 OK** each:

1. message `"Movies for the specified theatre fetched successfully"` — `data` includes both movies with shows (Steps 27–28).
2. message `"Theatres screening this movie fetched successfully"` — `data` includes `pvr acropolis`.

### Common Failure Cases

| Scenario                             | Status | Body                            |
| ------------------------------------ | ------ | ------------------------------- |
| Valid-UUID-but-unknown theatre/movie | 200    | `data: []` (not a 404)        |
| Malformed UUID                       | 500    | global handler (known behavior) |

### Next Step

Step 32.

---

## Step 32

### Objective

List shows for a movie+theatre pair. Two equivalent paths exist — test at least one, ideally both.

### Endpoints

- `GET /api/v1/users/theatre/{{THEATRE_ID}}/movie/{{MOVIE_ID}}?page=1&size=10`
- `GET /api/v1/users/movie/{{MOVIE_ID}}/theatre/{{THEATRE_ID}}?page=1&size=10` *(alias route, same handler)*

### Expected Response

**200 OK**, message `"Available shows for this movie and theatre fetched successfully"`:

```json
{
  "data": [
    {
      "id": "<SHOW_ID>",
      "start_time": "2026-07-14T14:30:00",
      "screen_id": "<SCREEN_ID>",
      "movie_id": "<MOVIE_ID>",
      "category_pricing": { "premium": 500.0, "standard": 250.0 },
      "is_deleted": false,
      "movie_name": "one battle after another",
      "theatre_name": "pvr acropolis",
      "screen_name": "audi 1 imax"
    }
  ]
}
```

### Next Step

Step 33 — profile setup, then the booking flow.

---

# PHASE 5 — User Profile & Booking Flow

Use the **regular user** token (`jaymindrive2023@gmail.com` — re-login from Step 8's note if needed).

## Step 33

### Objective

Fetch own profile.

### Endpoint

`GET /api/v1/users/me`

### Headers

| Header        | Value                       |
| ------------- | --------------------------- |
| Authorization | `Bearer {{ACCESS_TOKEN}}` |

### Expected Response

**200 OK**

```json
{
  "success": true,
  "message": "Profile fetched successfully",
  "data": {
    "id": "<uuid>",
    "email": "jaymindrive2023@gmail.com",
    "is_active": true,
    "role": "user",
    "google_id": null,
    "user_detail": null
  }
}
```

### Save

- **USER_ID** = `data.id`

### Next Step

Step 34.

---

## Step 34

### Objective

Update profile details (partial).

### Endpoint

`PATCH /api/v1/users/me`

### Headers

| Header        | Value                       |
| ------------- | --------------------------- |
| Authorization | `Bearer {{ACCESS_TOKEN}}` |
| Content-Type  | `application/json`        |

### Request Body

```json
{
  "first_name": "Jaymin",
  "last_name": "Dave",
  "mobile_no": "+919876543210"
}
```

### Expected Response

**200 OK**, `"Profile updated successfully"`, `data.user_detail = {"first_name": "Jaymin", "last_name": "Dave", "mobile_no": "+919876543210"}`.

### Database Verification

✓ `user_details` row updated for `USER_ID`

### Next Step

Step 35 — view the seat map.

---

## Step 35

### Objective

Fetch show details with the **live seat map** (statuses: `Available` / `Locked` / `Booked`, price per seat). First call generates the layout into Redis (cache TTL 100 min). **Public — no auth.**

### Endpoint

`GET /api/v1/users/show/{{SHOW_ID}}`

### Expected Response

**200 OK**, message `"Show details fetched successfully"`:

```json
{
  "data": {
    "layout": [
      [
        {"grid_type": "seat", "seat_number": "A1", "category": "premium", "price": 500.0, "status": "Available"},
        {"grid_type": "seat", "seat_number": "A2", "category": "premium", "price": 500.0, "status": "Available"},
        null,
        {"grid_type": "seat", "seat_number": "A3", "category": "premium", "price": 500.0, "status": "Available"}
      ],
      [ {"...": "B1–B4 standard @ 250.0, Available"} ],
      [ {"...": "gap"}, null, {"...": "C1, C2 standard, Available"} ]
    ],
    "metadata": { "row": 3, "column": 4, "total_seats": 9, "booked_seats": 0 },
    "category_pricing": { "premium": 500.0, "standard": 250.0 },
    "seat_mapping": { "A1": [0,0], "...": "..." }
  }
}
```

### Database Verification

✓ Redis: `show_seat_layout_<SHOW_ID>` JSON key created with TTL 6000 s

### Next Step

Step 36 — lock seats.

### Common Failure Cases

| Scenario          | Status | Body                             |
| ----------------- | ------ | -------------------------------- |
| Unknown show UUID | 404    | `{"detail": "Show not found"}` |

---

## Step 36

### Objective

Lock seats for checkout. Locks are **all-or-nothing** (atomic Lua script) and expire after **10 minutes**.

### Endpoint

`POST /api/v1/users/show/{{SHOW_ID}}/seat-lock`

### Headers

| Header        | Value                       |
| ------------- | --------------------------- |
| Authorization | `Bearer {{ACCESS_TOKEN}}` |
| Content-Type  | `application/json`        |

### Request Body

```json
{
  "seat_array": ["A1", "A2", "B1"]
}
```

### Expected Response

**201 Created**

```json
{ "success": true, "message": "Seats Locked Successfully", "data": null }
```

### Database Verification

✓ Redis hash `show_seat_locked_<SHOW_ID>` maps `A1/A2/B1 → USER_ID`, TTL 600 s
✓ Re-run Step 35: those seats now show `"status": "Locked"`

### Concurrency test (do this!)

Lock `["B2"]` with the regular user, then attempt `{"seat_array": ["B2", "B3"]}` with a **different** user's token → **400** `{"detail": "One or more seats were just locked by another user"}` **and** `B3` must remain Available (atomicity).

### Next Step

Step 37 — book.

### Common Failure Cases

| Scenario                    | Status | Body                                     |
| --------------------------- | ------ | ---------------------------------------- |
| Nonexistent seat (`"Z9"`) | 404    | `{"detail": "Seat Z9 not found"}`      |
| Seat already Locked/Booked  | 400    | `{"detail": "Seat A1 is unavailable"}` |
| Empty`seat_array`         | 422    | validation error (min 1 item)            |
| No token                    | 401    | `{"detail": "Not authenticated"}`      |

---

## Step 37

### Objective

Book the locked seats. Requires that **this user holds the lock** for every requested seat. Creates the booking, generates an encrypted ticket hash, and emails a **QR ticket** (background task).

### Endpoint

`POST /api/v1/users/show/{{SHOW_ID}}/seat-book`

### Headers

| Header        | Value                       |
| ------------- | --------------------------- |
| Authorization | `Bearer {{ACCESS_TOKEN}}` |
| Content-Type  | `application/json`        |

### Request Body

```json
{
  "seat_array": ["A1", "A2", "B1"]
}
```

### Expected Response

**201 Created**

```json
{
  "success": true,
  "message": "Tickets Booked Successfully",
  "data": {
    "booking_id": "<uuid>",
    "total_paid": 1250.0
  }
}
```

*(2 × premium 500 + 1 × standard 250 = 1250)*

### Database Verification

✓ `bookings` row: `user_id`, `show_id`, `number_of_seats=3`, `total_bill=1250`, `is_cancelled=false`, `created_at` populated
✓ `booked_seats_map`: 3 rows (A1, A2, B1), `is_cancelled=false`
✓ `booked_tickets` row: `ticket_hash` (Fernet), `expired_time` = show end time, `is_used=false`
✓ Redis: seats flipped to `"Booked"` in `show_seat_layout_<SHOW_ID>`; lock entries removed from `show_seat_locked_<SHOW_ID>`
✓ **Email received:** subject **"Your CineBook Digital Ticket"** with a QR code image — the QR encodes the ticket hash string

### Save

- **BOOKING_ID** = `data.booking_id`
- **TICKET_HASH** = decode the QR from the email (any phone/online QR reader) — a string starting with `gAAAA...`

### Next Step

Step 38 — booking history.

### Common Failure Cases

| Scenario                                                | Status | Body                                                                                                       |
| ------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------- |
| Booking without locking first (or lock expired >10 min) | 403    | `{"detail": "Seat A1 lock expired or invalid"}`                                                          |
| Booking a seat locked by another user                   | 403    | `{"detail": "Seat B2 lock expired or invalid"}`                                                          |
| Seat already booked (race)                              | 409    | `{"detail": "Seat(s) A1 already booked"}` or `"One or more seats were already booked by someone else"` |
| Empty`seat_array`                                     | 422    | validation error                                                                                           |

---

## Step 38

### Objective

Fetch booking history (paginated, newest first).

### Endpoint

`GET /api/v1/users/bookings?page=1&size=10`

### Headers

| Header        | Value                       |
| ------------- | --------------------------- |
| Authorization | `Bearer {{ACCESS_TOKEN}}` |

### Expected Response

**200 OK**, message `"Booking history fetched successfully"`:

```json
{
  "data": [
    {
      "id": "<BOOKING_ID>",
      "show_id": "<SHOW_ID>",
      "total_bill": 1250.0,
      "number_of_seats": 3,
      "is_cancelled": false,
      "created_at": "2026-07-13T...",
      "movie_name": "one battle after another",
      "theatre_name": "pvr acropolis",
      "show_start_time": "2026-07-14T14:30:00"
    }
  ]
}
```

### Next Step

Step 39.

---

## Step 39

### Objective

Fetch a single booking with per-seat detail. Ownership is enforced — only the booking's owner can read it.

### Endpoint

`GET /api/v1/users/bookings/{{BOOKING_ID}}`

### Headers

| Header        | Value                       |
| ------------- | --------------------------- |
| Authorization | `Bearer {{ACCESS_TOKEN}}` |

### Expected Response

**200 OK**, message `"Booking detail fetched successfully"` — same fields as Step 38 plus:

```json
"seats": [
  { "seats_number": "A1", "is_cancelled": false },
  { "seats_number": "A2", "is_cancelled": false },
  { "seats_number": "B1", "is_cancelled": false }
]
```

### Ownership test (do this!)

Request the same `BOOKING_ID` with `{{TA_ACCESS_TOKEN}}` → **404** `{"detail": "Booking not found"}` (not 403 — existence is not leaked).

### Next Step

Phase 6 — ticket verification.

---

# PHASE 6 — Ticket Verification (Theatre Admin)

## Step 40

### Objective

The theatre operator scans the customer's QR and verifies the ticket. Valid only if: ticket exists, show not ended (`expired_time` in future), **not already used**, booking not cancelled, and the verifying operator **owns the theatre**.

### Endpoint

`POST /api/v1/theatre-admin/verify-ticket`

### Headers

| Header        | Value                          |
| ------------- | ------------------------------ |
| Authorization | `Bearer {{TA_ACCESS_TOKEN}}` |
| Content-Type  | `application/json`           |

### Request Body

```json
{
  "ticket_hash": "{{TICKET_HASH}}"
}
```

### Expected Response

**200 OK**

```json
{ "success": true, "message": "Ticket verified successfully", "data": null }
```

### Database Verification

✓ `booked_tickets.is_used` flipped to `true` for `BOOKING_ID`

### Re-use test (do this!)

Send the **same request again** → **404** `{"detail": "Ticket is not valid"}` (single-entry enforcement).

### Next Step

Phase 7 — cancellation.

### Common Failure Cases

| Scenario                                 | Status | Body                                                  |
| ---------------------------------------- | ------ | ----------------------------------------------------- |
| Ticket already used                      | 404    | `{"detail": "Ticket is not valid"}`                 |
| Booking cancelled                        | 404    | `{"detail": "Ticket is not valid"}`                 |
| Show already ended                       | 404    | `{"detail": "Ticket is not valid"}`                 |
| Operator of a**different** theatre | 404    | `{"detail": "Ticket Not Found"}`                    |
| Garbage hash (not valid Fernet)          | 500    | global handler (decryption failure — known behavior) |
| Regular-user token                       | 403    | Permission denied                                     |

---

# PHASE 7 — Booking Cancellation

## Step 41

### Objective

Book seats on the **second show** (`SHOW_ID_CANCEL`, ≥ 8 h away) so we can cancel: cancellation is allowed only **≥ 6 hours before showtime**.

### Endpoints (as regular user, same pattern as Steps 36–37)

1. `POST /api/v1/users/show/{{SHOW_ID_CANCEL}}/seat-lock` body `{"seat_array": ["C1", "C2"]}` → 201
2. `POST /api/v1/users/show/{{SHOW_ID_CANCEL}}/seat-book` body `{"seat_array": ["C1", "C2"]}` → 201

### Save

- **BOOKING_ID_CANCEL** = `data.booking_id` from the book call

### Next Step

Step 42.

---

## Step 42

### Objective

Cancel the booking and verify seats are released.

### Endpoint

`POST /api/v1/users/bookings/{{BOOKING_ID_CANCEL}}/cancel`

### Headers

| Header        | Value                       |
| ------------- | --------------------------- |
| Authorization | `Bearer {{ACCESS_TOKEN}}` |

### Expected Response

**200 OK**

```json
{ "success": true, "message": "Booking cancelled successfully", "data": null }
```

### Database Verification

✓ `bookings.is_cancelled = true`
✓ `booked_seats_map.is_cancelled = true` for C1, C2
✓ Redis seat map: C1/C2 back to `"Available"` (confirm via `GET /users/show/{{SHOW_ID_CANCEL}}`)
✓ The seats can be locked & booked again by another user
✓ The cancelled booking's ticket now fails verify-ticket (404 `"Ticket is not valid"`)

### Next Step

Phase 8 — deletions.

### Common Failure Cases

| Scenario               | Status | Body                                                                             |
| ---------------------- | ------ | -------------------------------------------------------------------------------- |
| Cancel again           | 400    | `{"detail": "Booking is already cancelled"}`                                   |
| Show starts in < 6 h   | 400    | `{"detail": "Booking can only be cancelled at least 6 hours before the show"}` |
| Someone else's booking | 404    | `{"detail": "Booking not found"}`                                              |

---

# PHASE 8 — Deletions (Soft Deletes) & Cleanup

All deletions are **soft deletes** — rows stay in the DB with a flag (`is_active=false` / `is_deleted=true`) and disappear from listings.

## Step 43a — Delete show (theatre admin)

### Endpoint

`DELETE /api/v1/theatre-admin/show/delete/{{SHOW_ID_CANCEL}}`

### Headers

`Authorization: Bearer {{TA_ACCESS_TOKEN}}`

### Expected Response

**200 OK**, `"Show deleted successfully"`, `data.is_deleted = true`.

### Verification

✓ Show disappears from Step 32 listing
✓ Deleting again → 404 `{"detail": "Show not found"}`
✓ Another operator's token → 404

## Step 43b — Delete screen (theatre admin)

### Endpoint

`DELETE /api/v1/theatre-admin/screen/delete/{{SCREEN_ID}}`
*(⚠️ run only after finishing all show/booking tests — screens with the layout you need)*

### Expected Response

**200 OK**, `"Screen deleted successfully"`. Repeat → 404 `"Screen not found"`.

## Step 43c — Delete movie (admin)

### Endpoint

`DELETE /api/v1/admin/movie/delete/{{MOVIE_ID_2}}`

### Headers

`Authorization: Bearer {{ADMIN_ACCESS_TOKEN}}`

### Expected Response

**200 OK**, `"Movie deleted successfully"`, `data.is_deleted = true`.

### Verification

✓ Gone from `GET /admin/movies` and from ES search results (background re-sync)
✓ Creating a show with this movie now → 404 `"Movie not found"`
✓ Repeat delete → 404

## Step 43d — Delete theatre (admin)

### Endpoint

`DELETE /api/v1/admin/theatre/delete/{{THEATRE_ID}}`
*(run last — it cascades visibility: operator's my-theatres becomes empty, screens/shows under it become unreachable for creation flows)*

### Expected Response

**200 OK**, `"Theatre deleted successfully"`, `data.is_active = false`. Repeat → 404 `"Theatre not found"`.

## Step 43e — Delete own account (user)

### Endpoint

`DELETE /api/v1/users/user/delete`

### Headers

`Authorization: Bearer {{ACCESS_TOKEN}}` *(regular user)*

### Expected Response

**200 OK**, `"User deleted successfully"`.

### Verification

✓ `users.is_active = false`
✓ Re-login attempt (send-otp + signin) → **400** `{"detail": "User account is deleted"}`
✓ Calling delete again with the (still unexpired) token → 404 `"User not found"`
✓ User vanishes from `GET /admin/users`

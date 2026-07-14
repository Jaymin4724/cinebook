"""Locust load test for CineBook — seat booking + rate limiting.

Two independent user classes live here; pick one (or both) on the CLI:

    SeatBookingUser   full lock -> book flow against a real seeded show
    RateLimitUser     hammers a cheap endpoint to exercise the token-bucket
                      limiter and reports how many requests got 429'd

Before running, seed data once:

    uv run python loadtest/seed_loadtest_data.py

That writes loadtest/loadtest_data.json (show id, seat ids, user ids), which
this file loads at import time. Access tokens are NOT read from disk — they are
minted fresh here from the seeded user ids using the app's own JWT helper, so
they can never be stale.

See loadtest/README.md for full run/report commands and how to switch the
rate limiter on.
"""

import os
import sys
import json
import random
import itertools
from pathlib import Path

from locust import HttpUser, task, between, tag, events

# Make the project root importable so we can reuse the app's JWT helper and
# settings when Locust loads this file from the loadtest/ directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.helper import generate_access_token_and_refresh_token

# --- Load the seeded fixtures --------------------------------------------
DATA_FILE = Path(__file__).resolve().parent / "loadtest_data.json"
if not DATA_FILE.exists():
    raise RuntimeError(
        f"{DATA_FILE.name} not found. Run the seeder first:\n"
        f"    uv run python loadtest/seed_loadtest_data.py"
    )

_DATA = json.loads(DATA_FILE.read_text())
SHOW_ID: str = _DATA["show_id"]
THEATRE_ID: str = _DATA["theatre_id"]
MOVIE_ID: str = _DATA["movie_id"]
MOVIE_NAME: str = _DATA.get("movie_name", "movie")
SEAT_IDS: list[str] = _DATA["seat_ids"]
USER_IDS: list[str] = _DATA["user_ids"]

# API paths (api_router '/api' -> v1 '/v1' -> user_router '/users').
API = "/api/v1"
BASE = f"{API}/users"
SHOW_DETAILS_PATH = f"{BASE}/show/{SHOW_ID}"
SEAT_LOCK_PATH = f"{BASE}/show/{SHOW_ID}/seat-lock"
SEAT_BOOK_PATH = f"{BASE}/show/{SHOW_ID}/seat-book"

# Round-robin user ids across spawned Locust users so each virtual user acts as
# a distinct authenticated account (matters for seat-lock ownership checks).
_user_cycle = itertools.cycle(USER_IDS)


def _access_token(user_id: str) -> str:
    """Mint a fresh access token for a seeded user id (no OTP needed)."""
    return generate_access_token_and_refresh_token(
        payload={"user_id": user_id}, response=None
    )["access_token"]


def _is_json_envelope_ok(response) -> bool:
    """Validate the standard {status, message, data} response envelope."""
    try:
        body = response.json()
    except ValueError:
        return False
    return isinstance(body, dict) and "message" in body


# =========================================================================
# 1) SEAT BOOKING
# =========================================================================
class SeatBookingUser(HttpUser):
    """Exercises the browse -> lock -> book flow of the booking API.

    Each virtual user owns one seeded account and a private, shuffled pool of
    seats to try. Contention outcomes (seat already locked / already booked)
    are treated as EXPECTED, not failures — losing a race is correct behavior,
    so we only flag genuine errors (5xx, auth failures, malformed bodies).
    """

    # Realistic think-time between actions (seconds).
    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.user_id = next(_user_cycle)
        self.client.headers.update(
            {
                "Authorization": f"Bearer {_access_token(self.user_id)}",
                "Content-Type": "application/json",
            }
        )
        # Private shuffled seat order so users don't all collide on seat 1.
        self._seats = SEAT_IDS[:]
        random.shuffle(self._seats)
        self._seat_iter = iter(self._seats)

    def _next_seat(self) -> str:
        """Return the next seat to attempt, reshuffling when exhausted."""
        try:
            return next(self._seat_iter)
        except StopIteration:
            random.shuffle(self._seats)
            self._seat_iter = iter(self._seats)
            return next(self._seat_iter)

    @tag("booking", "browse")
    @task(3)
    def browse_show(self) -> None:
        """GET show details + seat layout (read-heavy, no side effects)."""
        with self.client.get(
            SHOW_DETAILS_PATH, name="GET show details", catch_response=True
        ) as resp:
            if resp.status_code == 429:
                resp.success()  # rate limited — expected when limiter is on
            elif resp.status_code == 200 and _is_json_envelope_ok(resp):
                resp.success()
            else:
                resp.failure(f"unexpected {resp.status_code}: {resp.text[:200]}")

    @tag("booking", "book")
    @task(1)
    def lock_and_book(self) -> None:
        """Lock a seat, then book it. The two-step flow the real client uses."""
        seat = self._next_seat()
        body = {"seat_array": [seat]}

        # --- Step 1: lock ---
        with self.client.post(
            SEAT_LOCK_PATH, json=body, name="POST seat-lock", catch_response=True
        ) as lock_resp:
            if lock_resp.status_code == 201:
                lock_resp.success()
            elif lock_resp.status_code == 400:
                # Seat unavailable / just locked by someone else — expected race.
                lock_resp.success()
                return
            elif lock_resp.status_code == 429:
                lock_resp.success()
                return
            else:
                lock_resp.failure(
                    f"lock unexpected {lock_resp.status_code}: {lock_resp.text[:200]}"
                )
                return

        # --- Step 2: book (only reached if the lock succeeded) ---
        with self.client.post(
            SEAT_BOOK_PATH, json=body, name="POST seat-book", catch_response=True
        ) as book_resp:
            if book_resp.status_code == 201 and _is_json_envelope_ok(book_resp):
                book_resp.success()
            elif book_resp.status_code in (403, 409):
                # 403 lock expired, 409 already booked — both expected races.
                book_resp.success()
            elif book_resp.status_code == 429:
                book_resp.success()
            else:
                book_resp.failure(
                    f"book unexpected {book_resp.status_code}: {book_resp.text[:200]}"
                )


# =========================================================================
# 2) WHOLE-APP READ LATENCY
# =========================================================================
class FullAppUser(HttpUser):
    """Exercises the read surface of the app to measure end-to-end latency.

    Each request gets a distinct `name=`, so Locust reports latency (avg /
    median / p95 / p99) per endpoint, and the "Aggregated" row gives the
    whole-app average across the mix below. Weights approximate a realistic
    read profile (browsing dominates). Use this class to answer "how fast is
    the app overall?" rather than to stress a single hot path.
    """

    wait_time = between(1, 3)

    def on_start(self) -> None:
        # Authenticate so /me and /bookings are reachable; harmless on the
        # public browse endpoints.
        self.user_id = next(_user_cycle)
        self.client.headers.update(
            {"Authorization": f"Bearer {_access_token(self.user_id)}"}
        )

    def _get(self, path: str, name: str, envelope: bool = True) -> None:
        """GET + validate. 429 (limiter) is treated as expected."""
        with self.client.get(path, name=name, catch_response=True) as resp:
            if resp.status_code == 429:
                resp.success()
            elif resp.status_code == 200 and (not envelope or _is_json_envelope_ok(resp)):
                resp.success()
            else:
                resp.failure(f"unexpected {resp.status_code}: {resp.text[:200]}")

    @tag("read", "health")
    @task(1)
    def health(self) -> None:
        # /health returns its own {status, checks} shape, not the envelope,
        # and 503 when a dependency is degraded — accept both 200 and 503.
        with self.client.get("/health", name="GET health", catch_response=True) as resp:
            if resp.status_code in (200, 503):
                resp.success()
            else:
                resp.failure(f"unexpected {resp.status_code}: {resp.text[:200]}")

    @tag("read", "browse")
    @task(4)
    def movies_by_theatre(self) -> None:
        self._get(f"{BASE}/theatre/{THEATRE_ID}/movies", "GET movies-by-theatre")

    @tag("read", "browse")
    @task(4)
    def theatres_by_movie(self) -> None:
        self._get(f"{BASE}/movie/{MOVIE_ID}/theatres", "GET theatres-by-movie")

    @tag("read", "browse")
    @task(3)
    def shows(self) -> None:
        self._get(
            f"{BASE}/theatre/{THEATRE_ID}/movie/{MOVIE_ID}", "GET shows"
        )

    @tag("read", "browse")
    @task(5)
    def show_details(self) -> None:
        # Heaviest read: builds/serves the full seat layout.
        self._get(SHOW_DETAILS_PATH, "GET show details")

    @tag("read", "search")
    @task(2)
    def search(self) -> None:
        self._get(
            f"{API}/search/?q={MOVIE_NAME}&limit=10", "GET search"
        )

    @tag("read", "profile")
    @task(2)
    def profile(self) -> None:
        self._get(f"{BASE}/me", "GET profile")

    @tag("read", "profile")
    @task(1)
    def bookings(self) -> None:
        self._get(f"{BASE}/bookings", "GET booking history")


# =========================================================================
# 3) RATE LIMITING
# =========================================================================
# The limiter (app/middlewares/rate_limiting_middleware.py) is a per-IP token
# bucket: capacity=10, refill_rate=0.1/s (1 token every 10s). It is only added
# when the app runs with ENV != "TESTING". All Locust traffic shares one host
# IP, so once the bucket drains you should see a burst of ~10 successes and
# then a stream of 429s. This class hits a cheap endpoint as fast as possible
# to make that transition visible.
_RL_STATS = {"passed": 0, "limited": 0}


class RateLimitUser(HttpUser):
    """Probes the token-bucket limiter and tallies 200s vs 429s."""

    wait_time = between(0, 0)  # no think time: drain the bucket aggressively

    @tag("ratelimit")
    @task
    def probe(self) -> None:
        with self.client.get(
            SHOW_DETAILS_PATH, name="RL probe (GET show)", catch_response=True
        ) as resp:
            if resp.status_code == 429:
                _RL_STATS["limited"] += 1
                resp.success()  # a 429 is the behavior we're validating
            elif resp.status_code == 200:
                _RL_STATS["passed"] += 1
                resp.success()
            else:
                resp.failure(f"unexpected {resp.status_code}: {resp.text[:200]}")


@events.quitting.add_listener
def _report_rate_limit(environment, **_kwargs) -> None:
    """Print the pass/429 split after a RateLimitUser run."""
    total = _RL_STATS["passed"] + _RL_STATS["limited"]
    if total == 0:
        return
    pct = 100 * _RL_STATS["limited"] / total
    print("\n--- Rate-limit summary -------------------------------------")
    print(f"  probes sent      : {total}")
    print(f"  passed (2xx)     : {_RL_STATS['passed']}")
    print(f"  rate-limited 429 : {_RL_STATS['limited']}  ({pct:.1f}%)")
    if _RL_STATS["limited"] == 0:
        print("  NOTE: no 429s seen — is the app running with ENV != TESTING?")
    print("------------------------------------------------------------")

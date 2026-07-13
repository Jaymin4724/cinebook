# ---------------------------------------------------------------------------
# Base image
# ---------------------------------------------------------------------------
# We start from the official "uv" image. It already contains Python 3.12 and
# "uv" (a very fast Python package manager, a modern replacement for pip).
# "slim" = a smaller image with only the essentials, so builds are faster.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /cinebook

# ---------------------------------------------------------------------------
# uv settings (make installs faster and containers cleaner)
# ---------------------------------------------------------------------------
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# ---------------------------------------------------------------------------
# Install dependencies (this layer is cached so rebuilds are fast)
# ---------------------------------------------------------------------------
# We copy ONLY the dependency files first. Docker caches this step, so as long
# as these two files don't change, it will reuse the installed packages and
# skip re-downloading everything on the next build.
COPY pyproject.toml uv.lock ./

# --frozen  : install the exact versions locked in uv.lock (reproducible builds)
# --no-dev  : skip dev-only tools we don't need to run the app
RUN uv sync --frozen --no-dev

# debugpy lets us attach a debugger from our editor (used by docker-compose).
# Installing it here means it's baked into the image ONCE, instead of being
# reinstalled every time the container starts.
RUN uv pip install debugpy

# ---------------------------------------------------------------------------
# Copy the application code
# ---------------------------------------------------------------------------
# Done AFTER installing packages so that editing your code doesn't invalidate
# the (slow) dependency layer above.
COPY . .

ENV PATH="/cinebook/.venv/bin:$PATH"

# The port the FastAPI app listens on (documentation only; publishing the port
# is done in docker-compose.yaml).
EXPOSE 8000

RUN chmod +x /cinebook/entrypoint.sh

ENTRYPOINT ["/cinebook/entrypoint.sh"]

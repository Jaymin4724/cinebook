FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /cinebook

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY . .

ENV PATH="/cinebook/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

EXPOSE 8000

RUN chmod +x /cinebook/entrypoint.sh

ENTRYPOINT ["/cinebook/entrypoint.sh"]
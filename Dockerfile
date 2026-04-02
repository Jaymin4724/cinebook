FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /online-ticket-booking-system

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY . .

ENV PATH="/online-ticket-booking-system/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

EXPOSE 8000

RUN chmod +x /online-ticket-booking-system/entrypoint.sh

ENTRYPOINT ["/online-ticket-booking-system/entrypoint.sh"]
dep-sync:
	uv sync

fastapi-run:
	uv run fastapi dev app/main.py

db-migration:
	uv run alembic revision --autogenerate -m "$(m)"

db-migrate:
	uv run alembic upgrade head

docker-watch:
	docker compose up --watch

docker-build:
	docker compose build
#!/bin/bash
# This script runs every time the container starts, BEFORE the app itself.

# Stop immediately if any command fails (so we don't start a broken app).
set -e

# Apply any pending database migrations to bring the schema up to date.
alembic upgrade head

# Hand off to the "command" from docker-compose.yaml (starts the server).
# "exec" replaces this script with that process so signals (e.g. Ctrl+C) work.
exec "$@"

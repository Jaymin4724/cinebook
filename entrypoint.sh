#!/bin/bash

set -e

alembic upgrade head

uv pip install debugpy

exec "$@"
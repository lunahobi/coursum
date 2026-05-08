#!/usr/bin/env sh
set -e

echo "Running database migrations..."
needs_stamp=0
python - <<'PY' || needs_stamp=$?
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings

engine = create_engine(get_settings().database_url)
with engine.connect() as connection:
    tables = set(inspect(connection).get_table_names())

has_alembic_version = "alembic_version" in tables
has_existing_schema = bool(tables - {"alembic_version"})
if not has_alembic_version and has_existing_schema:
    print("Existing schema detected without alembic_version table.")
    raise SystemExit(10)
PY

if [ "$needs_stamp" -eq 10 ]; then
  echo "Stamping existing schema to Alembic head..."
  alembic stamp head
elif [ "$needs_stamp" -ne 0 ]; then
  exit "$needs_stamp"
fi

alembic upgrade head
echo "Migrations applied. Starting application..."
exec "$@"

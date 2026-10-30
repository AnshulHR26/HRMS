#!/bin/sh
set -e

echo "Applying database migrations..."
alembic upgrade head

if [ -n "$BOOTSTRAP_ADMIN_PASSWORD" ]; then
  python -m app.scripts.bootstrap_admin
fi

if [ "$SEED_DEMO_DATA" = "true" ]; then
  python -m app.scripts.seed_demo
fi

exec "$@"

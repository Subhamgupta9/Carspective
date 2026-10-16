#!/bin/sh
# ==============================================================================
# CARspective — Production Container Entrypoint Script
# Phase 21D: Flexible startup supporting migrations, testing, and WSGI serving
# ==============================================================================

set -e

# In production mode with PostgreSQL, wait for database if configured
if [ -n "$DATABASE_URL" ] && [ "$DATABASE_WAIT" = "true" ]; then
    echo "Waiting for database readiness..."
    python -c "
import os, sys, time
from sqlalchemy import create_engine, text
url = os.environ.get('DATABASE_URL', '')
if not url:
    print('DATABASE_URL is empty or not configured.', file=sys.stderr)
    sys.exit(1)
for i in range(30):
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('Database connection established successfully.')
        sys.exit(0)
    except Exception as e:
        time.sleep(1)
print('Database connection timed out.', file=sys.stderr)
sys.exit(1)
"
fi

# Run pre-deploy migrations if requested via AUTO_MIGRATE=true
if [ "$AUTO_MIGRATE" = "true" ]; then
    echo "Executing pre-deploy schema migrations (alembic upgrade head)..."
    alembic upgrade head
    echo "Migrations applied successfully."
fi

# If custom arguments are passed to the container, execute them
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

# Default fallback: start production WSGI server
echo "Starting CarSpective production WSGI server..."
exec gunicorn \
    --bind 0.0.0.0:5001 \
    --workers 4 \
    --threads 2 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile - \
    server.wsgi:app

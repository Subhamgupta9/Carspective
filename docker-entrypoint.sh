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

# If custom arguments are passed to the container, execute them.
# Standard server startup uses default CMD ["gunicorn", "server.wsgi:app"] or empty args.
if [ "$#" -gt 0 ]; then
    if [ "$1" != "gunicorn" ] || { [ "$#" -eq 2 ] && [ "$2" != "server.wsgi:app" ]; } || [ "$#" -gt 2 ]; then
        exec "$@"
    fi
fi


# Default fallback: start production WSGI server
PORT_TO_BIND="${PORT:-5001}"
WORKERS_COUNT="${GUNICORN_WORKERS:-1}"
THREADS_COUNT="${GUNICORN_THREADS:-4}"
WORKER_CLASS="${GUNICORN_WORKER_CLASS:-gthread}"
TIMEOUT_SEC="${GUNICORN_TIMEOUT:-60}"

echo "Starting CarSpective production WSGI server on port ${PORT_TO_BIND} (workers: ${WORKERS_COUNT}, threads: ${THREADS_COUNT}, class: ${WORKER_CLASS})..."
exec gunicorn \
    --bind "0.0.0.0:${PORT_TO_BIND}" \
    --workers "${WORKERS_COUNT}" \
    --threads "${THREADS_COUNT}" \
    --worker-class "${WORKER_CLASS}" \
    --timeout "${TIMEOUT_SEC}" \
    --access-logfile - \
    --error-logfile - \
    server.wsgi:app

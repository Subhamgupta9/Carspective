# ==============================================================================
# CARspective — Production Multi-Stage Dockerfile
# Stage 1: Build modern React/Vite frontend assets
# Stage 2: Hardened Python runtime serving API and compiled client
# ==============================================================================

# ------------------------------------------------------------------------------
# STAGE 1: Frontend Build Environment
# ------------------------------------------------------------------------------
FROM node:20.18-alpine AS frontend-builder

WORKDIR /app/client

# Copy package manifests first for efficient Docker layer caching
COPY client/package.json client/package-lock.json* ./

# Install npm dependencies cleanly
RUN npm ci || npm install

# Copy frontend source code and configuration
COPY client/tsconfig.json client/vite.config.ts client/index.html ./
COPY client/src/ ./src/

# Compile production assets to /app/client/dist
RUN npm run build


# ------------------------------------------------------------------------------
# STAGE 2: Hardened Production Python Runtime
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Set production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CARSPECTIVE_ENV=production \
    CARSPECTIVE_DEBUG=false \
    PORT=5001 \
    PYTHONPATH=/app

WORKDIR /app

# Install system runtime dependencies:
# - libgomp1: Mandatory OpenMP runtime dependency for LightGBM model inference
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user and group
RUN groupadd -g 10001 carspective && \
    useradd -u 10001 -g carspective -s /sbin/nologin -d /app carspective

# Install Python production dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code, configuration, and migrations
COPY server/ ./server/
COPY alembic.ini ./

# Copy model artifacts and taxonomy seeds (read-only application assets)
COPY models/ ./models/
COPY data/taxonomy_seeds/ ./data/taxonomy_seeds/

# Copy compiled frontend distribution from Stage 1
COPY --from=frontend-builder /app/client/dist ./client/dist

# Copy container entrypoint script
COPY docker-entrypoint.sh ./

# Create persistent database directory, set entrypoint permissions, and assign non-root ownership
RUN chmod +x docker-entrypoint.sh && \
    mkdir -p /app/data/database && \
    chown -R carspective:carspective /app

# Switch to non-root runtime user
USER carspective:carspective

# Expose HTTP port
EXPOSE 5001

# Container healthcheck targeting lightweight liveness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request, os; sys_port = os.environ.get('PORT', '5001'); urllib.request.urlopen(f'http://127.0.0.1:{sys_port}/health/liveness')"

# Container entrypoint and production WSGI server startup command
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "server.wsgi:app"]

# ==============================================================================
# CARspective — Production NGINX Gateway Dockerfile
# Stage 1: Build client distribution assets
# Stage 2: Hardened Alpine NGINX runtime
# ==============================================================================

FROM node:20.18-alpine AS client-builder

WORKDIR /app/client

COPY client/package.json client/package-lock.json* ./
RUN npm ci || npm install

COPY client/tsconfig.json client/vite.config.ts client/index.html ./
COPY client/src/ ./src/

RUN npm run build

FROM nginx:1.27-alpine AS runtime

# Create certificate mount directory for production TLS termination
# Authoritative production certificates (carspective.crt and carspective.key) must be mounted over /etc/nginx/certs/
RUN mkdir -p /etc/nginx/certs && chmod 700 /etc/nginx/certs

# Copy custom NGINX configuration
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx/conf.d/ /etc/nginx/conf.d/

# Copy compiled frontend assets from Stage 1
COPY --from=client-builder /app/client/dist /usr/share/nginx/html

EXPOSE 80 443

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/health/liveness || exit 1

CMD ["nginx", "-g", "daemon off;"]

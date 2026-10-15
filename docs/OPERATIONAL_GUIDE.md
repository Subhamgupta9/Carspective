# CARSPECTIVE — OPERATIONAL & DEPLOYMENT RUNBOOK
## Production Architecture, Runtime Procedures, CI/CD & Disaster Recovery

**Target Environment:** Production WSGI / Docker / Multi-Database Compatible  
**Architecture:** Unified Flask 3.1 WSGI Backend + Compiled React 18 / Vite SPA Frontend  
**Revision Head:** Alembic `f3d730c46a23`  

---

## 1. ARCHITECTURE & SERVICE TOPOLOGY

CarSpective runs as a unified, high-performance web service:
1. **API Subsystem (`/api/v1/*`):** Modular Flask blueprints providing valuation, deal intelligence, scoring, recommendations, inspection, market analytics, and operational metrics.
2. **Client Serving (`/`):** When `client/dist` is present, the Flask WSGI server serves the pre-compiled, static SPA bundle with strict path-traversal sanitization and client-side fallback routing (`index.html`).
3. **Observability & Probes:** Lightweight liveness (`/health/liveness`), multi-component dependency readiness (`/health/readiness`), and authenticated Prometheus/JSON operational metrics (`/metrics`).

---

## 2. STARTUP & RUNTIME PROCEDURES

### A. Local Development Startup
For local active development with live reload:

1. **Backend Server (Flask Development Server):**
   ```bash
   # From repository root
   export CARSPECTIVE_ENV=development
   export CARSPECTIVE_DEBUG=true
   python server/app.py
   # Runs on http://127.0.0.1:5001 with hot reloading
   ```
2. **Frontend Development Server (Vite Dev Server):**
   ```bash
   cd client
   npm run dev
   # Runs on http://localhost:3000 with HMR and reverse proxy to port 5001
   ```

---

### B. Production WSGI Startup
In production, direct execution of `server/app.py` or `server/wsgi.py` via the built-in development server is **strictly prohibited and blocked at startup**. A production WSGI server must be used.

#### Linux / Containerized Production (Gunicorn)
```bash
# Recommended command: 4 workers, 2 threads per worker, 60s timeout
gunicorn \
  --bind 0.0.0.0:5001 \
  --workers 4 \
  --threads 2 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile - \
  "server.wsgi:app"
```

#### Windows Production (Waitress)
Because Gunicorn requires POSIX system calls (`fork`, `fcntl`), Waitress is the supported production WSGI server on Windows hosts:
```bash
waitress-serve --listen=0.0.0.0:5001 "server.wsgi:app"
```

---

### C. Docker Container Execution

#### Building the Container
```bash
docker build -t carspective:latest .
```
*Note: Multi-stage build automatically compiles the React frontend with Node 20 and packages it into the hardened Python 3.11 runtime container with non-root user `carspective`.*

#### Running with Persistent SQLite Volume
```bash
docker run -d \
  --name carspective-prod \
  -p 5001:5001 \
  -e CARSPECTIVE_ENV=production \
  -e CARSPECTIVE_DEBUG=false \
  -e SECRET_KEY="<cryptographically_random_secret>" \
  -e ADMIN_API_KEY="<cryptographically_random_admin_key>" \
  -e ALLOWED_HOSTS="carspective.yourdomain.com,127.0.0.1" \
  -e CORS_ALLOWED_ORIGINS="https://carspective.yourdomain.com" \
  -e DATABASE_URL="sqlite:////app/data/database/carspective.db" \
  -v carspective_data:/app/data/database \
  carspective:latest
```

#### Running with External PostgreSQL
```bash
docker run -d \
  --name carspective-prod \
  -p 5001:5001 \
  -e CARSPECTIVE_ENV=production \
  -e CARSPECTIVE_DEBUG=false \
  -e SECRET_KEY="<cryptographically_random_secret>" \
  -e ADMIN_API_KEY="<cryptographically_random_admin_key>" \
  -e ALLOWED_HOSTS="carspective.yourdomain.com" \
  -e CORS_ALLOWED_ORIGINS="https://carspective.yourdomain.com" \
  -e DATABASE_URL="postgresql+psycopg2://user:password@db.internal:5432/carspective" \
  carspective:latest
```

---

## 3. CONFIGURATION & ENVIRONMENT VARIABLES

All production settings are validated **fail-fast** during application startup. If any mandatory variable is missing or insecure, `ConfigurationError` is raised immediately, terminating startup.

### Generating Cryptographic Secrets
Never commit secrets or use default values in production. Generate cryptographically strong keys using Python's standard `secrets` module:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Environment Variables Reference
| Variable | Required in Prod? | Default | Description | Security Constraints |
|---|:---:|---|---|---|
| `CARSPECTIVE_ENV` | Yes | `development` | Deployment environment name (`production`, `development`, `test`). | In production, enables fail-fast validation and disables automated DDL. |
| `CARSPECTIVE_DEBUG` | No | `false` in prod | Application debug mode. | **Must be `false` in production.** Setting to `true` causes immediate startup failure. |
| `SECRET_KEY` | **YES** | None | Cryptographic session and cookie signing key. | Minimum 16 characters. Prohibits insecure defaults (`changeme`, `secret`, etc.). |
| `ADMIN_API_KEY` | **YES** | None | Administrative API key for ingestion/batch mutation endpoints. | Minimum 16 characters. Prohibits insecure defaults. |
| `DATABASE_URL` | **YES** | `sqlite:///data/database/carspective.db` | SQLAlchemy database connection URI. | Must be non-empty. Supports SQLite and PostgreSQL connection strings. |
| `ALLOWED_HOSTS` | **YES** | `localhost,127.0.0.1` | Comma-separated list of permitted HTTP `Host` headers. | Defense against DNS rebinding and HTTP host spoofing. |
| `CORS_ALLOWED_ORIGINS` | **YES** | Localhost origins | Comma-separated list of permitted CORS origins. | **Wildcard (`*`) is strictly prohibited in production.** |
| `TRUSTED_PROXIES` | No | `0` | Number of upstream reverse proxy hops (for `ProxyFix`). | Must be non-negative integer. Only set $>0$ behind vetted reverse proxies (e.g. Nginx, Cloudflare). |

---

## 4. DATABASE LIFECYCLE & MIGRATION PROCEDURES

In production mode, `init_db()` and `create_all()` are **explicitly bypassed** to prevent unreviewed automated DDL. All schema modifications are strictly governed via Alembic.

### Applying Migrations (Upgrade)
```bash
# Upgrade database schema to the latest versioned head
python -m alembic upgrade head
```

### Verifying Current Migration Revision
```bash
python -m alembic current
# Expected head: f3d730c46a23
```

### Rollback / Downgrade
```bash
# Downgrade to previous revision
python -m alembic downgrade -1

# Downgrade to specific revision (e.g., Phase 11 baseline)
python -m alembic downgrade d1b918a24e01
```

---

## 5. HEALTH, READINESS & OBSERVABILITY PROBES

CarSpective exposes RFC-compliant probes designed for container orchestrators (Kubernetes, ECS, Nomad) and load balancers:

### A. Liveness Probe: `GET /health/liveness` (or `/health`)
- **Purpose:** Fast, non-blocking check to confirm the WSGI worker process is responsive.
- **Dependencies:** None (does not query database or external storage).
- **HTTP Response:** `200 OK`
  ```json
  {
    "status": "UP",
    "service": "carspective-api",
    "version": "1.2.0",
    "request_id": "req-98f5b8a0..."
  }
  ```

### B. Readiness Probe: `GET /health/readiness` (or `/ready`)
- **Purpose:** Deep diagnostic verifying all service dependencies are operational before routing traffic.
- **Dependencies Checked:**
  1. Relational Database: Executes `SELECT 1`.
  2. Valuation ML Model: Confirms presence of `.joblib` model artifact and manifest.
  3. Taxonomy Data: Confirms `manufacturers` table is populated.
- **HTTP Response:** `200 OK` (Healthy) or `503 Service Unavailable` (Degraded/Down)
  ```json
  {
    "status": "READY",
    "service": "carspective-api",
    "checks": {
      "database": "CONNECTED",
      "valuation_model": "VERIFIED",
      "taxonomy": "READY (7 manufacturers)"
    },
    "request_id": "req-17b2f0..."
  }
  ```
- **Security:** Error details are sanitized to prevent internal path or credentials leakage.

### C. Operational Telemetry: `GET /metrics` (or `/api/v1/metrics`)
- **Formats:** JSON (default) or Prometheus text format (`?format=prometheus` or `Accept: text/plain`).
- **Authorization:** In production, requires `X-Admin-Api-Key` or `Authorization: Bearer <ADMIN_API_KEY>`.
- **Metrics Tracked:** Total requests, error counts, latency histograms, database availability.

---

## 6. CONTINUOUS INTEGRATION (GITHUB ACTIONS)

The automated CI pipeline (`.github/workflows/ci.yml`) executes on every `push` and `pull_request` targeting `main`:

```
┌─────────────────────────────────┐
│ 1. Security & Invariant Audit   │ ──► pip-audit + Model Hash + Checklist Catalog
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ 2. Backend Regression Suite     │ ──► Python 3.11 + In-Memory DB (410+ server tests + 182 root)
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ 3. Frontend Tests & Build       │ ──► Node 20 + Vitest (80 tests) + Vite Production Compilation
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ 4. Production Config Checks     │ ──► Fail-fast validation tests + WSGI guards
└─────────────────────────────────┘
```

### Interpreting CI Failures
- **Security Audit Failure:** Check `pip-audit` output for CVEs or advisory reports.
- **Model Invariant Failure:** The valuation model artifact `models/carspective_valuation_lgbm_v1.joblib` was altered. Restore from authoritative backup.
- **Inspection Catalog Failure:** Checklist count drifted from exactly 49 items or version `2.0.0` was changed.
- **Database Test Failure:** A test attempted to run without disposable database isolation or violated domain invariants.

---

## 7. ROLLBACK PROCEDURES & DATA PROTECTION

### Application vs. Database Rollback
Application code and database migrations must be decoupled during rollbacks:

1. **Application Code Rollback (Zero-DDL):**  
   If an application bug is discovered in a release that did **not** introduce backwards-incompatible database schema changes, simply roll back the container image or Git commit to the previous release tag:
   ```bash
   docker service update --image carspective:<previous_tag> carspective_service
   ```
2. **Coordinated Database Rollback (With DDL):**  
   If the release introduced schema changes:
   - Check if the previous application version is compatible with the new schema (backward-compatible columns).
   - If backward-compatible, roll back the application container first, then optionally downgrade the migration:
     ```bash
     python -m alembic downgrade <target_revision>
     ```
   - If not backward-compatible, schedule maintenance, drain traffic, downgrade the schema, and deploy the previous application version.

### Database Backup & Disaster Recovery Note
- **Current Storage:** SQLite database file at `data/database/carspective.db` (clean 984-row baseline).
- **Retained Safety Backup:** `data/database/carspective.db.phase19c_safety_backup` (SHA-256: `fe9d013cee...`).
- **Retained Pre-Cleanup Snapshot:** `data/database/carspective.db.pre_cleanup_snapshot_20261009_191728` (SHA-256: `c6d8093a41...`).
- **Automated Backup Utility:** `scripts/backup_database.py` (Phase 19F online SQLite backup with cryptographic manifests and retention pruning).
- **Automated Restore Utility:** `scripts/restore_database.py` (Phase 19F verified restore with fail-closed integrity checks and safety snapshots).
- **Disaster Recovery Runbook:** See detailed procedures, RPO/RTO metrics, and rollback matrices in [`docs/DISASTER_RECOVERY_RUNBOOK.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/DISASTER_RECOVERY_RUNBOOK.md).
- **Disaster Recovery Limitation:** The local SQLite storage is intended for single-node container deployment. Automated point-in-time recovery (PITR) and multi-region replication require configuring an external managed PostgreSQL database via `DATABASE_URL`.

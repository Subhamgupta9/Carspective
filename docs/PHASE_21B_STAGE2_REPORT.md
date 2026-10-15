# CARSPECTIVE — PHASE 21B STAGE 2 REPORT
## Container Build & Healthcheck Verification Assessment

**System:** CarSpective Intelligent Automotive Intelligence Platform  
**Document Type:** Engineering Execution & Operational Blocker Report  
**Phase:** 21B — Stage 2 (Container Build & Healthcheck Verification)  
**Execution Date:** October 15, 2026  
**Engineer:** Senior DevOps & Backend Infrastructure Engineer  

---

## 1. EXECUTIVE SUMMARY & AUTHORITATIVE STATUS

| Workstream / Phase | Authoritative Status | Scope & Context |
|---|:---:|---|
| **Phase 19: Operational Baseline & Invariants** | **CONDITIONAL ACCEPT** | 16/16 invariants pass, models/schemas/taxonomies verified. |
| **Phase 20 Workstream D: Search Engine Optimization** | **ACCEPT** | N+1 remediation and taxonomy caching verified. |
| **Phase 20 Workstreams E/F/G: Serving Performance** | **ACCEPT** | Local serving performance accepted across three independent Phase 20G treatment trials under HTTP Keep-Alive connection pooling. |
| **Phase 21A: Production Infrastructure Audit** | **COMPLETE** | Identified container build and PostgreSQL driver as primary production gaps. |
| **Phase 21B Stage 1: PostgreSQL Dependency Integration** | **PASS** | `psycopg2-binary==2.9.9` added to `requirements.txt` and verified in `.venv`. |
| **Phase 21B Stage 2: Container Build & Healthcheck** | **BLOCKED** | No container engine (Docker / Podman / WSL) is available or running on the Windows host. |
| **Overall Production Release Gate** | **HOLD** | **Strictly locked.** Container execution and PostgreSQL parity remain unverified. |

---

## 2. PREFLIGHT INSPECTION & RUNTIME AVAILABILITY

### 2.1 Static Configuration Audit
1. **`Dockerfile` (84 lines):**
   - Stage 1 (`node:20.18-alpine AS frontend-builder`): Copies `client/package*.json`, runs `npm ci || npm install`, compiles React frontend with `npm run build` to `/app/client/dist`.
   - Stage 2 (`python:3.11-slim AS runtime`): Sets `PYTHONPATH=/app`, `CARSPECTIVE_ENV=production`, `PORT=5001`. Installs `libgomp1` (mandatory for LightGBM OpenMP inference).
   - Non-root user: Creates group and user `carspective` (uid/gid 10001), chowns `/app` to `carspective:carspective`, and sets `USER carspective:carspective`.
   - Python dependencies: Installs from `requirements.txt` (now containing `psycopg2-binary==2.9.9`).
   - Liveness healthcheck: Configures internal Python urllib probe:
     ```dockerfile
     HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
         CMD python -c "import urllib.request, os; sys_port = os.environ.get('PORT', '5001'); urllib.request.urlopen(f'http://127.0.0.1:{sys_port}/health/liveness')"
     ```
   - Entrypoint: Starts Gunicorn with 4 workers and 2 threads (`gthread` model) binding to `0.0.0.0:5001`.
2. **`.dockerignore` (68 lines):**
   - Correctly excludes secrets (`.env*`, `*.pem`, `*.key`), local databases (`data/database/*.db`), SQLite WAL companions, test caches (`.pytest_cache/`), virtual environments (`.venv/`), and frontend `node_modules/`.
3. **Application Entrypoint (`server/wsgi.py`):**
   - Standard WSGI callable `app = create_app()`.
   - Enforces fail-fast validation in production mode: direct execution via `python server/wsgi.py` exits immediately with an error advising use of Gunicorn or Waitress.
4. **Required Production Environment Variables (`server/config/settings.py`):**
   - `SECRET_KEY`: Cryptographically random, $\ge 16$ characters.
   - `ADMIN_API_KEY`: Dedicated administrative secret, $\ge 16$ characters.
   - `ALLOWED_HOSTS`: Non-empty comma-separated list of host headers.
   - `CORS_ALLOWED_ORIGINS`: Non-empty comma-separated list of origins (wildcard `*` strictly disallowed).
   - `CARSPECTIVE_DEBUG`: Must be `False`.
   - `DATABASE_URL`: Valid connection URI (e.g. `sqlite:////app/data/database/carspective.db` or `postgresql+psycopg2://...`).

### 2.2 Container Runtime Availability Audit
Exhaustive probes were executed on the host system:
```powershell
# Probe 1: PATH CLI resolution
Get-Command docker, podman -ErrorAction SilentlyContinue
# Result: Exit code 1 (Neither 'docker' nor 'podman' found on PATH)

# Probe 2: Standard Windows executable discovery
where.exe docker
where.exe podman
# Result: INFO: Could not find files for the given pattern(s).

# Probe 3: Standard Docker Desktop installation directory
Test-Path 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
# Result: False

# Probe 4: Windows Subsystem for Linux (WSL)
wsl --list --verbose
# Result: The Windows Subsystem for Linux is not installed.
```

### 2.3 Strict Safety Invariant Adherence
Per the strict instructions of Phase 21B Stage 2:
> *"If no usable container runtime exists, stop and report the blocker. Do not install software, enable services, or change machine configuration without authorization."*

No attempt was made to install Docker Desktop, enable Hyper-V / WSL2, download third-party container engines, or alter the host system's configuration.

---

## 3. BUILD, STARTUP & HEALTHCHECK EVALUATION

Because no container engine exists on the audit workstation:
- **Image Build:** **`BLOCKED`** — `docker build -t carspective:test .` could not be executed locally.
- **Container Startup:** **`BLOCKED`** — No container daemon exists to instantiate a container.
- **Healthcheck & Readiness Verification:** **`BLOCKED IN CONTAINER`**.

### Architectural Assessment of the Healthcheck Contract
Although containerized execution could not take place, the healthcheck logic was evaluated against the application codebase:
1. **Liveness Probe (`/health/liveness`):**
   - Defined in `server/app.py` (lines 238–254).
   - Performs a zero-dependency JSON response (`{"status": "UP", "service": "carspective-api", "version": "1.2.0"}`).
   - Runs in $< 1\text{ ms}$ and does not touch the database, disk, or model inference pipeline.
   - The Dockerfile healthcheck command (`urllib.request.urlopen('http://127.0.0.1:5001/health/liveness')`) is syntactically correct and requires only Python standard libraries present in `python:3.11-slim`.
2. **Readiness Probe (`/health/readiness`):**
   - Defined in `server/app.py` (lines 255–319).
   - Evaluates three distinct subsystems:
     a. **Relational Database:** Executes `SELECT 1` through SQLAlchemy engine.
     b. **Valuation Model:** Confirms existence of `models/carspective_valuation_lgbm_v1.joblib` and companion manifest.
     c. **Taxonomy Availability:** Queries `Manufacturer` count from database; requires count $> 0$.
   - Returns `200 OK` (`{"status": "READY"}`) if all three checks pass, or `503 Service Unavailable` (`{"status": "NOT_READY"}`) if any check fails.
3. **Container Context Consideration:**
   - In a fresh container without a mounted database volume, the SQLite database at `/app/data/database/carspective.db` will not exist until initialized or mounted.
   - If the container starts with `CARSPECTIVE_ENV=production` and an empty SQLite volume, `init_db()` is bypassed (unreviewed DDL is forbidden in production per line 75 of `server/app.py`), meaning the readiness check would report `503` (taxonomy empty) until migrations and taxonomy seeds are executed.
   - In contrast, the liveness check (`/health/liveness`) will report `200 OK` immediately, satisfying container orchestration liveness gates.

---

## 4. PROTECTED ARTIFACT HASH VERIFICATION

Both protected repository artifacts were verified post-investigation to confirm zero data corruption or unintended mutation:

| Artifact | Baseline SHA-256 Checksum | Measured SHA-256 Checksum | Invariant Status |
|---|---|---|:---:|
| **Live Database** (`data/database/carspective.db`) | `cb655c06225c07af98a85a1171595d3c0d368db4e270c3170d57f96a874209e9` | `cb655c06225c07af98a85a1171595d3c0d368db4e270c3170d57f96a874209e9` | **PASS (UNTOUCHED)** |
| **Valuation Model** (`models/carspective_valuation_lgbm_v1.joblib`) | `4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1` | `4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1` | **PASS (UNTOUCHED)** |

---

## 5. SANITIZED EXECUTION LOGS

```
PS C:\Projects\smart-used-car-price-prediction> Get-Command docker, podman -ErrorAction SilentlyContinue
PS C:\Projects\smart-used-car-price-prediction> where.exe docker
INFO: Could not find files for the given pattern(s).
PS C:\Projects\smart-used-car-price-prediction> where.exe podman
INFO: Could not find files for the given pattern(s).
PS C:\Projects\smart-used-car-price-prediction> Test-Path 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
False
PS C:\Projects\smart-used-car-price-prediction> wsl --list --verbose
The Windows Subsystem for Linux is not installed. You can install by running 'wsl.exe --install'.

PS C:\Projects\smart-used-car-price-prediction> .venv\Scripts\python.exe -c "..."
DB hash:    cb655c06225c07af98a85a1171595d3c0d368db4e270c3170d57f96a874209e9
DB hash:    PASS
Model hash: 4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1
Model hash: PASS
```

---

## 6. BLOCKERS, RISKS & RESOLUTION OPTIONS

### 6.1 Identified Blockers
1. **Local Container Runtime Absent:** The Windows workstation does not possess Docker Engine, Docker Desktop, or WSL2. Local image build and container testing cannot be executed on this machine without authorization to install container virtualization software.
2. **Container Build Verification Unmet:** Because the image cannot be built locally, Docker layer generation, frontend asset compilation via Alpine Node 20, and Python dependency installation in Debian slim remain unverified by empirical execution.

### 6.2 Recommended Resolution Paths
To verify container build and runtime health without compromising the host environment:
- **Option A (Remote CI Pipeline — Recommended):**
  - Add a dedicated container build and test job to `.github/workflows/ci.yml`.
  - GitHub Actions `ubuntu-latest` runners provide native Docker Engine out-of-the-box.
  - The CI runner can execute `docker build -t carspective:ci .`, launch the container, and curl `/health/liveness` automatically on push/PR.
- **Option B (Local Container Tooling Authorization):**
  - If the user explicitly authorizes installing Docker Desktop or enabling WSL2 on this workstation, local container verification can proceed directly.
- **Option C (Dedicated Linux Build Agent):**
  - Execute the build on an external Linux staging host or VM equipped with Docker Engine.

---

## 7. FILES CHANGED

- **Modified Files:** None.
- **Created Files:**
  - `docs/PHASE_21B_STAGE2_REPORT.md` (this report).
- **Working Tree State:** All existing Stage 1 changes (`requirements.txt` with `psycopg2-binary==2.9.9` and `docs/PHASE_21B_STAGE1_REPORT.md`) are preserved exactly.

---

## 8. EXPLICIT CONFIRMATION OF UNVERIFIED SCOPE

In strict accordance with the audit protocol:
1. **Container Execution:** **UNVERIFIED** (No container was built or run due to missing host runtime).
2. **PostgreSQL Parity & Migrations:** **UNVERIFIED** (No live PostgreSQL database was connected, no migrations were executed).
3. **Production Deployment:** **UNVERIFIED**.
4. **Overall Production Release Status:** **`HOLD`** (Strictly maintained).

*Phase 21B Stage 2 is complete. Stopped per protocol. Awaiting user authorization and direction regarding remote CI vs. local container runtime setup.*

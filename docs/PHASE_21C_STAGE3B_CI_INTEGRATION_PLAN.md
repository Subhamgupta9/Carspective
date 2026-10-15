# CARSPECTIVE — PHASE 21C STAGE 3B REPORT & ENGINEERING PLAN
## PostgreSQL CI Integration Preparation & Repository Safety Audit

**System:** CarSpective Intelligent Automotive Intelligence Platform  
**Document Type:** Senior DevOps & Database Reliability Engineering (DBRE) CI Integration Plan  
**Phase:** 21C — Stage 3B (PostgreSQL CI Integration Preparation)  
**Execution Date:** October 15, 2026  
**Status:** Read-Only Planning Complete — Awaiting Review & Authorization  
**Production Release Gate:** **HOLD (Strictly Preserved)**

---

## 1. EXECUTIVE SUMMARY & AUTHORITATIVE PROJECT STATUS

| Workstream / Phase | Authoritative Status | Scope & Context |
|---|:---:|---|
| **Phase 19: Operational Baseline & Invariants** | **CONDITIONAL ACCEPT** | 16/16 invariants pass, models/schemas/taxonomies verified. |
| **Phase 20 Workstream D: Search Engine Optimization** | **ACCEPT** | N+1 remediation and taxonomy caching verified. |
| **Phase 20 Workstreams E/F/G: Serving Performance** | **ACCEPT** | Local serving performance accepted across three independent Phase 20G treatment trials under HTTP Keep-Alive connection pooling. |
| **Phase 21A: Production Infrastructure Audit** | **COMPLETE** | Identified missing PostgreSQL driver and container gaps. |
| **Phase 21B Stage 1: PostgreSQL Dependency Integration** | **PASS** | `psycopg2-binary==2.9.9` added to `requirements.txt` and verified in `.venv`. |
| **Phase 21B Stage 2: Container Build & Healthcheck** | **BLOCKED** | Blocked by absence of container runtime on host; resolution documented. |
| **Phase 21C Stage 1: PostgreSQL Compatibility Audit** | **COMPLETE** | Identified Boolean default syntax and URL normalization hazards. |
| **Phase 21C Stage 2: Minimal Compatibility Fixes** | **PASS** | Boolean defaults fixed in `d1b918a24e01`, URL normalization applied, 13/13 tests pass. |
| **Phase 21C Stage 3A: Test Environment Discovery** | **COMPLETE** | Evaluated local host, CI, and external testing options. Confirmed zero local PostgreSQL/Docker presence. |
| **Phase 21C Stage 3B: PostgreSQL CI Integration Preparation** | **COMPLETE (PLANNING)** | Comprehensive repository safety audit and CI workflow specification produced. |
| **Overall Production Release Gate** | **HOLD** | **Strictly locked.** Live PostgreSQL validation and deployment remain unexecuted. |

### 1.1 Objective of Phase 21C Stage 3B
Following the discovery in [`docs/PHASE_21C_STAGE3A_TEST_ENVIRONMENT_DISCOVERY.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_21C_STAGE3A_TEST_ENVIRONMENT_DISCOVERY.md) that the local Windows workstation lacks Docker and native PostgreSQL installations, GitHub Actions service containers emerged as the enterprise-grade, zero-local-mutation path for validating PostgreSQL compatibility.

This engineering plan prepares a reviewable, production-grade specification for adding a dedicated `postgres-integration-tests` service container job to GitHub Actions without modifying the repository or triggering remote workflows.

---

## 2. STEP 1: REPOSITORY SAFETY & GIT TRACKING AUDIT

A rigorous, read-only audit of Git repository metadata, branch state, remote configuration, and working tree tracking was conducted.

### 2.1 Branch and Remote Audit
```powershell
git branch --show-current
# Output: main

git remote -v
# Output:
# origin  https://github.com/Subhamgupta9/smart-used-car-price-prediction.git (fetch)
# origin  https://github.com/Subhamgupta9/smart-used-car-price-prediction.git (push)
```
- **Remote URL Sanitization:** Confirmed that the remote URL contains no embedded basic authentication tokens, passwords, or personal access tokens (PATs).
- **Branch Topology:** Active branch is `main`, tracking `origin/main`.

### 2.2 Working Tree Tracking Audit
Inspection of tracked vs. untracked files revealed a critical operational finding:
```powershell
git log -n 5 --oneline
# Output: 17fb04c Initial commit

git ls-files
# Output: .gitattributes
```
Every application directory and configuration file in the working directory is currently **untracked** (`??` in `git status --short`), including:
- Core application code: `server/`, `client/`, `app/`
- Alembic migrations: `alembic.ini`, `server/infrastructure/migrations/`
- Test suites: `tests/`, `server/tests/`
- CI definitions: `.github/workflows/ci.yml`
- Container infrastructure: `Dockerfile`, `docker-compose.yml`, `.dockerignore`
- Dependency declarations: `requirements.txt`, `requirements-dev.txt`
- Protected baseline models and data: `models/`, `data/`
- Documentation and reports: `docs/`

### 2.3 Remote Staleness & Execution Risk Analysis
> [!WARNING]
> **CRITICAL REPOSITORY SAFETY HAZARD: Remote `origin/main` Contains Only `.gitattributes`**
> 
> Because local development occurred in an untracked working directory on top of the initial commit (`17fb04c`), the remote GitHub repository currently contains **only `.gitattributes`**.
>
> **Consequences of Staleness:**
> 1. If a CI workflow change or manual trigger were pushed to GitHub today without the application codebase, all jobs would immediately crash because `requirements.txt`, `server/`, `alembic.ini`, and `models/` do not exist on `origin/main`.
> 2. The recent Phase 21B PostgreSQL dependency additions (`psycopg2-binary==2.9.9`) and Phase 21C compatibility fixes (`sa.false()` in `d1b918a24e01` and URL normalization in `server/config/settings.py`) are strictly local and untracked.
> 3. **Mitigation Requirement:** Prior to any remote CI execution, a disciplined, atomic staging and commit of the codebase and its `.gitignore` hygiene rules must be authorized and executed. Under no circumstances should remote workflows be triggered until the working tree is properly committed.

### 2.4 Protected Artifact Hash Verification
The SHA-256 integrity checksums for both protected assets were re-verified against established baselines:

| Protected Artifact | Baseline SHA-256 Checksum | Measured SHA-256 Checksum | Invariant Status |
|---|---|---|:---:|
| **Live Database** (`data/database/carspective.db`) | `cb655c06225c07af98a85a1171595d3c0d368db4e270c3170d57f96a874209e9` | `cb655c06225c07af98a85a1171595d3c0d368db4e270c3170d57f96a874209e9` | **PASS (UNTOUCHED)** |
| **Valuation Model** (`models/carspective_valuation_lgbm_v1.joblib`) | `4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1` | `4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1` | **PASS (UNTOUCHED)** |

---

## 3. STEP 2: CI PIPELINE TOPOLOGY & PROPOSED POSTGRESQL JOB

### 3.1 Existing CI Pipeline Topology
The current pipeline ([`.github/workflows/ci.yml`](file:///c:/Projects/smart-used-car-price-prediction/.github/workflows/ci.yml)) consists of four jobs:
```mermaid
flowchart TD
    A["security-and-invariants<br/>(pip-audit, model hash, catalog)"] --> B["backend-tests<br/>(Python 3.11, SQLite in-memory)"]
    A --> C["frontend-tests-and-build<br/>(Node 20, Vitest, Vite build)"]
    B --> D["production-config-checks<br/>(Fail-fast audit)"]
    C --> D
```

Currently, the `backend-tests` job binds strictly to:
```yaml
env:
  CARSPECTIVE_ENV: test
  CARSPECTIVE_DEBUG: false
  TESTING: true
  DATABASE_URL: "sqlite:///:memory:"
```
While this ensures rapid unit test execution, it provides zero validation of:
- PostgreSQL dialect compatibility
- Alembic DDL execution on PostgreSQL
- Table creation, constraints, foreign keys, and sequence generation
- PostgreSQL connection pooling and pre-ping behavior
- Seed script compatibility and batch upserts

### 3.2 Proposed Integrated CI Pipeline Topology
The proposed architecture introduces a parallel, isolated `postgres-integration-tests` service container job:

```mermaid
flowchart TD
    A["security-and-invariants<br/>(pip-audit, model hash, catalog)"] --> B["backend-tests<br/>(Python 3.11, SQLite in-memory)"]
    A --> P["postgres-integration-tests<br/>(Python 3.11 + Postgres 16-alpine Service)"]
    A --> C["frontend-tests-and-build<br/>(Node 20, Vitest, Vite build)"]
    B --> D["production-config-checks<br/>(Fail-fast audit)"]
    P --> D
    C --> D
```

**Key Advantages:**
1. **Parallel Execution:** Runs concurrently with `backend-tests`, adding zero wall-clock overhead to total pipeline runtime.
2. **Fail-Fast Gate:** Blocks `production-config-checks` if either SQLite regression or PostgreSQL integration fails.
3. **True Ephemeral Isolation:** PostgreSQL 16 container starts with a clean database per run, completely eliminating inter-test pollution.

---

## 4. DETAILED WORKFLOW SPECIFICATION (`postgres-integration-tests`)

### 4.1 Service Container Configuration
The job specifies a native GitHub Actions service container running `postgres:16-alpine`:

```yaml
  # ============================================================================
  # POSTGRESQL INTEGRATION & MIGRATION TEST SUITE (EPHEMERAL SERVICE CONTAINER)
  # ============================================================================
  postgres-integration-tests:
    name: PostgreSQL 16 Integration & Migration Drills
    runs-on: ubuntu-latest
    needs: security-and-invariants
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: carspective_test
          POSTGRES_PASSWORD: test_password_insecure_ci_only
          POSTGRES_DB: carspective_test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U carspective_test -d carspective_test_db"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
```

### 4.2 Explicit Driver & Environment Variables
The job injects normalized PostgreSQL driver URLs and test flags:
```yaml
    env:
      CARSPECTIVE_ENV: test
      CARSPECTIVE_DEBUG: false
      TESTING: true
      DATABASE_URL: "postgresql+psycopg2://carspective_test:test_password_insecure_ci_only@localhost:5432/carspective_test_db"
      TEST_DATABASE_URL: "postgresql+psycopg2://carspective_test:test_password_insecure_ci_only@localhost:5432/carspective_test_db"
```

### 4.3 Proposed Step Sequence

```yaml
    steps:
      - name: Checkout Code
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2

      - name: Set up Python 3.11
        uses: actions/setup-python@42375524e23c412d93fb67b49958b491fce71c38 # v5.4.0
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install System Dependencies (OpenMP & PostgreSQL Client)
        run: |
          sudo apt-get update
          sudo apt-get install -y --no-install-recommends libgomp1 postgresql-client

      - name: Install Python Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt

      - name: Verify PostgreSQL Service Liveness
        run: |
          echo "Waiting for PostgreSQL service container on localhost:5432..."
          until pg_isready -h localhost -p 5432 -U carspective_test -d carspective_test_db; do
            echo "PostgreSQL not yet ready; sleeping 2s..."
            sleep 2
          done
          echo "PostgreSQL 16 service container is ONLINE and receptive to connections!"

      - name: Execute Alembic Migration Chain to HEAD
        run: |
          echo "Applying all migrations from empty database to HEAD..."
          alembic upgrade head
          
          echo "Verifying migration version recorded in PostgreSQL alembic_version table..."
          HEAD_REV=$(psql "postgresql://carspective_test:test_password_insecure_ci_only@localhost:5432/carspective_test_db" -t -A -c "SELECT version_num FROM alembic_version;")
          echo "Recorded Alembic revision: $HEAD_REV"
          test "$HEAD_REV" = "f3d730c46a23"
          echo "Alembic HEAD revision f3d730c46a23 verified successfully on PostgreSQL!"

      - name: Verify Zero Schema Drift Against Base.metadata
        run: |
          python -c "
          import sqlalchemy as sa
          from alembic.migration import MigrationContext
          from alembic.autogenerate import compare_metadata
          from server.models import Base
          from server.config.settings import settings

          engine = sa.create_engine(settings.DATABASE_URL)
          with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            diff = compare_metadata(ctx, Base.metadata)
            assert len(diff) == 0, f'Schema drift detected on PostgreSQL: {diff}'
          print('Zero schema drift verified: Base.metadata matches PostgreSQL schema 100%!')
          "

      - name: Populate Canonical Seed & Vehicle Knowledge Data
        run: |
          echo "Seeding canonical taxonomy and evidence sources..."
          python scripts/generate_and_load_seeds.py
          
          echo "Seeding Phase 11 expanded vehicle knowledge..."
          python scripts/seed_vehicle_knowledge.py
          
          echo "Verifying row counts on PostgreSQL..."
          python -c "
          from server.infrastructure.database import SessionFactory
          from server.models.taxonomy import Manufacturer, VehicleModel, VehicleVariant
          from server.models.evidence import EvidenceSource, KnowledgeClaim
          from server.models.knowledge import VehicleFeatureMap, ReliabilityAdvisory

          sess = SessionFactory()
          assert sess.query(Manufacturer).count() >= 7, 'Manufacturer count failed'
          assert sess.query(VehicleModel).count() >= 15, 'Model count failed'
          assert sess.query(VehicleVariant).count() >= 40, 'Variant count failed'
          assert sess.query(EvidenceSource).count() >= 10, 'EvidenceSource count failed'
          assert sess.query(KnowledgeClaim).count() >= 50, 'KnowledgeClaim count failed'
          assert sess.query(VehicleFeatureMap).count() >= 20, 'FeatureMap count failed'
          assert sess.query(ReliabilityAdvisory).count() >= 5, 'Advisory count failed'
          sess.close()
          print('PostgreSQL seed data integrity verified across all core tables!')
          "

      - name: Run PostgreSQL Database Lifecycle & Regression Tests
        run: |
          pytest server/tests/test_database.py server/tests/test_phase19c_database_lifecycle.py server/tests/test_database_url_normalization.py -v

      - name: Execute Migration Downgrade & Re-upgrade Idempotency Drill
        run: |
          echo "Executing migration downgrade drill: alembic downgrade base..."
          alembic downgrade base
          
          echo "Verifying all application tables were dropped..."
          TABLE_COUNT=$(psql "postgresql://carspective_test:test_password_insecure_ci_only@localhost:5432/carspective_test_db" -t -A -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name != 'alembic_version';")
          test "$TABLE_COUNT" -eq 0
          echo "All application tables successfully dropped ($TABLE_COUNT remaining)."
          
          echo "Re-executing upgrade to HEAD to verify idempotency..."
          alembic upgrade head
          RE_UPGRADE_REV=$(psql "postgresql://carspective_test:test_password_insecure_ci_only@localhost:5432/carspective_test_db" -t -A -c "SELECT version_num FROM alembic_version;")
          test "$RE_UPGRADE_REV" = "f3d730c46a23"
          echo "Re-upgrade to f3d730c46a23 succeeded cleanly! Downgrade/upgrade idempotency verified."

      - name: Capture PostgreSQL Diagnostics on Failure
        if: failure()
        run: |
          echo "=== CI Step Failure Detected: Capturing PostgreSQL Container Logs ==="
          docker ps -a
          CONTAINER_ID=$(docker ps -q --filter ancestor=postgres:16-alpine)
          if [ -n "$CONTAINER_ID" ]; then
            echo "--- PostgreSQL Container Logs ($CONTAINER_ID) ---"
            docker logs "$CONTAINER_ID" | tail -n 100
          fi
```

---

## 5. TEST-FIXTURE ADAPTATION STRATEGY (`server/tests/conftest.py`)

### 5.1 The Dialect Limitation in Existing Fixtures
Currently, [`server/tests/conftest.py`](file:///c:/Projects/smart-used-car-price-prediction/server/tests/conftest.py) hardcodes SQLite in-memory:
```python
@pytest.fixture(scope="session")
def test_engine():
    """Create in-memory SQLite engine with foreign key enforcement."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True
    )
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    return engine
```

**Issues When Connecting to PostgreSQL:**
1. `connect_args={"check_same_thread": False}` is invalid for `psycopg2`.
2. The `@event.listens_for(Engine, "connect")` listener blindly issues SQLite `PRAGMA foreign_keys=ON`, which causes a PostgreSQL syntax error (`syntax error at or near "PRAGMA"`).
3. Session lifecycle: In-memory SQLite uses a single connection per thread; PostgreSQL uses standard client-server TCP pooling.

### 5.2 Proposed Dialect-Aware Adapter Implementation
When authorized in Stage 3C, `server/tests/conftest.py` will be adapted with zero regression to local developers:

```python
import os
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from server.models.base import Base
from server.config.settings import normalize_database_url

@pytest.fixture(scope="session")
def test_engine():
    """Create test engine: defaults to in-memory SQLite, or adapts to TEST_DATABASE_URL/DATABASE_URL."""
    raw_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or "sqlite:///:memory:"
    db_url = normalize_database_url(raw_url)
    
    is_sqlite = db_url.startswith("sqlite")
    
    if is_sqlite:
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            future=True
        )
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        # PostgreSQL / Client-Server Engine
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            future=True
        )

    # In PostgreSQL, tables are created via Alembic in CI or create_all in tests
    Base.metadata.create_all(bind=engine)
    return engine
```

### 5.3 Zero-Disruption Principle
- If `TEST_DATABASE_URL` and `DATABASE_URL` are unset (the default for all local pytest runs), `test_engine` continues to instantiate `"sqlite:///:memory:"` exactly as before.
- No local developer workflow, command, or environment variable requirement is disrupted.

---

## 6. EXACT FILES REQUIRING MODIFICATION WHEN AUTHORIZED

When Stage 3C authorization is granted, the following exact files will be modified:

| File Path | Action | Description of Modification |
|---|:---:|---|
| [`.github/workflows/ci.yml`](file:///c:/Projects/smart-used-car-price-prediction/.github/workflows/ci.yml) | **Modify** | Add `postgres-integration-tests` service container job; add `postgres-integration-tests` to `needs: [backend-tests, postgres-integration-tests, frontend-tests-and-build]` in `production-config-checks`. |
| [`server/tests/conftest.py`](file:///c:/Projects/smart-used-car-price-prediction/server/tests/conftest.py) | **Modify** | Parameterize `test_engine` to be dialect-aware; guard SQLite `PRAGMA` listeners; support `TEST_DATABASE_URL` while preserving `sqlite:///:memory:` default. |
| [`.gitignore`](file:///c:/Projects/smart-used-car-price-prediction/.gitignore) | **Modify** | Add hygiene entries for temporary/scratch files (`scratch/`, `backup_*`, `*.png`) before git commit. |

### Confirmation of Unchanged Core Components
- **Alembic Migrations:** No changes needed. The Boolean default fixes (`sa.false()` in `d1b918a24e01`) were completed in Phase 21C Stage 2.
- **Application Settings & DB Infrastructure:** No changes needed. URL normalization (`normalize_database_url`) and masking (`mask_database_url`) were completed in Phase 21C Stage 2.
- **Protected SQLite Database & Model:** No changes will be made to `data/database/carspective.db` or `models/carspective_valuation_lgbm_v1.joblib`.

---

## 7. SECURITY, CREDENTIAL SANITIZATION & FAILURE CONTROLS

### 7.1 Synthetic, Non-Production Test Credentials
- Credentials used in the CI container (`carspective_test` / `test_password_insecure_ci_only`) are hardcoded synthetic strings intended **exclusively** for the ephemeral GitHub runner.
- They have no access to any production infrastructure, cloud account, or staging database.
- The PostgreSQL service container only listens on the runner's loopback interface (`127.0.0.1:5432`) and is terminated and destroyed as soon as the job finishes.

### 7.2 URL Masking in CI Logs
- In Python code and diagnostics, database URLs printed to standard output must use `mask_database_url(url)`, rendering credentials as `postgresql+psycopg2://carspective_test:***@localhost:5432/carspective_test_db`.
- GitHub Actions secret masking is not strictly necessary for synthetic test credentials, but masking URLs prevents accidental token leakage if secrets are ever passed in future environments.

### 7.3 Automated Diagnostic Capture on Failure
- If any migration, seed, or test step fails, the `if: failure()` step dumps the last 100 lines of `docker logs` from the PostgreSQL container.
- This immediately reveals PostgreSQL server error codes (e.g. `23505` unique violation, `42P01` undefined table, `42804` datatype mismatch) in the CI console, enabling rapid triage without requiring access to the runner.

---

## 8. PREREQUISITE REPOSITORY COMMIT SEQUENCE (STALENESS RESOLUTION)

Because the working directory is currently untracked, remote GitHub Actions will fail until the codebase is committed. When authorized, the commit sequence must follow this strict staging protocol:

```powershell
# 1. Update .gitignore with temporary and scratch exclusions
# Ensure .env, backup_*, scratch*, *.png, .pytest_cache are excluded

# 2. Review git status to confirm only production-relevant assets will be tracked
git status --short

# 3. Stage core code, migrations, tests, and CI definitions
git add .gitignore requirements.txt requirements-dev.txt Dockerfile .dockerignore docker-compose.yml
git add alembic.ini server/ app/ client/ scripts/ tests/ data/ models/ docs/ .github/

# 4. Create an atomic, verifiable commit
git commit -m "feat(infra): integrate PostgreSQL support, alembic migrations, and CI service container"

# 5. Push to origin/main (only upon explicit user authorization)
git push origin main
```

---

## 9. PLANNING VS. REMOTE EXECUTION BOUNDARIES

> [!IMPORTANT]
> **Strict Adherence to Read-Only Planning Directives:**
> 1. **No Code Files Were Modified:** Neither `.github/workflows/ci.yml`, `server/tests/conftest.py`, application code, nor migrations were edited during Stage 3B.
> 2. **No Git Mutations Occurred:** No `git add`, `git commit`, `git push`, `git pull`, `git checkout`, or `git reset` commands were executed.
> 3. **No Remote Workflows Triggered:** No remote API calls or GitHub Actions executions were initiated.
> 4. **Protected Artifact Hashes Remain 100% Intact.**
> 5. **Production Release Gate Status:** **HOLD.** Production deployment remains blocked until PostgreSQL CI integration is authorized, implemented, executed, and audited.

---

## 10. CONCLUSION & RECOMMENDED NEXT ACTIONS

Stage 3B has established an airtight, reviewable plan for running PostgreSQL integration tests in GitHub Actions.

**Recommended Next Step:**
Awaiting user review and authorization to proceed to **Phase 21C Stage 3C (CI Implementation & Repository Staging)**, which will:
1. Apply the dialect-aware fixture updates to `server/tests/conftest.py`.
2. Add the `postgres-integration-tests` service container job to `.github/workflows/ci.yml`.
3. Authorize the atomic staging and commit of the codebase to resolve the remote repository staleness.
4. Execute and monitor the remote GitHub Actions workflow to obtain empirical proof of PostgreSQL compatibility.

# CARSPECTIVE — PHASE 21C STAGE 1 REPORT
## PostgreSQL Compatibility & Schema Parity Audit

**System:** CarSpective Intelligent Automotive Intelligence Platform  
**Document Type:** Senior Database Reliability Engineering (DBRE) Audit Report  
**Phase:** 21C — Stage 1 (PostgreSQL Static Compatibility Audit)  
**Execution Date:** October 15, 2026  
**Auditor:** Senior Database Reliability Engineer (DBRE)  

---

## 1. EXECUTIVE VERDICT & AUTHORITATIVE STATUS

### 1.1 Executive Compatibility Verdict: **`CONDITIONAL`**

CarSpective's data access architecture is predominantly built on modern SQLAlchemy 2.0 ORM patterns, client-side UUID4 primary keys, explicit relationship loaders, and dialect-agnostic data modeling. However, moving to live disposable PostgreSQL testing is **CONDITIONAL** upon addressing one critical DDL syntax blocker in existing migrations and one runtime URL resolution hazard:
1. **Critical DDL Syntax Blocker:** Migration `d1b918a24e01` declares boolean column server defaults using integer literal `sa.text('0')` (lines 235–236). While valid in SQLite, PostgreSQL strictly rejects integer literals as boolean defaults with `ERROR: column is of type boolean but default expression is of type integer`. This will cause `alembic upgrade head` to crash on a fresh PostgreSQL instance.
2. **URL Normalization Hazard:** SQLAlchemy 2.1.3 defaults generic `postgresql://` URIs to the uninstalled `psycopg` (v3) driver. Any orchestrator supplying standard `postgresql://` will crash with `ModuleNotFoundError` unless automatic scheme normalization (`postgresql+psycopg2://`) is applied.

Once these specific remediations are authorized, the codebase is structurally well-prepared for disposable PostgreSQL validation.

### 1.2 Authoritative Status Matrix
| Workstream / Phase | Authoritative Status | Scope & Context |
|---|:---:|---|
| **Phase 19: Operational Baseline & Invariants** | **CONDITIONAL ACCEPT** | 16/16 invariants pass, models/schemas/taxonomies verified. |
| **Phase 20 Workstream D: Search Engine Optimization** | **ACCEPT** | N+1 remediation and taxonomy caching verified. |
| **Phase 20 Workstreams E/F/G: Serving Performance** | **ACCEPT** | Local serving performance accepted across three independent Phase 20G treatment trials under HTTP Keep-Alive connection pooling. |
| **Phase 21A: Production Infrastructure Audit** | **COMPLETE** | Identified missing PostgreSQL driver and container gaps. |
| **Phase 21B Stage 1: PostgreSQL Dependency Integration** | **PASS** | `psycopg2-binary==2.9.9` added to `requirements.txt` and verified in `.venv`. |
| **Phase 21B Stage 2: Container Build & Healthcheck** | **BLOCKED** | Blocked by absence of container runtime on host; resolution documented. |
| **Phase 21C Stage 1: PostgreSQL Compatibility Audit** | **COMPLETE (CONDITIONAL)** | Comprehensive static audit of migrations, models, engines, and queries. |
| **Overall Production Release Gate** | **HOLD** | **Strictly locked.** Live PostgreSQL validation and deployment remain unexecuted. |

---

## 2. EXACT ALEMBIC MIGRATION REVISION CHAIN

The repository governs 25 relational tables through a linear 4-revision migration chain located in `server/infrastructure/migrations/versions/`:

```
  [Base / Empty Schema]
          │
          ▼
  Revision: cb1c167fc450
  Title:    initial_canonical_taxonomy_and_evidence
  Date:     2026-10-07 20:29:08
  Revises:  None (Root Revision)
  Tables:   11 tables (evidence_sources, knowledge_claims, manufacturers, 
            claim_evidence_mappings, manufacturer_aliases, vehicle_models, 
            model_aliases, vehicle_generations, model_years, vehicle_variants, 
            powertrain_configurations)
          │
          ▼
  Revision: d1b918a24e01
  Title:    phase11_vehicle_knowledge
  Date:     2026-10-09 14:40:00
  Revises:  cb1c167fc450
  Tables:   9 tables (vehicle_features, vehicle_specifications, vehicle_dimensions, 
            vehicle_safety_ratings, variant_feature_mappings, ownership_profiles, 
            reliability_issues, vehicle_pros_cons, review_syntheses)
          │
          ▼
  Revision: e2c829b35f12
  Title:    phase16_data_pipeline_governance
  Date:     2026-10-09 14:41:00
  Revises:  d1b918a24e01
  Tables:   3 tables (ingestion_batches, ingestion_records, data_quality_reports)
          │
          ▼
  Revision: f3d730c46a23 (HEAD)
  Title:    phase17_market_observations
  Date:     2026-10-09 14:42:00
  Revises:  e2c829b35f12
  Tables:   1 table (current_market_observations)
```

### Downgrade Function Audit
1. `f3d730c46a23.py` (lines 70–77): Drops `current_market_observations`.
2. `e2c829b35f12.py` (lines 85–99): Drops `data_quality_reports`, `ingestion_records`, `ingestion_batches`.
3. `d1b918a24e01.py` (lines 248–268): Drops all 9 vehicle knowledge tables in reverse dependency order.
4. `cb1c167fc450.py` (lines 169–192): Drops all 11 taxonomy and evidence tables in reverse dependency order.

---

## 3. COMPREHENSIVE COMPATIBILITY AUDIT FINDINGS

### 3.1 Migration DDL & Dialect Differences

#### Finding 1: Boolean Column Server Default Syntax (`CRITICAL`)
- **Location:** `server/infrastructure/migrations/versions/d1b918a24e01_phase11_vehicle_knowledge.py`, lines 235–236:
  ```python
  sa.Column('has_owner_evidence', sa.Boolean(), nullable=False, server_default=sa.text('0')),
  sa.Column('has_expert_evidence', sa.Boolean(), nullable=False, server_default=sa.text('0')),
  ```
- **Dialect Discrepancy:**
  - In SQLite, booleans are represented as numeric integers (`0` / `1`). `server_default=sa.text('0')` emits `DEFAULT 0`, which SQLite accepts.
  - In PostgreSQL, boolean is a discrete type (`BOOLEAN`). PostgreSQL does not implicitly cast integer literals to boolean:
    ```sql
    -- PostgreSQL Error Output:
    ERROR: column "has_owner_evidence" is of type boolean but default expression is of type integer
    HINT: You will need to rewrite or cast the expression.
    ```
- **Impact:** Any attempt to execute `alembic upgrade head` on a fresh PostgreSQL database will fail at migration `d1b918a24e01`.
- **Remediation:** Replace `server_default=sa.text('0')` with `server_default=sa.false()` (or `server_default=sa.text('false')`). This generates `DEFAULT 0` on SQLite and `DEFAULT false` on PostgreSQL portably.

#### Finding 2: PostgreSQL ENUM Type Lifecycle & Idempotency (`HIGH`)
- **Location:**
  - `cb1c167fc450`: lines 27, 34, 44, 48 (`organizationtype`, `evidencestate`, `hierarchylevel`).
  - `d1b918a24e01`: lines 68, 96, 122, 141, 168, 193, 215, 237 (`evidencestate`).
- **Dialect Discrepancy:**
  - In SQLite, `sa.Enum` creates an inline `CHECK (col IN (...))` constraint. Dropping the table drops the check constraint automatically.
  - In PostgreSQL, named enums (`sa.Enum(name='evidencestate')`) execute `CREATE TYPE evidencestate AS ENUM (...)` at schema level.
  - In `cb1c167fc450`, `downgrade()` drops the tables but **does not drop the ENUM types**. If `downgrade` is executed to clean the database and `upgrade` is run again, PostgreSQL will fail with `psycopg2.errors.DuplicateObject: type "organizationtype" already exists`.
  - In `d1b918a24e01`, multiple tables reference `name='evidencestate'`. When `evidencestate` is created by `cb1c167fc450`, subsequent tables must reuse the existing type rather than re-creating it.
- **Remediation:**
  - In `cb1c167fc450.py:downgrade()`, append explicit type teardown:
    ```python
    for enum_name in ['hierarchylevel', 'evidencestate', 'organizationtype']:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
    ```
  - In `d1b918a24e01.py`, set `create_type=False` on `sa.Enum(..., name='evidencestate')` since the type is already established by `cb1c167fc450`.

#### Finding 3: Alembic Batch Mode vs. Native PostgreSQL DDL (`RESOLVED / VERIFIED`)
- **Location:** `server/infrastructure/migrations/env.py`, lines 28–35 & 46–51.
- **Audit Assessment:**
  - SQLite requires table-copy batch mode (`render_as_batch=True`) to alter columns, drop constraints, or change tables because SQLite lacks comprehensive `ALTER TABLE` support.
  - `env.py` dynamically detects the dialect:
    ```python
    is_sqlite = connection.dialect.name == "sqlite"
    context.configure(..., render_as_batch=is_sqlite)
    ```
  - When running against PostgreSQL, `render_as_batch` evaluates to `False`, allowing native, transactional PostgreSQL DDL. This is properly implemented.

---

### 3.2 SQLAlchemy Engine, Connection Pooling & URL Handling

#### Finding 4: Generic `postgresql://` URL Scheme Resolution (`MEDIUM`)
- **Location:** `server/config/settings.py` (lines 58–61) & `server/infrastructure/database.py` (lines 37–40).
- **Dialect Discrepancy:**
  - In SQLAlchemy 2.0, `postgresql://` defaulted to `psycopg2`.
  - In SQLAlchemy 2.1.3 (the repository's pinned version), bare `postgresql://` defaults to `psycopg` (v3).
  - Since Stage 1 integrated `psycopg2-binary==2.9.9`, passing `DATABASE_URL=postgresql://user:pass@host/db` will cause SQLAlchemy to attempt loading `psycopg` and crash:
    ```
    ModuleNotFoundError: No module named 'psycopg'
    ```
- **Remediation:** In `server/infrastructure/database.py` (and `alembic/env.py`), implement transparent scheme normalization:
  ```python
  raw_url = settings.DATABASE_URL
  if raw_url.startswith("postgresql://"):
      db_url = raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
  else:
      db_url = raw_url
  ```

#### Finding 5: Connection Pool Tuning for PostgreSQL (`VERIFIED`)
- **Location:** `server/infrastructure/database.py`, lines 28–36.
- **Audit Assessment:**
  ```python
  if is_sqlite:
      engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30.0}
  else:
      engine_kwargs.update({
          "pool_size": 10,
          "max_overflow": 20,
          "pool_recycle": 1800,
          "pool_timeout": 30.0,
      })
  ```
  - `pool_size=10, max_overflow=20` provides up to 30 concurrent connections per WSGI worker process.
  - `pool_recycle=1800` (30 minutes) prevents PostgreSQL backend connection disconnects caused by stateful firewalls or cloud TCP timeout drops.
  - `pool_pre_ping=True` (line 20) emits a lightweight ping (`SELECT 1`) to detect and discard stale or closed connections before handing them to requests.
  - Connection disposal hook (`dispose_engine()`) is registered with `atexit` in `server/app.py` (lines 81–90) to close socket handles cleanly on worker termination.

---

### 3.3 Data Modeling & Type Parity

#### Finding 6: Primary Key Architecture (`POSITIVE INVARIANT`)
- **Location:** Across all 25 declarative models in `server/models/`.
- **Audit Assessment:**
  - Every primary key is defined as a client-side generated UUID4 string:
    ```python
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ```
  - **No integer autoincrement sequences** (`SERIAL` / `IDENTITY`) are utilized.
  - This guarantees that PostgreSQL sequence synchronization (`setval`), sequence permissions, and autoincrement lock contention do not exist in CarSpective. Data can be inserted with explicit IDs without sequence desynchronization.

#### Finding 7: JSON Column Serialization (`POSITIVE INVARIANT`)
- **Location:** `server/models/data_pipeline.py` (line 77) & `server/models/market_observation.py` (line 67).
- **Audit Assessment:**
  - Complex nested payloads (`metrics_json`, `outlier_reasons`, `raw_payload`) are declared as `Text` and serialized/deserialized in Python application code via `json.dumps()` / `json.loads()`.
  - Because no database-side JSON operators (`->`, `->>`, `@>`, `json_extract`) are invoked, `Text` columns behave identically on SQLite and PostgreSQL.

#### Finding 8: Case-Insensitive String Filters (`POSITIVE INVARIANT`)
- **Location:** `server/repositories/taxonomy_repository.py`, lines 197, 210, 260, 278, 349, 362, 364.
- **Audit Assessment:**
  - SQLite default string comparison (`LIKE`) can be case-insensitive, whereas PostgreSQL `LIKE` is strictly case-sensitive.
  - The repository avoids relying on dialect-specific collation and instead uses `func.lower(Column) == value.lower()` uniformly.
  - This ensures identical case-insensitive lookup behavior on PostgreSQL without requiring PostgreSQL-specific `ILIKE` operators.

---

### 3.4 Seed & Catalog Portability

#### Finding 9: Taxonomy Seed Script Portability (`VERIFIED`)
- **Location:** `scripts/generate_and_load_seeds.py` & `scripts/seed_vehicle_knowledge.py`.
- **Audit Assessment:**
  - Seed scripts use standard SQLAlchemy ORM session patterns (`session.query().filter_by().first()`, `session.add()`, `session.commit()`).
  - No raw SQLite statements, dialect-specific upserts, or PRAGMAs are present in the seed pipeline.
  - The seed data can be loaded into PostgreSQL directly via `python scripts/generate_and_load_seeds.py` once tables are created.

---

### 3.5 Test Fixtures & Test Suite Parity

#### Finding 10: In-Memory SQLite Hardcoding in Test Suite (`MEDIUM`)
- **Location:** `server/tests/conftest.py`, lines 16–30.
- **Audit Assessment:**
  - The test suite's `test_engine` fixture hardcodes `sqlite:///:memory:` and sets SQLite PRAGMA `PRAGMA foreign_keys=ON`.
  - Even if `DATABASE_URL` is set to PostgreSQL in the test runner's environment, `pytest` ignores it and executes against in-memory SQLite.
- **Remediation:** Parameterize `conftest.py` to inspect `os.getenv("TEST_DATABASE_URL")` or `os.getenv("DATABASE_URL")`. If pointing to PostgreSQL, skip SQLite PRAGMA execution and use the provided database engine.

---

## 4. PRIORITIZED COMPATIBILITY MATRIX

| # | Finding & Subsystem | File & Lines | Severity | Impact on PostgreSQL | Proposed Remediation |
|---|---|---|:---:|---|---|
| **1** | Boolean `server_default=sa.text('0')` | `server/infrastructure/migrations/versions/d1b918a24e01_phase11_vehicle_knowledge.py`: 235–236 | **`CRITICAL`** | **Fatal DDL Error:** PostgreSQL rejects integer literal as default for `BOOLEAN`. Blocks `alembic upgrade head`. | Change `server_default=sa.text('0')` to `server_default=sa.false()` in migration `d1b918a24e01`. |
| **2** | ENUM Type Drop on Downgrade | `server/infrastructure/migrations/versions/cb1c167fc450_initial_canonical_taxonomy_and_evidence.py`: 169–192 | **`HIGH`** | **Migration Rollback Error:** Dropping tables does not drop schema ENUM types. Subsequent upgrade fails on duplicate type. | Add explicit `sa.Enum(name=...).drop(checkfirst=True)` to `downgrade()` in `cb1c167fc450.py`. |
| **3** | URL Scheme Normalization | `server/config/settings.py`: 58–61<br>`server/infrastructure/database.py`: 37–40 | **`MEDIUM`** | **Runtime Crash:** Bare `postgresql://` defaults to uninstalled `psycopg` (v3) in SQLAlchemy 2.1. | Transparently rewrite `postgresql://` to `postgresql+psycopg2://` before `create_engine`. |
| **4** | Test Suite SQLite Hardcoding | `server/tests/conftest.py`: 16–30 | **`MEDIUM`** | **Testing Gap:** `pytest` cannot run against a live PostgreSQL database because `sqlite:///:memory:` is hardcoded. | Allow `conftest.py` to bind to `TEST_DATABASE_URL` when provided. |
| **5** | Re-declared ENUM in Downstream Migration | `server/infrastructure/migrations/versions/d1b918a24e01_phase11_vehicle_knowledge.py`: lines 68, 96, etc. | **`LOW`** | Potential duplicate type creation warning/error if type already created. | Pass `create_type=False` to `sa.Enum(..., name='evidencestate')` in downstream migrations. |

---

## 5. SEVERITY-RANKED REMEDIATION PLAN

Before executing migrations on any live PostgreSQL instance, the following authorized changes should be staged:

```
  Step 1 (CRITICAL): Fix Boolean server_default in migration d1b918a24e01
     │  Change sa.text('0') -> sa.false() for has_owner_evidence and has_expert_evidence.
     ▼
  Step 2 (HIGH): Harden ENUM drop in migration cb1c167fc450
     │  Ensure organizationtype, evidencestate, hierarchylevel are dropped cleanly in downgrade().
     ▼
  Step 3 (MEDIUM): Implement URL scheme normalization in database.py
     │  Automatically translate postgresql:// to postgresql+psycopg2://.
     ▼
  Step 4 (MEDIUM): Parameterize test fixtures in conftest.py
     │  Allow testing against disposable PostgreSQL when TEST_DATABASE_URL is provided.
```

---

## 6. PROPOSED DISPOSABLE POSTGRESQL VALIDATION PROTOCOL

When live testing is authorized, the following strictly isolated protocol must be used:

### 6.1 Prerequisites
1. Dedicated disposable PostgreSQL 15 or 16 container/database with zero production or persistent data.
2. Connection string configured strictly as:
   ```
   TEST_DATABASE_URL="postgresql+psycopg2://test_user:test_password@localhost:5433/carspective_test"
   ```
3. Live SQLite database (`data/database/carspective.db`) completely unmounted and untouched.

### 6.2 Test Execution Sequence
1. **Fresh Migration Upgrade Drill:**
   ```bash
   python -m alembic -x db_url="${TEST_DATABASE_URL}" upgrade head
   ```
   *Verification:* Confirm Alembic head reaches `f3d730c46a23` and all 25 tables are created.
2. **Seed Data Ingestion Drill:**
   ```bash
   python scripts/generate_and_load_seeds.py --db-url "${TEST_DATABASE_URL}"
   ```
   *Verification:* Verify all 28 manufacturers, models, generations, variants, and knowledge claims are populated.
3. **Core Application Query & Readiness Verification:**
   - Probe database connectivity via `SELECT 1`.
   - Execute taxonomy resolution (`GET /api/v1/taxonomy/manufacturers`).
   - Query vehicle specifications and review syntheses.
   - Verify `/health/readiness` returns `200 OK` with `"database": "CONNECTED"`.
4. **Full Migration Rollback Drill (Downgrade to Base):**
   ```bash
   python -m alembic -x db_url="${TEST_DATABASE_URL}" downgrade base
   ```
   *Verification:* Confirm all tables and custom ENUM types are cleanly dropped without orphaned types.
5. **Re-Upgrade Drill:**
   ```bash
   python -m alembic -x db_url="${TEST_DATABASE_URL}" upgrade head
   ```
   *Verification:* Confirms migrations can be repeatedly rolled back and applied cleanly without state leakage.
6. **Teardown & Verification:**
   - Terminate disposable database container.
   - Re-verify SHA-256 hashes of live SQLite database and valuation model.

---

## 7. EXPLICIT AUDIT LIMITATIONS & INTEGRITY CONFIRMATION

1. **Read-Only Audit:**
   - This audit was strictly observational and analytical.
   - Zero files, code, dependencies, migrations, schemas, or configurations were modified during this stage.
2. **No Live Database Connections:**
   - No PostgreSQL daemon was connected to, provisioned, or queried.
   - No migrations or database writes were executed.
3. **Protected Artifact Hashes (Unchanged):**

| Artifact | Baseline SHA-256 Checksum | Measured SHA-256 Checksum | Invariant Status |
|---|---|---|:---:|
| **Live Database** (`data/database/carspective.db`) | `cb655c06225c07af98a85a1171595d3c0d368db4e270c3170d57f96a874209e9` | `cb655c06225c07af98a85a1171595d3c0d368db4e270c3170d57f96a874209e9` | **PASS (UNTOUCHED)** |
| **Valuation Model** (`models/carspective_valuation_lgbm_v1.joblib`) | `4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1` | `4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1` | **PASS (UNTOUCHED)** |

4. **Production Release Gate:**
   - Overall production release gate remains strictly on **`HOLD`**.

---

*Report prepared by Senior Database Reliability Engineer (DBRE) for CarSpective.*

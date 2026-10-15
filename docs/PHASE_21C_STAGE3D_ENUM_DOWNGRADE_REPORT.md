# CARSPECTIVE — PHASE 21C STAGE 3D REPORT
## PostgreSQL ENUM Downgrade Remediation

**System:** CarSpective Intelligent Automotive Intelligence Platform  
**Document Type:** Senior SQLAlchemy & Alembic Migration Engineering Report  
**Phase:** 21C — Stage 3D (PostgreSQL ENUM Downgrade Remediation)  
**Execution Date:** October 15, 2026  
**Status:** Remediation Complete — Verified Locally — Awaiting Review  
**Production Release Gate:** **HOLD (Strictly Preserved)**

---

## 1. EXECUTIVE SUMMARY & AUTHORITATIVE STATUS

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
| **Phase 21C Stage 3A: Test Environment Discovery** | **COMPLETE** | Confirmed zero local PostgreSQL/Docker presence; identified CI service container as primary testing path. |
| **Phase 21C Stage 3B: PostgreSQL CI Integration Preparation** | **COMPLETE** | Authored repository safety audit and CI workflow plan. |
| **Phase 21C Stage 3C: Local PostgreSQL CI Implementation** | **PASS (LOCAL)** | Implemented `postgres-integration-tests` job, parameterized test fixtures (37/37 tests pass locally). |
| **Phase 21C Stage 3D: PostgreSQL ENUM Downgrade Remediation** | **PASS (LOCAL)** | Remediated initial migration downgrade to drop PostgreSQL ENUM types; verified via mock engine and SQLite downgrade-to-base drill. |
| **Overall Production Release Gate** | **HOLD** | **Strictly locked.** Live PostgreSQL validation and deployment remain unexecuted. |

### 1.1 Objective & Scope of Stage 3D
In [`docs/PHASE_21C_STAGE3C_LOCAL_IMPLEMENTATION_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_21C_STAGE3C_LOCAL_IMPLEMENTATION_REPORT.md), a known migration risk was audited: the initial Alembic migration ([`cb1c167fc450_initial_canonical_taxonomy_and_evidence.py`](file:///c:/Projects/smart-used-car-price-prediction/server/infrastructure/migrations/versions/cb1c167fc450_initial_canonical_taxonomy_and_evidence.py)) created three PostgreSQL user-defined types (UDTs) in `upgrade()`, but failed to drop them in `downgrade()`. On PostgreSQL, this caused subsequent re-upgrades from `base` to crash with duplicate type errors.

Phase 21C Stage 3D resolves this cleanup hazard safely and portably without altering migration revision IDs, upgrade semantics, or SQLite compatibility.

---

## 2. ROOT CAUSE & ENUM CLEANUP HAZARD ANALYSIS

### 2.1 The PostgreSQL ENUM Persistence Problem
In PostgreSQL, an enumerated column created via `sa.Enum(..., name='my_enum')` does not store values as simple string check constraints (as in SQLite). Instead, PostgreSQL creates a standalone user-defined type (UDT) entry in the system catalog (`pg_type`):
```sql
CREATE TYPE organizationtype AS ENUM ('SAFETY_AGENCY', 'REGULATORY_BODY', ...);
```

When Alembic auto-generates a migration, its `downgrade()` script drops the table columns and tables (`op.drop_table('evidence_sources')`), but **does not emit `DROP TYPE` statements** for the standalone types.

### 2.2 The Three Types Created by `cb1c167fc450`
Detailed inspection of `upgrade()` in `cb1c167fc450` confirmed exactly three ENUM types:
1. `organizationtype`: Created on `evidence_sources.organization_type`
   - Values: `'SAFETY_AGENCY'`, `'REGULATORY_BODY'`, `'OEM_MANUFACTURER'`, `'EMPIRICAL_DATASET'`, `'INDUSTRY_AUDIT'`, `'OTHER'`
2. `evidencestate`: Created on `evidence_sources.verification_status` and reused on `knowledge_claims.evidence_state`
   - Values: `'VERIFIED'`, `'SUPPORTED'`, `'EMPIRICAL'`, `'MODEL_ESTIMATE'`, `'INSUFFICIENT_DATA'`, `'UNVERIFIED'`, `'DEPRECATED'`
3. `hierarchylevel`: Created on `knowledge_claims.hierarchy_level`
   - Values: `'MANUFACTURER'`, `'MODEL'`, `'GENERATION'`, `'MODEL_YEAR'`, `'VARIANT'`, `'POWERTRAIN'`

### 2.3 The Failure Mode
If an operator or automated CI drill executed `alembic downgrade base` followed by `alembic upgrade head`:
1. `downgrade base` drops all tables, but leaves `organizationtype`, `evidencestate`, and `hierarchylevel` intact in PostgreSQL's `pg_type`.
2. `upgrade head` begins by executing `cb1c167fc450`.
3. `op.create_table('evidence_sources', ...)` encounters `sa.Enum(..., name='organizationtype')` and issues `CREATE TYPE organizationtype AS ENUM (...)`.
4. PostgreSQL aborts with a fatal transaction error:
   ```
   psycopg2.errors.DuplicateObject: type "organizationtype" already exists
   ```

---

## 3. REMEDIATION IMPLEMENTATION & CODE DIFFS

### 3.1 Design Principles for the Fix
1. **Explicit Dialect Guard:** The cleanup must check `bind is not None and bind.dialect.name == "postgresql"`. It must not execute on SQLite or MySQL where PostgreSQL UDTs do not exist.
2. **Safe Drop with `checkfirst=True`:** Use `sa.Enum(name=enum_name).drop(bind, checkfirst=True)` to prevent errors if a type was already dropped.
3. **Execution Order:** Must execute **after** all dependent tables (`claim_evidence_mappings`, `knowledge_claims`, `evidence_sources`) have been dropped so that no active column dependencies remain.
4. **Immutability of Revision Chain:** Revision ID `cb1c167fc450`, `down_revision = None`, and `upgrade()` behavior remain strictly unchanged.

### 3.2 Exact Diff in [`server/infrastructure/migrations/versions/cb1c167fc450_initial_canonical_taxonomy_and_evidence.py`](file:///c:/Projects/smart-used-car-price-prediction/server/infrastructure/migrations/versions/cb1c167fc450_initial_canonical_taxonomy_and_evidence.py)

```python
@@ -190,4 +190,11 @@
     op.drop_table('knowledge_claims')
     op.drop_table('evidence_sources')
     # ### end Alembic commands ###
+
+    # Drop PostgreSQL-specific user-defined ENUM types created by this initial migration
+    bind = op.get_bind()
+    if bind is not None and bind.dialect.name == "postgresql":
+        for enum_name in ('hierarchylevel', 'evidencestate', 'organizationtype'):
+            sa.Enum(name=enum_name).drop(bind, checkfirst=True)
+
```

---

## 4. FOCUSED TEST RESULTS & EMPIRICAL EVIDENCE

Three focused test methods were added to [`server/tests/test_database_url_normalization.py`](file:///c:/Projects/smart-used-car-price-prediction/server/tests/test_database_url_normalization.py) under the `TestMigrationEnumDowngradeRemediation` class:

### 4.1 Test Implementations
1. **`test_enum_downgrade_emits_drop_type_statements_for_postgresql`**:
   Configures an Alembic `MigrationContext` bound to a SQLAlchemy `create_mock_engine` using `postgresql+psycopg2://`. Executes `migration.downgrade()` and asserts that the SQL statement sequence captures:
   - `DROP TYPE hierarchylevel`
   - `DROP TYPE evidencestate`
   - `DROP TYPE organizationtype`
2. **`test_enum_downgrade_is_safe_noop_for_sqlite`**:
   Executes `migration.downgrade()` with an in-memory SQLite bind. Confirms that no `DROP TYPE` statements are issued and the migration downgrades cleanly without errors.
3. **`test_downgrade_base_and_reupgrade_head_on_sqlite`**:
   Executes a full, unmocked end-to-end Alembic migration drill on a fresh disposable SQLite database:
   - `command.upgrade(cfg, 'head')` (25 tables created at `f3d730c46a23`)
   - `command.downgrade(cfg, 'base')` (0 application tables remaining; all 4 migration downgrades exercised)
   - `command.upgrade(cfg, 'head')` (25 tables recreated cleanly)
   - `compare_metadata(ctx, Base.metadata)` (asserts 0 schema drift)

### 4.2 Test Execution Results

```powershell
.venv\Scripts\python.exe -m pytest server/tests/test_database_url_normalization.py server/tests/test_phase19c_database_lifecycle.py -v
```

**Results:**
```
============================= test session starts =============================
platform win32 -- Python 3.11.8, pytest-9.1.1, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: C:\Projects\smart-used-car-price-prediction
configfile: pytest.ini
collecting ... collected 29 items

server/tests/test_database_url_normalization.py::TestDatabaseURLNormalization::test_bare_postgresql_url_normalized_to_psycopg2 PASSED [  3%]
server/tests/test_database_url_normalization.py::TestDatabaseURLNormalization::test_legacy_postgres_url_normalized_to_psycopg2 PASSED [  6%]
server/tests/test_database_url_normalization.py::TestDatabaseURLNormalization::test_already_qualified_psycopg2_url_preserved PASSED [ 10%]
server/tests/test_database_url_normalization.py::TestDatabaseURLNormalization::test_alternative_driver_url_preserved PASSED [ 13%]
server/tests/test_database_url_normalization.py::TestDatabaseURLNormalization::test_sqlite_file_url_preserved PASSED [ 17%]
server/tests/test_database_url_normalization.py::TestDatabaseURLNormalization::test_sqlite_memory_url_preserved PASSED [ 20%]
server/tests/test_database_url_normalization.py::TestDatabaseURLNormalization::test_other_dialect_url_preserved PASSED [ 24%]
server/tests/test_database_url_normalization.py::TestDatabaseURLNormalization::test_query_parameters_preserved PASSED [ 27%]
server/tests/test_database_url_normalization.py::TestDatabaseURLNormalization::test_empty_and_none_handling PASSED [ 31%]
server/tests/test_database_url_normalization.py::TestDatabaseURLNormalization::test_sqlalchemy_engine_dialect_resolution_with_normalized_url PASSED [ 34%]
server/tests/test_database_url_normalization.py::TestDatabaseURLNormalization::test_mask_database_url_masks_credentials PASSED [ 37%]
server/tests/test_database_url_normalization.py::TestDatabaseURLNormalization::test_settings_reload_applies_normalization PASSED [ 41%]
server/tests/test_database_url_normalization.py::TestMigrationBooleanDefaultParity::test_boolean_defaults_compile_portably PASSED [ 44%]
server/tests/test_database_url_normalization.py::TestMigrationEnumDowngradeRemediation::test_enum_downgrade_emits_drop_type_statements_for_postgresql PASSED [ 48%]
server/tests/test_database_url_normalization.py::TestMigrationEnumDowngradeRemediation::test_enum_downgrade_is_safe_noop_for_sqlite PASSED [ 51%]
server/tests/test_database_url_normalization.py::TestMigrationEnumDowngradeRemediation::test_downgrade_base_and_reupgrade_head_on_sqlite PASSED [ 55%]
server/tests/test_phase19c_database_lifecycle.py::test_migration_from_empty_database_to_head PASSED [ 58%]
server/tests/test_phase19c_database_lifecycle.py::test_upgrade_from_supported_previous_revision PASSED [ 62%]
server/tests/test_phase19c_database_lifecycle.py::test_migration_downgrade_and_reupgrade PASSED [ 65%]
server/tests/test_phase19c_database_lifecycle.py::test_transaction_scope_commits_on_success PASSED [ 68%]
server/tests/test_phase19c_database_lifecycle.py::test_transaction_scope_rolls_back_on_exception PASSED [ 72%]
server/tests/test_phase19c_database_lifecycle.py::test_session_cleanup_lifecycle PASSED [ 75%]
server/tests/test_phase19c_database_lifecycle.py::test_engine_pool_pre_ping_enabled PASSED [ 79%]
server/tests/test_phase19c_database_lifecycle.py::test_sqlite_pragmas_enabled_on_connection PASSED [ 82%]
server/tests/test_phase19c_database_lifecycle.py::test_engine_disposal PASSED [ 86%]
server/tests/test_phase19c_database_lifecycle.py::test_database_unavailable_readiness_failure PASSED [ 89%]
server/tests/test_phase19c_database_lifecycle.py::test_production_startup_prohibits_automated_create_all PASSED [ 93%]
server/tests/test_phase19c_database_lifecycle.py::test_existing_database_preservation PASSED [ 96%]
server/tests/test_phase19c_database_lifecycle.py::test_postgresql_configuration_parameters PASSED [100%]

============================= 29 passed in 2.21s ==============================
```

> [!IMPORTANT]
> **Engineering Rigor Notice:**
> The unit tests above verify compilation of `DROP TYPE` SQL commands under SQLAlchemy's PostgreSQL dialect and confirm SQLite migration safety. However, **simulated and unit-level checks do not prove live PostgreSQL behavior.** Definitive proof of type destruction and subsequent re-creation requires execution against an actual PostgreSQL 16 database server (such as the GitHub Actions service container planned in Stage 3B/3C).

---

## 5. PROTECTED ARTIFACT HASH VERIFICATION

Both protected repository assets were verified post-remediation to confirm complete integrity:

| Protected Artifact | Baseline SHA-256 Checksum | Measured SHA-256 Checksum | Invariant Status |
|---|---|---|:---:|
| **Live Database** (`data/database/carspective.db`) | `cb655c06225c07af98a85a1171595d3c0d368db4e270c3170d57f96a874209e9` | `cb655c06225c07af98a85a1171595d3c0d368db4e270c3170d57f96a874209e9` | **PASS (UNTOUCHED)** |
| **Valuation Model** (`models/carspective_valuation_lgbm_v1.joblib`) | `4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1` | `4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1` | **PASS (UNTOUCHED)** |

---

## 6. REMAINING POSTGRESQL VALIDATION REQUIREMENTS

Now that the ENUM downgrade cleanup is remediated in `cb1c167fc450`:
1. **CI Workflow Drill Update:** When authorized, the `downgrade base` and re-upgrade drill can be safely added back to the `postgres-integration-tests` job in `.github/workflows/ci.yml`.
2. **Remote Workflow Execution:** A remote GitHub Actions run against `postgres:16-alpine` is required to provide empirical proof that PostgreSQL successfully executes the full migration chain, seed ingestion, `downgrade base`, and re-upgrade `upgrade head`.
3. **Repository Staging & Commit:** As detailed in Stage 3B, the untracked codebase must be staged and committed to `main` before triggering remote CI.

---

## 7. CONFIRMATION OF SAFETY BOUNDARIES & STOP PROTOCOL

In strict adherence to instructions:
- **No live database was connected to or modified.** All tests ran against in-memory SQLite and mock PostgreSQL engines.
- **No Git staging, commits, pushes, pulls, or branch changes were performed.**
- **No Docker, WSL, or external software was installed.**
- **Production Release Gate:** **HOLD.**

*Phase 21C Stage 3D is complete. Stopped per protocol. Awaiting user review and authorization.*

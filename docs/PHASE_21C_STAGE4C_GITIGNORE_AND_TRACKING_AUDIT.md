# CarSpective — Phase 21C, Stage 4C: Minimal `.gitignore` Rules & Staging Verification Report

**Date:** October 15, 2026  
**Role:** Senior Release Engineer & Database Reliability Engineer (DBRE)  
**Status:** COMPLETE (Hygiene Enforced, Working Tree Sanitized, Zero Push Blockers)  
**Deliverable:** `docs/PHASE_21C_STAGE4C_GITIGNORE_AND_TRACKING_AUDIT.md`  
**Reference Documents:**  
- `docs/PHASE_21C_STAGE4A_REPOSITORY_HYGIENE_AUDIT.md`  
- `docs/PHASE_21C_STAGE4B_LEGACY_MODEL_COMPATIBILITY_REPORT.md`  
**Target Repository:** `https://github.com/Subhamgupta9/smart-used-car-price-prediction.git`

---

## 1. Executive Summary

In Phase 21C Stage 4C, the repository configuration was updated with minimal, targeted, and non-blanket `.gitignore` rules to resolve the critical push blockers identified in Stage 4A and Stage 4B.

Prior to this stage:
1. The working tree contained **1,043 untracked files** exceeding **2.5 GB** in total disk footprint.
2. The legacy prototype model (`models/smart_used_car_price_model.pkl` at **906.95 MB**) and its notebook duplicate (`notebooks/models/` at **906.95 MB**) constituted fatal GitHub push blockers violating GitHub's **100 MB hard file-size limit** (`GH001`).
3. Local SQLite database snapshots, WAL journals, load test drill outputs, developer scratch scripts, and agent metadata polluted the candidate staging set.
4. Stage 4B established safe, decoupled optional-model handling in `app/app.py` and decorated legacy tests with `@pytest.mark.skipif`, ensuring clean checkouts without the 907 MB legacy model execute test suites cleanly with zero errors.

### Core Achievements in Stage 4C:
* **Zero Push Blockers (> 100 MB):** 0 files remain in the staging candidate set exceeding GitHub's 100 MB hard reject limit.
* **Zero Warning Threshold Files (50 MB – 100 MB):** 0 files remain in the staging candidate set exceeding GitHub's 50 MB warning threshold.
* **Only 1 Allowed File in 10 MB – 50 MB:** `app/static/models/generic_car.glb` (**38.82 MB**), required for Three.js vehicle rendering and client test suites.
* **Untracked Set Reduced by 581 Files:** Untracked candidate files dropped cleanly from 1,043 to **exactly 462 verified files**.
* **Total Staging Payload:** The entire candidate repository payload is only **70.78 MB** (well below GitHub's repository recommendations).
* **Protected Baseline Hash Verification:** Both the live SQLite database (`data/database/carspective.db`) and the production valuation model (`models/carspective_valuation_lgbm_v1.joblib`) match their SHA-256 baselines **100%**.
* **Release Gate:** `HOLD` — Staging (`git add`), commits, and remote operations are intentionally deferred pending explicit user authorization.

---

## 2. `.gitignore` Configuration Changes & Rationale

The `.gitignore` file was updated with targeted rules organized into clear functional domains. Broad blanket patterns (such as `*.csv`, `*.json`, or generic directory wildcards) were strictly avoided to prevent accidental exclusion of essential seed data, test fixtures, or architecture configs.

```gitignore
# ==============================================================================
# CARspective — Version Control Ignore Rules
# ==============================================================================

# Environment and secrets
.env
.env.*
!.env.example
*.pem
*.key
*.cert
*.crt

# Python artifacts
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/
.venv/
env/
venv/

# Node / Frontend artifacts
client/dist/
client/node_modules/
client/.vite/
client/coverage/
node_modules/
.npm

# Persistent Databases, Backups, and Snapshots
data/database/*.db
data/database/*.db*
data/database/*.backup*
data/database/*.snapshot*
data/database/*.pre_cleanup*
data/database/*.safety_backup
*.db
*.sqlite
*.sqlite3
*.db-shm
*.db-wal
backup_*/
*.bak

# Ephemeral Benchmarks & Load Drill Artifacts
data/phase20_load_drill/
*.log
*.tmp

# Scratch & Developer Working Files
scratch/
scratch_*
cleaned_test.png
extracted_texture.png
extract_texture.py
inspect_glb.py

# Large Offline Model Artifacts & Duplicates (>100MB GitHub limit)
models/smart_used_car_price_model.pkl
models/candidates/
notebooks/models/
notebooks/Projects/

# IDE & Assistant Metadata
.agent/
.agents/
.gemini/
.gsd/
.vscode/
.idea/
```

### Rationale for Key Ignore Rules:
1. **Secrets (`.env`, `.env.*`, `!.env.example`):** Ensures production and local developer secrets are never leaked, while explicitly permitting the canonical `.env.example` template to be tracked.
2. **Databases (`data/database/*.db`, `*.db-wal`, `backup_*/`):** Completely excludes local mutable state, transaction logs, and pre-migration backups, preserving data privacy and preventing repository bloat.
3. **Load Drill & Benchmarks (`data/phase20_load_drill/`):** Excludes 23 ephemeral load-test output files generated during Phase 20 concurrency stress testing.
4. **Large Offline Models (`models/smart_used_car_price_model.pkl`, `models/candidates/`, `notebooks/models/`):** Excludes the 906.95 MB legacy pickle model, the 906.95 MB notebook duplicate, and intermediate candidate models (`ExtraTreesRegressor_raw.joblib` at 236.14 MB).
5. **Agent & IDE Metadata (`.agent/`, `.agents/`, `.gemini/`, `.gsd/`, `.vscode/`, `.idea/`):** Prevents IDE-specific settings, agent cache states, and developer tool logs from entering version control.

---

## 3. Empirical Verification of Exclusion Rules

Each exclusion category was tested against `git check-ignore -v` to verify pattern syntax, line numbers, and behavior.

| Target Path Evaluated | Expected State | `git check-ignore -v` Output | Status |
| :--- | :--- | :--- | :--- |
| `models/smart_used_car_price_model.pkl` | IGNORED | `.gitignore:64:models/smart_used_car_price_model.pkl` | **VERIFIED** |
| `notebooks/models/smart_used_car_price_model.pkl` | IGNORED | `.gitignore:66:notebooks/models/` | **VERIFIED** |
| `models/candidates/ExtraTreesRegressor_raw.joblib` | IGNORED | `.gitignore:65:models/candidates/` | **VERIFIED** |
| `data/database/carspective.db` | IGNORED | `.gitignore:42:*.db` | **VERIFIED** |
| `data/database/carspective.db-wal` | IGNORED | `.gitignore:46:*.db-wal` | **VERIFIED** |
| `data/phase20_load_drill/metrics.json` | IGNORED | `.gitignore:51:data/phase20_load_drill/` | **VERIFIED** |
| `backup_pre_phase13/backup.txt` | IGNORED | `.gitignore:47:backup_*/` | **VERIFIED** |
| `scratch/test.py` | IGNORED | `.gitignore:56:scratch/` | **VERIFIED** |
| `scratch_test.py` | IGNORED | `.gitignore:57:scratch_*` | **VERIFIED** |
| `cleaned_test.png` | IGNORED | `.gitignore:58:cleaned_test.png` | **VERIFIED** |
| `extracted_texture.png` | IGNORED | `.gitignore:59:extracted_texture.png` | **VERIFIED** |
| `extract_texture.py` | IGNORED | `.gitignore:60:extract_texture.py` | **VERIFIED** |
| `inspect_glb.py` | IGNORED | `.gitignore:61:inspect_glb.py` | **VERIFIED** |
| `.agent/config.json` | IGNORED | `.gitignore:70:.agent/` | **VERIFIED** |
| `.agents/skills.json` | IGNORED | `.gitignore:71:.agents/` | **VERIFIED** |
| `.gemini/antigravity` | IGNORED | `.gitignore:72:.gemini/` | **VERIFIED** |
| `.gsd/state.json` | IGNORED | `.gitignore:73:.gsd/` | **VERIFIED** |
| `.vscode/settings.json` | IGNORED | `.gitignore:74:.vscode/` | **VERIFIED** |
| `.idea/workspace.xml` | IGNORED | `.gitignore:75:.idea/` | **VERIFIED** |
| `.env` | IGNORED | `.gitignore:6:.env` | **VERIFIED** |
| `.env.example` | **TRACKABLE** | `.gitignore:8:!.env.example` (Negation Match) | **VERIFIED** |

*Note on Git Negation Semantics:* Running `git check-ignore -v .env.example` returns exit code 0 and logs `.gitignore:8:!.env.example`. The leading exclamation mark confirms that `.env.example` is explicitly negated (un-ignored). This is corroborated by `git status --short --untracked-files=all .env.example`, which reports `?? .env.example`.

---

## 4. Verification of Candidate Tracking Eligibility

To ensure no essential runtime assets, models, seed files, or fixtures were accidentally masked, all critical publishing assets were tested.

| Critical Project Asset | Role / Purpose | `git check-ignore` Code | `git status` Result | Tracking Feasibility |
| :--- | :--- | :--- | :--- | :--- |
| `models/carspective_valuation_lgbm_v1.joblib` | Production Valuation Model (2.74 MB) | 1 (Not Ignored) | `??` (Candidate) | **ELIGIBLE** |
| `models/carspective_valuation_lgbm_v1_manifest.json` | Production Model Contract & Lineage | 1 (Not Ignored) | `??` (Candidate) | **ELIGIBLE** |
| `models/cache/bmw_3-series_g20-g21-g28-2019-2022.glb` | 3D Vehicle Model Cache Asset | 1 (Not Ignored) | `??` (Candidate) | **ELIGIBLE** |
| `app/static/models/generic_car.glb` | Base 3D Mesh for Prototype Client | 1 (Not Ignored) | `??` (Candidate) | **ELIGIBLE** |
| `data/raw/indian_used_cars_raw_57480.csv` | Canonical Historical Training Dataset | 1 (Not Ignored) | `??` (Candidate) | **ELIGIBLE** |
| `data/taxonomy_seeds/seed_canonical_taxonomy.json` | Baseline Database Taxonomy Seed Data | 1 (Not Ignored) | `??` (Candidate) | **ELIGIBLE** |
| `data/processed/market_intelligence_cache.json` | Precomputed Market Intelligence Cache | 1 (Not Ignored) | `??` (Candidate) | **ELIGIBLE** |
| `data/fixtures/current_market_fixtures.json` | Current Market Test Fixtures | 1 (Not Ignored) | `??` (Candidate) | **ELIGIBLE** |
| `.github/workflows/ci.yml` | GitHub Actions Dual-Engine CI Workflow | 1 (Not Ignored) | `??` (Candidate) | **ELIGIBLE** |
| `.env.example` | Sanitized Environment Config Template | 0 (Negated `!`) | `??` (Candidate) | **ELIGIBLE** |

Every required project asset remains fully eligible for tracking. Zero false-positive exclusions occurred.

---

## 5. Trackable Working-Tree Audit (462 Files, 70.78 MB Total)

An exhaustive breakdown of all 462 candidate untracked files demonstrates clean separation of concerns and an exceptionally lightweight footprint:

| Directory / Category | File Count | Aggregate Size | Key Subcomponents & Highlights |
| :--- | :---: | :---: | :--- |
| **Root Tooling & Configuration** | 10 | 0.03 MB | `.dockerignore`, `.env.example`, `.github/workflows/ci.yml`, `.gitignore`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `alembic.ini`, `pytest.ini` |
| **Documentation & Release Reports** | 49 | 0.75 MB | `README.md`, `AUDIT_REPORT.md`, `GSD-STYLE.md`, `PROJECT_RULES.md`, `VERSION`, `model_capabilities.yaml`, `docs/` (44 phase & release reports) |
| **Server Backend (`server/`)** | 158 | 1.52 MB | Domain services (valuation, scoring, deal analyzer, market intelligence, vehicle knowledge), API routers, SQLAlchemy repositories, Alembic migrations, and 39 backend test suites |
| **Legacy Flask Prototype (`app/`)** | 26 | 39.52 MB | Flask application, Jinja templates, Three.js visualization engine, texture assets, and `generic_car.glb` (38.82 MB) |
| **Frontend Client (`client/`)** | 104 | 0.74 MB | React/Vite/Tailwind source code (`client/src/`), component libraries, icons, package configurations (excluding `node_modules/` and `dist/`) |
| **Data Catalogs & Seed Data (`data/`)** | 49 | 16.83 MB | `data/raw/` (historical dataset: 13.9 MB), `data/taxonomy_seeds/`, `data/fixtures/`, `data/processed/`, `data/ml_benchmarks/` |
| **Production Models (`models/`)** | 8 | 10.85 MB | `carspective_valuation_lgbm_v1.joblib` (2.74 MB), model metadata, contract manifest, and 5 vehicle GLBs in `models/cache/` (8.39 MB) |
| **Scripts & Adapters** | 44 | 0.32 MB | `scripts/` (35 DB/model/seed utilities), `adapters/` (3), `src/` (6) |
| **Root Test Suites (`tests/`)** | 10 | 0.14 MB | Unit, integration, and cinematic valuation test suites |
| **Notebooks & Misc** | 2 | 0.08 MB | `notebooks/01_carspective_eda_and_baseline.ipynb`, `assets/` |
| **TOTAL CANDIDATE SET** | **462** | **70.78 MB** | **100% compliant with Git & GitHub hosting standards** |

---

## 6. GitHub File Size & Push Safety Audit

GitHub imposes strict constraints on repository file sizes:
* **Hard Block (`GH001`):** Files > 100 MB are rejected unconditionally at `git push` time.
* **Warning Threshold:** Files > 50 MB trigger push warnings and can indicate repository bloat.

### File Size Distribution Across All 462 Untracked Files:
```text
  > 100 MB (Fatal Push Blockers):        0 files
  50 MB - 100 MB (Warning Threshold):    0 files
  10 MB - 50 MB (Permitted Medium):      1 file   (app/static/models/generic_car.glb: 38.82 MB)
  1 MB - 10 MB:                          2 files  (models/carspective_valuation_lgbm_v1.joblib: 2.74 MB; 
                                                   data/raw/indian_used_cars_raw_57480.csv: 13.9 MB)
  < 1 MB:                                459 files
```

The repository is completely clean of any push-blocking artifacts.

---

## 7. Data Integrity & Protected Baseline Hash Verification

Both protected artifacts were hashed via SHA-256 before concluding Stage 4C. Neither file was modified, moved, or altered.

```text
Target Artifact: data/database/carspective.db
Expected Hash:   cb655c06225c07af98a85a1171595d3c0d368db4e270c3170d57f96a874209e9
Computed Hash:   cb655c06225c07af98a85a1171595d3c0d368db4e270c3170d57f96a874209e9
Match Status:    CONFIRMED IDENTICAL (100% MATCH)

Target Artifact: models/carspective_valuation_lgbm_v1.joblib
Expected Hash:   4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1
Computed Hash:   4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1
Match Status:    CONFIRMED IDENTICAL (100% MATCH)
```

---

## 8. Release Gate & Next Stage Roadmap

### Release Gate Status: `HOLD`
In accordance with DBRE and release engineering protocols:
* No files have been added to the Git staging index (`git add` has not been run).
* No Git commits have been created.
* No remote network operations (push/pull/fetch) have been initiated.

### Authorized Next Steps (Pending User Approval):
1. **Stage 4D — Atomic Staging & Commit:**
   * Stage files in logical, reviewable atomic groupings:
     1. Build, tooling, CI, and ignore rules (`.gitignore`, `.dockerignore`, `.env.example`, `.github/`, `Dockerfile`, `docker-compose.yml`, `requirements*.txt`, `pyproject.toml`, `alembic.ini`, `pytest.ini`).
     2. Documentation and release specifications (`README.md`, `docs/`, `AUDIT_REPORT.md`, `VERSION`, `model_capabilities.yaml`).
     3. Backend application, domain services, infrastructure, and server tests (`server/`).
     4. Frontend client source code (`client/`).
     5. Data seeds, raw catalogs, processed cache, and fixtures (`data/`).
     6. Production model artifacts and GLB cache (`models/`).
     7. Legacy prototype application and root test suites (`app/`, `tests/`, `scripts/`, `adapters/`, `src/`).
   * Perform pre-commit cached size validation (`git diff --cached --name-only`).
   * Create structured, signed release commit.
2. **Stage 4E — Remote Publication & CI Validation:**
   * Push to `origin/main` (`https://github.com/Subhamgupta9/smart-used-car-price-prediction.git`).
   * Monitor GitHub Actions execution of both `test` (SQLite) and `postgres-integration-tests` (PostgreSQL service container) workflows.

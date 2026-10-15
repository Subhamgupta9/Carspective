# CarSpective Project Handover & Operational Continuity Document

**Document ID:** `docs/ANTIGRAVITY_HANDOVER.md`  
**Date:** October 15, 2026 *(updated for Phase 20E closure — C4 final result recorded)*  
**Author:** Antigravity Autonomous Diagnostic Agent  
**Repository Path:** `C:\Projects\smart-used-car-price-prediction`  
**Host Environment:** Windows 10 Pro / Python 3.11.8 (`.venv`)  
**Current Phase:** Phase 20 (Operational Readiness & Infrastructure Verification)  
**Phase 19 Status:** **CONDITIONAL ACCEPT** (Local sign-off achieved; Docker, remote CI, live PostgreSQL, offsite backup, and PITR unverified)  
**Phase 20 Status:** **IN PROGRESS** (Workstreams A & D Accepted; Workstream E on **HOLD**)  
**Invariant Baseline Status:** **16 / 16 PASS** (Verified pre- and post-C4 benchmark, 2026-10-10 and 2026-10-12)  

---

## 1. Project Identity, Architecture, and Core Product Contracts

### 1.1 Project Identity & Core Promise
- **Project Identity:** **CarSpective — Intelligent Automotive Intelligence Platform**
- **Product Promise:** *“Know the car. Know the value. Know the truth.”*

CarSpective is an enterprise-grade AI and analytics platform tailored to the Indian used car market. It provides:
1. **Fair Market Valuation (FMV):** Machine-learning-driven price prediction with dynamic depreciation curves, conformal prediction confidence intervals, and confidence bands.
2. **Multi-Criteria Vehicle Scoring:** 5-dimensional holistic vehicle scoring (Reliability, Value for Money, Performance, Safety, and Ownership Costs) normalized to a 0–100 scale.
3. **Comparative Analysis:** Multi-vehicle side-by-side evaluation with specification normalization, valuation comparison, and tradeoff matrix generation.
4. **Deal Analysis:** Real-time evaluation of listing prices against fair market valuations to rate deal attractiveness.
5. **3D Interactive Experience:** Web-based Three.js vehicle visualizer and digital inspection catalog.

### 1.2 System Architecture Overview
```
┌─────────────────────────────────────────────────────────────┐
│                    Client Applications                      │
│   (Web Frontend, Three.js 3D View, Admin & Telemetry APIs)  │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────▼──────────────────────────────┐
│                  Waitress WSGI Server                       │
│    (Port 5001/5009, Host 127.0.0.1, Worker Threads = 8)     │
└──────────────────────────────┬──────────────────────────────┘
                               │ WSGI Dispatch
┌──────────────────────────────▼──────────────────────────────┐
│                    Flask 3.x Application                    │
│   (server/app.py - Factory Pattern, Request Middleware)     │
│   - Request ID Injection & Structured JSON Access Logging   │
│   - Per-Request Timing Middleware (before/after_request)    │
│   - ScopedSession Lifecycle Management                      │
└──────┬───────────────────────┼───────────────────────┬──────┘
       │                       │                       │
┌──────▼───────┐       ┌───────▼────────┐      ┌───────▼──────┐
│  Valuation   │       │  Comparison    │      │  Knowledge   │
│   Service    │       │   Service      │      │   Service    │
│  (LRU Cache  │       │  (Multi-car    │      │  (Snapshot   │
│   + ML)      │       │   Evaluation)  │      │   Cache)     │
└──────┬───────┘       └───────┬────────┘      └───────┬──────┘
       │                       │                       │
┌──────▼───────────────────────▼───────────────────────▼──────┐
│                 SQLAlchemy ORM Layer                        │
│            (ScopedSession / Request-Scoped)                 │
└──────────────────────────────┬──────────────────────────────┘
                               │ SQLite WAL / Pool
┌──────────────────────────────▼──────────────────────────────┐
│               SQLite Relational Database                    │
│      (data/database/carspective.db - 25 Tables)             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Core Product Contracts & Invariants
- **Deterministic Valuation & Scoring:** The valuation model (`models/carspective_valuation_lgbm_v1.joblib`) and scoring weights are strictly calibrated. Output contracts (valuation ranges, score dimensions 0–100, evidence states) must never be altered without explicit product approval.
- **Request-Scoped Session Lifecycle:** Every incoming request receives an isolated database session via `ScopedSession()`. Sessions are never shared across threads or stored in process-level singletons. They are deterministically closed in Flask's `teardown_request`.
- **Database Safety Isolation:** The production database (`data/database/carspective.db`) is protected and strictly read-only during testing. All load drills, benchmarks, and disaster recovery operations must target disposable database files (e.g. `data/phase20_load_drill/carspective_load.db`).
- **Alembic Schema Invariance:** Schema version is pinned to migration revision `f3d730c46a23`. No migrations may run against live database assets.

---

## 2. Current Phase and Exact Status Distinctions (Phase 19 & Phase 20)

### 2.1 Phase 19 Status: CONDITIONAL ACCEPT
Phase 19 is recorded as **CONDITIONAL ACCEPT**, not an unconditional PASS.

- **Verified Local Scope (Signed Off Locally):**
  - **Phase 19A–19D:** Codebase audit, test isolation defect corrections, forensic contamination cleanup, and persistent market data reconciliation completed.
  - **Phase 19E:** Deployment scripts, Dockerfile hardening, CI workflow definitions, and local WSGI configuration audited (`docs/PHASE_19E_DEPLOYMENT_AND_CI_REPORT.md`).
  - **Phase 19F:** Backup and recovery runbook validation, transactional backup utilities, and local recovery drill completed (`docs/PHASE_19F_BACKUP_RECOVERY_REPORT.md`).
- **Unverified Production Infrastructure (The Condition):**
  - **Docker Runtime:** Container execution and Docker daemon operations remain unsupported and unverified on this Windows host.
  - **Remote CI Pipeline:** Automated CI executions on remote runners remain unverified.
  - **Live Production Database:** A production PostgreSQL instance has not been provisioned or verified.
  - **Offsite Backup Storage & PITR:** Cloud-based offsite storage replication and Point-in-Time Recovery (PITR) workflows remain unverified against production backends.
  - **Production-Scale Load Testing:** High-concurrency testing against real production hardware has not occurred.

Because these production operational capabilities cannot be validated on the local workstation, Phase 19 status is strictly **CONDITIONAL ACCEPT**.

### 2.2 Phase 20 Status: IN PROGRESS — Workstream E on HOLD
- **Workstream A (Preflight & Environment Audit):** **ACCEPTED** — Dependencies, virtual environment, and configuration verified.
- **Workstream D (Disaster Recovery Drill):** **ACCEPTED** — Executed recovery drill against disposable database files (`docs/PHASE_20_WORKSTREAM_D_RECOVERY_DRILL_REPORT.md`).
- **Workstream E (Concurrent Load & Resilience Benchmark):** **HOLD**
  - **Run 1 (Initial Benchmark):** Failed early due to process-level database session contention and thread timeouts (`docs/PHASE_20_WORKSTREAM_E_LOAD_BENCHMARK_REPORT.md`).
  - **Remediation 1 (Session Lifecycle):** Replaced process-level singleton with request-scoped database sessions (`docs/PHASE_20E_SESSION_LIFECYCLE_REMEDIATION_REPORT.md`).
  - **Run 2 (Post-Session Fix Benchmark):** 300 requests succeeded with 0 timeouts and 0 5xx errors, but comparison endpoint P95 was 2,178 ms (`docs/PHASE_20E_POST_REMEDIATION_BENCHMARK_REPORT.md`).
  - **Remediation 2 (Comparison Optimization):** Deduplicated comparison SQL queries, reducing query count from ~40 to 21 queries (`docs/PHASE_20E_COMPARISON_LATENCY_REMEDIATION_REPORT.md`).
  - **Run 3 (Post-Remediation Benchmark):** 300 requests completed (100% HTTP 200, 39.15 req/s), but all 4 endpoints missed proposed Client P95 engineering targets (`docs/PHASE_20E_POST_REMEDIATION_BENCHMARK_REPORT.md`).
  - **Diagnostic Investigation:** Identified Waitress thread saturation (70% full saturation), Search N+1 queries (56 queries/req), and Comparison computational dominance (`docs/PHASE_20E_TAIL_LATENCY_ROOT_CAUSE_REPORT.md`).
  - **Remediation 3 (Search N+1 Query Fix):** Applied `selectinload` eager loading across 4-level taxonomy hierarchy in `TaxonomyRepository`, dropping search queries from 56 to 5 (-91.1%) (`docs/PHASE_20E_SEARCH_N_PLUS_ONE_REMEDIATION_REPORT.md`).
  - **Run 4 (Post-Search Benchmark):** 300 requests completed with 100% success; throughput increased to 53.29 req/sec (`docs/PHASE_20E_POST_SEARCH_REMEDIATION_BENCHMARK_REPORT.md`).
  - **Controlled Sizing Experiment:** Evaluated Waitress `threads=8` vs `threads=16`. Confirmed 16 threads completely eliminated queue backlog warnings and dropped compare P95 to 788 ms, but CPython GIL contention prevented valuation P95 from reaching < 150 ms (`docs/PHASE_20E_WAITRESS_WORKER_SIZING_EXPERIMENT.md`).
  - **CPU & Profiling Investigation:** Confirmed scikit-learn preprocessing and model inference CPU demand, along with repeated taxonomy resolution in valuation (`docs/PHASE_20E_CPU_AND_INFERENCE_PROFILING_REPORT.md`).
  - **Remediation 4 (Targeted Taxonomy Caching):** Implemented in-memory hierarchy snapshot cache for search (1,275x speedup, 0 DB queries) and LRU canonical resolution cache for valuation/compare (95.2% hit rate, 0 DB queries on hits) (`docs/PHASE_20E_TAXONOMY_CACHING_REMEDIATION_REPORT.md`).
  - **Run 5 (Post-Caching Benchmark):** 300 requests completed (100% HTTP 200, 57.41 req/sec); client P50 dropped to 84.25 ms (-26.5%) and P99 dropped to 910.65 ms (-30.0%).
  - **Multi-Process Serving Experiment:** Evaluated 1P $\times$ 8T baseline vs 2P $\times$ 4T and 2P $\times$ 8T. Demonstrated 63%–102% throughput gain (up to 115.04 req/sec), 47% reduction in client P95, 93% reduction in queue backlog warnings, and Search P95 passed the $< 250$ ms gate (183.74 ms) (`docs/PHASE_20E_MULTIPROCESS_SERVING_EXPERIMENT.md`).
  - **Multi-Process Tail-Latency Investigation:** Profiled sub-stages and decomposed queue dwell time under `variant_2p4t` (`docs/PHASE_20E_MULTIPROCESS_TAIL_LATENCY_REPORT.md`). Proved that server-side execution alone passes Readiness (44.99 ms vs 50 ms gate) and Valuation (138.59 ms vs 150 ms gate). Client P95 failure is driven by Waitress FIFO socket queue dwell time combined with CPython GIL serialization during Scikit-learn `ColumnTransformer` execution.
  - **Request Scheduling Validation:** Evaluated Round-Robin vs. Least-Active-Worker dispatch strategies across 4 repeated 300-request runs under 2P $\times$ 4T (`docs/PHASE_20E_REQUEST_SCHEDULING_VALIDATION.md`). Demonstrated Least-Active dispatching reduced paired overhead P95 by 44.8% (148 ms $\rightarrow$ 81 ms), increased throughput to 100.6 req/s, and capped queue depth to 4 in-flight requests.
  - **Fast-Endpoint Isolation Experiment:** Evaluated physical separation of lightweight traffic from CPU-heavy traffic across 6 repeated 300-request runs under an exact 8-thread global compute ceiling (`docs/PHASE_20E_FAST_ENDPOINT_ISOLATION_EXPERIMENT.md`). Proved dedicated fast workers decouple health and search (Readiness P95 dropped to 17.85–28.89 ms; Search P95 dropped to 18.78–39.11 ms, both PASS). Variant B (2P $\times$ 3T compute) reached 122.21 req/s and stabilized Compare P95 at 323.14 ms (PASS). However, allocating 2 threads to Fast traffic left only 6 threads for Compute traffic against 10 concurrent clients, leaving Valuation P95 at 203.27–213.33 ms (FAIL vs 150 ms target).
  - **Valuation Inference Bottleneck Investigation:** Conducted runtime microsecond-level stage decomposition and contention profiling under Variant B (`docs/PHASE_20E_VALUATION_INFERENCE_INVESTIGATION.md`). Proved valuation client P95 was 279.63 ms (FAIL), while server processing alone was 127.60 ms P95. Feature preprocessing P95 was 44.03 ms (GIL thrashing), predict P95 was 61.36 ms (OpenMP contention), and DB queries were exactly 0 (0.00 ms).
  - **Valuation Preprocessing Optimization:** Implemented `CategoricalPreprocessingCache` — a thread-safe, immutable-result cache for the fitted `ColumnTransformer` output on identical categorical inputs. Reduced repeated DataFrame construction and preprocessing overhead without refitting any pipeline component. Validated prediction equivalence before proceeding.
  - **Serving Topology Experiment Series (C1–C3):** Systematically evaluated three 3-process × 4-thread topologies with different compute-pool partitioning strategies (`docs/PHASE_20E_TOPOLOGY_EXPERIMENT.md`). Raw results preserved in `data/phase20_load_drill/topology_experiment_results.json`.
    - **C1 (Shared Compute):** Valuation FAIL (196.66 ms); Comparison FAIL (624.35 ms due to OpenMP lock contention across shared threads); 1 of 4 gates passing.
    - **C2 (Isolated Compare):** First valuation gate PASS (115.53 ms). Comparison exploded to 591.12 ms (single-process isolation under dual-LightGBM concurrency); 2 of 4 gates passing.
    - **C3 (3T Isolated Compare):** Thread reduction to 9 total; Comparison improved to 524.40 ms but still FAIL; 2 of 4 gates passing.
  - **Variant C4 Benchmark (Asymmetric Spillover, Authorized 2026-10-10):** Implemented asymmetric Least-Active dispatch with spillover threshold = 2 across 3 processes × 4 threads = 12 total threads (`docs/PHASE_20E_VARIANT_C4_BENCHMARK.md`). Executed 2026-10-10T09:19:04Z. Raw results: `data/phase20_load_drill/variant_c4_benchmark_results.json`. **Best result in all Phase 20E experiments: 3 of 4 gates passing for the first time.**
    - Readiness P95: **63.84 ms** — **FAIL** (13.84 ms over the 50 ms target; sole remaining gate failure)
    - Valuation P95: **139.94 ms** — **PASS** (10.06 ms margin)
    - Search P95: **64.86 ms** — **PASS** (185.14 ms margin)
    - Comparison P95: **197.87 ms** — **PASS** (152.13 ms margin)
    - Throughput: **168.10 req/s** — **PASS**; Errors: **0** — **PASS**
    - Post-flight invariants: **16/16 PASS** (verified 2026-10-12)
  - **Current Gate Verdict:** **HOLD** — Readiness P95 = 63.84 ms exceeds the frozen 50 ms target. All 4 gates have never passed simultaneously.

### 2.3 Frozen Acceptance Latency Gates
All performance targets remain strictly frozen. **Do not relax acceptance thresholds or change test workloads to manufacture a pass:**

| Metric / Gate | Frozen Acceptance Target | Run 5 (Single Process) | **Latest: Variant C4** | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Request Completion Rate** | 100.0% (300/300) | 100.0% | 100.0% | **PASS** |
| **Observed Throughput** | $> 10.0$ req/sec | 57.41 req/sec | **168.10 req/sec** | **PASS** |
| **HTTP 5xx Error Rate** | $< 0.1\%$ (0 errors) | 0.0% (0 errors) | 0.0% (0 errors) | **PASS** |
| **Request Timeouts** | 0 timeouts | 0 timeouts | 0 timeouts | **PASS** |
| **Post-Benchmark Readiness** | $< 50.0$ ms (HTTP 200) | 3.68 ms | 3.74 ms (port 5009 probe) | **PASS** |
| **Health Readiness Client P95** | **$< 50.0$ ms** | 115.68 ms | **63.84 ms** | ❌ **FAIL (Release Blocker)** |
| **Search Client P95** | **$< 250.0$ ms** | 401.14 ms | **64.86 ms** | **PASS** |
| **Compare Client P95** | **$< 350.0$ ms** | 974.26 ms | **197.87 ms** | **PASS** |
| **Valuation Client P95** | **$< 150.0$ ms** | 417.65 ms | **139.94 ms** | **PASS** |
| **Phase 20 Workstream E Gate** | **All Endpoints Must Pass** | **HOLD** | **HOLD** | **HOLD** |


> [!IMPORTANT]
> **Non-Negotiable Release Policy:** Fast-endpoint isolation, taxonomy caching, search N+1 remediation, session concurrency remediation, and comparison query optimization are prior experimental/remediation results. They do **not** mean the overall release gate has passed. Workstream E remains strictly on **HOLD** until every frozen gate passes reproducibly.

---

## 3. Latest Authoritative Investigation Summary (October 10–12, 2026)

The authoritative findings from the Variant C4 benchmark are recorded in [`docs/PHASE_20E_VARIANT_C4_BENCHMARK.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_VARIANT_C4_BENCHMARK.md). The topology experiment series (C1–C3) is recorded in [`docs/PHASE_20E_TOPOLOGY_EXPERIMENT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_TOPOLOGY_EXPERIMENT.md). The valuation inference investigation that preceded them is in [`docs/PHASE_20E_VALUATION_INFERENCE_INVESTIGATION.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_VALUATION_INFERENCE_INVESTIGATION.md).

### 3.1 C4 Overall Metrics (Authoritative Latest Result)
- **Architecture:** 3P × 4T = 12 threads — asymmetric Least-Active dispatch, spillover threshold = 2.
  - **Fast Pool (Port 5009):** 1P × 4T — readiness + search.
  - **Compute-A (Port 5010):** 1P × 4T — valuation-preferred, comparison overflow.
  - **Compute-B (Port 5011):** 1P × 4T — comparison-preferred, valuation overflow.
- **Workload:** 300 mixed requests (75 readiness, 75 search, 105 valuation, 45 compare), 10 concurrent clients.
- **Completion Rate:** 300/300 (100%). Zero timeouts, zero HTTP 5xx.
- **Throughput:** **168.10 req/s**.
- **Client P95 Latencies:**
  - Health Readiness: **63.84 ms** ❌ FAIL vs. < 50 ms gate — **sole remaining release blocker**
  - Search: **64.86 ms** ✅ PASS vs. < 250 ms gate
  - Valuation: **139.94 ms** ✅ PASS vs. < 150 ms gate (10.06 ms margin)
  - Comparison: **197.87 ms** ✅ PASS vs. < 350 ms gate (152.13 ms margin)

### 3.2 Readiness Gate Failure — Measured vs. Hypothesised

**Measured facts (from correlated per-request `X-Socket-Queue-Dwell-Ms` headers in C4):**
- Readiness server execution P95: **19.76 ms** under load; **3.74 ms** in isolation (post-run probe).
- Readiness socket queue dwell P95: **46.42 ms** — measured per-request, not derived by subtracting percentiles.
- Client P95 = 63.84 ms = server (19.76 ms) + dwell (46.42 ms) + transit — consistent with per-request correlated records.
- Pattern across all variants (C1–C4): readiness P95 is consistently 55–64 ms regardless of fast-pool thread count (3T or 4T), isolating the issue to accept-queue behaviour, not thread count.

**Hypothesis (not yet independently validated beyond benchmark observations):**
- The accept-queue pressure is attributed to Windows OS localhost socket sequentialisation under 10-client burst. This is a plausible and internally consistent explanation. However, it has not been verified against a Linux host or a non-Waitress socket binding.

> [!NOTE]
> The socket queue dwell measurement methodology used in C4 is validated: per-request correlated `X-Socket-Queue-Dwell-Ms` and `X-Server-Duration-Ms` headers are used; no independent percentile subtraction is performed. This resolves the measurement caution recorded in the prior version of this document.

### 3.3 Prior Valuation Stage Breakdown (From Variant B Investigation — Still Valid Reference)
- **Preprocessing P95 (`ColumnTransformer`):** **44.03 ms** under Variant B. Partially mitigated by `CategoricalPreprocessingCache` introduced before C1.
- **Model Inference P95 (`LGBMRegressor.predict`):** **61.36 ms** under Variant B.
- **Database Contention:** Disproved — 0 DB queries across all 105 valuation requests in both Variant B and C4 investigations. LRU cache covers canonical vehicle resolution.
- **Host CPU Saturation:** ~99.64% (Variant B); 93.3% average (C4 — lower due to process isolation reducing GIL contention).



---

## 4. Phase 20E Closure Status & Remaining Evidence Gaps

### 4.1 Phase 20E Final Status
Phase 20 Workstream E is **HOLD**. The Variant C4 benchmark (the strongest configuration tested) achieved 3 of 4 latency gates for the first time. The sole remaining gate failure is Readiness P95 = 63.84 ms vs. the 50 ms frozen target. No further experiments have been authorized.

**To lift the HOLD, the following evidence is required before reconsidering:**
1. A reproducible benchmark run (same 300-request workload, 10 concurrent clients) in which **all four** latency gates pass simultaneously — including Readiness P95 < 50 ms.
2. Post-run invariant verification confirming 16/16 PASS on the same run.
3. Zero HTTP 5xx errors and zero timeouts.

### 4.2 Unverified Deployment Requirements (Unchanged from Phase 19)
The following deployment capabilities remain unverified and must not be assumed operational:

| Requirement | Status | Notes |
|:--|:--|:--|
| **Docker runtime** | ❌ Unverified | Dockerfile audited but never executed; Docker daemon unavailable on Windows host |
| **Remote CI pipeline** | ❌ Unverified | GitHub Actions workflows defined; remote runner execution unverified |
| **Live PostgreSQL** | ❌ Unverified | All work used SQLite (`carspective.db`); no PostgreSQL instance provisioned |
| **Point-in-Time Recovery (PITR)** | ❌ Unverified | Local recovery drill completed (Workstream D); cloud/PostgreSQL PITR untested |
| **Offsite backup storage** | ❌ Unverified | Local filesystem backup verified; S3/cloud replication not configured or tested |
| **Concurrent-load validation beyond experiments** | ❌ Unverified | All load testing used disposable SQLite on local Windows hardware; Linux/production-scale validation pending |

### 4.3 Non-Negotiable Boundaries & Constraints
The following negative constraints remain in force for any future engineering task:

1. **Do not refit, replace, or modify the trained model or fitted preprocessing components:** The model artifact `models/carspective_valuation_lgbm_v1.joblib` and its internal scikit-learn transformers must remain byte-identical.
2. **Do not change feature definitions, feature ordering, missing-value behavior, valuation response contracts, or prediction semantics.**
3. **Do not introduce unsafe shared mutable state:** Thread safety and process safety must be preserved across all serving workers.
4. **Re-run the established mixed-workload benchmark only when explicitly authorized:** Do not run ad-hoc benchmarks without explicit user instructions.
5. **Preserve all frozen acceptance gates:** Do not relax any latency, throughput, or error-rate targets.
6. **Workstream E remains HOLD:** The workstream must not be marked PASS or ACCEPTED unless every gate passes reproducibly in a single run.



## 5. Environment, Safety, Integrity, and Infrastructure Discrepancies

### 5.1 Protected Baseline Assets & Reference Hashes
All baseline assets are locked and protected. The reference hashes recorded in prior authoritative reports are:
- **Live Database (`data/database/carspective.db`):**  
  `cb655c06225c07af98a85a1171595d3c0d368db4e270c3170d57f96a874209e9`
- **Valuation Model Pipeline (`models/carspective_valuation_lgbm_v1.joblib`):**  
  `4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1`
- **Phase 19C Safety Backup (`data/database/carspective.db.phase19c_safety_backup`):**  
  `fe9d013cee0d9e16bbd1453aaa6bcf0cf6b966a42c5da818ab75e8db2c7d47cf`
- **Pre-Cleanup Snapshot (`data/database/carspective.db.pre_cleanup_snapshot_20261009_191728`):**  
  `c6d8093a413dde469363b377ef92d76c31fca60d0eeed148c86b036a136c31a6`
- **Alembic Schema Revision ID:** `f3d730c46a23`
- **Inspection Catalog:** Version `2.0.0` (49 items)

*(Note: These are reference values recorded from prior reports, not a claim that they were recomputed or reverified during this documentation-only task).*

### 5.2 Invariant Verification Command
The established invariant verification command is:
```powershell
.venv\Scripts\python scripts/verify_phase19_invariants.py
```
*The C4 post-flight verification (2026-10-12) confirmed **16/16 invariants passing** and all benchmark ports (5009, 5010, 5011) cleanly released.*

### 5.3 Infrastructure Distinction: Local vs. Production
To avoid false operational assumptions, the project environment is split into verified local capabilities vs. unverified production infrastructure:

| Infrastructure Component | Local Status | Production Status | Operational Reality |
| :--- | :---: | :---: | :--- |
| **Operating System** | Windows 10 Pro | Linux (Ubuntu/Debian) | Local scripts use Windows PowerShell and `.venv\Scripts\` |
| **Database** | SQLite WAL | PostgreSQL | Live PostgreSQL has not been deployed or tested |
| **Containerization** | Unsupported | Docker / Podman | Docker runtime is unavailable locally; Dockerfile is audited but unrun |
| **CI / CD Pipeline** | Local pytest | Remote GitHub Actions | Remote workflow runners are unverified |
| **Backup Storage** | Local filesystem | S3 / Cloud Storage | Offsite replication and Point-in-Time Recovery (PITR) unverified |
| **Load Testing** | Disposable SQLite DB | Production Database | All load tests run against `data/phase20_load_drill/carspective_load.db` |

---

## 6. Transfer Instructions for the Second Antigravity Account

### 6.1 Resume on a Second Antigravity Account Checklist
When transferring this repository to a second Antigravity account, execute the following 10-point checklist:

1. **Open the existing project directory:** Work strictly within `C:\Projects\smart-used-car-price-prediction`. Do not create a new project, reinitialize git, or clone over existing work.
2. **Read `docs/ANTIGRAVITY_HANDOVER.md` first:** Establish baseline understanding of project status, architecture, and constraints.
3. **Read the latest investigation reports:** Read [`docs/PHASE_20E_VARIANT_C4_BENCHMARK.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_VARIANT_C4_BENCHMARK.md) (primary C4 result) and [`docs/PHASE_20E_TOPOLOGY_EXPERIMENT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_TOPOLOGY_EXPERIMENT.md) (C1–C3 context). The valuation inference investigation is in [`docs/PHASE_20E_VALUATION_INFERENCE_INVESTIGATION.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_VALUATION_INFERENCE_INVESTIGATION.md).
4. **Inspect `git status --short` before modifying anything:** Preserve and review existing uncommitted diagnostic scripts and reports; do not reset, clean, discard, or overwrite them.
5. **Confirm current repository state and virtual environment:** Verify that `.venv\Scripts\python.exe` exists and is Python 3.11.8 before invoking commands.
6. **Run the invariant verifier only when needed:** Execute `.venv\Scripts\python scripts/verify_phase19_invariants.py` within available execution budget when an actual verification check is required.
7. **Understand the closure state:** Phase 20E Workstream E is on HOLD. There is no pending next authorized engineering task. Any new investigation requires explicit user authorization.
8. **Keep Workstream E on HOLD:** Do not declare a pass until all four frozen acceptance gates pass simultaneously and reproducibly in a single run.
9. **Protect sensitive data:** Never expose secrets, `.env` file contents, credentials, private account data, or unnecessary personal paths in handover documents.
10. **Verify transfer before declaring success:** Do not claim the project has been transferred successfully until the second account has opened the same repository, reviewed the files, and verified the handover.

### 6.2 First-Message Prompt for the Second Account
Copy and paste this exact prompt into the first message of the second Antigravity account:

```text
Read `docs/ANTIGRAVITY_HANDOVER.md` and the latest referenced Phase 20E investigation report. Treat the handover as the project continuity source. Do not restart the project, rerun completed experiments, modify code, or relax acceptance gates. First summarize the current state, verified facts versus reported findings, remaining release blockers, and the single next authorized task. Then wait for my approval before making changes.
```

---

## 7. Authoritative Documentation Index

All completed diagnostic and remediation reports are indexed below:

| Document Path | Title & Description | Status / Outcome |
| :--- | :--- | :---: |
| [`docs/PHASE_19_FINAL_PRODUCTION_READINESS_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_19_FINAL_PRODUCTION_READINESS_REPORT.md) | Phase 19 Final Production Readiness Sign-off Report | **CONDITIONAL ACCEPT** |
| [`docs/PHASE_19E_DEPLOYMENT_AND_CI_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_19E_DEPLOYMENT_AND_CI_REPORT.md) | Deployment, CI pipeline, and WSGI operational audit | **CONDITIONAL ACCEPT** (Local signoff; Docker/CI unverified) |
| [`docs/PHASE_19F_BACKUP_RECOVERY_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_19F_BACKUP_RECOVERY_REPORT.md) | Backup and recovery verification report | **CONDITIONAL ACCEPT** (Local signoff; PostgreSQL/offsite unverified) |
| [`docs/DISASTER_RECOVERY_RUNBOOK.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/DISASTER_RECOVERY_RUNBOOK.md) | Standard Operating Procedure for backup & restore | **ACTIVE** |
| [`docs/OPERATIONAL_GUIDE.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/OPERATIONAL_GUIDE.md) | Runbook for operational management & telemetry | **ACTIVE** |
| [`docs/ERROR_BUDGET_FRAMEWORK.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/ERROR_BUDGET_FRAMEWORK.md) | Service Level Objectives (SLOs) and Error Budget policy | **ACTIVE** |
| [`docs/PHASE_20_WORKSTREAM_D_RECOVERY_DRILL_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20_WORKSTREAM_D_RECOVERY_DRILL_REPORT.md) | Phase 20 Workstream D Disaster Recovery Drill report | **ACCEPTED** |
| [`docs/PHASE_20_WORKSTREAM_E_LOAD_BENCHMARK_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20_WORKSTREAM_E_LOAD_BENCHMARK_REPORT.md) | Phase 20 Workstream E Initial Concurrent Benchmark (Run 1) | **HOLD** |
| [`docs/PHASE_20E_CONCURRENCY_ROOT_CAUSE_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_CONCURRENCY_ROOT_CAUSE_REPORT.md) | Diagnostic analysis of database session contention | **RESOLVED** |
| [`docs/PHASE_20E_SESSION_LIFECYCLE_REMEDIATION_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_SESSION_LIFECYCLE_REMEDIATION_REPORT.md) | Remediation report for request-scoped database sessions | **ACCEPTED** |
| [`docs/PHASE_20E_COMPARISON_LATENCY_INVESTIGATION.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_COMPARISON_LATENCY_INVESTIGATION.md) | Diagnostic investigation of comparison endpoint query load | **RESOLVED** |
| [`docs/PHASE_20E_COMPARISON_LATENCY_REMEDIATION_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_COMPARISON_LATENCY_REMEDIATION_REPORT.md) | Remediation report for comparison query deduplication | **ACCEPTED** |
| [`docs/PHASE_20E_POST_REMEDIATION_BENCHMARK_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_POST_REMEDIATION_BENCHMARK_REPORT.md) | Post-remediation 300-request concurrent benchmark (Run 3) | **HOLD** |
| [`docs/PHASE_20E_TAIL_LATENCY_ROOT_CAUSE_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_TAIL_LATENCY_ROOT_CAUSE_REPORT.md) | In-depth diagnostic investigation of tail latency | **CONFIRMED** |
| [`docs/PHASE_20E_SEARCH_N_PLUS_ONE_REMEDIATION_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_SEARCH_N_PLUS_ONE_REMEDIATION_REPORT.md) | Search N+1 eager loading remediation report | **ACCEPTED** |
| [`docs/PHASE_20E_POST_SEARCH_REMEDIATION_BENCHMARK_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_POST_SEARCH_REMEDIATION_BENCHMARK_REPORT.md) | Post-search-remediation 300-request benchmark (Run 4) | **HOLD** |
| [`docs/PHASE_20E_WAITRESS_WORKER_SIZING_EXPERIMENT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_WAITRESS_WORKER_SIZING_EXPERIMENT.md) | Controlled worker sizing experiment (8 vs 16 threads) | **COMPLETED** |
| [`docs/PHASE_20E_CPU_AND_INFERENCE_PROFILING_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_CPU_AND_INFERENCE_PROFILING_REPORT.md) | In-depth CPU, inference, and memory profiling report | **COMPLETED** |
| [`docs/PHASE_20E_TAXONOMY_CACHING_REMEDIATION_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_TAXONOMY_CACHING_REMEDIATION_REPORT.md) | Targeted taxonomy caching remediation and Run 5 report | **ACCEPTED** (Overall gate on HOLD) |
| [`docs/PHASE_20E_MULTIPROCESS_SERVING_EXPERIMENT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_MULTIPROCESS_SERVING_EXPERIMENT.md) | Multi-process serving experiment and scalability report | **COMPLETED** |
| [`docs/PHASE_20E_MULTIPROCESS_TAIL_LATENCY_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_MULTIPROCESS_TAIL_LATENCY_REPORT.md) | Multi-process tail-latency root cause report | **DIAGNOSED** |
| [`docs/PHASE_20E_REQUEST_SCHEDULING_VALIDATION.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_REQUEST_SCHEDULING_VALIDATION.md) | Request scheduling validation report (Least-Active vs Round-Robin) | **VALIDATED** |
| [`docs/PHASE_20E_FAST_ENDPOINT_ISOLATION_EXPERIMENT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_FAST_ENDPOINT_ISOLATION_EXPERIMENT.md) | Fast-endpoint isolation architecture experiment report | **COMPLETED** |
| [`docs/PHASE_20E_VALUATION_INFERENCE_INVESTIGATION.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_VALUATION_INFERENCE_INVESTIGATION.md) | Valuation inference bottleneck investigation report | **DIAGNOSED** |
| [`docs/PHASE_20E_TOPOLOGY_EXPERIMENT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_TOPOLOGY_EXPERIMENT.md) | Serving topology experiment series (Variants C1, C2, C3) | **COMPLETED — HOLD** |
| [`docs/PHASE_20E_VARIANT_C4_BENCHMARK.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_VARIANT_C4_BENCHMARK.md) | Variant C4 asymmetric spillover benchmark (final authorized run) | **COMPLETED — HOLD** (Readiness P95 gate unmet) |

---

## 8. Key Reference Files & Implementations

- **Taxonomy Repository:** [`server/repositories/taxonomy_repository.py`](file:///c:/Projects/smart-used-car-price-prediction/server/repositories/taxonomy_repository.py)
- **Canonical Resolver:** [`server/domain/taxonomy/resolver.py`](file:///c:/Projects/smart-used-car-price-prediction/server/domain/taxonomy/resolver.py)
- **Knowledge / Search Service:** [`server/domain/knowledge/service.py`](file:///c:/Projects/smart-used-car-price-prediction/server/domain/knowledge/service.py)
- **Valuation Service:** [`server/domain/valuation/service.py`](file:///c:/Projects/smart-used-car-price-prediction/server/domain/valuation/service.py)
- **Comparison Service:** [`server/domain/comparison/service.py`](file:///c:/Projects/smart-used-car-price-prediction/server/domain/comparison/service.py)
- **Valuation Model Pipeline:** [`models/carspective_valuation_lgbm_v1.joblib`](file:///c:/Projects/smart-used-car-price-prediction/models/carspective_valuation_lgbm_v1.joblib)
- **C4 Benchmark Harness:** [`scratch/run_phase20_variant_c4_benchmark.py`](file:///c:/Projects/smart-used-car-price-prediction/scratch/run_phase20_variant_c4_benchmark.py)
- **Topology Experiment Harness:** [`scratch/run_phase20_topology_experiment.py`](file:///c:/Projects/smart-used-car-price-prediction/scratch/run_phase20_topology_experiment.py)
- **Phase 19 Invariant Verification Script:** [`scripts/verify_phase19_invariants.py`](file:///c:/Projects/smart-used-car-price-prediction/scripts/verify_phase19_invariants.py)

---

**Handover Document Author:** Antigravity Autonomous Diagnostic Agent  
**Continuity Status:** Authoritative — Phase 20E Closure Recorded  
**Last Updated:** October 15, 2026 (Phase 20E C4 final result, Workstream E HOLD confirmed)  
**Next Action:** No engineering task is pending. Any further investigation requires explicit user authorization.


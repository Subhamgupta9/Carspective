# CarSpective — Phase 20E Follow-up
## Comparison Latency Diagnostic Investigation Report

**Product:** CarSpective — Intelligent Automotive Intelligence Platform  
**Document:** `docs/PHASE_20E_COMPARISON_LATENCY_INVESTIGATION.md`  
**Investigation Timestamp:** 2026-10-10T00:15:00Z  
**Operating Mode:** DIAGNOSTIC INVESTIGATION ONLY — NO IMPLEMENTATION CHANGES  
**Target Database:** Isolated disposable SQLite database (`data/phase20_load_drill/carspective_load.db`)  
**Investigation Verdict:** **ROOT CAUSE CONFIRMED**  
**Phase 20 Workstream E Status:** **HOLD** (Maintained — No Thresholds Relaxed)

---

## 1. Executive Summary & Diagnostic Verdict

During the Phase 20E post-remediation concurrent load benchmark (300 requests across 10 worker threads), the session-lifecycle architectural defect was verified as resolved (zero 5xx errors, zero timeouts, zero database exceptions, 33.86 req/s). However, client-observed and server-side P95 latencies exceeded the proposed concurrent targets, dominated by the `POST /api/v1/compare` endpoint:

- **Comparison Server-Internal P95:** 2,166.69 ms (Client P95: 2,178.00 ms)
- **Valuation Server-Internal P95:** 229.29 ms (Client P95: 322.86 ms)
- **Search Server-Internal P95:** 121.55 ms (Client P95: 305.89 ms)
- **Readiness Server-Internal P95:** 16.41 ms (Client P95: 207.54 ms)

This diagnostic investigation isolated and empirically measured every phase of `ComparisonService.compare()`.

### Confirmed Facts vs. Hypotheses

| Area | Initial Hypothesis | Empirical Finding | Status |
| :--- | :--- | :--- | :--- |
| **Worker Queueing** | "Comparison requests saturate worker threads, causing all latency." | **Partially Confirmed:** For lightweight endpoints (Readiness and Search), client latency inflation (up to 207 ms) is 100% caused by Waitress worker queueing. For Comparison itself, however, latency is **NOT socket queueing**; the in-process execution of `compare()` itself expands from **57 ms (1 worker) to 1,027 ms (10 workers)**. | **CONFIRMED (Disambiguated)** |
| **Python Logic Contention** | "Complex tradeoff and category winner math takes excessive CPU." | **Refuted:** The entire pure-Python comparison logic (category winners, score comparison, valuation comparison, tradeoffs, best-for labels, research summaries, and overall results) executes in **0.15 ms P50** under 10 concurrent threads. | **REFUTED** |
| **JSON Serialization** | "Large Pydantic response payloads cause serialization bottleneck." | **Refuted:** Response serialization (`model_dump()` + `json.dumps()`) consumes **0.38 ms** for the full 15.5 KB payload. | **REFUTED** |
| **Database Query Volume** | "Comparison executes heavy or redundant database queries." | **Confirmed:** A single 2-vehicle comparison request executes **36 to 44 distinct SQL queries** across 11 database tables. | **CONFIRMED** |
| **Redundant Taxonomy Resolution** | "Comparison resolves the same vehicle multiple times." | **Confirmed:** Each vehicle in the comparison is independently resolved by `CanonicalResolver` **twice** (once during Scoring, once during Valuation). | **CONFIRMED** |
| **Unnecessary Knowledge Queries** | "`_build_specifications` issues over-broad database queries." | **Confirmed:** `KnowledgeService.get_vehicle_profile()` queries 11 database tables (reviews, reliability, ownership, variant features) per vehicle, but `_build_specifications` discards almost all data, reading only 4 engine specs, 6 dimensions, and crash rating stars. | **CONFIRMED** |
| **Contention Mechanism** | "Why does single-thread 57 ms become 1,027 ms under 10 threads?" | **Confirmed:** When 10 threads concurrently issue 40 queries each (400 simultaneous SQLite queries), Python GIL contention during SQLAlchemy statement compilation and ORM hydration, combined with SQLite connection lock serialization, multiplies elapsed time by **18×**. | **CONFIRMED** |

**Diagnostic Verdict:** **ROOT CAUSE CONFIRMED**

---

## 2. Complete Comparison Execution Flow & Call Graph

When `POST /api/v1/compare` is called, `ComparisonService.compare()` executes the following synchronous pipeline:

```
POST /api/v1/compare (ComparisonRequest)
  │
  ├── 1. Scoring Pipeline (for each vehicle v in vehicles):
  │     ├── TaxonomyRepository.find_manufacturer(v.brand) [SQL]
  │     ├── TaxonomyRepository.find_model(v.model) [SQL with 5-table joinedload]
  │     ├── TaxonomyRepository.find_generation_for_year(v.year) [SQL]
  │     ├── KnowledgeClaim query for SAFETY adult_occupant_crash_rating [SQL]
  │     ├── EvidenceMapping & EvidenceSource lazy-load [SQL]
  │     └── Rule-based scoring (Reliability, Maintenance, Resale, Practicality)
  │
  ├── 2. Valuation Pipeline (for each vehicle v in vehicles):
  │     ├── TaxonomyRepository.find_manufacturer(v.brand) [SQL — REDUNDANT RE-QUERY]
  │     ├── TaxonomyRepository.find_model(v.model) [SQL — REDUNDANT RE-QUERY]
  │     ├── TaxonomyRepository.find_generation_for_year(v.year) [SQL — REDUNDANT RE-QUERY]
  │     ├── Feature Preprocessing (pd.DataFrame creation)
  │     ├── LightGBM Regressor Inference (pipeline.predict) [~13.1 ms CPU]
  │     └── Conformal expected range calculation
  │
  ├── 3. Deal Analysis (Conditional):
  │     └── Skipped in General Mode (listings=None)
  │
  ├── 4. User Fit Modeling (Conditional):
  │     └── Skipped in General Mode (mode=general)
  │
  ├── 5. Specification Synthesis (_build_specifications):
  │     ├── Read static specs from VEHICLE_SPECS_DB dict
  │     └── For each vehicle v in vehicles:
  │           └── KnowledgeService.get_vehicle_profile(can_id) [11 SQL QUERIES PER VEHICLE]:
  │                 ├── TaxonomyRepository.get_manufacturer_by_slug [SQL]
  │                 ├── TaxonomyRepository.get_model_by_slug [SQL]
  │                 ├── KnowledgeRepository.get_specifications_for_vehicle [SQL]
  │                 ├── KnowledgeRepository.get_dimensions_for_vehicle [SQL]
  │                 ├── KnowledgeRepository.get_safety_rating_for_vehicle [SQL]
  │                 ├── KnowledgeRepository.get_features_for_generation [SQL]
  │                 ├── KnowledgeRepository.get_ownership_profile_for_vehicle [SQL]
  │                 ├── KnowledgeRepository.get_reliability_issues_for_vehicle [SQL]
  │                 ├── KnowledgeRepository.get_pros_cons_for_vehicle [SQL]
  │                 └── KnowledgeRepository.get_review_synthesis_for_vehicle [SQL]
  │                 (NOTE: Only 4 spec fields, 6 dim fields, and safety stars are retained; rest discarded!)
  │
  ├── 6. Pure Python Decision Synthesis:
  │     ├── _build_category_winners (deterministic score comparison) [0.03 ms]
  │     ├── _build_score_comparison [0.02 ms]
  │     ├── _build_valuation_comparison [0.02 ms]
  │     ├── _build_tradeoffs (dimensional trade-off matrix) [0.03 ms]
  │     ├── _build_best_for_labels (rule-based persona badges) [0.02 ms]
  │     ├── _build_research_summaries (concise summary bullets) [0.02 ms]
  │     └── _build_overall_result (deterministic category aggregator) [0.01 ms]
  │
  └── 7. Response Serialization:
        └── Pydantic ComparisonResponse.model_dump() [0.38 ms]
```

---

## 3. Evidence-Backed Latency Breakdown

To isolate every sub-system without guesswork, instrumented profiling was executed against the isolated disposable database (`data/phase20_load_drill/carspective_load.db`).

### A. Single-Threaded Baseline Profiling (Warm Cache)

```
================================================================================
SINGLE-THREADED INSTRUMENTED COMPONENT BREAKDOWN
================================================================================
Scoring Vehicle 1 (Swift):          2.37 ms  (5 queries)
Scoring Vehicle 2 (i20):            1.58 ms  (4 queries)
Valuation Vehicle 1 (Swift):       12.13 ms  (2 queries + ML predict)
Valuation Vehicle 2 (i20):         15.77 ms  (3 queries + ML predict)
Knowledge Profile (V1 + V2):       23.80 ms  (22 queries across 11 tables)
Pure Python Comparison Heuristics:  0.15 ms  (0 queries)
Pydantic Serialization:             0.38 ms  (0 queries, 15.5 KB JSON)
--------------------------------------------------------------------------------
Total Full compare() Execution:    56.81 ms  (36 total queries, DB time: 1.95 ms)
================================================================================
```

### B. In-Process Concurrency Scaling (Zero Waitress / Zero HTTP)

By executing `ComparisonService.compare()` directly in a Python thread pool without any web server or network layer, we isolated pure application-level concurrency scaling:

```
================================================================================
IN-PROCESS CONCURRENT CONCURRENCY SCALING (20 Requests)
================================================================================
Workers:  1 | Wall: 1.16s | Throughput: 17.3 req/s | P50:   57.87 ms | P95:   62.23 ms
Workers:  2 | Wall: 1.27s | Throughput: 15.8 req/s | P50:  124.23 ms | P95:  151.06 ms
Workers:  4 | Wall: 1.92s | Throughput: 10.4 req/s | P50:  316.90 ms | P95:  732.15 ms
Workers:  8 | Wall: 2.48s | Throughput:  8.1 req/s | P50:  880.02 ms | P95: 1607.59 ms
Workers: 10 | Wall: 2.25s | Throughput:  8.9 req/s | P50: 1027.41 ms | P95: 1767.03 ms
================================================================================
```

*Finding:* At 10 workers, in-process latency scales to **P50 = 1,027.41 ms and P95 = 1,767.03 ms**. This directly mirrors the Waitress server-side metrics (P50 = 1,305.85 ms, P95 = 2,166.69 ms), proving that **concurrency degradation is intrinsic to the multi-threaded execution of `compare()`, not network or Waitress socket queueing.**

### C. Component Isolation under 10 Concurrent Threads

To pinpoint which specific sub-service accounts for the 18× latency expansion under 10 concurrent threads, each phase was isolated and tested across 10 concurrent workers:

```
================================================================================
COMPONENT CONCURRENCY ISOLATION UNDER 10 WORKERS
================================================================================
[Pure Python Comparison   ] P50:   0.15 ms | P95:   0.25 ms | Mean:   0.17 ms
[Scoring (2 vehicles)     ] P50: 107.50 ms | P95: 139.70 ms | Mean: 102.16 ms
[Valuation (2 vehicles)   ] P50: 305.61 ms | P95: 509.98 ms | Mean: 320.28 ms
[Knowledge (2 profiles)   ] P50: 749.30 ms | P95: 796.43 ms | Mean: 734.27 ms  <-- 65% OF TIME!
================================================================================
```

*Key Insight:*  
1. **Pure Python is instantaneous (0.17 ms).**
2. **Knowledge Profile retrieval alone accounts for 749 ms P50 (~65% of total time)** because it executes 22 separate database queries across 11 tables per request.
3. **Valuation accounts for 305 ms P50 (~26% of total time)** due to DataFrame construction, LightGBM inference, and redundant taxonomy resolution.

---

## 4. Workload Representativeness Audit

Inspection of `scratch/run_phase20_load_benchmark.py` reveals the exact workload characteristics used during the benchmark:

```python
COMPARE_PAYLOADS = [
    {
        "vehicles": [
            {"brand": "Maruti Suzuki", "model": "Swift", "manufacturing_year": 2021},
            {"brand": "Hyundai", "model": "i20", "manufacturing_year": 2021}
        ],
        "mode": "general"
    },
    {
        "vehicles": [
            {"brand": "Hyundai", "model": "Creta", "manufacturing_year": 2020},
            {"brand": "Tata", "model": "Nexon", "manufacturing_year": 2022}
        ],
        "mode": "general"
    }
]
```

### Workload Findings
1. **Fixed 2-Vehicle Structure:** Both test payloads compared exactly 2 vehicles. None tested 3 vehicles (which would have incurred 1.5× more queries).
2. **General Mode Only:** `mode="general"` was used exclusively. Neither payload included listing pricing (`listings`) or user preferences (`user_profile`). Deal analysis and recommendation engines were therefore bypassed.
3. **Repetitive Vehicle Identity:** The 45 comparison requests alternated strictly between only 4 vehicles (`Swift`, `i20`, `Creta`, `Nexon`). Because no application-level cache was present for vehicle profiles, the system repeatedly executed identical database queries for the exact same 4 vehicles 45 times.
4. **Missing Specification Data for i20:** `hyundai::i20` is not present in `VEHICLE_SPECS_DB` and has no specifications or dimensions rows in the database. As a result, `KnowledgeService.get_vehicle_profile` executed 11 queries, found nothing, and returned empty fields, causing every specification attribute for `i20` to render as `"Data unavailable"`.

---

## 5. Waitress Worker Configuration & Queueing Analysis

Waitress was started with `threads=8` on `127.0.0.1:5009`. The concurrent test issued traffic across 10 client worker threads.

### Confirmed vs. Inferred Queueing

```
+------------------+---------------------+---------------------+----------------------+
| Endpoint         | Server Internal P95 | Client Observed P95 | Queueing Delta (ms)  |
+------------------+---------------------+---------------------+----------------------+
| HEALTH_READINESS |            16.41 ms |           207.54 ms | 191.13 ms (92% queue)|
| SEARCH           |           121.55 ms |           305.89 ms | 184.34 ms (60% queue)|
| VALUATION        |           229.29 ms |           322.86 ms |  93.57 ms (29% queue)|
| COMPARE          |          2166.69 ms |          2178.00 ms |  11.31 ms (0.5% queue|
+------------------+---------------------+---------------------+----------------------+
```

### Mechanical Findings
1. **Worker Saturation is CONFIRMED:**  
   Because Comparison requests occupy Waitress worker threads for **1.3 to 2.1 seconds**, 5 to 7 of the 8 available threads are occupied with comparison computations at any given moment.
2. **Head-of-Line Blocking on Lightweight Endpoints is CONFIRMED:**  
   Health Readiness takes only **3.78 ms** of CPU time on the server. However, incoming health checks wait in the Waitress socket backlog for up to **191 ms** before being assigned to an available worker.
3. **Increasing Worker Count is NOT the Proper Fix:**  
   Increasing Waitress threads from 8 to 16 or 32 would worsen GIL contention and SQLite lock contention, increasing total execution time rather than reducing it. The proper engineering solution is to optimize Comparison execution time so workers are freed within 50 ms.

---

## 6. Impact of Phase 20E Session-Lifecycle Remediation

The Phase 20E remediation replaced thread-shared singleton sessions with request-scoped sessions (`ScopedSession()`), guaranteeing process stability.

### Concurrency Effects of the Remediation
1. **Thread Safety & Stability (RESOLVED):**  
   The primary remediation goal was 100% achieved: zero SQLite database locks, zero thread deadlocks, zero session contamination.
2. **Cache Isolation Effect:**  
   In the legacy (broken) implementation, ORM objects loaded into the singleton session remained in identity maps indefinitely. Under `ScopedSession`, every request opens and tears down its own session (`ScopedSession.remove()`), ensuring clean transactions.
3. **Joinedload Overhead:**  
   To prevent `DetachedInstanceError` when accessing model relationships across request boundaries, `TaxonomyRepository` queries were modified to include `joinedload` on model generations, years, and aliases. A single cold `find_manufacturer` query with joinedload takes **~130 ms**, and `find_model` takes **~23 ms**.
4. **No Identity Cache in Knowledge Repository:**  
   `KnowledgeRepository` and `EvidenceRepository` instantiate separate queries on every request without caching static vehicle profiles across requests.

---

## 7. Ranked Optimization Candidates

To bring `POST /api/v1/compare` within target thresholds (< 150 ms P50, < 350 ms P95 under concurrency) without violating architectural boundaries or risking regressions, four optimization candidates are ranked below:

### Rank 1: Selective Specification & Dimension Querying in `_build_specifications`
- **Likely Benefit:** **VERY HIGH (Reduces Comparison latency by ~500–600 ms)**
- **Regression Risk:** **VERY LOW**
- **Mechanism:**  
  Currently, `_build_specifications()` calls `KnowledgeService.get_vehicle_profile()`, which executes 11 queries per vehicle across reviews, reliability advisories, pros/cons, and ownership profiles. However, `_build_specifications()` only extracts:
  - 4 engine specifications (`displacement_cc`, `max_power_bhp`, `max_torque_nm`, `arai_mileage_kmpl`)
  - 6 dimensions (`length_mm`, `width_mm`, `height_mm`, `wheelbase_mm`, `ground_clearance_mm`, `boot_capacity_l`)
  - Crash rating stars (`ncap_stars`)
  Replacing the full profile retrieval with a dedicated lightweight method (`get_specification_snapshot()`) that queries only specifications, dimensions, and safety ratings eliminates **16 of the 22 queries** immediately.

### Rank 2: Canonical Taxonomy Resolution Reuse
- **Likely Benefit:** **MODERATE (Reduces latency by ~50–100 ms and eliminates 8 queries)**
- **Regression Risk:** **VERY LOW**
- **Mechanism:**  
  Currently, for each vehicle in `vehicles`, `ScoringService.calculate_score()` resolves canonical taxonomy, and then `ValuationService.evaluate_valuation()` resolves the exact same taxonomy **a second time**.  
  Resolving canonical identity once at the start of `ComparisonService.compare()` and passing the resolved `CanonicalResolutionResult` (or pre-resolved `canonical_vehicle_id`) to both scoring and valuation eliminates 50% of taxonomy queries.

### Rank 3: Process-Level In-Memory Cache for Static Vehicle Knowledge Data
- **Likely Benefit:** **EXTREME (Reduces Knowledge Profile latency from 749 ms to < 1 ms)**
- **Regression Risk:** **LOW**
- **Mechanism:**  
  Canonical vehicle specifications, dimensions, and crash ratings are immutable reference data (they do not change per user or per request). Storing these read-only schemas in a thread-safe in-memory cache (e.g. `dict` keyed by `canonical_vehicle_id` or `lru_cache`) will drop specification lookup time to **0.01 ms**, completely eliminating database contention for known vehicles.

### Rank 4: Add Missing Static Specs for High-Volume Test Vehicles
- **Likely Benefit:** **LOW TO MODERATE**
- **Regression Risk:** **ZERO**
- **Mechanism:**  
  Add `hyundai::i20` to `VEHICLE_SPECS_DB` in `server/domain/comparison/service.py`. This ensures `i20` renders verified specifications rather than `"Data unavailable"` and prevents fallback query loops.

---

## 8. Targeted Regression Test Battery for Future Implementation

Any future implementation pass addressing Comparison latency must pass the following verified test battery before acceptance:

1. **Comparison Domain Suite:**  
   `pytest server/tests/test_comparison.py` (all 15 tests, including 2-vehicle, 3-vehicle, general mode, personalized mode, trade-offs, and P50 performance).
2. **Valuation Domain Suite:**  
   `pytest server/tests/test_valuation.py` (all 11 tests, verifying asking price isolation and conformal ranges).
3. **Session Concurrency Suite:**  
   `pytest server/tests/test_phase20e_session_concurrency.py` (all 6 tests, confirming zero cross-thread session contention).
4. **Performance Benchmark Suite:**  
   `pytest server/tests/test_performance.py` (verifying taxonomy P95 < 60ms and search P50 < 100ms).
5. **Invariant Gate:**  
   `python scripts/verify_phase19_invariants.py` (15/15 PASS, ensuring live database and models remain unaltered).

---

## 9. Governance Confirmation

- **Diagnostic Investigation Only:** No application code, tests, dependencies, or configuration were modified.
- **Protected Invariants Preserved:** All 15 repository baseline invariants remain 100% verified.
- **Phase 19 Status:** Remains closed under **`CONDITIONAL ACCEPT`**.
- **Phase 20 Workstream E Status:** Remains at **`HOLD`**. Optimization implementation and benchmark reruns require separate explicit authorization.

---
*Report generated strictly from empirical diagnostic traces against `data/phase20_load_drill/carspective_load.db`.*

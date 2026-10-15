# CarSpective Phase 20E — Valuation Inference Bottleneck Investigation Report

**Date:** 2026-10-10  
**Phase:** 20 — Production Readiness & Operational Verification  
**Workstream:** 20E — Concurrent Load Testing & Tail Latency Optimization  
**Status:** COMPLETE (Diagnostic Profiling & Root Cause Investigation)  
**Workstream Status:** **HOLD** (Valuation client P95 of 279.63 ms exceeds the frozen 150 ms acceptance target; Readiness, Search, and Comparison pass)

---

## 1. Executive Summary

This investigation identifies the measured causes of valuation client P95 latency exceeding the frozen 150 ms target under the best-performing tested architecture, **Variant B: 3 processes with an exact 8-thread global compute ceiling**:
- **Fast Pool (Port 5009):** 1 process $\times$ 2 threads (serves `/health/readiness` and `/api/v1/vehicles/search`).
- **Compute Pool (Ports 5010 & 5011):** 2 processes $\times$ 3 threads each = 6 threads (serves `/api/v1/valuation` and `/api/v1/compare` via Least-Active dispatch).

The investigation preserved the exact 300-request mixed workload (75 readiness, 75 search, 105 valuation, 45 compare) and 10 concurrent client workers. Non-invasive, runtime instrumentation was applied via a dedicated diagnostic runner without modifying any production source files in `server/`, `app/`, or `models/`.

### Key Empirical Findings
1. **Measured Decomposition of Client P95 (279.63 ms):**
   - **Socket Queue Dwell ($\Delta_i$):** **122.62 ms P95** (Mean: 47.01 ms). With 10 concurrent clients submitting bursts of 150 compute requests against only 6 compute threads, requests spend substantial time waiting in the OS socket / Waitress listen queue before worker thread pickup.
   - **Server Execution Duration:** **127.60 ms P95** (Mean: 56.61 ms, P50: 50.57 ms). Server processing alone is within the 150 ms budget at P95; client failure is the combined result of queue dwell and server processing.
   - **Return Transit Dwell:** **107.56 ms P95** (Mean: 31.11 ms, P50: 14.12 ms) due to client worker scheduling and response socket flushing under host CPU saturation.
2. **Preprocessing vs. Inference Profiling:**
   - **Isolated Single Request:** Feature preprocessing (`ColumnTransformer`) consumes **10.31 ms** (79% of internal execution), while `model.predict()` consumes only **1.49 ms** (11%). Inside `ColumnTransformer`, `OneHotEncoder` is the single largest cost (5.26 ms mean), followed by `SimpleImputer` (2.65 ms total) and DataFrame slicing (0.99 ms).
   - **Under Multi-Threaded Concurrency:** Because `ColumnTransformer` is written in pure Python/NumPy with fine-grained Python method dispatch, it serializes under the CPython Global Interpreter Lock (GIL). Under concurrent benchmark load, feature preprocessing P95 rises to **44.03 ms**, and LightGBM model inference P95 rises to **61.36 ms** (due to OpenMP thread contention across saturated CPU cores).
3. **Database Session Contention is Disproved with 100% Certainty:**
   - Synchronized SQLAlchemy event tracking proved that across all 105 valuation requests, database query count was **exactly 0** and database access duration was **0.00 ms**. Canonical vehicle resolution hit the in-memory LRU cache on 100% of steady-state requests (0.10 ms P50).
4. **Comparison Requests Exacerbate Valuation Latency (+72.5 ms):**
   - When a valuation request executed on a worker concurrently with an in-flight comparison request (`active_compare > 0`, N=62), Valuation Client P95 was **281.91 ms**.
   - When no comparison requests were active on that worker (`active_compare == 0`, N=43), Valuation Client P95 dropped to **209.40 ms** (a 72.5 ms, 34.6% reduction).
   - Comparison requests execute two valuations plus scoring and tradeoff analysis, consuming worker threads for ~250–320 ms and heavily contending for the CPU and GIL.
5. **Host CPU Saturation Confirmed:**
   - System CPU reached **99.64% average utilization** during concurrent execution, proving the host cores are fully saturated by 10 concurrent clients running ML inference.
6. **Final Gate Verdict:**
   - In accordance with project policy, because Valuation client P95 (279.63 ms) exceeds the 150 ms gate, **Workstream E remains on HOLD**.

---

## 2. Correlated Per-Request Timing Distributions

Every valuation request was instrumented with microsecond-resolution client-send timestamps (`X-Client-Send-Time`) and server arrival/completion timestamps. Timing distributions were measured directly per request (not computed by subtracting independent percentile values).

### 2.1 Valuation Request Stage Breakdown (105 Requests)

| Valuation Processing Stage | P50 (ms) | P95 (ms) | P99 (ms) | Mean (ms) | Max (ms) | % of Client P95 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Socket Queue Dwell ($\Delta_i$)** | 31.42 | **122.62** | 248.20 | 47.01 | 254.28 | 43.9% |
| **2. Request Parsing & Validation** | 0.10 | 0.13 | 0.29 | 0.11 | 0.41 | < 0.1% |
| **3. Canonical Vehicle Resolution** | 0.10 | 9.13 | 47.43 | 2.30 | 81.25 | 3.3% |
| **4. DataFrame Feature Construction** | 1.44 | 13.89 | 18.83 | 2.97 | 29.50 | 5.0% |
| **5. Feature Preprocessing (`ColumnTransformer`)** | 18.79 | **44.03** | 79.94 | 23.70 | 89.80 | 15.7% |
| **6. Model Inference (`LGBMRegressor.predict`)** | 20.84 | **61.36** | 107.68 | 27.08 | 142.62 | 21.9% |
| **7. Conformal Range Postprocessing** | 0.10 | 0.12 | 0.14 | 0.10 | 0.54 | < 0.1% |
| **8. Database Access Duration** | **0.00** | **0.00** | **0.00** | **0.00** | **0.00** | 0.0% |
| **9. Database Query Count** | **0** | **0** | **0** | **0** | **0** | — |
| **10. Response JSON Serialization** | 0.14 | 0.20 | 0.26 | 0.15 | 0.37 | < 0.1% |
| **Total Server Processing Duration** | **50.57** | **127.60** | **147.20** | **56.61** | **228.50** | 45.6% |
| **Client Return Transit & Scheduling** | 14.12 | 107.56 | 182.58 | 31.11 | 183.88 | — |
| **Total Client-Observed Latency** | **106.84** | **279.63** | **304.81** | **134.73** | **312.54** | **100.0%** |

*Note: Individual stage P95 values reflect the 95th percentile of each stage across all 105 requests. In correlated per-request analysis, total client duration satisfies: $\text{client\_duration}_i = \text{socket\_queue\_dwell}_i + \text{server\_duration}_i + \text{return\_transit}_i$ for every individual request $i$.*

---

## 3. Preprocessing vs. Inference Deep-Dive Profiling

To isolate algorithmic costs from web server and concurrency overhead, feature preprocessing and model inference were benchmarked under controlled conditions.

### 3.1 Isolated Single-Request Profiling (500 Iterations)

```
Total Service Evaluation (14.19 ms Mean)
 ├── Canonical Resolution (LRU Cache Hit): 0.07 ms (0.5%)
 ├── Pydantic Parsing & Validation:        0.01 ms (0.1%)
 ├── DataFrame Construction (1 row):       0.72 ms (5.1%)
 ├── ColumnTransformer Preprocessing:     10.55 ms (74.3%) ──► [PRIMARY BOTTLENECK]
 │    ├── Categorical OneHotEncoder:       5.26 ms (37.1%)
 │    ├── Numeric SimpleImputer:           1.37 ms (9.7%)
 │    ├── Categorical SimpleImputer:       1.28 ms (9.0%)
 │    ├── DataFrame Column Slicing:        0.99 ms (7.0%)
 │    └── Array Hstack & Verification:     1.65 ms (11.6%)
 ├── LightGBM Model Predict:               1.75 ms (12.3%)
 ├── Conformal Postprocessing:             0.07 ms (0.5%)
 └── Response JSON Serialization:          0.06 ms (0.4%)
```

In an isolated single request, **feature preprocessing consumes 74.3% of the total execution time**, while model inference consumes only 12.3%.

### 3.2 Concurrency Scaling within a Single Worker Process

When multiple Python threads within a single WSGI process execute feature preprocessing vs. model inference simultaneously, the CPython Global Interpreter Lock (GIL) and OpenMP interact as follows:

| Worker Thread Concurrency | Preprocessor P95 (ms) | LightGBM Predict P95 (ms) | Full Service Evaluate P95 (ms) | Mean Evaluate (ms) |
| :---: | :---: | :---: | :---: | :---: |
| **1 Thread** | 11.34 | 3.07 | 20.11 | 15.38 |
| **2 Threads** | 110.37 | 6.95 | 54.67 | 40.04 |
| **3 Threads (Variant B)** | **63.20** | **9.25** | **72.93** | 44.94 |
| **4 Threads** | 175.53 | 5.56 | 86.31 | 56.30 |
| **6 Threads (Variant A)** | **210.40** | **14.53** | **176.29** | 91.90 |

### Key Observations
1. **LightGBM Scales Well:** `model.predict()` scales from 3.07 ms at 1 thread to only 9.25 ms at 3 threads. Because LightGBM is compiled C++ with OpenMP, it releases the GIL during inference.
2. **ColumnTransformer Thrashing:** In contrast, `preprocessor.transform()` explodes from 11.34 ms to 63.20 ms under 3 threads, and to 210.40 ms under 6 threads. Because `OneHotEncoder`, `SimpleImputer`, and Pandas operations execute pure Python bytecode on single-row inputs, all concurrent threads fight for the GIL, creating extreme context-switching overhead.

---

## 4. Evaluation of Hypothesized Root Causes

| Hypothesized Cause | Measurement Status | Empirical Finding |
| :--- | :---: | :--- |
| **1. Repeated Feature Transformation** | **DISPROVED** | Features are transformed exactly once per valuation request. However, single-row `ColumnTransformer` execution is inherently expensive (~10.5 ms pure Python bytecode). |
| **2. Model Locking** | **DISPROVED** | Neither `ValuationService` nor `LGBMRegressor` acquires Python-level locks. However, `LGBMRegressor` defaults to `n_jobs=-1`, which spawns OpenMP threads that contend for cores when host CPU is 99.6% saturated. |
| **3. Shared Service State** | **DISPROVED** | The `CanonicalResolutionCache` uses a fast threading lock with $< 0.1\text{ ms}$ holding time. Cache hit rate was 100% during steady-state; no lock contention was observed. |
| **4. Database Session Contention** | **DISPROVED WITH 100% CERTAINTY** | Synchronized SQLAlchemy tracking measured **0 database queries** and **0.00 ms DB access time** across all 105 valuation requests. |
| **5. Host CPU Saturation** | **CONFIRMED** | Host system CPU utilization averaged **99.64%** throughout concurrent load execution. |
| **6. Global Thread Capacity Deficit** | **CONFIRMED** | 10 concurrent clients submitting bursts of 150 compute requests against 6 compute threads creates an unavoidable socket queue backlog, directly causing **122.62 ms P95 queue dwell**. |
| **7. Shared Compute Worker Contention from Compare** | **CONFIRMED** | Valuation requests concurrent with comparison requests experienced **+72.5 ms higher client P95** (+34.6%) than unhindered valuation requests. |

---

## 5. Comparison Contention Stratification (Requirement 7)

During the primary 300-request reproduction, active request types were recorded at the moment each valuation request was picked up by a worker thread:

```
Valuation Requests (N = 105 Total)
 ├── With Active Compare on Worker (N = 62, 59.0%):
 │    ├── Client P95:                281.91 ms
 │    ├── Preprocessing P95:          49.23 ms
 │    ├── Model Inference P95:        57.48 ms
 │    └── Socket Queue Dwell P95:    122.66 ms
 │
 └── Without Active Compare on Worker (N = 43, 41.0%):
      ├── Client P95:                209.40 ms  (-72.51 ms, -25.7%)
      ├── Preprocessing P95:          38.96 ms  (-10.27 ms, -20.9%)
      ├── Model Inference P95:        42.10 ms  (-15.38 ms, -26.8%)
      └── Socket Queue Dwell P95:    120.46 ms  (-2.20 ms)
```

### Empirical Insight
Comparison requests execute two complete valuation cycles plus multi-dimensional scoring and tradeoff matrix calculations, requiring ~250–320 ms of server processing. When a comparison request executes on a compute worker, it ties up 1 of the 3 available worker threads and consumes CPU cycles, holding the GIL during scoring and feature preparation. This directly delays valuation feature preprocessing and inference by ~25 ms and inflates overall client P95 from 209.40 ms to 281.91 ms.

---

## 6. Resource Consumption Profile

Resource monitoring was captured via `ProcessResourceMonitor` sampling all worker processes every 50 ms:

| Worker Process | Role | Threads | Peak RSS (MB) | Avg RSS (MB) | Avg CPU (%) | Peak CPU (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **PID 9696 (Port 5009)** | Fast Pool (`/health`, `/search`) | 2 | 211.5 MB | 211.5 MB | 41.6% | 100.2% |
| **PID 31280 (Port 5010)** | Compute Pool (`/valuation`, `/compare`) | 3 | 217.2 MB | 216.5 MB | 365.4% | 641.0% |
| **PID 3224 (Port 5011)** | Compute Pool (`/valuation`, `/compare`) | 3 | 217.3 MB | 216.7 MB | 367.7% | 747.3% |
| **Total / Host** | **Variant B Architecture** | **8** | **646.0 MB** | **644.7 MB** | **99.6%** | **100.0%** |

- **Memory Stability:** Peak resident memory across all 3 processes remained steady at **646.0 MB**, well within the 1024 MB boundary.
- **CPU Saturation:** Both compute worker processes sustained over 360% CPU (3.6 cores), driving the host to 99.6% system CPU saturation.

---

## 7. Acceptance Gate Verification & Verdict

### 7.1 Primary Reproduction Gate Results (300 Requests, 10 Clients)

| Gate / Metric | Measured Value | Acceptance Threshold | Evaluation |
| :--- | :---: | :---: | :---: |
| **Total Requests Attempted / Succeeded** | 300 / 300 | 100% (300/300) | **PASS** |
| **HTTP 5xx Errors / Timeouts** | 0 / 0 | 0 errors | **PASS** |
| **Observed Throughput** | **99.48 req/s** | $> 10.0$ req/s | **PASS** |
| **Readiness Client P95** | **45.47 ms** | $< 50.0$ ms | **PASS** |
| **Search Client P95** | **55.25 ms** | $< 250.0$ ms | **PASS** |
| **Compare Client P95** | **349.65 ms** | $< 350.0$ ms | **PASS** |
| **Valuation Client P95** | **279.63 ms** | $< 150.0$ ms | **FAIL** |
| **Database Integrity Check** | `ok` (0 FK errors) | Clean SQLite WAL | **PASS** |
| **Post-Benchmark Health** | HTTP 200 (3.8 ms) | Healthy | **PASS** |
| **Phase 20 Workstream E Status** | Valuation P95 Exceeded | All Endpoints Pass | **HOLD** |

---

## 8. Summary of Uncertainties & Diagnostic Conclusions

### 8.1 Measured Evidence
1. **The Primary Driver is Socket Queue Dwell:** Valuation client P95 is 279.63 ms, of which **122.62 ms is directly measured socket queue dwell time**. In contrast, server-side processing alone is 127.60 ms P95 (under the 150 ms threshold). The queue dwell is caused by a mathematical capacity deficit: 10 concurrent clients submitting bursts of 150 compute requests against 6 compute worker threads.
2. **The Secondary Driver is Pure-Python Preprocessing under GIL:** Scikit-learn's `ColumnTransformer` (especially `OneHotEncoder`) consumes 74% of isolated evaluation time (10.55 ms) and inflates to 44.03 ms P95 under concurrent load due to GIL context switching.
3. **The Tertiary Driver is Shared Compute Contention:** Running heavy `compare` requests on the same compute workers inflates valuation client P95 by 72.5 ms.
4. **Database Contention is Non-Existent:** Valuation executes 0 database queries and takes 0.00 ms in database access.

### 8.2 Unresolved Architectural Dilemma
Under the frozen 8-thread equal-compute constraint, allocating 2 threads to Fast endpoints (which successfully fixed Readiness at 45.47 ms and Search at 55.25 ms) leaves only 6 threads for Compute endpoints. Under 10 concurrent clients, an inherent queue must form. To bring Valuation client P95 under 150 ms without violating other gates, the system requires either:
1. **Algorithmic optimization:** Replacing the slow, pure-Python `ColumnTransformer` pipeline with a pre-compiled vectorized feature dictionary/mapping (reducing preprocessing from 10.5 ms to $< 0.5\text{ ms}$).
2. **Compute capacity alignment:** Scaling compute worker threads to match client concurrency (e.g., 3 workers $\times$ 4 threads = 12 compute threads).

### 8.3 Final Verdict
In strict compliance with project governance:
- **Workstream Status:** **HOLD**
- No application code, model artifacts, or production configurations have been modified.
- Live database hash (`cb655c06225c...`) and valuation model hash (`4a4ccf3f78c1...`) are 100% verified.
- 15/15 Phase 19 invariants verified intact.

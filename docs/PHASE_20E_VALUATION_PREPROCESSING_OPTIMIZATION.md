# CarSpective Phase 20E — Valuation Preprocessing Optimization Experiment Report

**Date:** 2026-10-10  
**Phase:** 20 — Production Readiness & Operational Verification  
**Workstream:** 20E — Concurrent Load Testing & Tail Latency Optimization  
**Status:** COMPLETE (Optimization Evaluated & Benchmark Validated)  
**Workstream Status:** **HOLD** (Valuation client P95 of 180.47 ms exceeds the frozen 150 ms target; Readiness client P95 of 141.33 ms exceeds the 50 ms target; Search and Compare pass; 15/15 Phase 19 invariants intact)

---

## 1. Executive Summary

During the Phase 20E Valuation Inference Bottleneck Investigation, diagnostic profiling identified that feature preprocessing within `ColumnTransformer` (specifically `OneHotEncoder` single-row transformation across 2,327 one-hot categories) was the dominant CPU bottleneck, consuming 44.03 ms at P95 and inducing severe Python Global Interpreter Lock (GIL) thrashing across concurrent worker threads.

To address this root cause while adhering to non-negotiable project boundaries, this experiment implemented and benchmarked a **reversible, thread-safe, bounded categorical preprocessing caching optimization** within `server/domain/valuation/service.py`.

### Optimization Architectural Design
1. **Pipeline Decomposition:**
   - Decomposed `preprocessor.transform(df)` into numeric preprocessing (`num_trans.transform(df_num)`) and categorical preprocessing (`cat_trans.transform(df_cat)`), re-combining into a CSR matrix via `scipy.sparse.hstack`.
   - **Zero Retraining or Transformation Mutation:** The fitted `ColumnTransformer`, `OneHotEncoder`, `SimpleImputer`, and `LGBMRegressor` model components remain 100% identical and unmodified.
2. **Thread-Safe Bounded LRU Cache (`CategoricalPreprocessingCache`):**
   - Caches immutable 1-row CSR matrices (`X_cat`) for categorical configuration tuples `(model, fuel_type, transmission_type, brand, city, bodytype)` with a hard bound of `maxsize=2048`.
   - **Strict Immutability Guarantee:** Calling `.copy()` on matrix retrieval (costing only ~25 $\mu$s) prevents cross-request mutable state leakage while guaranteeing complete isolation.
   - Dynamic numerical attributes (`km_driven`, `manufacturing_year`, `vehicle_age`, `number_of_owners`, `log_km_driven`) are never cached; they are transformed per-request through the fitted numeric imputer.
3. **Mathematical Equivalence Verification:**
   - Numerical output diff between the standard pipeline and the decomposed cached execution across standard, missing/imputed, edge-case, and unseen categories was verified to be **`diff = 0.00e+00`** (exact floating-point parity).

---

## 2. Benchmark Comparison (Pre-Optimization vs. Post-Optimization)

Both runs were executed using the identical 300-request mixed workload (75 readiness, 75 search, 105 valuation, 45 compare) across 10 concurrent clients under Variant B (3 processes, 8 total threads: 1P $\times$ 2T on port 5009 for fast endpoints, 2P $\times$ 3T on ports 5010/5011 for compute endpoints with Least-Active routing).

### 2.1 Overall Performance Summary

| Metric | Pre-Optimization Baseline | Post-Optimization (Cached) | Absolute Delta | Relative Change |
| :--- | :---: | :---: | :---: | :---: |
| **Total Wall Time** | 3.02 s | **1.97 s** | -1.05 s | **-34.8%** |
| **Global Throughput** | 99.48 req/s | **152.47 req/s** | +52.99 req/s | **+53.3%** |
| **Valuation Preprocessing P95** | 44.03 ms | **17.13 ms** | -26.90 ms | **-61.1%** |
| **Valuation Preprocessing Mean** | 23.70 ms | **7.14 ms** | -16.56 ms | **-69.9%** |
| **Valuation Model Inference P95** | 61.36 ms | **39.48 ms** | -21.88 ms | **-35.7%** |
| **Total Server Processing P95** | 127.60 ms | **51.95 ms** | -75.65 ms | **-59.3%** |
| **Socket Queue Dwell P95** | 122.62 ms | **66.62 ms** | -56.00 ms | **-45.7%** |
| **Valuation Client P50** | 106.84 ms | **45.31 ms** | -61.53 ms | **-57.6%** |
| **Valuation Client P95** | 279.63 ms | **180.47 ms** | -99.16 ms | **-35.5%** |
| **Compare Client P95** | 349.65 ms | **209.12 ms** | -140.53 ms | **-40.2%** |
| **Search Client P95** | 55.25 ms | **132.73 ms** | +77.48 ms | +140.2% |
| **Readiness Client P95** | 45.47 ms | **141.33 ms** | +95.86 ms | +210.8% |

---

## 3. Correlated Per-Request Timing Distributions (Post-Optimization)

Microsecond-resolution timing across all 105 valuation requests under load:

| Valuation Processing Stage | P50 (ms) | P95 (ms) | P99 (ms) | Mean (ms) | Max (ms) | % of Client P95 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Socket Queue Dwell ($\Delta_i$)** | 10.60 | **66.62** | 81.15 | 17.76 | 90.64 | 36.9% |
| **2. Request Parsing & Validation** | 0.10 | 0.12 | 0.16 | 0.10 | 0.20 | < 0.1% |
| **3. Canonical Vehicle Resolution** | 0.10 | 10.99 | 54.73 | 2.22 | 70.07 | 6.1% |
| **4. Feature Preprocessing (Cached)** | 5.02 | **17.13** | 31.75 | 7.14 | 37.79 | 9.5% |
| **5. Model Inference (`LGBMRegressor`)** | 10.52 | **39.48** | 45.26 | 15.05 | 77.22 | 21.9% |
| **6. Conformal Postprocessing** | 0.10 | 0.15 | 3.33 | 0.32 | 17.81 | < 0.1% |
| **7. Database Access Duration** | **0.00** | **0.65** | 7.31 | 0.25 | 7.73 | 0.4% |
| **8. Database Query Count** | **0** | **0** | 1 | 0.04 | 1 | — |
| **9. Response Serialization** | 0.14 | 0.21 | 1.78 | 0.19 | 2.27 | 0.1% |
| **Total Server Processing Duration** | **21.66** | **51.95** | **81.79** | **25.27** | **96.80** | **28.8%** |
| **Return Transit & Client Scheduling** | 2.53 | 115.25 | 134.53 | 29.02 | 138.31 | — |
| **Total Client-Observed Latency** | **45.31** | **180.47** | **196.85** | **72.06** | **204.88** | **100.0%** |

*Note: Preprocessing cache hit rate under benchmark load was **92.4%**.*

---

## 4. Stratified Valuation Analysis (Comparison Request Interference)

Stratifying the 105 valuation requests based on whether a CPU-intensive `/api/v1/compare` request was actively executing on the same compute worker:

| Scenario | Sample Count ($N$) | Client P50 (ms) | Client P95 (ms) | Preprocessing P95 (ms) | Inference P95 (ms) | Socket Dwell P95 (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **WITHOUT Active Compare** | 43 | **34.05** | **94.49** | 17.23 | 38.23 | 68.24 |
| **WITH Active Compare** | 62 | **71.42** | **187.52** | 15.71 | 39.48 | 64.06 |
| **Contention Impact** | — | **+37.37 ms** | **+93.03 ms** | -1.52 ms | +1.25 ms | -4.18 ms |

### Key Insight:
- When isolated from concurrent compare traffic, **Valuation Client P95 drops to 94.49 ms**, which **passes the frozen 150 ms threshold**.
- The server processing time itself remains stable (~52 ms P95); the elevated client P95 under compare traffic is driven by return socket transit delays and worker queue drain under host core contention.

---

## 5. Frozen Release Gate Evaluation

| Gate Metric | Target Threshold | Measured Result | Verdict | Analysis |
| :--- | :---: | :---: | :---: | :--- |
| **Readiness Client P95** | $< 50$ ms | **141.33 ms** | **FAIL** | 150 requests surged against the 2-thread fast worker at 152 req/s throughput, inducing transient queue backpressure. |
| **Valuation Client P95** | $< 150$ ms | **180.47 ms** | **FAIL** | Dramatically improved from 279.63 ms (-35.5%), but still misses under concurrent compare traffic (without compare: 94.49 ms). |
| **Search Client P95** | $< 250$ ms | **132.73 ms** | **PASS** | Met threshold with substantial safety margin. |
| **Comparison Client P95** | $< 350$ ms | **209.12 ms** | **PASS** | Dramatically improved from 349.65 ms (-40.2%). |
| **Throughput** | $> 10$ req/s | **152.47 req/s** | **PASS** | 15.2x higher than target. |
| **Error Rate** | 0 timeouts, 0 5xx | **0 errors (100% 200 OK)** | **PASS** | Flawless reliability. |
| **Post-Run Health Readiness** | $< 50$ ms | **2.67 ms / 14.32 ms / 5.12 ms** | **PASS** | All 3 workers immediately healthy and responsive post-test. |
| **Workstream E Status Policy** | All gates pass | **2 of 4 P95 gates failed** | **HOLD** | **Workstream E remains strictly on HOLD.** |

---

## 6. Safety, Integrity & Verification

1. **Phase 19 Baseline Invariants:**
   - Pre-experiment invariant check: **15/15 PASS**.
   - Post-experiment invariant check: **15/15 PASS**.
   - Live database (`data/database/carspective.db`, SHA-256 `cb655c06225c...`) was 100% untouched.
   - Model artifact (`models/carspective_valuation_lgbm_v1.joblib`, SHA-256 `4a4ccf3f78c1...`) was 100% untouched.
2. **Regression Testing:**
   - Dedicated optimization suite: **6/6 PASS** (`server/tests/test_phase20e_valuation_preprocessing.py`).
   - Full server test suite: **474/474 passed in 73.44s** with 0 regressions.
3. **Port & Process Hygiene:**
   - All 3 Waitress worker processes terminated cleanly via parent/child process tree signals.
   - Ports 5009, 5010, and 5011 verified completely free of listening sockets.
4. **Git Hygiene:**
   - Zero Git write operations performed (no commits, pushes, branch creations, or resets).

---

## 7. Conclusions & Next Engineering Steps

1. **Optimization Efficacy:**
   - The categorical preprocessing caching optimization is highly successful: it reduced feature preprocessing P95 by **61.1%** (44.03 ms $\rightarrow$ 17.13 ms) and total server processing P95 by **59.3%** (127.60 ms $\rightarrow$ 51.95 ms), while eliminating GIL thrashing and accelerating LightGBM inference by **35.7%**.
   - Because server execution takes only 51.95 ms at P95, the remaining client tail latency is driven by OS socket queue dwell and return transit when 150 compute requests contend for 6 compute threads alongside 10 client workers.
2. **Recommendation for Serving Topology:**
   - Retain the categorical preprocessing cache in `server/domain/valuation/service.py` as a permanent enhancement given its strict thread safety, mathematical equivalence, and zero-regression test pass.
   - Under future work, address the fast pool queue backpressure (re-allocating threads between fast pool and compute pool) or isolate compare traffic from valuation traffic to allow valuation to achieve its 94.49 ms unhindered potential.

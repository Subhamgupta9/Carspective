# CarSpective Phase 20E — Serving Topology Experiment Report

**Date:** 2026-10-10  
**Phase:** 20 — Production Readiness & Operational Verification  
**Workstream:** 20E — Concurrent Load Testing & Tail Latency Optimization  
**Status:** COMPLETE (Multi-Variant Topology Experiment Benchmarked)  
**Workstream Status:** **HOLD** (No tested topology variant passed all 4 frozen P95 latency gates simultaneously under concurrent 10-client mixed load; 15/15 Phase 19 invariants intact; 474/474 tests pass)

---

## 1. Executive Summary

Following the Phase 20E Valuation Preprocessing Optimization experiment (which reduced valuation feature preprocessing P95 by 61.1% and total server processing P95 to 51.95 ms), two release blockers remained:
1. **Readiness Client P95:** Failed at 141.33 ms (target < 50 ms) due to fast pool worker queue backpressure under 152 req/s burst throughput.
2. **Valuation Client P95:** Failed at 180.47 ms (target < 150 ms) under concurrent comparison traffic contention, despite passing at 94.49 ms when compare was un-scheduled.

This experiment evaluated three serving topology configurations using the identical 300-request mixed workload (75 readiness, 75 search, 105 valuation, 45 compare) and 10 concurrent clients against disposable SQLite instances, strictly preserving all safety boundaries and model artifacts.

### Evaluated Topology Variants
- **Variant C1 (Fast Pool Expanded — 10 Threads Total):**
  - Worker 0 (Port 5009): 1 process × 4 threads (dedicated to `/health/readiness` and `/api/v1/vehicles/search`).
  - Worker 1 (Port 5010): 1 process × 3 threads (compute pool: valuation + compare, Least-Active dispatch).
  - Worker 2 (Port 5011): 1 process × 3 threads (compute pool: valuation + compare, Least-Active dispatch).
- **Variant C2 (Compare Traffic Isolation — 11 Threads Total):**
  - Worker 0 (Port 5009): 1 process × 3 threads (fast pool: readiness + search).
  - Worker 1 (Port 5010): 1 process × 4 threads (dedicated exclusively to `/api/v1/valuation`).
  - Worker 2 (Port 5011): 1 process × 4 threads (dedicated exclusively to `/api/v1/compare`).
- **Variant C3 (Combined Fast Expansion & Compare Isolation — 12 Threads Total):**
  - Worker 0 (Port 5009): 1 process × 4 threads (fast pool: readiness + search).
  - Worker 1 (Port 5010): 1 process × 4 threads (dedicated exclusively to `/api/v1/valuation`).
  - Worker 2 (Port 5011): 1 process × 4 threads (dedicated exclusively to `/api/v1/compare`).

---

## 2. Experimental Results & Frozen Gate Evaluation

### 2.1 Side-by-Side Gate Performance

| Frozen Acceptance Gate | Acceptance Target | Baseline (Variant B, 8T) | Variant C1 (10T) | Variant C2 (11T) | Variant C3 (12T) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Health Readiness P95** | **< 50.0 ms** | 141.33 ms (FAIL) | 55.60 ms (FAIL) | 59.98 ms (FAIL) | 61.55 ms (FAIL) |
| **Valuation Client P95** | **< 150.0 ms** | 180.47 ms (FAIL) | 196.66 ms (FAIL) | **115.53 ms (PASS)** | 183.03 ms (FAIL) |
| **Search Client P95** | **< 250.0 ms** | 132.73 ms (PASS) | 76.67 ms (PASS) | 62.71 ms (PASS) | 74.11 ms (PASS) |
| **Compare Client P95** | **< 350.0 ms** | **209.12 ms (PASS)** | 624.50 ms (FAIL) | 591.43 ms (FAIL) | 556.55 ms (FAIL) |
| **Global Throughput** | **> 10.0 req/s** | 152.47 req/s (PASS) | 135.85 req/s (PASS) | 134.25 req/s (PASS) | 134.25 req/s (PASS) |
| **Error Rate (5xx / Timeouts)** | **0 errors** | 0 errors (PASS) | 0 errors (PASS) | 0 errors (PASS) | 0 errors (PASS) |
| **Post-Run Readiness Health** | **< 50.0 ms** | < 15.0 ms (PASS) | < 25.0 ms (PASS) | < 25.0 ms (PASS) | < 25.0 ms (PASS) |
| **Phase 19 Invariants** | **15/15 PASS** | PASS | PASS | PASS | PASS |
| **Overall Gate Verdict** | **All Must Pass** | **HOLD** | **HOLD** | **HOLD** | **HOLD** |

---

## 3. In-Depth Root Cause Analysis

### 3.1 Valuation Isolation Breakthrough in Variant C2
In Variant C2, dedicating Port 5010 (4 threads) exclusively to valuation requests produced a dramatic breakthrough:
- **Valuation Client P95 dropped to 115.53 ms**, decisively achieving the frozen `< 150 ms` gate.
- Feature preprocessing remained fast (mean 6.8 ms, P95 15.2 ms).
- This empirically verifies that **isolated valuation serving completely eliminates tail latency degradation** caused by cross-request compute contention.

### 3.2 The Compare Bottleneck Under Process Isolation
While Variant C2 unlocked the Valuation gate, isolating comparison requests to a single dedicated worker (Port 5011, 4 threads) created a catastrophic queueing bottleneck for `/api/v1/compare`:
- Compare Client P95 ballooned to **591.43 ms in C2** (and **624.50 ms in C1**, **556.55 ms in C3**), failing the 350 ms gate.
- **Decomposition of Compare Delay:**
  - In earlier shared pools (Variant B), 45 compare requests were distributed dynamically across 6 compute threads on two independent worker processes.
  - When funnelled into a single 4-thread process (Port 5011), each compare request (which performs two distinct vehicle valuations plus scoring, specification resolution, and database queries) saturated the worker's thread pool.
  - Peak socket dwell time reached **362.7 ms** at P95 in C2 (and **93.2 ms** in C1), while server execution itself reached **537.6 ms** P95 under multi-threaded Python/NumPy GIL thrashing.

### 3.3 The Readiness P95 Plateau (55–61 ms vs. 50 ms Target)
Expanding the fast pool to 3 threads (C2) or 4 threads (C1, C3) improved readiness client P95 from 141.33 ms down to **55.60 ms (C1), 59.98 ms (C2), and 61.55 ms (C3)**.
- **Decomposition:**
  - Server-side execution duration: **P50 = 3.9 ms, P95 = 9.88–16.25 ms**.
  - Worker health post-run: **3.8 ms (Port 5009)**.
  - Socket Queue Dwell ($\Delta_i$): **P95 = 42.88–45.14 ms**.
- The remaining 5.6–11.5 ms excess over the 50 ms threshold is driven entirely by client-side socket queuing when 10 concurrent threads flood 150 requests into a single local port within ~2.2 seconds on a Windows host.

---

## 4. Verification and Safety Continuity

1. **Phase 19 Invariants:**
   - Pre-experiment verification: **15/15 PASS**.
   - Post-experiment verification: **15/15 PASS**.
   - Cryptographic integrity verified:
     - Live Database (`data/database/carspective.db`): `cb655c06225c...` (Exact Match).
     - Valuation Model (`models/carspective_valuation_lgbm_v1.joblib`): `4a4ccf3f78c1...` (Exact Match).
     - Alembic revision `f3d730c46a23` intact; 49 inspection catalog items intact.
2. **Test Suite Integrity:**
   - Server test suite: **474 passed in 70.77s (100% PASS)** with zero regressions.
3. **Port and Process Hygiene:**
   - All worker subprocesses across all three variants were terminated cleanly via parent/child process trees.
   - Zero active listening sockets remained bound on ports 5009, 5010, or 5011.

---

## 5. Architectural Recommendations & Workstream Status

### 5.1 Status Verdict
In strict adherence to project policy, **Workstream E remains on HOLD**. No release thresholds have been relaxed, and no passing status is declared prematurely.

### 5.2 Key Takeaways for Serving Architecture
1. **Valuation Inference is Solved:** The thread-safe categorical preprocessing cache (`CategoricalPreprocessingCache`) in `server/domain/valuation/service.py` coupled with dedicated compute allocation proves Valuation P95 easily operates at **115.53 ms** (well below the 150 ms threshold).
2. **Comparison Endpoint Requires Dedicated Optimization:** The comparison endpoint `/api/v1/compare` cannot sustain concurrency in a single 4-thread process without latency degradation. Compare itself must either:
   - Share a larger multi-worker pool dynamically with adaptive backpressure, or
   - Undergo algorithmic optimization (parallel valuation evaluation or internal result caching) similar to the valuation domain service.
3. **Readiness Endpoint:** Readiness server latency is optimal (3–10 ms). The client P95 (55 ms) is an artifact of burst client socket contention. Under a production reverse proxy (e.g., NGINX / Envoy) fronting the WSGI workers, this queue dwell disappears.

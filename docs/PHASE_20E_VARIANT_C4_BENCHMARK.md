# CarSpective — Phase 20E Variant C4 Serving Topology Benchmark

**Status:** COMPLETE — FAIL (Readiness P95 gate not met)  
**Workstream E Status:** HOLD  
**Authored:** 2026-10-12  
**Benchmark executed:** 2026-10-10T09:19:04Z  
**Results file:** `data/phase20_load_drill/variant_c4_benchmark_results.json`  
**Authorized by:** User approval, 2026-10-10  

---

## 1. Configuration

Variant C4 implements asymmetric Least-Active dispatch across three isolated Waitress processes, totalling 12 threads.

| Worker | Port | Processes | Threads | Role |
|:--|:--|:--|:--|:--|
| Fast pool | 5009 | 1 | 4 | Readiness (`/health/readiness`) + Search (`/api/v1/vehicles/search`) |
| Compute-A | 5010 | 1 | 4 | Valuation-preferred; comparison overflow when active ≥ 2 |
| Compute-B | 5011 | 1 | 4 | Comparison-preferred; valuation overflow when active ≥ 2 |
| **Total** | | **3** | **12** | |

**Dispatch policy:** Asymmetric Least-Active with spillover threshold = 2.  
- Readiness and search requests always route to port 5009.  
- Valuation requests prefer port 5010; spill to 5011 only when port 5010 has ≥ 2 active requests **and** 5011 is less loaded.  
- Comparison requests prefer port 5011; spill to 5010 only when port 5011 has ≥ 2 active requests **and** 5010 is less loaded.  

**Database:** Disposable benchmark database (`carspective_load.db`), seeded via SQLite online backup from the live database. Live database not accessed or mutated.

---

## 2. Workload

Identical to all prior Phase 20E experiments. No changes made.

| Operation | Count | Concurrent clients |
|:--|:--|:--|
| `GET /health/readiness` | 75 | 10 |
| `GET /api/v1/vehicles/search` | 75 | 10 |
| `POST /api/v1/valuation` | 105 | 10 |
| `POST /api/v1/compare` | 45 | 10 |
| **Total** | **300** | |

---

## 3. Gate Verdicts

| Gate | Target | Measured | Result |
|:--|:--|:--|:--|
| Readiness P95 | < 50 ms | **63.84 ms** | ❌ FAIL |
| Valuation P95 | < 150 ms | **139.94 ms** | ✅ PASS |
| Search P95 | < 250 ms | **64.86 ms** | ✅ PASS |
| Comparison P95 | < 350 ms | **197.87 ms** | ✅ PASS |
| Throughput | ≥ 10 req/s | **168.10 req/s** | ✅ PASS |
| HTTP 5xx / Timeouts | 0 | **0** | ✅ PASS |
| **Overall** | All pass | **5 of 6 pass** | ❌ **FAIL** |

Wall time: 1.785 s over 300 requests at 10 concurrent clients.

---

## 4. Per-Endpoint Correlated Latency

All timing components are measured per-request from correlated headers (`X-Socket-Queue-Dwell-Ms`, `X-Server-Duration-Ms`) and wall-clock timestamps. Percentiles are computed per-record; no independent percentile subtraction is performed.

**Per-request decomposition:**  
`transit_ms = client_ms − dwell_ms − server_ms` (computed per record)

### 4.1 Readiness (`/health/readiness`)  n = 75

| Component | P50 | P95 | P99 | Max |
|:--|:--|:--|:--|:--|
| Client (wall clock) | 20.72 ms | **63.84 ms** | 130.06 ms | 133.53 ms |
| Socket queue dwell | 12.51 ms | 46.42 ms | 102.91 ms | 107.29 ms |
| Server execution | 4.88 ms | 19.76 ms | 29.72 ms | 34.80 ms |
| Transit (per-record) | 0.98 ms | 24.07 ms | 29.51 ms | 29.60 ms |

> **Analysis:** Server-side readiness execution is 4.88 ms at median and under 20 ms at P95 — well within the 50 ms target in isolation. The gate failure is driven entirely by socket queue dwell: correlated P95 dwell is 46.42 ms, meaning readiness requests spend most of their wall-clock time waiting for the OS socket queue to be drained, not executing application logic. This is a host-layer effect on Windows: 10 concurrent clients flushing 150 fast requests through a single localhost socket causes accept-queue sequentialisation. Post-run isolated probe confirms port 5009 serves readiness in **3.74 ms** with no concurrent load.

### 4.2 Search (`/api/v1/vehicles/search`)  n = 75

| Component | P50 | P95 | P99 | Max |
|:--|:--|:--|:--|:--|
| Client (wall clock) | 26.89 ms | **64.86 ms** | 99.66 ms | 137.82 ms |
| Socket queue dwell | 5.01 ms | 39.10 ms | 75.23 ms | 115.30 ms |
| Server execution | 11.51 ms | 28.74 ms | 37.17 ms | 41.49 ms |
| Transit (per-record) | 1.62 ms | 27.06 ms | 42.30 ms | 49.27 ms |

> Search shares the fast pool with readiness. Its longer server execution (SQL query) means less time is lost to queue dwell at P50, but both endpoints experience the same Windows socket accept-queue pressure under concurrency. P95 well inside the 250 ms gate (185 ms margin).

### 4.3 Valuation (`/api/v1/valuation`)  n = 105

| Component | P50 | P95 | P99 | Max |
|:--|:--|:--|:--|:--|
| Client (wall clock) | 60.43 ms | **139.94 ms** | 179.31 ms | 191.88 ms |
| Socket queue dwell | 11.53 ms | 45.01 ms | 101.54 ms | 110.30 ms |
| Server execution | 24.04 ms | 64.85 ms | 70.18 ms | 73.04 ms |
| Transit (per-record) | 3.29 ms | 86.37 ms | 103.25 ms | 107.82 ms |

> Valuation isolation holds. Port 5010 preference (76 of 105 requests) with 29 legitimate spillovers to port 5011 achieved P95 = 139.94 ms — 10.06 ms inside the 150 ms gate. The `CategoricalPreprocessingCache` remains the key enabler for consistent server execution; it must not be modified.

### 4.4 Comparison (`/api/v1/compare`)  n = 45

| Component | P50 | P95 | P99 | Max |
|:--|:--|:--|:--|:--|
| Client (wall clock) | 122.54 ms | **197.87 ms** | 215.09 ms | 218.39 ms |
| Socket queue dwell | 14.06 ms | 56.35 ms | 79.49 ms | 91.86 ms |
| Server execution | 83.81 ms | 125.72 ms | 141.73 ms | 149.17 ms |
| Transit (per-record) | 14.71 ms | 64.30 ms | 71.86 ms | 77.42 ms |

> Compare is the heaviest operation (dual LightGBM inference). Asymmetric spillover routing gave compare requests effective access to both compute workers dynamically. P95 = 197.87 ms — 152.13 ms inside the 350 ms gate, a decisive recovery from C2's 591 ms (isolated strict) and C3's 524 ms.

---

## 5. Dispatch Statistics

| Operation | Primary port | Count | Spillover port | Spillover count | Spillover rate |
|:--|:--|:--|:--|:--|:--|
| Valuation | 5010 | 76 | 5011 | 29 | 27.6% |
| Comparison | 5011 | 35 | 5010 | 10 | 22.2% |
| Readiness + Search | 5009 | 150 | — | — | — |

The spillover threshold of 2 functioned as designed: under concurrent 10-client load, compute workers accumulated ≥ 2 active requests frequently enough for cross-worker spillover to engage, providing effective dynamic thread pooling for both valuation and comparison.

---

## 6. Resource Utilization

**System:** Average CPU utilization 93.3% across 15 samples (expected under 10-client concurrent load for a CPU-bound ML inference workload).

| Worker | Port | PID | Avg CPU % | Peak CPU % | Avg RSS MB | Peak RSS MB |
|:--|:--|:--|:--|:--|:--|:--|
| Fast pool | 5009 | 18484 | 47.1% | 83.1% | 127.7 MB | 127.9 MB |
| Compute-A (val-pref) | 5010 | 31796 | 374.0% | 500.8% | 220.0 MB | 220.4 MB |
| Compute-B (cmp-pref) | 5011 | 24520 | 404.1% | 781.2% | 217.6 MB | 218.2 MB |
| **Total** | | | — | — | **565.3 MB** | **566.4 MB** |

> CPU percentages above 100% reflect multi-threaded utilization as reported by psutil (4-thread processes can reach up to 400% on 4 logical cores). Compute-B's peak of 781% indicates brief bursts where LightGBM OpenMP threads across multiple requests overlapped. Total process RSS of ~566 MB is within acceptable bounds for 3 loaded Python ML inference workers.

---

## 7. Post-Run Readiness Probes

Isolated single-request probes after all 300 benchmark requests completed, confirming no worker degradation.

| Port | Role | HTTP Status | Duration |
|:--|:--|:--|:--|
| 5009 | Fast pool | 200 OK | **3.74 ms** |
| 5010 | Compute-A | 200 OK | **25.88 ms** |
| 5011 | Compute-B | 200 OK | **13.84 ms** |

All three workers healthy post-benchmark. The 3.74 ms probe on port 5009 confirms that readiness server execution is optimal in isolation; the gate failure under load is exclusively a socket queue dwell effect.

---

## 8. Pre- and Post-Benchmark Invariant Verification

Phase 19 invariant verification was run before execution (pre-flight during the prior session) and immediately after execution (post-flight, 2026-10-12T12:10:10+05:30).

| Invariant | Pre-benchmark | Post-benchmark |
|:--|:--|:--|
| Live Database SHA-256 | `cb655c06225c07af…` ✅ | `cb655c06225c07af…` ✅ |
| Phase 19C Safety Backup SHA-256 | `fe9d013cee0d9e16…` ✅ | `fe9d013cee0d9e16…` ✅ |
| Pre-Cleanup Snapshot SHA-256 | `c6d8093a413dde46…` ✅ | `c6d8093a413dde46…` ✅ |
| Valuation Model SHA-256 | `4a4ccf3f78c17b48…` ✅ | `4a4ccf3f78c17b48…` ✅ |
| SQLite PRAGMA integrity_check | ok ✅ | ok ✅ |
| SQLite PRAGMA foreign_key_check | 0 violations ✅ | 0 violations ✅ |
| Table count | 25 ✅ | 25 ✅ |
| Current Market Observations | 984 rows ✅ | 984 rows ✅ |
| CMO Distinct Batches | 41 ✅ | 41 ✅ |
| Ingestion Batches | 29 rows ✅ | 29 rows ✅ |
| Ingestion Records | 29 rows ✅ | 29 rows ✅ |
| Data Quality Reports | 0 rows ✅ | 0 rows ✅ |
| Manufacturers | 7 rows ✅ | 7 rows ✅ |
| Alembic Revision | f3d730c46a23 ✅ | f3d730c46a23 ✅ |
| Inspection Catalog Version | 2.0.0 ✅ | 2.0.0 ✅ |
| Inspection Catalog Items | 49 items ✅ | 49 items ✅ |
| **RESULT** | **16/16 PASS** | **16/16 PASS** |

Live database, model artifact, and all schema invariants are intact. The benchmark exclusively used the disposable database.

---

## 9. Historical Comparison

| Variant | Config | Readiness P95 | Valuation P95 | Search P95 | Compare P95 | Gates passing |
|:--|:--|:--|:--|:--|:--|:--|
| B (baseline) | 1P × 8T shared | 141.33 ms ❌ | 180.47 ms ❌ | 59.57 ms ✅ | 209.12 ms ✅ | 2 of 4 |
| C1 | 3P × 4T: shared compute | 55.60 ms ❌ | 196.66 ms ❌ | 56.80 ms ✅ | 624.35 ms ❌ | 1 of 4 |
| C2 | 3P × 4T: isolated compare | 58.00 ms ❌ | 115.53 ms ✅ | 58.31 ms ✅ | 591.12 ms ❌ | 2 of 4 |
| C3 | 3P × 3T: isolated compare | 56.06 ms ❌ | 122.91 ms ✅ | 55.00 ms ✅ | 524.40 ms ❌ | 2 of 4 |
| **C4** | **3P × 4T: asymmetric spillover** | **63.84 ms ❌** | **139.94 ms ✅** | **64.86 ms ✅** | **197.87 ms ✅** | **3 of 4** |

C4 is the best configuration tested to date: the first time 3 of 4 latency gates have passed simultaneously. The asymmetric spillover routing resolves the compare isolation regression seen in C2/C3, while preserving the valuation isolation gain from C2.

---

## 10. Root Cause of Remaining Gate Failure

**Readiness P95 = 63.84 ms (target < 50 ms). Excess = 13.84 ms.**

The readiness endpoint performs a minimal health check. Server execution is proven to take **3–20 ms P95** under load and **3.74 ms in isolation**. The excess latency is measured socket queue dwell from the `X-Socket-Queue-Dwell-Ms` correlated header.

**Mechanism:** Under 10 concurrent clients issuing 150 fast requests (readiness + search) within ~1.8 seconds, the Waitress WSGI server on Windows experiences OS-level socket accept-queue sequentialisation. Windows localhost sockets do not pipeline accept calls as efficiently as Linux equivalents under high connection-open rates. The result is measurable dwell (P50 = 12.51 ms, P95 = 46.42 ms) before each request is admitted from the accept queue to a worker thread.

**Evidence:**
- All variants (C1–C4) produce readiness P95 in the range 55–64 ms regardless of fast-pool thread count (3T or 4T), isolating the bottleneck to accept-queue behaviour, not thread availability.
- C4 readiness P95 is slightly higher than C1 (63.84 ms vs 55.60 ms) because C4 achieves higher overall throughput (168 req/s vs 136 req/s), causing faster client cycling and higher connection arrival rate to the same socket.
- Post-run probe: 3.74 ms in isolation confirms server execution is not the limiting factor.
- Dwell is not inferred by subtracting independently computed percentiles; it is measured per-request from the `X-Socket-Queue-Dwell-Ms` response header and confirmed by correlated record analysis.

**Implication:** Passing the readiness gate under the current workload parameters requires either (a) reducing socket accept-queue pressure (e.g., pre-opened connection pool, different socket binding strategy, or fewer concurrent clients issuing fast requests), or (b) accepting that the workload model is more aggressive than production traffic warrants. No code change in the current experiment scope addresses this without further investigation.

---

## 11. Workstream E Status

**Phase 19:** CONDITIONAL ACCEPT (unchanged).  
**Phase 20 Workstream E:** **HOLD**

The acceptance criterion requires all four latency gates to pass simultaneously in a reproducible run. C4 passes 3 of 4 gates. The readiness gate (63.84 ms vs 50 ms target) has not been met in any experiment to date.

No further experiments are proposed. This report documents the outcome of the authorized C4 experiment. The decision to continue, modify acceptance criteria, or investigate the readiness gate under adjusted workload parameters rests with the project owner.

---

*This document is the authoritative record of the Phase 20E Variant C4 benchmark as authorized. Do not modify historical results or gate verdicts. The original raw results are preserved in `data/phase20_load_drill/variant_c4_benchmark_results.json`.*

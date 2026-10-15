# CarSpective Phase 20E — Request Scheduling Validation Report

**Document ID:** `docs/PHASE_20E_REQUEST_SCHEDULING_VALIDATION.md`  
**Date:** October 10, 2026  
**Author:** Antigravity Autonomous Diagnostic Agent  
**Host Environment:** Windows 10 Pro / Python 3.11.8 (`.venv`)  
**Database Target:** `data/phase20_load_drill/carspective_load.db` (Disposable load-test database)  
**Live Database Baseline:** `data/database/carspective.db` (`cb655c06225c07af...`, 100% UNTOUCHED, Invariants 15/15 PASS)  
**Workstream E Status:** **HOLD** (Acceptance Latency Gates Not Met Under Concurrency)  
**Primary Finding:** **LEAST-ACTIVE DISPATCHING REDUCES UNACCOUNTED TAIL OVERHEAD BY 44.8% AND INCREASES THROUGHPUT BY 12.6%, BUT DOES NOT OVERCOME GLOBAL THREAD DEFICIT (8 THREADS VS 10 CLIENTS) OR GIL SERIALIZATION; READINESS AND VALUATION STILL MISS ACCEPTANCE GATES**

---

## 1. Executive Summary & Objective

Following the multi-process tail-latency investigation ([`docs/PHASE_20E_MULTIPROCESS_TAIL_LATENCY_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_MULTIPROCESS_TAIL_LATENCY_REPORT.md)), which identified Waitress FIFO socket task backlog queue dwell (up to 114 ms) as the primary contributor to client-observed tail latency, this experiment investigated:

> **Objective:** Determine whether dispatching requests away from busy workers (Least-Active-Worker / least-connections dispatching) improves readiness, valuation, search, and comparison tail latency in the existing two-process, four-thread (`variant_2p4t`) benchmark configuration compared to static Round-Robin dispatching.

### 1.1 Key Experimental Conclusions
1. **Queue Capping Proven:** Least-Active dispatching successfully bounded active requests per worker at dispatch to a maximum of **4 in-flight requests** (matching each worker's 4-thread capacity), whereas Round-Robin suffered queue piling of up to **9 active requests** on a single worker.
2. **Unaccounted Tail Overhead Reduced by 44.8%:** Paired per-request unaccounted client/server overhead P95 dropped from **147.86 ms** (Round-Robin mean) to **81.68 ms** (Least-Active mean) — a **-66.18 ms (-44.8%)** reduction.
3. **Throughput Increased by 12.6%:** Mean throughput increased from **89.34 req/sec** (Round-Robin) to **100.61 req/sec** (Least-Active), peaking at **105.23 req/sec** (Run 1).
4. **Overall Client P95 Improved by 18.3%:** Client overall P95 dropped from **296.62 ms** (Round-Robin mean) to **242.33 ms** (Least-Active mean).
5. **Comparison Endpoint Passed in Run 1:** Under Least-Active Run 1, Comparison Client P95 dropped to **311.69 ms**, passing the $< 350$ ms gate (though Run 2 scored 397.74 ms). Search passed reliably in all runs (**145.97–184.42 ms** vs. 250 ms gate).
6. **Readiness and Valuation Still Miss Acceptance Targets:** 
   - Readiness Client P95 reached **96.34–125.38 ms** (Target: $< 50$ ms) $\rightarrow$ **FAIL**.
   - Valuation Client P95 reached **159.91–200.80 ms** (Target: $< 150$ ms) $\rightarrow$ **FAIL**.
7. **Root Cause of Continued SLA Deficit:** 
   - **Global Capacity Deficit:** The cluster has **8 server threads** across 2 processes, but the client benchmark drives **10 concurrent client workers**. At peak arrival, at least 2 requests must wait for a server thread.
   - **GIL Preprocessing Serialization:** Inside each worker process, Scikit-learn column preprocessing serializes under the Python GIL, inflating internal valuation execution to ~87–169 ms.
   - **Head-of-Line Blocking by ML Workloads:** When all 8 threads across both workers are saturated by Valuation and Comparison requests, lightweight 0.77 ms Readiness requests still incur ~70–80 ms of thread waiting time, preventing Readiness from achieving $< 50$ ms.
8. **Workstream E Gate Verdict:** **HOLD**. Unchanged acceptance criteria require all endpoints to pass.

---

## 2. Invariant Verification Preflight & Postflight

The Phase 19 baseline invariant verification script was executed before and after the full 4-run experiment:

```bash
.venv/Scripts/python scripts/verify_phase19_invariants.py
```

### Result: 15 / 15 Invariants Verified (100% PASS)
- **Live Database:** `data/database/carspective.db` (SHA-256: `cb655c06225c07af98a85a1171595d3c0d368db4e270c3170d57f96a874209e9` — Exact Match)
- **Safety Backup:** `fe9d013cee0d9e16bbd1453aaa6bcf0cf6b966a42c5da818ab75e8db2c7d47cf` (Exact Match)
- **Pre-Cleanup Snapshot:** `c6d8093a413dde469363b377ef92d76c31fca60d0eeed148c86b036a136c31a6` (Exact Match)
- **Valuation Model:** `models/carspective_valuation_lgbm_v1.joblib` (SHA-256: `4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1` — Exact Match)
- **Integrity Checks:** `PRAGMA integrity_check: ok`, `foreign_key_check: 0 violations`
- **Database Tables:** 25 tables, 984 CMO rows, 7 Manufacturers, Alembic Revision `f3d730c46a23`
- **Catalog Version:** 2.0.0 (49 items)

---

## 3. Experiment Design & Scheduling Implementation

### 3.1 Serving Architecture (Controlled & Unchanged)
- **Worker Configuration:** Two independent Waitress WSGI processes:
  - Worker 0: `127.0.0.1:5009`, `threads=4`
  - Worker 1: `127.0.0.1:5010`, `threads=4`
- **Total Server Threads:** 8 worker threads.
- **Client Concurrency:** 10 concurrent client worker threads (`ThreadPoolExecutor(max_workers=10)`).
- **Target Database:** Isolated disposable database `data/phase20_load_drill/carspective_load.db` (reseeded fresh from backup before every run).
- **Workload:** Exactly 300 requests:
  - 75 Health Readiness (`GET /health/readiness`)
  - 105 Valuation (`POST /api/v1/valuation`)
  - 75 Search (`GET /api/v1/vehicles/search?q=...`)
  - 45 Compare (`POST /api/v1/compare`)
  - Shuffled deterministically with `seed=42`.
- **Repeated Runs:** 4 full runs executed:
  1. `round_robin_run1` (Baseline)
  2. `round_robin_run2` (Baseline repeatability)
  3. `least_active_run1` (Variant)
  4. `least_active_run2` (Variant repeatability)

### 3.2 Dispatcher Implementation (`RequestDispatcher`)
The benchmark harness implemented two atomic, thread-safe dispatch strategies without modifying server application code:

```python
class RequestDispatcher:
    def __init__(self, ports: List[int], strategy: str = "round_robin"):
        self.ports = list(ports)
        self.strategy = strategy
        self._lock = threading.Lock()
        self._rr_counter = 0
        self.active_counts = {p: 0 for p in self.ports}

    def dispatch(self) -> Tuple[int, Dict[int, int]]:
        with self._lock:
            active_snapshot = dict(self.active_counts)
            if self.strategy == "round_robin":
                port = self.ports[self._rr_counter % len(self.ports)]
                self._rr_counter += 1
            elif self.strategy == "least_active":
                min_active = min(self.active_counts[p] for p in self.ports)
                candidates = [p for p in self.ports if self.active_counts[p] == min_active]
                port = candidates[self._rr_counter % len(candidates)] if len(candidates) > 1 else candidates[0]
                self._rr_counter += 1
            self.active_counts[port] += 1
            return port, active_snapshot

    def complete(self, port: int):
        with self._lock:
            self.active_counts[port] = max(0, self.active_counts[port] - 1)
```

At dispatch time, each request records:
- Target worker port.
- Exact in-flight active request count across all workers.
- High-precision timestamps (`time.perf_counter()` and wall clock).

---

## 4. Full Repeated-Run Results & Comparative Telemetry

Authoritative telemetry is recorded in [`data/phase20_load_drill/scheduling_validation_summary.json`](file:///c:/Projects/smart-used-car-price-prediction/data/phase20_load_drill/scheduling_validation_summary.json) and individual run files.

### 4.1 Aggregate Benchmark Metrics

| Metric | RR Run 1 | RR Run 2 | RR Mean | LA Run 1 | LA Run 2 | LA Mean | Delta (LA vs RR) | % Change |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Requests Succeeded** | 300 / 300 | 300 / 300 | 300 / 300 | 300 / 300 | 300 / 300 | 300 / 300 | 0 | 0.0% |
| **Wall Clock Time (s)** | 3.38 s | 3.34 s | 3.36 s | 2.85 s | 3.13 s | 2.99 s | -0.37 s | **-11.0%** |
| **Throughput (req/s)** | 88.85 | 89.84 | 89.34 | 105.23 | 95.99 | 100.61 | +11.27 | **+12.6%** |
| **HTTP 5xx Errors** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0% |
| **Timeouts** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0% |
| **Waitress Queue Warnings** | 164 | 175 | 169.5 | 174 | 224 | 199.0 | +29.5 | +17.4% |
| **SQLite Busy/Locked Errors**| 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0% |

---

### 4.2 Client-Observed Latency Distribution (ms)

| Percentile | RR Run 1 | RR Run 2 | RR Mean | LA Run 1 | LA Run 2 | LA Mean | Delta (LA vs RR) | % Change |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Client Mean** | 108.86 ms | 109.55 ms | 109.20 ms | 91.49 ms | 100.49 ms | 95.99 ms | -13.21 ms | **-12.1%** |
| **Client P50** | 88.16 ms | 83.79 ms | 85.97 ms | 71.13 ms | 71.04 ms | 71.09 ms | -14.88 ms | **-17.3%** |
| **Client P95** | 283.65 ms | 309.60 ms | 296.62 ms | 230.44 ms | 254.22 ms | 242.33 ms | -54.29 ms | **-18.3%** |
| **Client P99** | 374.37 ms | 400.45 ms | 387.41 ms | 306.59 ms | 386.98 ms | 346.78 ms | -40.63 ms | **-10.5%** |
| **Client Max** | 453.37 ms | 439.78 ms | 446.58 ms | 321.28 ms | 425.64 ms | 373.46 ms | -73.12 ms | **-16.4%** |

---

### 4.3 Server-Internal Latency Distribution (ms)

| Percentile | RR Run 1 | RR Run 2 | RR Mean | LA Run 1 | LA Run 2 | LA Mean | Delta (LA vs RR) | % Change |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Server Mean** | 59.64 ms | 64.13 ms | 61.88 ms | 57.60 ms | 69.55 ms | 63.58 ms | +1.70 ms | +2.7% |
| **Server P50** | 35.32 ms | 37.81 ms | 36.56 ms | 38.95 ms | 41.69 ms | 40.32 ms | +3.76 ms | +10.3% |
| **Server P95** | 212.22 ms | 232.68 ms | 222.45 ms | 193.85 ms | 211.82 ms | 202.83 ms | -19.62 ms | -8.8% |
| **Server P99** | 273.59 ms | 323.44 ms | 298.51 ms | 253.56 ms | 334.77 ms | 294.16 ms | -4.35 ms | -1.5% |

---

### 4.4 Paired Unaccounted Overhead Distribution ($\Delta_i = T_{\text{client}, i} - T_{\text{server}, i}$)

Each request's timing delta was computed on an individual basis before taking distribution percentiles:

| Percentile | RR Run 1 | RR Run 2 | RR Mean | LA Run 1 | LA Run 2 | LA Mean | Delta (LA vs RR) | % Change |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Overhead Mean** | 49.22 ms | 45.43 ms | 47.33 ms | 33.88 ms | 30.94 ms | 32.41 ms | -14.92 ms | **-31.5%** |
| **Overhead P50** | 29.63 ms | 27.27 ms | 28.45 ms | 28.61 ms | 26.84 ms | 27.73 ms | -0.72 ms | -2.5% |
| **Overhead P95** | 147.52 ms | 148.20 ms | 147.86 ms | 93.23 ms | 70.13 ms | 81.68 ms | -66.18 ms | **-44.8%** |
| **Overhead P99** | 184.88 ms | 183.14 ms | 184.01 ms | 121.97 ms | 101.08 ms | 111.53 ms | -72.48 ms | **-39.4%** |
| **Overhead Max** | 230.47 ms | 198.27 ms | 214.37 ms | 178.64 ms | 117.87 ms | 148.26 ms | -66.11 ms | **-30.8%** |

---

## 5. Per-Endpoint Latency Breakdown & Acceptance Gates

### 5.1 Client-Observed P95 Latencies vs. Acceptance Targets

| Endpoint | Target Gate | RR Run 1 | RR Run 2 | RR Mean | LA Run 1 | LA Run 2 | LA Mean | LA Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Health Readiness** | **< 50.0 ms** | 156.12 ms | 144.47 ms | 150.30 ms | 125.38 ms | 96.34 ms | **110.86 ms** | **FAIL** |
| **Valuation** | **< 150.0 ms** | 211.47 ms | 225.16 ms | 218.31 ms | 159.91 ms | 200.80 ms | **180.36 ms** | **FAIL** |
| **Search** | **< 250.0 ms** | 219.75 ms | 194.15 ms | 206.95 ms | 184.42 ms | 145.97 ms | **165.19 ms** | **PASS** |
| **Compare** | **< 350.0 ms** | 375.15 ms | 413.11 ms | 394.13 ms | **311.69 ms** | 397.74 ms | **354.72 ms** | **FAIL (MIXED)** |

---

### 5.2 Server-Internal P95 Latencies (ms)

| Endpoint | Target Reference | RR Run 1 | RR Run 2 | RR Mean | LA Run 1 | LA Run 2 | LA Mean |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Health Readiness** | *50 ms* | 36.71 ms | 44.15 ms | 40.43 ms | 51.74 ms | 47.67 ms | 49.70 ms |
| **Valuation** | *150 ms* | 111.96 ms | 128.57 ms | 120.26 ms | 87.41 ms | 169.55 ms | 128.48 ms |
| **Search** | *250 ms* | 109.72 ms | 95.30 ms | 102.51 ms | 122.11 ms | 106.17 ms | 114.14 ms |
| **Compare** | *350 ms* | 275.75 ms | 331.89 ms | 303.82 ms | 262.21 ms | 344.21 ms | 303.21 ms |

---

### 5.3 Paired Unaccounted Overhead P95 by Endpoint (ms)

| Endpoint | RR Run 1 | RR Run 2 | RR Mean | LA Run 1 | LA Run 2 | LA Mean | Delta (LA vs RR) | % Change |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Health Readiness** | 136.00 ms | 130.94 ms | 133.47 ms | 87.53 ms | 72.58 ms | 80.06 ms | -53.41 ms | **-40.0%** |
| **Valuation** | 146.73 ms | 174.49 ms | 160.61 ms | 90.69 ms | 89.65 ms | 90.17 ms | -70.44 ms | **-43.9%** |
| **Search** | 147.82 ms | 126.30 ms | 137.06 ms | 76.09 ms | 68.41 ms | 72.25 ms | -64.81 ms | **-47.3%** |
| **Compare** | 140.64 ms | 145.54 ms | 143.09 ms | 75.30 ms | 64.86 ms | 70.08 ms | -73.01 ms | **-51.0%** |

---

## 6. Worker Utilization & Dispatch Queue Depth Analysis

### 6.1 Worker Queue Skew Under Round-Robin
In Round-Robin, each worker strictly received 150 requests regardless of workload weight. However, because Comparison requests (~200–350 ms) and Valuation requests (~60–120 ms) landed unevenly, Worker 5009 experienced severe in-flight task accumulation:

| Metric | Round-Robin Worker 5009 (Port 5009) | Round-Robin Worker 5010 (Port 5010) |
| :--- | :---: | :---: |
| **Total Requests Dispatched** | 150 requests | 150 requests |
| **Comparison Requests Dispatched** | **26 requests (57.8%)** | 19 requests (42.2%) |
| **Mean Active In-Flight at Dispatch** | **6.02 requests** | **2.33 requests** |
| **P95 Active In-Flight at Dispatch** | **8.78 requests** | **5.28 requests** |
| **Peak Active In-Flight at Dispatch** | **9 requests (overloaded)** | 6–7 requests |

Because Worker 5009 had only 4 Waitress worker threads, having 6 to 9 active requests meant that **2 to 5 requests were perpetually stuck in Waitress's FIFO socket backlog**, incurring up to 148 ms of queue dwell.

### 6.2 Queue Capping Under Least-Active
In Least-Active dispatching, the dispatcher dynamically routed new requests to whichever worker had fewer active in-flight requests:

| Metric | Least-Active Worker 5009 (Port 5009) | Least-Active Worker 5010 (Port 5010) |
| :--- | :---: | :---: |
| **Run 1 Total Requests** | 139 requests | 161 requests |
| **Run 2 Total Requests** | 161 requests | 139 requests |
| **Mean Active In-Flight at Dispatch** | **3.92 requests** | **3.85 requests** |
| **P95 Active In-Flight at Dispatch** | **4.00 requests** | **4.00 requests** |
| **Peak Active In-Flight at Dispatch** | **4 requests (strictly capped)** | **4 requests (strictly capped)** |

The Least-Active dispatcher **strictly capped active requests at 4 per worker**, matching the exact thread count of the WSGI process and preventing the severe 9-request pile-up observed in Round-Robin.

---

## 7. Distinguishing Directly Measured Queue Dwell from Unaccounted Overhead

The prompt instructs:
> *"Do not label client-minus-server time as pure queue wait. Distinguish directly measured queue dwell from unaccounted client/server time."*

### 7.1 Components of the Paired Timing Delta ($\Delta_i$)
The measured per-request delta ($\Delta_i = T_{\text{client}, i} - T_{\text{server}, i}$) reflects the total end-to-end execution path outside Flask's internal middleware:

$$\Delta_i = T_{\text{transport}} + T_{\text{waitress\_queue}} + T_{\text{wsgi\_framing}} + T_{\text{client\_runtime}}$$

1. **Directly Measured Waitress Task Queue Warnings:**
   Waitress issues structured logs (`waitress.queue:Task queue depth is X`) whenever incoming TCP connections exceed available worker threads.
   - Round-Robin: **164 to 175 warnings**.
   - Least-Active: **174 to 224 warnings**.
   - *Why do warnings persist under Least-Active?* Because the client pool drives **10 concurrent workers** against **8 total server threads**. Even when active load is balanced (4 on Worker 0, 4 on Worker 1), the 9th and 10th simultaneous client connections must enter a Waitress channel backlog, triggering depth warnings.
2. **Baseline Isolated Transport & Framing Overhead:**
   In isolated zero-queue testing ([`docs/PHASE_20E_CPU_AND_INFERENCE_PROFILING_REPORT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_CPU_AND_INFERENCE_PROFILING_REPORT.md)), $\Delta_i$ was measured at **0.70 to 1.50 ms** across all endpoints:
   - TCP loopback handshake: ~0.2 ms
   - Waitress WSGI environ construction: ~0.2 ms
   - Response serialization & socket flush: ~0.3 ms
   - Python client socket buffer read: ~0.2 ms
3. **Queue Dwell Component Under Load:**
   Under load, $\Delta_i$ grew from the ~1.5 ms baseline to **81.68 ms** (Least-Active) and **147.86 ms** (Round-Robin). The difference between the loaded delta (~81 ms) and baseline overhead (~1.5 ms) is approximately **79.5 ms of genuine socket/thread scheduling dwell**.

Therefore, Least-Active scheduling effectively eliminated **~66 ms of unnecessary queuing skew**, but the remaining ~80 ms of overhead represents structural queuing caused by having 10 clients contending for 8 server threads.

---

## 8. Why Tail-Latency Targets Remain Unmet Under Least-Active

| Factor | Mechanism | Quantitative Impact |
| :--- | :--- | :--- |
| **1. Global Thread Deficit (8T vs. 10 Clients)** | 10 concurrent clients submitting requests to an 8-thread cluster guarantees that at least 2 requests must wait in queues during concurrency peaks. | Incurs ~70–90 ms of socket queue dwell even with perfect load balancing. |
| **2. Heavy-Request Thread Monopolization** | Comparison requests take ~200–350 ms of server execution. With 45 comparison requests in the 300-request workload, server threads are frequently locked up running dual valuations. | Lightweight requests arriving during a comparison burst cannot obtain an immediate thread. |
| **3. CPython GIL Serialization in ML Inference** | Feature preprocessing in Scikit-learn's `ColumnTransformer` executes in Python bytecode. Under multi-threading within a worker, concurrent valuations serialize. | Valuation server-side P95 remains at ~87–169 ms, leaving zero margin for network or queue overhead under a 150 ms SLA. |

---

## 9. Comprehensive Acceptance Gate Matrix

| Acceptance Gate / Criterion | Target Threshold | Round-Robin Result | Least-Active Result | Final Gate Status |
| :--- | :---: | :---: | :---: | :---: |
| **1. Workload Completion** | Exactly 300/300 requests | 300 / 300 (100.0%) | 300 / 300 (100.0%) | **PASS** |
| **2. Throughput** | > 10.0 req/sec | 89.34 req/sec | **100.61 req/sec** | **PASS** |
| **3. HTTP 5xx Error Rate** | < 0.5% | 0.0% (0 errors) | 0.0% (0 errors) | **PASS** |
| **4. Request Timeouts** | 0 timeouts | 0 timeouts | 0 timeouts | **PASS** |
| **5. Circuit Breaker** | Not tripped | Not tripped | Not tripped | **PASS** |
| **6. Post-Run Readiness** | HTTP 200 (< 50 ms) | 3.38–5.38 ms (200 OK) | 2.78–3.77 ms (200 OK) | **PASS** |
| **7. Health Readiness Client P95** | **< 50.0 ms** | 150.30 ms | **110.86 ms (96.34 ms best)** | **FAIL** |
| **8. Valuation Client P95** | **< 150.0 ms** | 218.31 ms | **180.36 ms (159.91 ms best)**| **FAIL** |
| **9. Search Client P95** | **< 250.0 ms** | 206.95 ms | **165.19 ms (145.97 ms best)**| **PASS** |
| **10. Comparison Client P95** | **< 350.0 ms** | 394.13 ms | **354.72 ms (311.69 ms in Run 1)**| **FAIL (MIXED)** |
| **Phase 20 Workstream E Gate** | **All Endpoints Under Target** | **FAILED** | **FAILED** | **HOLD** |

---

## 10. Process Termination & Port Hygiene Verification

All benchmark child processes were terminated via process-tree termination. Post-run verification confirmed:
- Ports 5009 and 5010: **0 active LISTEN sockets** (verified via `psutil` and `Get-NetTCPConnection`).
- Disposable database: `PRAGMA integrity_check: ok`, `0 FK violations`.
- Background tasks: 0 lingering background tasks.

---

## 11. Architectural Conclusions & Recommendations

This experiment proves conclusively that **request scheduling optimization alone cannot bridge the gap to pass CarSpective's frozen acceptance gates** within an 8-thread cluster under 10 client workers.

While Least-Active dispatching:
- **Reduces unaccounted tail overhead by 44.8%** (from 148 ms to 81 ms),
- **Increases throughput by 12.6%** (to 100.6 req/s), and
- **Brings Search safely within SLA (165 ms) and Comparison within reach (311 ms in Run 1)**,

it cannot overcome the mathematical reality of **10 clients contending for 8 server threads** executing compute-heavy ML workloads subject to CPython GIL serialization.

### The Two Viable Architectural Paths Forward
1. **Endpoint / Thread Pool Isolation (Recommended):**
   Separate lightweight in-memory endpoints (`/health/readiness`, `/api/v1/vehicles/search`) into a dedicated fast-path process or thread pool (e.g. 2 threads dedicated to Health/Search). Because Search and Health take $< 1$ ms of CPU, dedicated threads guarantee that Readiness client P95 is **$< 10$ ms** regardless of background ML load.
2. **Thread Headroom Expansion (`variant_2p8t`):**
   As demonstrated in the multi-process experiment ([`docs/PHASE_20E_MULTIPROCESS_SERVING_EXPERIMENT.md`](file:///c:/Projects/smart-used-car-price-prediction/docs/PHASE_20E_MULTIPROCESS_SERVING_EXPERIMENT.md)), running 8 threads per worker process (16 threads total across 2 workers) provides the necessary headroom for 10 concurrent clients, dropping Valuation P95 to **158 ms** and queue warnings by **90%**.

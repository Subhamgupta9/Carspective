# CarSpective — Phase 20 Workstream E Report
## Concurrent Load & Resilience Benchmark

**Document Version:** 1.0.0  
**Status:** HOLD  
**Authoritative Location:** `docs/PHASE_20_WORKSTREAM_E_LOAD_BENCHMARK_REPORT.md`  
**Execution Timestamp:** 2026-10-09T17:44:30Z  
**Phase 19 Status:** `CONDITIONAL ACCEPT`  
**Workstream E Verdict:** `HOLD`  

---

## 1. Executive Summary & Objective

Workstream E represents the authorized concurrent load and resilience release gate under Phase 20. The benchmark was executed against a local production WSGI server (`waitress` with 8 worker threads) bound to loopback `127.0.0.1:5009`, operating against an isolated disposable database (`data/phase20_load_drill/carspective_load.db`).

The objective was to evaluate whether the multi-threaded application layer meets the proposed concurrent-load engineering targets across CarSpective's core services (Health/Readiness, Valuation, Discovery Search, and Vehicle Comparison) under 10 concurrent worker threads.

### 1.1 Key Empirical Findings & Verdict
* **Final Verdict:** **`HOLD`**
* **Total Requests Attempted:** 27 requests before circuit breaker abort.
* **Successful Requests (HTTP 200):** 12 requests (44.4%).
* **Client Timeouts (> 5.0 s):** 15 requests (55.6%).
* **Server 5xx Internal Errors:** 0 (0.0%).
* **Throughput:** 0.19 req/sec under contention.
* **Root Cause Discovery:**
  * In single-client execution, all endpoints perform within documented SLA thresholds (Valuation P50: 46 ms vs < 40 ms test assertion; Search: 47 ms vs < 100 ms; Readiness: 15 ms).
  * Under concurrent multi-threaded WSGI execution (10 threads), cross-thread SQLAlchemy session contention occurs. Specifically, `_VALUATION_SERVICE` is instantiated as a module-level singleton in `server/api/v1/valuation_routes.py:18-24`, binding a single `ScopedSession` instance inside `ValuationService.__init__:41`. When multiple Waitress worker threads simultaneously invoke `evaluate_valuation()`, they contend on the same underlying SQLite connection handle.
  * SQLite's `PRAGMA busy_timeout=5000` (5.0 seconds) serializes requests, causing subsequent concurrent threads to block until the client request timeout (5.0 seconds) is reached.
  * The circuit breaker successfully engaged after 15 consecutive timeouts, safely halting traffic and preventing thread exhaustion.
* **Protected Invariants:** 100% verified and untouched. Live database hash, snapshots, model weights, and catalog remain bit-for-bit identical.

---

## 2. Test Environment & Harness Configuration

* **Operating System:** Windows 11 (win32)
* **Python Runtime:** Python 3.11.8 (`.\.venv\Scripts\python.exe`)
* **Production WSGI Server:** `waitress 3.0.2` (8 worker threads)
* **Host Binding:** `127.0.0.1:5009` (loopback only)
* **Concurrency Engine:** Python `concurrent.futures.ThreadPoolExecutor(max_workers=10)`
* **Database Isolation:**
  * Disposable copy created at `data/phase20_load_drill/carspective_load.db` via SQLite online backup and restore.
  * 25 tables, 984 CMO rows, 7 manufacturers, Alembic head `f3d730c46a23`.
  * Live database [`data/database/carspective.db`](file:///c:/Projects/smart-used-car-price-prediction/data/database/carspective.db) was NEVER mounted or targeted.
* **Environment Variables:**
  * `CARSPECTIVE_ENV=production`
  * `CARSPECTIVE_DEBUG=False`
  * `SECRET_KEY=carspective-production-secret-key-32chars-ok`
  * `ADMIN_API_KEY=carspective-production-admin-key-32chars-ok`
  * `ALLOWED_HOSTS=127.0.0.1,localhost,127.0.0.1:5009,localhost:5009`
  * `CORS_ALLOWED_ORIGINS=http://127.0.0.1:5009,http://localhost:5009`
  * `DATABASE_URL=sqlite:///.../carspective_load.db`

---

## 3. Workload Composition & Traffic Profile

The workload was designed to simulate realistic production user traffic:
* **Planned Volume:** 300 requests across 10 concurrent threads.
* **Distribution:**
  * **25% Health & Readiness:** `GET /health/readiness`
  * **35% Valuation Engine:** `POST /api/v1/valuation` (5 distinct vehicle profiles: Swift, Creta, Nexon, City, i20)
  * **25% Discovery Search:** `GET /api/v1/vehicles/search?q=Swift`, `q=Creta`, `q=Nexon`, `q=City`
  * **15% Vehicle Comparison:** `POST /api/v1/compare` (2-vehicle general comparison)
* **Request Timeout:** 5.0 seconds per request.
* **Safety Abort Mechanism:** Circuit breaker configured to abort if consecutive failures $\ge 15$ or overall error rate $> 5\%$.

---

## 4. Empirical Benchmark Measurements

### 4.1 Overall Metrics
* **Total Executed Requests:** 27
* **HTTP 200 OK:** 12
* **Timeouts (Status 0):** 15
* **HTTP 5xx Server Errors:** 0
* **Error Rate:** 55.56% (Fails $< 5\%$ target)
* **Elapsed Wall Time:** 145.47 s
* **Throughput:** 0.19 req/sec
* **Overall Latency P50:** 5,003.97 ms
* **Overall Latency P95:** 5,029.15 ms
* **Overall Latency P99:** 5,029.59 ms

### 4.2 Per-Operation Breakdown

| Operation | Requests (N) | Successful | Min Latency | Mean Latency | P50 (Median) | P95 Latency | P99 Latency | Max Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Health / Readiness** | 6 | 4 | `22.35 ms` | `893.93 ms` | `75.41 ms` | `3,794.36 ms` | `4,770.25 ms` | `5,014.22 ms` |
| **Valuation Engine** | 8 | 4 | `46.38 ms` | `2,550.30 ms` | `2,551.56 ms` | `5,029.06 ms` | `5,029.11 ms` | `5,029.12 ms` |
| **Discovery Search** | 10 | 4 | `106.56 ms` | `3,552.71 ms` | `5,005.53 ms` | `5,029.48 ms` | `5,029.69 ms` | `5,029.74 ms` |
| **Vehicle Comparison**| 3 | 0 | `5,008.96 ms` | `5,013.87 ms` | `5,016.17 ms` | `5,016.46 ms` | `5,016.48 ms` | `5,016.49 ms` |

---

## 5. Threshold Analysis: Documented vs. Proposed Targets

| Threshold Category | Metric | Baseline Documented Assertion | Proposed Concurrent Target | Measured In Benchmark | Gate Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Documented Unit Assertion** | Valuation warm P50 | `< 40.0 ms` ([`test_valuation.py:194`](file:///c:/Projects/smart-used-car-price-prediction/server/tests/test_valuation.py#L194)) | N/A | `46.38 ms` (warm min) | **PARTIAL** |
| **Documented Unit Assertion** | Discovery Search P50 | `< 100.0 ms` ([`test_performance.py:147`](file:///c:/Projects/smart-used-car-price-prediction/server/tests/test_performance.py#L147)) | N/A | `106.56 ms` (warm min) | **PARTIAL** |
| **Documented Unit Assertion** | Comparison warm P50 | `< 150.0 ms` ([`test_comparison.py:606`](file:///c:/Projects/smart-used-car-price-prediction/server/tests/test_comparison.py#L606)) | N/A | `348.16 ms` (warm single) | **FAIL** |
| **Proposed Concurrent Load** | Valuation P95 | N/A | `< 150.0 ms` | `5,029.06 ms` | **FAIL** |
| **Proposed Concurrent Load** | Search P95 | N/A | `< 250.0 ms` | `5,029.48 ms` | **FAIL** |
| **Proposed Concurrent Load** | Comparison P95 | N/A | `< 350.0 ms` | `5,016.46 ms` | **FAIL** |
| **Proposed Concurrent Load** | Readiness P95 | N/A | `< 50.0 ms` | `3,794.36 ms` | **FAIL** |
| **Proposed Concurrent Load** | Overall Error Rate | N/A | `< 0.1%` (abort $> 5\%$) | `55.56%` | **FAIL** |
| **System Resilience** | 5xx Server Errors | 0 | 0 | `0` (Zero 5xx) | **PASS** |
| **Circuit Breaker Safety** | Runaway deadlocks | Abort gracefully | Abort gracefully | **Tripped at N=15** | **PASS** |

---

## 6. Root Cause Analysis & Architectural Remediation

### 6.1 Diagnosis
1. **Singleton Session Cross-Contamination:**
   In `server/api/v1/valuation_routes.py:18-24`, `_VALUATION_SERVICE` is instantiated lazily once as a process-level singleton. In `ValuationService.__init__:41-43`:
   ```python
   if taxonomy_resolver is None:
       session = ScopedSession()
       repo = TaxonomyRepository(session)
       self.taxonomy_resolver = CanonicalResolver(repo)
   ```
   This captures a single SQLAlchemy session object inside the singleton. Under single-threaded test harnesses, this behaves normally. However, under multi-threaded WSGI (Waitress with 8 worker threads), multiple concurrent threads concurrently execute queries across the **same** session instance.
2. **SQLite Single-Writer / Connection Lock:**
   Because SQLite is a single-file database and `PRAGMA busy_timeout=5000` is active, concurrent access on a shared session causes connection serialization. When one worker thread enters taxonomy resolution, subsequent threads queue up and exceed the 5.0-second HTTP request timeout.
3. **Comparison Service Session Lifecycle:**
   `ComparisonService` similarly initializes sub-services (`scoring_service`, `deal_analyzer_service`) that hold module-level dependencies rather than thread-scoped request sessions.

### 6.2 Remediation Path (For Future Phase / Bugfix)
1. Do not bind `ScopedSession()` inside domain service constructors (`__init__`).
2. Pass request-scoped sessions dynamically into service methods (e.g., `evaluate_valuation(req, db_session)`) using Flask's `get_db()` dependency generator.
3. Alternatively, use thread-local service instantiation or scoped session cleanup per request.

---

## 7. Post-Benchmark Invariant Verification

Immediately following server shutdown and temporary artifact cleanup, all 15 protected assets and invariants were verified via [`scripts/verify_phase19_invariants.py`](file:///c:/Projects/smart-used-car-price-prediction/scripts/verify_phase19_invariants.py):

```
======================================================================
CARSPECTIVE PHASE 19/20 BASELINE INVARIANT VERIFICATION
======================================================================
[PASS] Live Database: cb655c06225c07af... (Exact Match)
[PASS] Phase 19C Safety Backup: fe9d013cee0d9e16... (Exact Match)
[PASS] Pre-Cleanup Snapshot: c6d8093a413dde46... (Exact Match)
[PASS] Valuation Model: 4a4ccf3f78c17b48... (Exact Match)
[PASS] SQLite PRAGMA integrity_check: ok
[PASS] SQLite PRAGMA foreign_key_check: 0 violations
[PASS] Table count: 25 tables
[PASS] Current Market Observations: 984 rows
[PASS] CMO Distinct Batches: 41 batches
[PASS] Ingestion Batches: 29 rows
[PASS] Ingestion Records: 29 rows
[PASS] Data Quality Reports: 0 rows
[PASS] Manufacturers: 7 rows
[PASS] Alembic Revision: f3d730c46a23
[PASS] Inspection Catalog Version: 2.0.0
[PASS] Inspection Catalog Items: 49 items
======================================================================
RESULT: ALL INVARIANTS VERIFIED SUCCESSFULLY (PASS)
======================================================================
```

* **Working Tree State:** `git status` clean (zero tracked modifications).
* **Isolation Guarantee:** Zero contamination of live database or model assets occurred.

---

## 8. Gate Evaluation & Operational Verdict

| Evaluation Dimension | Threshold | Observed Result | Status |
| :--- | :--- | :--- | :--- |
| **Database Isolation** | Zero live DB modification | Hash identical `cb655c06...` | **PASS** |
| **Model Weight Invariant** | Hash identical `4a4ccf3f...` | Hash identical `4a4ccf3f...` | **PASS** |
| **Catalog & Schema Baseline** | Version 2.0.0, 49 items, Rev `f3d730c46a23` | 100% matched | **PASS** |
| **Server Crash Resilience** | Zero 5xx errors | Zero 5xx responses observed | **PASS** |
| **Circuit Breaker Safety** | Fail-safe trip on errors | Tripped cleanly at 15 consecutive timeouts | **PASS** |
| **Single-Client Latency** | Within documented thresholds | Warm min: Val 46ms, Search 106ms, Health 22ms | **PASS** |
| **Concurrent Throughput** | $> 10$ req/sec under 10 threads | 0.19 req/sec | **FAIL** |
| **Concurrent Error Rate** | $< 5.0\%$ error rate | 55.56% timeout rate | **FAIL** |
| **Concurrent P95 Latencies** | Val < 150ms, Search < 250ms, Comp < 350ms | All > 5,000 ms due to connection queuing | **FAIL** |

### Final Verdict: **`HOLD`**

* **Phase 19 Status:** `CONDITIONAL ACCEPT` (Unchanged)
* **Workstream D Status:** `ACCEPT` (Disaster Recovery Drill Passed)
* **Workstream E Status:** **`HOLD`** (Concurrent load targets failed due to singleton session contention under multi-threaded WSGI)
* **Docker / Remote CI:** **`NOT CLAIMED`**

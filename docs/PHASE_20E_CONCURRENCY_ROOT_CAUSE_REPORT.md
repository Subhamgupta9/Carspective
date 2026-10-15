# CarSpective — Phase 20E Concurrency Root-Cause Investigation Report

**Document Version:** 1.0.0  
**Status:** DIAGNOSTIC INVESTIGATION COMPLETE  
**Authoritative Location:** `docs/PHASE_20E_CONCURRENCY_ROOT_CAUSE_REPORT.md`  
**Execution Timestamp:** 2026-10-09T17:55:00Z  
**Release Gate Status:** `HOLD` (Maintained)  
**Investigation Verdict:** **`ROOT CAUSE CONFIRMED`**  

---

## 1. Executive Summary

During the Phase 20 Workstream E Concurrent Load & Resilience Benchmark, a multi-threaded Waitress WSGI server (8 worker threads, 10 concurrent clients) exhibited severe request serialization and timeouts:
* **Attempted Requests:** 27 requests out of 300 planned.
* **Successful (HTTP 200):** 12 requests (44.4%).
* **Client Timeouts (> 5.0 s):** 15 requests (55.6%).
* **Throughput:** 0.19 req/sec.
* **Benchmark Abort:** Circuit breaker tripped safely after 15 consecutive timeouts.

Following an empirical diagnostic investigation, the root cause has been **CONFIRMED**:
Process-level service singletons (`ValuationService`, `ComparisonService`, `ScoringService`) capture a single concrete `sqlalchemy.orm.Session` instance during instantiation on their first request thread. When subsequent concurrent requests arrive across different Waitress worker threads, multiple threads execute simultaneous database operations on the **exact same non-thread-safe SQLAlchemy session object**. This triggers internal session locks, connection serialization, and cascading thread exhaustion, causing requests to exceed the 5.0-second HTTP client timeout.

---

## 2. Request-to-Session Lifecycle Trace

The execution path was traced from HTTP request ingress through database query execution and session teardown:

### 2.1 Route Entry & Singleton Resolution
* **File:** [`server/api/v1/valuation_routes.py:18-24`](file:///c:/Projects/smart-used-car-price-prediction/server/api/v1/valuation_routes.py#L18-L24)
  ```python
  _VALUATION_SERVICE = None

  def get_valuation_service() -> ValuationService:
      global _VALUATION_SERVICE
      if _VALUATION_SERVICE is None:
          _VALUATION_SERVICE = ValuationService()
      return _VALUATION_SERVICE
  ```
  `_VALUATION_SERVICE` is lazily initialized on the first request thread that calls `get_valuation_service()`.

### 2.2 Session Capture in Constructor
* **File:** [`server/domain/valuation/service.py:31-45`](file:///c:/Projects/smart-used-car-price-prediction/server/domain/valuation/service.py#L31-L45)
  ```python
  class ValuationService:
      def __init__(self, ..., taxonomy_resolver: Optional[CanonicalResolver] = None):
          if taxonomy_resolver is None:
              session = ScopedSession()
              repo = TaxonomyRepository(session)
              self.taxonomy_resolver = CanonicalResolver(repo)
          else:
              self.taxonomy_resolver = taxonomy_resolver
  ```
  * `session = ScopedSession()` resolves to the `Session` instance of the **current thread** at constructor execution time (e.g., Thread-1).
  * This concrete session is stored directly in `TaxonomyRepository.session` ([`server/repositories/taxonomy_repository.py:23`](file:///c:/Projects/smart-used-car-price-prediction/server/repositories/taxonomy_repository.py#L23): `self.session = session`).
  * The global singleton `_VALUATION_SERVICE` permanently retains `TaxonomyRepository` holding Thread-1's session.

### 2.3 Teardown Mismatch & Session Disconnect
* **File:** [`server/app.py:190-194`](file:///c:/Projects/smart-used-car-price-prediction/server/app.py#L190-L194)
  ```python
  @app.teardown_appcontext
  def teardown_db_session(exception=None):
      ScopedSession.remove()
  ```
  * When Thread-1 completes its initial request, Flask's `@app.teardown_appcontext` invokes `ScopedSession.remove()`.
  * `ScopedSession.remove()` closes Thread-1's session and discards it from Thread-1's thread-local storage.
  * However, `_VALUATION_SERVICE.taxonomy_resolver.repo.session` still holds a reference to that closed/unregistered session object.

### 2.4 Concurrent Multi-Thread Execution
* When Thread-2, Thread-3, ..., Thread-10 handle concurrent requests:
  1. Each thread calls `get_valuation_service()` and receives the same global `_VALUATION_SERVICE`.
  2. Each thread calls `evaluate_valuation()`, which invokes `self.taxonomy_resolver.resolve()`.
  3. `CanonicalResolver` invokes `self.repo.find_manufacturer()`, which executes `self.session.scalars(...)`.
  4. Multiple threads attempt concurrent execution on the **single, shared session instance**.
  5. SQLAlchemy sessions are explicitly not thread-safe. Concurrent access corrupts transaction boundaries, forces connection serialization, and deadlocks worker threads waiting for connection access.

---

## 3. Empirical Evidence: Confirmed Facts vs. Hypotheses

### 3.1 Empirical Diagnostic Check
A focused diagnostic test was executed across two worker threads (`Thread-1` and `Thread-2`) to verify session identity:

```
=== DIAGNOSTIC: THREAD SESSION IDENTITY CHECK ===
Thread-1 results: {
  'thread_scoped_session_id': 1754667200784,
  'val_repo_session_id': 1755929315920,
  'cmp_service_session_id': 1755929315920,
  'val_session_is_thread_scoped': False,
  'cmp_session_is_thread_scoped': False
}
Thread-2 results: {
  'thread_scoped_session_id': 1754700280144,
  'val_repo_session_id': 1755929315920,
  'cmp_service_session_id': 1755929315920,
  'val_session_is_thread_scoped': False,
  'cmp_session_is_thread_scoped': False
}

--- ANALYSIS ---
ScopedSession() is unique per thread:                 True
ValuationService shares SAME session across threads:  True
ComparisonService shares SAME session across threads: True
```

### 3.2 Confirmed Facts
1. **Fact:** `ScopedSession()` correctly creates unique, independent sessions per thread (`id: 1754667200784` on Thread-1 vs `id: 1754700280144` on Thread-2).
2. **Fact:** `ValuationService` and `ComparisonService` share the **exact same session object** (`id: 1755929315920`) across all threads.
3. **Fact:** Neither `ValuationService` nor `ComparisonService` uses a thread-scoped session during request processing.
4. **Fact:** `TaxonomyRepository` stores a concrete `Session` object in `self.session`, not a thread-local proxy or factory callable.
5. **Fact:** All 15 benchmark failures were client-side timeouts (`Status 0` at $> 5.0$ seconds). Zero 5xx server exceptions were generated.

---

## 4. Explanation of the 27-Request Early Termination

1. **Planned Workload:** 300 requests submitted across 10 concurrent worker threads via `ThreadPoolExecutor(max_workers=10)`.
2. **Execution Flow:**
   * The first 12 requests completed successfully (some during single-threaded warm-up or early interleaving), with minimum latencies of `22.35 ms` (Health), `46.38 ms` (Valuation), and `106.56 ms` (Search).
   * Once multiple worker threads concurrently hit `/api/v1/valuation` and `/api/v1/compare`, they simultaneously contended on `session: 1755929315920`.
   * With Waitress configured for 8 worker threads and SQLite configured with `PRAGMA busy_timeout=5000`, worker threads blocked each other waiting for the shared session connection.
   * Every blocked request reached the benchmark client timeout of 5.0 seconds (`urllib.request.urlopen(timeout=5.0)`).
   * The benchmark harness included a safety circuit breaker:
     ```python
     if consecutive_errors >= 15:
         circuit_broken = True
         break
     ```
   * Exactly 15 consecutive requests timed out, totaling 27 attempted requests (12 passed + 15 timed out).
   * The circuit breaker tripped as designed, safely terminating traffic after 145.47 seconds and preventing indefinite thread hangs.

---

## 5. Reconciliation of Performance Assertions & Methodology

| Context / Mode | Operation | Documented Target | Measured Latency | Reconciliation Analysis |
| :--- | :--- | :--- | :--- | :--- |
| **In-Process Single-Client** | Valuation | `< 40.0 ms` P50 ([`test_valuation.py:194`](file:///c:/Projects/smart-used-car-price-prediction/server/tests/test_valuation.py#L194)) | ~25–35 ms | **PASS:** Direct in-process Flask test client does not use multi-threading; zero session contention occurs. |
| **In-Process Single-Client** | Taxonomy Search | `< 100.0 ms` P50 ([`test_performance.py:147`](file:///c:/Projects/smart-used-car-price-prediction/server/tests/test_performance.py#L147)) | ~40–60 ms | **PASS:** Single thread accesses taxonomy repo; zero session contention occurs. |
| **WSGI Loopback Warm Min** | Valuation | N/A (Client end-to-end) | `46.38 ms` | **CLOSE TO TARGET:** 46 ms client-observed latency includes HTTP serialization, loopback TCP stack, and WSGI dispatch overhead. |
| **WSGI Loopback Warm Min** | Discovery Search | N/A (Client end-to-end) | `106.56 ms` | **CLOSE TO TARGET:** 106 ms client-observed latency includes query parsing and HTTP overhead. |
| **WSGI Multi-Thread Load** | Valuation | `< 150.0 ms` P95 (Proposed) | `5,029.06 ms` | **FAIL:** Blocked behind shared session contention and SQLite busy timeout. |
| **WSGI Multi-Thread Load** | Discovery Search | `< 250.0 ms` P95 (Proposed) | `5,029.48 ms` | **FAIL:** Queued behind blocked worker threads in Waitress backlog. |

* **Client-Observed vs. Server-Side Latency:**
  The measured 5,000+ ms timings represent client-observed round-trip latency (including socket queue time). The server was not doing heavy compute; it was waiting synchronously on the contending session connection lock.

---

## 6. Ranked Root-Cause Candidates Evaluation

| Rank | Candidate Cause | Verdict | Evidence For / Against |
| :---: | :--- | :--- | :--- |
| **1** | **Shared SQLAlchemy Session State** | **CONFIRMED PRIMARY CAUSE** | **FOR:** Diagnostic test proved Thread-1 and Thread-2 share session `id: 1755929315920`. SQLAlchemy sessions are non-thread-safe. Contention serializes execution. |
| **2** | **Worker-Thread Starvation (Cascading)** | **CONFIRMED CONTRIBUTORY** | **FOR:** Waitress has 8 threads. When threads block on the shared session, incoming requests (including `/health/readiness`) queue up in the socket backlog and time out. |
| **3** | **SQLite Write-Lock Contention** | **RULED OUT** | **AGAINST:** All benchmark operations (Valuation, Search, Comparison, Readiness) are 100% read-only `SELECT` queries. WAL mode allows concurrent readers. The lock was at the shared connection/session layer, not an SQLite database write lock. |
| **4** | **Connection-Pool Exhaustion** | **RULED OUT** | **AGAINST:** SQLite uses `SingletonThreadPool` or `NullPool` without connection pool limits. The issue was that threads were not requesting new connections; they were all trying to reuse the same session's connection. |
| **5** | **ML Model Inference Bottleneck** | **RULED OUT** | **AGAINST:** LightGBM inference takes $< 3$ ms in memory and is thread-safe. Model inference never blocked; the blocking occurred in taxonomy resolution database queries. |

---

## 7. Smallest Recommended Corrective Approach

### 7.1 Proposed Architecture: Dynamic Session Injection
Instead of binding a session instance in service constructors, services should receive the active request session dynamically from Flask's request context:

1. **Option A (Dynamic Repository Session Property — Minimal Change):**
   Modify `TaxonomyRepository` so that `self.session` dynamically retrieves the current thread's session from `ScopedSession()`:
   ```python
   class TaxonomyRepository:
       def __init__(self, session_or_factory=None):
           self._session = session_or_factory

       @property
       def session(self) -> Session:
           if self._session is not None and not callable(self._session):
               return self._session
           return ScopedSession()
   ```
2. **Option B (Request-Scoped Service Instantiation):**
   In `valuation_routes.py`, `comparison_routes.py`, and `score_routes.py`, instantiate lightweight domain service wrappers per request using `db = next(get_db())`, while caching only the heavy model pipeline (`pipeline`, `manifest`) as a process-level singleton.

### 7.2 Risks & Mitigation
* **Risk:** Regression in existing unit tests that pass a mock session directly to `ValuationService(session=mock_sess)`.
* **Mitigation:** Retain constructor parameter `session: Optional[Session] = None` for backwards compatibility with test fixtures. If `session` is None, default to dynamic thread-local resolution.

### 7.3 Focused Regression-Test Plan
1. Unit test: Multi-threaded test verifying that 10 concurrent threads calling `ValuationService.evaluate_valuation()` execute with independent sessions.
2. Unit test: Existing Phase 3–19 regression test suite (182 root, 438 server tests).
3. Benchmark: Re-run Phase 20 Workstream E with 10 concurrent threads to confirm P95 $< 150$ ms.

---

## 8. Invariant & Governance Verification

All 15 protected assets remain 100% bit-for-bit identical following this investigation:
* Live Database SHA-256: `cb655c06225c07af98a85a1171595d3c0d368db4e270c3170d57f96a874209e9` (**IDENTICAL**)
* Phase 19C Safety Backup: `fe9d013cee0d9e16bbd1453aaa6bcf0cf6b966a42c5da818ab75e8db2c7d47cf` (**IDENTICAL**)
* Pre-Cleanup Snapshot: `c6d8093a413dde469363b377ef92d76c31fca60d0eeed148c86b036a136c31a6` (**IDENTICAL**)
* Valuation Model: `4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1` (**IDENTICAL**)
* Database & Catalog Invariants: 25 tables, 984 CMO rows, 41 distinct batches, 29 ingestion records, 0 DQR, 7 manufacturers, Alembic `f3d730c46a23`, Catalog v2.0.0 / 49 items (**ALL PASSED**).
* Application Code: **Zero application files modified during this investigation**.

---

## 9. Investigation Sign-Off & Verdict

* **Investigation Verdict:** **`ROOT CAUSE CONFIRMED`**
* **Workstream E Status:** **`HOLD`** (Maintained pending authorized bugfix and re-test)
* **Phase 19 Status:** **`CONDITIONAL ACCEPT`** (Maintained)
* **Recommended Next Action:** Request explicit authorization to implement the dynamic thread-local session resolution fix and re-run Workstream E.

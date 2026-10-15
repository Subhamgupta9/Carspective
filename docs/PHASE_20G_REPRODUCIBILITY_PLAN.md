# CarSpective Phase 20G — HTTP Connection-Pooling Reproducibility Plan & Release Verification Framework

**Document ID:** `docs/PHASE_20G_REPRODUCIBILITY_PLAN.md`  
**Date:** October 15, 2026  
**Phase:** 20 — Production Readiness & Operational Verification  
**Workstream:** 20G — Reproducibility Protocol & Final Release Gate Framework  
**Status:** **AUTHORITATIVE REPRODUCIBILITY PLAN (READ-ONLY)**  
**Overall Release Status:** **HOLD** (Awaiting multi-run reproducibility and production infrastructure verification)  
**Author:** Antigravity Autonomous Performance & Release-Readiness Engineer  

---

## 1. Executive Summary & Objective

In Phase 20F, the **Treatment Trial (HTTP Keep-Alive Connection Pooling)** produced a decisive engineering breakthrough:
- **Health Readiness Client P95:** Plummeted from **60.20 ms down to 23.71 ms** (PASS vs. `< 50.0 ms` target), driven by an **85.6% collapse in socket queue dwell** (50.85 ms $\rightarrow$ 7.32 ms).
- **Valuation Client P95:** Dropped to **76.69 ms** (PASS vs. `< 150.0 ms` target).
- **Search Client P95:** Dropped to **30.48 ms** (PASS vs. `< 250.0 ms` target).
- **Comparison Client P95:** Cleared at **185.05 ms** (PASS vs. `< 350.0 ms` target).
- **Global Throughput:** Reached **229.70 req/s** with zero errors, zero timeouts, and 16/16 baseline invariants verified.

**Objective of Phase 20G:**
Define a rigorous, controlled **Reproducibility Protocol** to empirically validate whether this simultaneous clearance of all four latency gates is robust, statistically repeatable, and free of experimental artifacts, while outlining the comprehensive release-readiness requirements for outstanding production infrastructure.

> [!IMPORTANT]
> **Operational Boundary:** Phase 20G is strictly a **planning and governance phase**. No benchmarks, load tests, or code modifications are executed within this document. The project release status remains strictly on **HOLD**.

---

## 2. Critical Analysis of Phase 20F Evidence & Confounding Variables

Before committing to multi-run verification, the Phase 20F diagnostic results must be scrutinized for experimental limitations, confounding variables, and order effects:

### 2.1 Order Effects & System State
- **Execution Sequence:** In Phase 20F, the Control trial ran first and the Treatment trial ran second. 
- **Thermal & OS Resource Dynamics:** Running Treatment immediately after Control could have benefited from operating system page-cache warming, filesystem metadata caching, or JIT/bytecode compilation in worker subprocesses. Conversely, lingering `TIME_WAIT` TCP sockets from Control could have degraded Treatment if port reuse wasn't clean.
- **Protocol Remediation:** The reproducibility protocol enforces a **symmetrical, fully interleaved alternating sequence** ($C_1 \rightarrow T_1 \rightarrow C_2 \rightarrow T_2 \rightarrow C_3 \rightarrow T_3$) with a mandatory **10-second quiescence/cooldown period** between every trial, ensuring all OS socket tables, TCP buffers, and garbage collectors are fully reset.

### 2.2 Harness Implementation Differences
- **Client Libraries:** Control utilized Python's standard library `urllib.request`, which establishes and terminates a TCP socket for every individual request. Treatment utilized `urllib3.PoolManager` with thread-local pooling.
- **Protocol Remediation:** Both client implementations are pure Python within the same `.venv`, but Treatment's socket reuse is the intended independent variable. The reproducibility protocol must explicitly verify and record the count of unique client sockets created per worker to prove that connection pooling—and not client library internal overhead—is the sole differentiator.

### 2.3 Single-Trial Risk ($N = 1$)
- **Sample Variance:** A single 300-request trial cannot rule out an opportunistic low-latency window (e.g., absence of Windows background indexing, transient core scheduling alignment).
- **Protocol Remediation:** The reproducibility protocol requires **three independent Treatment trials ($T_1, T_2, T_3$)**. Every single trial must independently pass all four gates; averaging across runs to mask a failure is strictly prohibited.

### 2.4 Localhost Loopback vs. Production Network
- **Architectural Reality:** On local Windows development machines, load generator and WSGI server share the loopback interface (`127.0.0.1`). 
- **Production Translation:** In production, end-user browsers rarely maintain unpooled burst connections directly to WSGI workers. Instead, an edge reverse proxy (e.g., NGINX, HAProxy, AWS Application Load Balancer) terminates public client traffic, multiplexes requests, and maintains persistent upstream Keep-Alive connection pools to the application servers. The Phase 20F treatment accurately models this production reverse-proxy-to-upstream tier.

---

## 3. Controlled Reproducibility Protocol Specification

When authorized, the reproducibility validation must execute under the following deterministic protocol:

### 3.1 Serving Topology (Frozen C4 Configuration)
- **Total Capacity:** 12 threads across 3 independent OS worker processes.
- **Worker 0 (Port 5009 - Fast Pool):** 1 process $\times$ 4 threads. Dedicated exclusively to `/health/readiness` and `/api/v1/vehicles/search`.
- **Worker 1 (Port 5010 - Compute-A):** 1 process $\times$ 4 threads. Dedicated to `/api/v1/valuation` (preferred); accepts `/api/v1/compare` spillover when active $\ge 2$.
- **Worker 2 (Port 5011 - Compute-B):** 1 process $\times$ 4 threads. Dedicated to `/api/v1/compare` (preferred); accepts `/api/v1/valuation` spillover when active $\ge 2$.
- **Routing Engine:** Asymmetric Least-Active router with spillover threshold = 2.

### 3.2 Workload Profile (Identical 300-Request Mix)
- **Request Volume:** Exactly 300 requests per trial.
- **Distribution:**
  - 75 requests (25%): `GET /health/readiness`
  - 75 requests (25%): `GET /api/v1/vehicles/search?q={query}` (5 rotating queries)
  - 105 requests (35%): `POST /api/v1/valuation` (5 realistic Indian market vehicle profiles)
  - 45 requests (15%): `POST /api/v1/compare` (2 dual-vehicle comparison payloads)
- **Client Concurrency:** Exactly 10 concurrent client workers managed via `concurrent.futures.ThreadPoolExecutor(max_workers=10)`.
- **Dispatch Order:** Deterministic modulo-20 interleaving preserving exact historical arrival patterns.

### 3.3 Revised Interleaved Trial Execution Sequence ($N = 6$ Total Trials)
To rigorously eliminate order effects, temporal drift, thermal throttling bias, and socket state carryover, the protocol implements a **symmetrical, fully interleaved alternating sequence** ($C_1 \rightarrow T_1 \rightarrow C_2 \rightarrow T_2 \rightarrow C_3 \rightarrow T_3$):

1. **Trial 1 — Control 1 ($C_1$):** Connection-Per-Request (establishes baseline failure mode under clean initial start).
2. **Trial 2 — Treatment 1 ($T_1$):** HTTP Keep-Alive Connection Pooling (first independent treatment replication).
3. **Trial 3 — Control 2 ($C_2$):** Connection-Per-Request (intermediate control recheck; verifies baseline failure mode returns immediately when pooling is removed).
4. **Trial 4 — Treatment 2 ($T_2$):** HTTP Keep-Alive Connection Pooling (second independent treatment replication).
5. **Trial 5 — Control 3 ($C_3$):** Connection-Per-Request (late control recheck; confirms unpooled socket dwell persists under late-run thermal conditions).
6. **Trial 6 — Treatment 3 ($T_3$):** HTTP Keep-Alive Connection Pooling (third independent treatment replication).

#### Scientific Rationale for Symmetrical Interleaving
- **Elimination of Temporal / Thermal Confounders:** Rather than running back-to-back treatment runs, every Treatment trial is paired with an adjacent Control trial. If host thermal throttling, CPU frequency scaling, or background OS processes degrade performance over time, both Control and Treatment are exposed equally across early ($C_1, T_1$), mid ($C_2, T_2$), and late ($C_3, T_3$) epochs.
- **A/B State Contrast:** Alternating modes three times demonstrates that the performance difference is strictly reversible and reproducible: switching from pooled to unpooled repeatedly causes Readiness P95 to fail (> 50 ms), and switching from unpooled to pooled repeatedly causes it to pass (< 50 ms).
- **Three Independent Treatment Passes Required:** The acceptance criteria require all three Treatment trials ($T_1, T_2, T_3$) to independently clear every gate.

#### Strict Per-Trial Reset Protocol (Applied Universally across All 6 Trials)
Between **every single trial** without exception:
1. **Worker Process Teardown:** Cleanly terminate all three worker processes (`psutil` recursive parent/child termination).
2. **Port Hygiene Verification:** Programmatically scan ports 5009, 5010, and 5011 to guarantee zero listening sockets remain.
3. **Mandatory 10-Second Quiescence Cooldown:** Enforce a full 10.0-second pause to allow OS TCP stack sockets (`TIME_WAIT`) to clear and CPU temperatures to stabilize.
4. **Isolated Database Reset:** Completely unlink `data/phase20_load_drill/carspective_load.db` (including `-wal` and `-shm` sidecars) and re-seed a fresh disposable copy via SQLite online backup API from the protected read-only baseline `data/database/carspective.db`.

---

## 4. Exact Acceptance Criteria & Statistical Rules

All frozen engineering acceptance thresholds remain strictly non-negotiable. **No targets shall be relaxed:**

| Metric / Gate | Frozen Acceptance Threshold | Phase 20F Treatment Result | Reproducibility Pass Condition |
| :--- | :---: | :---: | :--- |
| **Health Readiness Client P95** | **$< 50.0\text{ ms}$** | 23.71 ms | **Must be $< 50.0\text{ ms}$ in all 3 Treatment trials** |
| **Valuation Client P95** | **$< 150.0\text{ ms}$** | 76.69 ms | **Must be $< 150.0\text{ ms}$ in all 3 Treatment trials** |
| **Search Client P95** | **$< 250.0\text{ ms}$** | 30.48 ms | **Must be $< 250.0\text{ ms}$ in all 3 Treatment trials** |
| **Comparison Client P95** | **$< 350.0\text{ ms}$** | 185.05 ms | **Must be $< 350.0\text{ ms}$ in all 3 Treatment trials** |
| **Observed Throughput** | **$> 10.0\text{ req/s}$** | 229.70 req/s | **Must exceed $> 10.0\text{ req/s}$ in all 3 Treatment trials** |
| **Error Count (5xx / Timeouts)**| **0 errors** | 0 errors | **Must be exactly 0 across all 3 Treatment trials** |
| **Post-Run Readiness Health** | **$< 50.0\text{ ms}$** | 3.74–28.06 ms | **Must be $< 50.0\text{ ms}$ across all workers post-trial** |
| **Baseline Invariants** | **16/16 PASS** | 16/16 PASS | **Must verify 16/16 PASS pre- and post-suite** |

### Statistical Reporting Requirements
The final reproducibility report must publish:
1. **Per-Trial Percentiles:** P50, P95, P99, and Max for every endpoint across each trial.
2. **Correlated Decomposition:** Explicit breakdown of Client duration, Socket Queue Dwell (`X-Socket-Queue-Dwell-Ms`), Server Execution (`X-Server-Duration-Ms`), and Transit time.
3. **Cross-Trial Stability:** Mean, standard deviation ($\sigma$), and worst-case peak across the three Treatment runs.
4. **Three-of-Three Rule:** If any single Treatment trial breaches a latency gate (e.g., Readiness P95 reaches 50.1 ms in Run 2), the entire suite is marked **FAIL / HOLD**.

---

## 5. Circuit Breakers, Safety Controls & Stop Conditions

The reproducibility test runner must strictly adhere to automated circuit breakers:
1. **Immediate Circuit Breaker:** If $\ge 5$ consecutive HTTP errors or request timeouts occur during any trial, abort execution immediately.
2. **Invariant Breach Halt:** If pre-flight or post-flight invariant verification fails, abort immediately.
3. **Database Write Protection:** The production database `data/database/carspective.db` (`cb655c06225c...`) must be accessed exclusively in read-only mode (`?mode=ro`) during disposable database seeding. Any attempt to write to the live database will invalidate the run.
4. **Model Immutability:** The valuation model artifact `models/carspective_valuation_lgbm_v1.joblib` (`4a4ccf3f78c1...`) must remain byte-identical.
5. **No Ad-Hoc Parameter Tuning:** If a run fails, the agent must record the failure and stop. Modifying thread counts, timeouts, or dispatch logic during execution is prohibited.

---

## 6. Unverified Production Deployment Evidence Matrix

Even after local reproducibility is proven, local workstation benchmarking cannot validate production infrastructure. The following checklist defines the mandatory evidence required before full production release sign-off:

| Infrastructure Requirement | Current Status | Verification Gap | Definitive Evidence Required for Release |
| :--- | :---: | :--- | :--- |
| **1. Docker Container Runtime** | ❌ Unverified | Dockerfile is audited but unexecuted; Docker daemon is unavailable on local Windows host. | Build production container image; run container under Linux; pass health probes and run integration tests inside container. |
| **2. Remote CI / CD Pipeline** | ❌ Unverified | GitHub Actions workflow definitions audited locally; remote runner execution unverified. | Clean, green GitHub Actions execution of test suite and linting across target runner environments. |
| **3. Live PostgreSQL Database** | ❌ Unverified | All local development and benchmarking executed against SQLite (`carspective.db`). | Provision managed PostgreSQL; execute Alembic migrations (`f3d730c46a23`); run concurrent load test against PostgreSQL via PgBouncer. |
| **4. Offsite Backup Replication** | ❌ Unverified | Backups validated on local filesystem (`carspective_backup_*`); cloud replication unconfigured. | Automated script replicating snapshot archives to secure cloud object storage (e.g., S3/GCS) with lifecycle policies and integrity checks. |
| **5. Point-in-Time Recovery (PITR)** | ❌ Unverified | Local database restore verified (Phase 20 Workstream D); PostgreSQL WAL archiving untested. | Drill executing WAL-based point-in-time recovery on PostgreSQL staging database to a specific historical transaction timestamp. |
| **6. Production Reverse Proxy Tier** | ❌ Unverified | Localhost harness simulates connection pooling via client-side `urllib3.PoolManager`. | Verification of NGINX / Envoy upstream reverse proxy configuration maintaining persistent Keep-Alive connections to WSGI workers. |

---

## 7. Authoritative Release Decision

- **Phase 19 Status:** **CONDITIONAL ACCEPT** (Local sign-off complete; production infrastructure unverified).
- **Phase 20 Workstream D:** **ACCEPT** (Local recovery drill completed).
- **Phase 20 Workstream E / F:** **HOLD (PRELIMINARY ACCEPTANCE CANDIDATE)**.

### Release Recommendation
**Maintain HOLD on production release approval.**

**Justification:**
1. While Phase 20F demonstrated that connection pooling resolves the readiness gate and achieves the first simultaneous 4-gate pass, this represents **single-run diagnostic evidence**.
2. Workstream E remains on **HOLD** until the multi-run reproducibility protocol defined in Section 3 is formally authorized, executed, and passed (3/3 trials).
3. Production deployment remains conditional upon completing the outstanding infrastructure validations detailed in Section 6.

---

*This document serves as the authoritative blueprint for Phase 20G. It establishes the exact conditions under which CarSpective's serving performance can be deemed reproducibly verified.*

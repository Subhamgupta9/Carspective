# CarSpective Phase 20F — Controlled HTTP Connection-Pooling A/B Diagnostic Report

**Date:** October 15, 2026  
**Phase:** 20 — Production Readiness & Operational Verification  
**Workstream:** 20E / 20F — Tail Latency Root Cause & Diagnostic Benchmarking  
**Status:** **DIAGNOSTIC COMPLETE — PRELIMINARY BENCHMARK PASS (TREATMENT)**  
**Overall Release Status:** **HOLD** (Preliminary diagnostic result; production deployment requirements remain unverified)  
**Author:** Antigravity Autonomous Performance & Release-Readiness Engineer  
**Data Artifact:** `data/phase20_load_drill/phase20f_connection_pooling_diagnostic_results.json`  

---

## 1. Executive Summary

This report documents the empirical findings of the **Phase 20F Controlled HTTP Connection-Pooling A/B Diagnostic**, authorized to investigate the sole remaining latency gate failure from Phase 20E Variant C4 (Health Readiness Client P95 of 63.84 ms vs. the `< 50.0 ms` frozen target).

The diagnostic evaluated whether the excess pre-server latency observed across all Phase 20E topology variants was an artifact of client-side ephemeral TCP connection churn (opening 300 unpooled TCP sockets in under two seconds on Windows loopback) or genuine server capacity saturation.

### Key Findings
1. **Control Trial (Connection-Per-Request):** Replicated the baseline C4 failure mode. Readiness Client P95 was **60.20 ms** (FAIL vs. 50 ms gate), with correlated pre-server queue dwell accounting for **50.85 ms** (84.5% of total request duration). Server processing alone was **12.89 ms P95** and **5.21 ms P50**.
2. **Treatment Trial (HTTP Keep-Alive Connection Pooling):** Enabling per-worker connection pooling collapsed readiness socket queue dwell from **50.85 ms down to 7.32 ms P95** (an **85.6% reduction**). 
3. **Simultaneous Clearance of All Four Latency Gates:** For the first time in CarSpective's benchmark history, the Treatment trial achieved **simultaneous passes across all frozen latency gates** under the full 300-request, 10-client concurrent mixed workload:
   - **Health Readiness Client P95:** **23.71 ms** (PASS vs. `< 50.0 ms`, 26.29 ms margin)
   - **Valuation Client P95:** **76.69 ms** (PASS vs. `< 150.0 ms`, 73.31 ms margin)
   - **Search Client P95:** **30.48 ms** (PASS vs. `< 250.0 ms`, 219.52 ms margin)
   - **Comparison Client P95:** **185.05 ms** (PASS vs. `< 350.0 ms`, 164.95 ms margin)
   - **Throughput:** **229.70 req/s** (PASS vs. `> 10.0 req/s`)
   - **Error Rate:** **0 errors / 0 timeouts** (PASS)
4. **Invariant Baseline Preserved:** 16/16 baseline invariants verified pre- and post-flight; live database and model artifact hashes are 100% identical.

---

## 2. Preflight Verification & Environmental Controls

Prior to benchmark execution, all strict safety controls were validated:

| Preflight Check | Requirement | Result | Evidence |
| :--- | :--- | :---: | :--- |
| **Baseline Invariants** | 16/16 checks pass | ✅ PASS | Verified via `scripts/verify_phase19_invariants.py` |
| **Port Hygiene** | Ports 5009, 5010, 5011 released | ✅ PASS | Zero active listeners detected via `psutil` / `Get-NetTCPConnection` |
| **Historical Data Protection** | `variant_c4_benchmark_results.json` preserved | ✅ PASS | Artifact untouched; diagnostic results written to separate file |
| **Backup Integrity** | Backup archive intact | ✅ PASS | `carspective_backup_20261010_140841.zip` verified |
| **Database Isolation** | Disposable database only | ✅ PASS | Fresh `carspective_load.db` seeded via SQLite online backup API before each trial |
| **Equal-Compute Rule** | Identical topology & capacity | ✅ PASS | 3P $\times$ 4T (12 threads total) across both trials |

---

## 3. Experimental Design: Control vs. Treatment

The diagnostic was strictly controlled to isolate a single variable: **HTTP connection reuse**.

| Parameter | Trial 1: Control | Trial 2: Treatment (Pooled) | Control Note |
| :--- | :--- | :--- | :--- |
| **Serving Topology** | 3P $\times$ 4T (12 threads) | 3P $\times$ 4T (12 threads) | Identical C4 topology (5009 fast, 5010 val-pref, 5011 cmp-pref) |
| **Workload Profile** | 300 requests | 300 requests | Identical deterministic mix (75 ready, 75 search, 105 val, 45 cmp) |
| **Concurrency** | 10 client threads | 10 client threads | `concurrent.futures.ThreadPoolExecutor(max_workers=10)` |
| **Dispatch Policy** | Asymmetric Least-Active | Asymmetric Least-Active | Spillover threshold = 2 |
| **Database Target** | Disposable `carspective_load.db` | Freshly re-seeded `carspective_load.db` | Re-seeded between trials to eliminate state bleed |
| **HTTP Client Mode** | **Connection-Per-Request** | **HTTP Keep-Alive Connection Pooling** | **The ONLY experimental variable** |
| **Client Implementation** | `urllib.request.urlopen` (closes TCP socket on exit) | `urllib3.PoolManager(maxsize=5, retries=False)` per worker | Reuses persistent TCP connections per worker thread |
| **Timeout & Abort** | 12.0s timeout; 5 consecutive error circuit breaker | 12.0s timeout; 5 consecutive error circuit breaker | Identical safety threshold |

---

## 4. Empirical Results & Gate Evaluation

### 4.1 Gate-by-Gate Comparison Table

| Metric / Gate | Frozen Acceptance Target | C4 Historical Baseline | Trial 1: Control (Per-Request) | Trial 2: Treatment (Pooled) | Gate Status (Treatment) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Health Readiness P95** | **$< 50.0\text{ ms}$** | 63.84 ms (FAIL) | 60.20 ms (FAIL) | **23.71 ms** | ✅ **PASS** |
| **Valuation Client P95** | **$< 150.0\text{ ms}$** | 139.94 ms (PASS) | 111.04 ms (PASS) | **76.69 ms** | ✅ **PASS** |
| **Search Client P95** | **$< 250.0\text{ ms}$** | 64.86 ms (PASS) | 58.00 ms (PASS) | **30.48 ms** | ✅ **PASS** |
| **Compare Client P95** | **$< 350.0\text{ ms}$** | 197.87 ms (PASS) | 185.75 ms (PASS) | **185.05 ms** | ✅ **PASS** |
| **Throughput** | **$> 10.0\text{ req/s}$** | 168.10 req/s | 207.18 req/s | **229.70 req/s** | ✅ **PASS** |
| **Error Rate (5xx/Timeouts)**| **0 errors** | 0 errors | 0 errors | **0 errors** | ✅ **PASS** |
| **Wall-Clock Duration** | — | 1.785 s | 1.448 s | **1.306 s** | — |
| **Post-Run Readiness** | $< 50.0\text{ ms}$ | 3.74 ms | 3.60–20.79 ms | 3.74–28.06 ms | ✅ **PASS** |
| **Phase 19 Invariants** | **16/16 PASS** | 16/16 PASS | 16/16 PASS | **16/16 PASS** | ✅ **PASS** |
| **Overall Gate Verdict** | **All Must Pass** | **HOLD** | **HOLD** | **PRELIMINARY PASS** | ✅ **ALL GATES SATISFIED** |

---

## 5. Correlated Per-Request Latency Breakdown

All latency components are derived on a per-request correlated basis (`client_ms`, `dwell_ms` from `X-Socket-Queue-Dwell-Ms`, `server_ms` from `X-Server-Duration-Ms`, and per-request `transit_ms = client - dwell - server`). No percentiles are subtracted independently.

### 5.1 Health Readiness (`/health/readiness`, N = 75)

| Metric | Control P50 | Control P95 | Control P99 | Treatment P50 | Treatment P95 | Treatment P99 | Delta (P95) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Client Duration** | 15.74 ms | **60.20 ms** | 95.31 ms | 8.67 ms | **23.71 ms** | 27.70 ms | **-36.49 ms (-60.6%)** |
| **Socket Queue Dwell** | 5.39 ms | **50.85 ms** | 78.19 ms | 2.00 ms | **7.32 ms** | 11.43 ms | **-43.53 ms (-85.6%)** |
| **Server Processing** | 5.21 ms | 12.89 ms | 14.90 ms | 3.34 ms | 13.21 ms | 22.79 ms | +0.32 ms |
| **Transit Overhead** | 0.96 ms | 20.10 ms | 34.94 ms | 1.32 ms | 18.84 ms | 20.09 ms | -1.26 ms |

> **Key Observation:** In the Control run, socket queue dwell P95 reached 50.85 ms while server processing was only 12.89 ms. In the Treatment run, connection pooling reduced dwell P95 to **7.32 ms**, pulling total client P95 down to **23.71 ms**. Server-side execution was virtually identical (12.89 ms vs. 13.21 ms), confirming that the server was never the bottleneck.

### 5.2 Vehicle Search (`/api/v1/vehicles/search`, N = 75)

| Metric | Control P50 | Control P95 | Control P99 | Treatment P50 | Treatment P95 | Treatment P99 | Delta (P95) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Client Duration** | 27.67 ms | 58.00 ms | 72.32 ms | 14.68 ms | **30.48 ms** | 34.69 ms | **-27.52 ms (-47.4%)** |
| **Socket Queue Dwell** | 9.00 ms | 36.89 ms | 41.43 ms | 2.07 ms | **7.50 ms** | 13.59 ms | **-29.39 ms (-79.7%)** |
| **Server Processing** | 12.70 ms | 29.21 ms | 30.80 ms | 8.41 ms | 20.74 ms | 24.69 ms | -8.47 ms |
| **Transit Overhead** | 1.37 ms | 28.88 ms | 45.42 ms | 1.76 ms | 18.24 ms | 21.38 ms | -10.64 ms |

### 5.3 Vehicle Valuation (`/api/v1/valuation`, N = 105)

| Metric | Control P50 | Control P95 | Control P99 | Treatment P50 | Treatment P95 | Treatment P99 | Delta (P95) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Client Duration** | 46.29 ms | 111.04 ms | 203.03 ms | 40.11 ms | **76.69 ms** | 117.44 ms | **-34.35 ms (-30.9%)** |
| **Socket Queue Dwell** | 7.04 ms | 37.20 ms | 70.32 ms | 7.00 ms | **24.75 ms** | 38.16 ms | **-12.45 ms (-33.5%)** |
| **Server Processing** | 17.11 ms | 63.01 ms | 117.06 ms | 24.34 ms | 59.08 ms | 87.41 ms | -3.93 ms |
| **Transit Overhead** | 2.81 ms | 54.49 ms | 69.74 ms | 6.09 ms | 17.64 ms | 27.30 ms | -36.85 ms |

### 5.4 Vehicle Comparison (`/api/v1/compare`, N = 45)

| Metric | Control P50 | Control P95 | Control P99 | Treatment P50 | Treatment P95 | Treatment P99 | Delta (P95) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Client Duration** | 88.89 ms | 185.75 ms | 221.41 ms | 125.70 ms | **185.05 ms** | 199.83 ms | **-0.70 ms** |
| **Socket Queue Dwell** | 8.25 ms | 42.72 ms | 87.81 ms | 7.21 ms | **49.03 ms** | 50.35 ms | +6.31 ms |
| **Server Processing** | 69.85 ms | 110.91 ms | 185.16 ms | 102.47 ms | 132.59 ms | 170.42 ms | +21.68 ms |
| **Transit Overhead** | 2.40 ms | 43.55 ms | 54.86 ms | 4.75 ms | 20.06 ms | 24.94 ms | -23.49 ms |

---

## 6. Resource Utilization & Dispatch Statistics

### 6.1 Worker Resource Consumption

| Metric | Control Trial | Treatment Trial (Pooled) | Variance |
| :--- | :---: | :---: | :---: |
| **Average System CPU** | 93.8% | 94.7% | +0.9% |
| **Total Peak RSS Memory** | 566.2 MB | 564.3 MB | -1.9 MB |
| **Worker 0 (Port 5009, Fast)** | 127.8 MB peak | 127.6 MB peak | Stable |
| **Worker 1 (Port 5010, Val-Pref)** | 219.8 MB peak | 218.5 MB peak | Stable |
| **Worker 2 (Port 5011, Cmp-Pref)** | 218.6 MB peak | 218.2 MB peak | Stable |

### 6.2 Router Dispatch Breakdown

| Operation | Target Routing | Control Count | Treatment Count | Routing Behavior |
| :--- | :--- | :---: | :---: | :--- |
| **Readiness + Search** | Port 5009 (Fast Pool) | 150 | 150 | 100% fast worker isolation |
| **Valuation** | Port 5010 (Compute-A) | 77 | 78 | Primary designated worker |
| **Valuation Spillover** | Port 5011 (Compute-B) | 28 (26.7%) | 27 (25.7%) | Dynamic spillover when active $\ge 2$ |
| **Comparison** | Port 5011 (Compute-B) | 33 | 32 | Primary designated worker |
| **Comparison Spillover** | Port 5010 (Compute-A) | 12 (26.7%) | 13 (28.9%) | Dynamic spillover when active $\ge 2$ |

---

## 7. Connection Reuse Evidence & Limitations

### 7.1 Empirical Proof of Connection Reuse
1. **Dwell Collapse Mechanism:** Pre-server socket queue dwell fell by **85.6%** (from 50.85 ms to 7.32 ms) exclusively on lightweight requests. Since server code was identical, this delta directly reflects the elimination of TCP SYN/ACK three-way handshakes and loopback socket creation.
2. **Socket Allocation Deficit:** 
   - In Control, every request closed its connection, forcing Windows to allocate 300 ephemeral outbound ports into `TIME_WAIT`.
   - In Treatment, each of the 10 worker threads maintained persistent connection pools (`maxsize=5`), bounding total TCP connection creations to $\le 30$ across the entire benchmark run.

### 7.2 Engineering Limitations
- **Client-Side Scope:** Connection pooling was implemented on the load generator client side. In a production environment, connection pooling is typically maintained between an edge reverse proxy (e.g., NGINX, HAProxy, AWS ALB) and the upstream Waitress WSGI instances.
- **Single Host Loopback:** The test ran over `127.0.0.1`. Network latency across physical interfaces (VPC, TLS negotiation, MTU limits) was not evaluated.

---

## 8. Invariant Baseline & Post-Flight Verification

Both trials ran against isolated disposable databases. Post-flight verification verified that no corruption, regression, or state mutation occurred:

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

**Port Cleanup Verification:** All benchmark ports (5009, 5010, 5011) were scanned immediately after both trials and confirmed to have zero active listeners.

---

## 9. Distinction: Measured Facts vs. Inferred Hypotheses

| Topic | Measured Fact | Inferred Hypothesis |
| :--- | :--- | :--- |
| **Readiness Latency** | Under connection pooling, Readiness Client P95 is **23.71 ms** (PASS). Dwell drops from 50.85 ms to 7.32 ms. | In a containerized Linux production setup fronted by NGINX, readiness latency will perform identically or better due to epoll-based connection multiplexing. |
| **Server Capacity** | Server-side execution duration is **3.34 ms P50** and **13.21 ms P95** under 10-client concurrency. | The application server and domain services have zero performance debt on readiness. |
| **Comparison Endpoint** | Compare Client P95 operates at **185.05 ms** (well within 350 ms target) under C4 asymmetric spillover routing. | Further algorithmic optimization of compare is not required for Phase 20 gate clearance. |

---

## 10. Release Decision & Outstanding Production Requirements

### 10.1 Authoritative Workstream Status

- **Phase 19:** **CONDITIONAL ACCEPT** (Unchanged)
- **Phase 20 Workstream D:** **ACCEPT** (Unchanged)
- **Phase 20 Workstream E:** **HOLD (PRELIMINARY ACCEPTANCE CANDIDATE)**

### 10.2 Release Recommendation
**Maintain HOLD on production release approval.**

**Technical Justification:**
1. While the Treatment trial produced the first 100% compliant benchmark run in CarSpective history (all four latency gates cleared simultaneously with zero errors), **a single successful treatment run is preliminary diagnostic evidence**, not proof of production readiness.
2. The core Phase 19 conditional acceptance requirements remain **unverified on production infrastructure**:
   - **Docker Runtime:** Containerized deployment remains unexecuted on this workstation.
   - **Live PostgreSQL Database:** All benchmarks targeted SQLite; PostgreSQL query execution remains unverified under concurrency.
   - **Remote CI Pipeline:** Automated tests on remote GitHub Actions runners remain unverified.
   - **Offsite Backup & PITR:** Cloud-based replication and point-in-time recovery workflows remain untested.
3. **Next Step Required:** Document the Phase 20F diagnostic findings and maintain Workstream E on HOLD until production infrastructure verification is authorized.

---

*This document represents the authoritative record of the Phase 20F Connection-Pooling A/B Diagnostic. Raw diagnostic data is preserved in `data/phase20_load_drill/phase20f_connection_pooling_diagnostic_results.json`.*

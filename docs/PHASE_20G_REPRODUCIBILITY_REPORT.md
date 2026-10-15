# CarSpective Phase 20G — Reproducibility Benchmark Suite Report

**Date:** October 15, 2026  
**Phase:** 20 — Production Readiness & Operational Verification  
**Workstream:** 20G — Symmetrical Interleaved Reproducibility Benchmark  
**Status:** **REPRODUCIBILITY VERIFIED — 3 OF 3 TREATMENT TRIALS PASSED INDEPENDENTLY**  
**Overall Release Status:** **HOLD** (Local serving performance validated; production deployment requirements remain unverified)  
**Author:** Antigravity Autonomous Performance & Release-Readiness Engineer  
**Data Artifact:** `data/phase20_load_drill/phase20g_reproducibility_results.json`  

---

## 1. Executive Summary & Authoritative Verdict

The **Phase 20G Symmetrical Interleaved Reproducibility Suite** was executed under strict oversight, evaluating the stability and repeatability of the Phase 20F connection-pooling breakthrough across six sequential trials ($C_1 \rightarrow T_1 \rightarrow C_2 \rightarrow T_2 \rightarrow C_3 \rightarrow T_3$).

### Key Findings
1. **Three-of-Three Treatment Gate Clearance:** All three independent Treatment trials ($T_1, T_2, T_3$) **passed every single frozen acceptance gate simultaneously**:
   - **Health Readiness Client P95:** $T_1 = 19.24\text{ ms}$, $T_2 = 42.67\text{ ms}$, $T_3 = 28.62\text{ ms}$ (Target: $< 50.0\text{ ms}$).
   - **Valuation Client P95:** $T_1 = 83.60\text{ ms}$, $T_2 = 105.43\text{ ms}$, $T_3 = 95.08\text{ ms}$ (Target: $< 150.0\text{ ms}$).
   - **Search Client P95:** $T_1 = 30.00\text{ ms}$, $T_2 = 52.79\text{ ms}$, $T_3 = 61.82\text{ ms}$ (Target: $< 250.0\text{ ms}$).
   - **Comparison Client P95:** $T_1 = 159.25\text{ ms}$, $T_2 = 162.70\text{ ms}$, $T_3 = 158.72\text{ ms}$ (Target: $< 350.0\text{ ms}$).
   - **Observed Throughput:** $T_1 = 251.77\text{ req/s}$, $T_2 = 223.48\text{ req/s}$, $T_3 = 234.00\text{ req/s}$ (Target: $> 10.0\text{ req/s}$).
   - **Error Rate:** Exactly **0 errors and 0 timeouts** across all 1,800 requests in the suite.
2. **Deterministic Control Failure:** All three Control trials ($C_1, C_2, C_3$) failed the readiness gate ($C_1 = 55.90\text{ ms}$, $C_2 = 52.44\text{ ms}$, $C_3 = 56.02\text{ ms}$), proving that the failure mode is 100% reproducible when connection pooling is absent.
3. **Reversibility Confirmed:** The alternation between failure in Control and success in Treatment across all three epochs establishes that connection reuse—and not temporal drift or thermal favorability—is the direct cause of gate clearance.
4. **Baseline Invariants & Hashes Preserved:** Pre-suite and post-suite invariant checks passed **16/16**, with byte-identical protected hashes for the live database and valuation model.

---

## 2. Trial-by-Trial Results & Gate Evaluation Table

Every trial executed the full 300-request mixed workload (75 readiness, 75 search, 105 valuation, 45 comparison) across 10 concurrent clients under the C4 serving topology (3P $\times$ 4T = 12 total capacity, asymmetric least-active router).

| Trial ID | Mode / Configuration | Readiness P95 ($< 50\text{ ms}$) | Valuation P95 ($< 150\text{ ms}$) | Search P95 ($< 250\text{ ms}$) | Compare P95 ($< 350\text{ ms}$) | Throughput ($> 10\text{ req/s}$) | Errors / Timeouts | Trial Gate Verdict |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$C_1$** | Control 1 (Unpooled) | 55.90 ms ❌ | 90.01 ms ✅ | 64.75 ms ✅ | 152.84 ms ✅ | 222.26 req/s ✅ | 0 / 0 ✅ | **FAIL** (Readiness) |
| **$T_1$** | Treatment 1 (Pooled) | **19.24 ms** ✅ | **83.60 ms** ✅ | **30.00 ms** ✅ | **159.25 ms** ✅ | **251.77 req/s** ✅ | **0 / 0** ✅ | ✅ **PASS (ALL GATES)** |
| **$C_2$** | Control 2 (Unpooled) | 52.44 ms ❌ | 91.51 ms ✅ | 68.97 ms ✅ | 158.77 ms ✅ | 226.06 req/s ✅ | 0 / 0 ✅ | **FAIL** (Readiness) |
| **$T_2$** | Treatment 2 (Pooled) | **42.67 ms** ✅ | **105.43 ms** ✅ | **52.79 ms** ✅ | **162.70 ms** ✅ | **223.48 req/s** ✅ | **0 / 0** ✅ | ✅ **PASS (ALL GATES)** |
| **$C_3$** | Control 3 (Unpooled) | 56.02 ms ❌ | 81.73 ms ✅ | 63.02 ms ✅ | 159.68 ms ✅ | 223.14 req/s ✅ | 0 / 0 ✅ | **FAIL** (Readiness) |
| **$T_3$** | Treatment 3 (Pooled) | **28.62 ms** ✅ | **95.08 ms** ✅ | **61.82 ms** ✅ | **158.72 ms** ✅ | **234.00 req/s** ✅ | **0 / 0** ✅ | ✅ **PASS (ALL GATES)** |

### Treatment Statistical Stability ($N = 3$)
- **Readiness P95:** Mean = **30.18 ms**, Standard Deviation $\sigma = 11.79\text{ ms}$, Worst-Case Peak = **42.67 ms** (7.33 ms safety margin).
- **Valuation P95:** Mean = **94.70 ms**, Standard Deviation $\sigma = 10.92\text{ ms}$, Worst-Case Peak = **105.43 ms** (44.57 ms safety margin).
- **Search P95:** Mean = **48.20 ms**, Standard Deviation $\sigma = 16.41\text{ ms}$, Worst-Case Peak = **61.82 ms** (188.18 ms safety margin).
- **Comparison P95:** Mean = **160.22 ms**, Standard Deviation $\sigma = 2.16\text{ ms}$, Worst-Case Peak = **162.70 ms** (187.30 ms safety margin).

---

## 3. Pre-Trial System Telemetry & Socket State Analysis

Before every trial, the runner captured a system state snapshot and enforced a minimum 10.0-second cooldown:

| Trial | Pre-Trial Available RAM | Pre-Trial CPU % | Pre-Trial TIME_WAIT Sockets | Post-Trial Readiness Probe (5009 / 5010 / 5011) |
| :---: | :---: | :---: | :---: | :---: |
| **$C_1$** | 3,268.7 MB | 35.2% | 16 | 3.59 ms / 3.49 ms / 3.53 ms |
| **$T_1$** | 3,151.3 MB | 29.2% | 84 | 4.31 ms / 3.90 ms / 3.56 ms |
| **$C_2$** | 3,400.5 MB | 8.0% | 117 | 3.86 ms / 3.73 ms / 3.59 ms |
| **$T_2$** | 3,344.8 MB | 21.0% | 192 | 3.66 ms / 3.63 ms / 3.60 ms |
| **$C_3$** | 3,137.3 MB | 38.1% | 230 | 3.57 ms / 3.49 ms / 3.82 ms |
| **$T_3$** | 2,940.3 MB | 36.0% | 278 | 3.61 ms / 3.49 ms / 3.77 ms |

### Empirical Insights on OS Socket Buildup
1. **TIME_WAIT Accumulation:** Unpooled Control runs rapidly deposited sockets into Windows OS `TIME_WAIT` status, growing from 16 before $C_1$ to 278 before $T_3$.
2. **Resilience of Treatment:** Despite running with 278 `TIME_WAIT` sockets present on the host, Trial $T_3$ completed with Readiness P95 at **28.62 ms**, because Keep-Alive connection pooling reuses established connections and bypasses the congested OS ephemeral socket allocation path.
3. **Worker Stability:** Isolated post-trial readiness probes across all workers consistently registered between **3.49 ms and 4.31 ms**, proving that internal worker health remained pristine throughout the entire multi-trial suite.

---

## 4. Correlated Latency Decomposition: Control vs. Treatment

Latency decomposition was computed per record across all 1,800 requests (`transit = client - dwell - server`):

### 4.1 Readiness Endpoint Comparison ($N = 75$ per trial)

| Metric | $C_1$ | $T_1$ | $C_2$ | $T_2$ | $C_3$ | $T_3$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Client P95** | **55.90 ms** | **19.24 ms** | **52.44 ms** | **42.67 ms** | **56.02 ms** | **28.62 ms** |
| **Queue Dwell P95** | 39.55 ms | **4.74 ms** | 27.16 ms | **6.28 ms** | 39.90 ms | **9.62 ms** |
| **Server P95** | 12.96 ms | 9.62 ms | 9.30 ms | 12.46 ms | 10.15 ms | 12.70 ms |
| **Transit P95** | 24.35 ms | 7.15 ms | 26.96 ms | 35.45 ms | 27.02 ms | 11.45 ms |

> **Conclusion:** Across all trials, server processing remained steady at **9–13 ms P95**. The determining factor between pass and fail was pre-server socket queue dwell: averaging **35.54 ms in Control** vs. **6.88 ms in Treatment** (an **80.6% reduction**).

---

## 5. Pre- and Post-Suite Invariant & Hash Integrity

The suite executed strictly against independent disposable database instances. Both pre-suite and post-suite automated verifications confirmed 100% compliance:

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

**Port Cleanup:** Ports 5009, 5010, and 5011 were scanned immediately following $T_3$ teardown and confirmed cleanly released with zero active listeners.

---

## 6. Authoritative Production Release Decision

### Workstream Status Summary

| Phase / Workstream | Prior Status | Phase 20G Verdict | Justification |
| :--- | :---: | :---: | :--- |
| **Phase 19** | CONDITIONAL ACCEPT | **CONDITIONAL ACCEPT** | Core codebase accepted; remote production deployment unverified. |
| **Phase 20 Workstream D** | ACCEPT | **ACCEPT** | Disaster recovery drill validated. |
| **Phase 20 Workstream E / F / G** | HOLD | ✅ **ACCEPT (Serving Performance)** | **Reproducibility verified:** 3 of 3 Treatment trials passed all four frozen latency gates independently with zero errors. |
| **Overall Production Release** | **HOLD** | **HOLD (DEPLOYMENT PREREQUISITES REMAINING)** | Production infrastructure must be validated before release sign-off. |

### Release Recommendation & Outstanding Gaps
While CarSpective's serving architecture has now conclusively proven that it meets all frozen latency, throughput, and error gates under concurrent load with statistical reproducibility, **production release approval remains on HOLD pending verification of the five core infrastructure requirements**:

1. **Docker Container Execution:** Image build and runtime verification under Linux.
2. **Remote CI/CD Pipeline:** Clean execution of automated test suites on remote GitHub Actions runners.
3. **Live PostgreSQL Integration:** Database migration and concurrent load validation against managed PostgreSQL.
4. **Offsite Cloud Backup:** Automated replication of database archives to cloud object storage (S3/GCS).
5. **Point-in-Time Recovery (PITR):** PostgreSQL WAL-based historical restoration drill.

---

*This document represents the final authoritative record of the Phase 20G Reproducibility Suite. Raw data is preserved in `data/phase20_load_drill/phase20g_reproducibility_results.json`.*

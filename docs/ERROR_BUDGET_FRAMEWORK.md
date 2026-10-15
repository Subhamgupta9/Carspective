# CARSPECTIVE — OPERATIONAL OBSERVABILITY & ERROR-BUDGET FRAMEWORK
**Document Version:** 1.0.0 (Provisional Proposal)  
**Status:** Approved for Implementation & Pre-Production Baselining  
**Scope:** Core CarSpective API, Valuation Engine, Market Intelligence, Data Governance

---

## 1. PURPOSE & PROVISIONAL STATUS DECLARATION

This framework defines the service-level indicators (SLIs), proposed service-level objectives (SLOs), and error-budget governance rules for CarSpective.

> [!IMPORTANT]
> **Provisional Status:** All quantitative objectives, latency thresholds, and availability percentages defined in this document are **provisional proposals**. They establish engineering expectations for system health and automated testing. They must not be claimed as empirical measurements of live production traffic until real production telemetry is connected to an active monitoring pipeline.

---

## 2. SEPARATION OF CONCERNS: OPERATIONAL VS. ANALYTICAL QUALITY

CarSpective strictly separates **operational infrastructure performance** (HTTP status, process uptime, database connectivity) from **domain analytical quality** (valuation cryptographic integrity, market freshness, evidence classification). These require independent indicators.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   CARSPECTIVE QUALITY DIMENSIONS                       │
├───────────────────────────┬────────────────────────────────────────────┤
│  OPERATIONAL DIMENSION    │  ANALYTICAL & GOVERNANCE DIMENSION         │
│  • HTTP Availability      │  • Valuation Cryptographic Integrity       │
│  • Response Latency (p95) │  • Conformal Coverage Validity             │
│  • Database Connectivity  │  • Evidence Lineage & Epistemic States     │
│  • Process Liveness       │  • Market Observation Freshness            │
└───────────────────────────┴────────────────────────────────────────────┘
```

---

## 3. SERVICE-LEVEL INDICATORS (SLIs)

### Dimension A: Operational Infrastructure & HTTP Performance

| SLI ID | Name | Measurement Formula | Telemetry Source |
|---|---|---|---|
| **SLI-OP-1** | **API Availability** | $\frac{\text{Count of HTTP responses with status } < 500}{\text{Total HTTP requests handled}} \times 100\%$ | `carspective_http_requests_total`<br>`carspective_http_5xx_total` |
| **SLI-OP-2** | **Request Latency (Normal)** | $\frac{\text{Count of API requests completed in } \le 250\text{ms}}{\text{Total API requests handled}} \times 100\%$ | `carspective_http_request_duration_seconds_bucket{le="0.25"}` |
| **SLI-OP-3** | **Request Latency (Tail)** | $\frac{\text{Count of API requests completed in } \le 1000\text{ms}}{\text{Total API requests handled}} \times 100\%$ | `carspective_http_request_duration_seconds_bucket{le="1.0"}` |
| **SLI-OP-4** | **Database Readiness** | $\frac{\text{Count of successful readiness probes}}{\text{Total readiness probes evaluated}} \times 100\%$ | `/health/readiness`<br>`carspective_database_failures_total` |

### Dimension B: Valuation Model Integrity & Prediction Performance

| SLI ID | Name | Measurement Formula | Telemetry Source |
|---|---|---|---|
| **SLI-VAL-1** | **Cryptographic Artifact Integrity** | $\frac{\text{Model deserialization attempts matching SHA-256 } \text{4a4ccf3f...}}{\text{Total model deserialization attempts}} \times 100\%$ | `ValuationService._load_and_verify_model` |
| **SLI-VAL-2** | **Inference Latency** | $\frac{\text{Valuation inferences completed in } \le 50\text{ms}}{\text{Total valuation inferences executed}} \times 100\%$ | `ValuationResponse.evaluation_time_ms` |
| **SLI-VAL-3** | **Asking-Price Quarantine Invariance** | $\frac{\text{Valuations evaluated with asking price excluded from feature matrix}}{\text{Total valuations evaluated}} \times 100\%$ | Invariant Test Suite |

### Dimension C: Data Freshness & Evidence Provenance

| SLI ID | Name | Measurement Formula | Telemetry Source |
|---|---|---|---|
| **SLI-DAT-1** | **Market Observation Freshness** | $\frac{\text{Active observation records within freshness TTL (e.g. 7 days)}}{\text{Total active current market observations}} \times 100\%$ | `current_market_observations.retrieved_at` |
| **SLI-DAT-2** | **Evidence Lineage Completeness** | $\frac{\text{Knowledge claims assigned valid canonical EvidenceState}}{\text{Total registered knowledge claims}} \times 100\%$ | `knowledge_claims.evidence_state` |
| **SLI-DAT-3** | **Catalog Parity** | Inspection checklist maintains strictly 49 canonical items, v2.0.0 | `server.domain.inspection.checklist` |

---

## 4. PROPOSED SERVICE-LEVEL OBJECTIVES (SLOs)

*The following targets are proposed baselines over a rolling 30-day window:*

| Indicator | Proposed SLO Target | Error Budget | Rationale |
|---|:---:|:---:|---|
| **SLI-OP-1 (Availability)** | **99.5%** | **0.5%** of requests | Allows ~3.6 hours of planned or unplanned outage per month for single-instance setups. |
| **SLI-OP-2 (Latency p95)** | **95.0%** $\le 250\text{ms}$ | **5.0%** of requests | Ensures responsive consumer UI across valuation and vehicle discovery pages. |
| **SLI-OP-3 (Latency p99)** | **99.0%** $\le 1000\text{ms}$ | **1.0%** of requests | Prevents extreme tail latency stalls on complex comparisons. |
| **SLI-OP-4 (DB Readiness)** | **99.9%** | **0.1%** of checks | Relational backing store must remain available during active serving. |
| **SLI-VAL-1 (Artifact SHA)** | **100.0%** | **0.0%** (Zero tolerance) | Deserialization of unverified model artifacts is strictly prohibited. |
| **SLI-VAL-2 (Inference)** | **98.0%** $\le 50\text{ms}$ | **2.0%** of runs | In-memory LightGBM inference is expected to execute in ~15ms. |

---

## 5. ERROR-BUDGET CALCULATION & INTERPRETATION

### Mathematical Definition
For any metric $M$ with an SLO target $T$ over total valid events $N$:
$$\text{Error Budget} = N \times (1.0 - T)$$

**Example (HTTP Availability):**
- If CarSpective processes $1,000,000$ HTTP requests in a 30-day rolling window:
  - Allowed 5xx responses: $1,000,000 \times (1.0 - 0.995) = 5,000$ failed requests.
  - If 5xx count exceeds 5,000, the error budget is **exhausted**.

### Burn Rate Monitoring
Burn rate represents the rate at which error budget is consumed relative to the baseline allowable rate:
- **1x Burn Rate:** Budget will be completely consumed in exactly 30 days (nominal operation).
- **2x Burn Rate:** Budget consumed in 15 days (warning state, inspect logs).
- **5x Burn Rate:** Budget consumed in 6 days (requires active engineering investigation).
- **14.4x Burn Rate:** 10% of monthly budget consumed in 5 hours (triggers immediate SEV-2 alert).

---

## 6. MEASUREMENT WINDOW & EXCLUSIONS

### Measurement Window
- **Default Window:** 30-day rolling calendar window (720 hours).
- **Evaluation Cadence:** Evaluated hourly for burn-rate alerts; evaluated weekly for release gating.

### Legitimate Exclusions
The following events are explicitly excluded from error-budget consumption:
1. **Client-side Errors (HTTP 4xx):** User validation failures (400, 422), unauthorized requests (401, 403), or non-existent routes (404) are client errors and do not consume operational error budget.
2. **Scheduled Maintenance:** Pre-announced maintenance windows (limited to $\le 2$ hours per month) where database migrations or host upgrades occur.
3. **Synthetic Load Tests:** Benchmarking and test suite requests explicitly tagged with `X-Test-Suite: true` or executed against disposable test environments.

---

## 7. INCIDENT SEVERITY & ESCALATION MATRIX

| Severity Level | Definition | Impact Criteria | Initial Response Time | Escalation Actions |
|---|---|---|:---:|---|
| **SEV-1 (Critical)** | Catastrophic outage; service completely unusable. | • HTTP 5xx rate $> 10\%$ over 5 min<br>• Persistent database unreachable<br>• Core valuation endpoint failing 100% | **< 15 minutes** | Immediate engineer mobilization; failover to maintenance notice; incident commander assigned. |
| **SEV-2 (Major)** | Severe performance degradation or critical feature outage. | • HTTP 5xx rate $> 2\%$ over 15 min<br>• p95 latency $> 2000\text{ms}$<br>• Readiness probe reporting NOT_READY | **< 30 minutes** | On-call engineer alerted; investigate logs and DB lock contention; pause pending deployments. |
| **SEV-3 (Moderate)** | Non-blocking degradation or background pipeline failure. | • Data ingestion batch failures<br>• Stale market observations (> 14 days)<br>• Cache eviction thrashing | **< 4 hours** | Create prioritized tracking ticket; review background tasks and telemetry. |
| **SEV-4 (Minor)** | Minor telemetry anomaly or transient cosmetic fault. | • Isolated client timeout<br>• Metric counter reset anomaly | **Next business day** | Addressed during standard sprint triage. |

---

## 8. RELEASE FREEZE & OPERATIONAL ACTION POLICY

To maintain service stability without stalling feature velocity, CarSpective adheres to the following error-budget governance gates:

```
┌────────────────────────────────────────────────────────┐
│             ERROR BUDGET REMAINING IN WINDOW           │
├─────────────────────────┬──────────────────────────────┤
│ Budget Remaining > 50%  │ GREEN: Normal feature releases│
├─────────────────────────┼──────────────────────────────┤
│ Budget Remaining 20–50% │ YELLOW: Fast-track reliability│
│                         │ fixes; high-risk releases    │
│                         │ require architectural sign-off│
├─────────────────────────┼──────────────────────────────┤
│ Budget Remaining < 20%  │ RED: Soft release freeze;    │
│                         │ only security & bug fixes     │
├─────────────────────────┼──────────────────────────────┤
│ Budget Exhausted (0%)   │ CRITICAL: Hard release freeze;│
│                         │ all engineering prioritized   │
│                         │ onto reliability until budget│
│                         │ recovers                      │
└─────────────────────────┴──────────────────────────────┘
```

1. **Yellow State (< 50% remaining):** Any planned deployment that touches core database schema or routing must include an automated rollback verification.
2. **Red State (< 20% remaining):** Feature deployment freeze. Only fixes directly addressing the incident root cause are permitted.
3. **Budget Recovery:** A release freeze can only be lifted when the rolling 7-day burn rate drops below 1.0x for at least 48 consecutive hours.

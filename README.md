# CARspective — Intelligent Automotive Intelligence Platform

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.11.8-blue.svg)]()
[![Frontend](https://img.shields.io/badge/react-18.3%20%7C%20vite-6.0-61dafb.svg)]()
[![Backend Tests](https://img.shields.io/badge/pytest-377%20passed-success.svg)]()
[![Frontend Tests](https://img.shields.io/badge/vitest-40%20passed-success.svg)]()
[![Evidence Governance](https://img.shields.io/badge/governance-RFC%207807%20verified-purple.svg)]()

> **Know the car. Know the value. Know the truth.**  
> CARspective is an evidence-grounded automotive intelligence platform for evaluating used vehicles in the Indian automotive market. Rather than relying on black-box predictions, dealer commissions, or unverified claims, CARspective provides mathematically calibrated valuations, intrinsic vehicle quality scores, deterministic deal analysis, adaptive buyer checklists, and a grounded AI assistant.

---

## 1. Core Architecture & Philosophy

CARspective enforces strict mathematical and architectural boundaries across all subsystems:

1. **Valuation Engine ≠ Seller Asking Price:**
   The statistical valuation engine predicts the **Estimated Fair Market Value (Historical Asking-Price Baseline)** based purely on intrinsic vehicle attributes (make, model, year, odometer km, fuel, transmission, body type). The seller's asking price is strictly isolated and never leaked into model inference.
2. **CARspective Score ≠ Deal Quality:**
   The intrinsic CARspective Score (0–100) measures long-term vehicle ownership proposition across 5 locked dimensions (Structural Safety, Reliability, Maintenance, Resale Liquidity, Real-World Practicality). An excellent car can be a terrible deal if overpriced; a mediocre car can be a great deal if heavily discounted.
3. **AI Assistant ≠ Independent Analytical Engine:**
   The Grounded AI Assistant is strictly an explainer and contextualizer. It retrieves structured evidence bundles produced by deterministic domain engines; it never computes independent prices or hallucinated ratings.
4. **Evidence Governance & Provenance:**
   Every factual claim carries explicit provenance across 7 governed states (`VERIFIED`, `SUPPORTED`, `EMPIRICAL`, `MODEL_ESTIMATE`, `INSUFFICIENT_DATA`, `UNVERIFIED`, `DEPRECATED`). A lower confidence claim is never upgraded without authoritative documentation.

For complete architectural specifications, see [docs/architecture.md](docs/architecture.md).

---

## 2. Platform Architecture Overview

```
client/ (React 18 + TypeScript + Vite)
   │
   ▼ HTTP / JSON (RFC 7807)
server/app.py (Flask Gateway + Request Tracing + Error Handlers)
   │
   ├── /api/v1/vehicles          ──> Taxonomy & Identity Domain
   ├── /api/v1/valuation         ──> Conformal LightGBM Valuation Engine
   ├── /api/v1/deal-analysis     ──> Deal Analyzer & Negotiation Intelligence
   ├── /api/v1/score             ──> 5-Dimension CARspective Score
   ├── /api/v1/recommendation    ──> Personalized Recommendation Spectrum
   ├── /api/v1/compare           ──> 2-to-3 Vehicle Comparison Engine
   ├── /api/v1/inspection        ──> 45-Item Adaptive Inspection Intelligence
   └── /api/v1/assistant         ──> Grounded Automotive AI Assistant
```

---

## 3. Local Setup & Quickstart

### Prerequisites
- Python 3.11+
- Node.js v18+ (v20 LTS recommended) & npm

### Backend Setup
1. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # Linux / macOS:
   source .venv/bin/activate
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Initialize the canonical taxonomy database:
   ```bash
   python scripts/generate_and_load_seeds.py
   ```

### Frontend Setup
1. Navigate to the client directory and install dependencies:
   ```bash
   cd client
   npm install
   ```
2. Build the production React bundle:
   ```bash
   npm run build
   cd ..
   ```

### Running the Application
Start the Flask application server:
```bash
python -m server.app
```
Access the application in your browser:
- **Web UI:** `http://localhost:5001/`
- **API Status:** `http://localhost:5001/api/v1`
- **Health Probe:** `http://localhost:5001/health`
- **Readiness Probe:** `http://localhost:5001/ready`

---

## 4. Testing & Verification

CARspective maintains comprehensive test coverage across backend domain logic, governance invariants, end-to-end user journeys, and frontend UI components.

### Run Backend Test Suite (377 Tests)
```bash
pytest
```
Test suite includes:
- `server/tests/test_governance_invariants.py`: 15 strict architectural governance invariants.
- `server/tests/test_e2e_resilience.py`: Flows A–G and failure recovery / graceful degradation.
- Domain unit test suites covering valuation, taxonomy, scoring, deal analysis, comparison, inspection, and assistant.

### Run Frontend Test Suite (40 Tests)
```bash
npm --prefix client test -- --run
```
Test suite covers currency formatters, component primitives, evidence badges, modal behavior, accessibility keys, and user interaction flows.

---

## 5. Machine Learning Valuation Model

- **Model Type:** LightGBM Tuned Regressor (`models/carspective_valuation_lgbm_v1.joblib`)
- **Target Transformation:** $\log(1 + \text{price})$ with inverse $\exp(y) - 1$ transformation
- **Calibration:** Conformal prediction intervals (80% coverage $\pm 21.78\%$, 90% coverage $\pm 31.45\%$)
- **Data Foundation:** 57,480 historical Indian used car listing records (`data/raw/indian_used_cars_raw_57480.csv`)
- **Cryptographic Security Gate:** SHA-256 digest verified against `models/carspective_valuation_lgbm_v1_manifest.json` before deserialization. Startup halts immediately upon hash tampering.

---

## 6. API Reference

All endpoints return RFC 7807 structured JSON errors on failure with unique `X-Request-ID` tracing headers.

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Liveness probe verifying HTTP availability |
| `/ready` | GET | Readiness probe verifying DB, model artifact, and taxonomy |
| `/api/v1/vehicles/manufacturers` | GET | List canonical vehicle manufacturers |
| `/api/v1/vehicles/resolve` | POST | Resolve raw vehicle inputs to canonical taxonomy ID |
| `/api/v1/valuation` | POST | Compute fair market baseline and conformal range |
| `/api/v1/deal-analysis` | POST | Evaluate listing asking price against fair value |
| `/api/v1/score` | POST | Calculate intrinsic 5-dimension CARspective Score |
| `/api/v1/recommendation` | POST | Personalized recommendation and alternatives |
| `/api/v1/compare` | POST | Rigorous 2–3 vehicle comparison and trade-offs |
| `/api/v1/inspection` | POST | Adaptive buyer checklist and purchase readiness |
| `/api/v1/assistant` | POST | Grounded automotive Q&A with structured evidence citations |

---

## 7. Security, Privacy & Performance

- **Zero Secret Leakage:** No API keys, credentials, or private tokens committed to version control.
- **Path Traversal Shield:** Strict filesystem containment checks on static file delivery and vehicle provenance routes.
- **Client Bundle Size:** Optimized 284 kB uncompressed (77 kB gzip transfer size) with sub-second initial load.
- **API Latency:** p50 latency < 40 ms across all 8 analytical endpoints.
- **3D Asset Policy:** Exact digital twin loaded only for verified canonical models; non-matched models display a lightweight, non-blocking technical blueprint card (0 KB WebGL overhead).

---

## 8. Known Limitations

1. **Historical Asking Price Baseline:** Valuations estimate the asking-price baseline from historical marketplace listings, not verified private transaction settlements.
2. **Physical Inspection Pre-Requisite:** Statistical valuation assumes standard mechanical wear; buyers must perform physical inspection and vehicle title verification before binding transactions.
3. **Regional Distribution:** Marketplace density is highest in major Tier-1 and Tier-2 Indian metropolitan clusters; rural listings represent sparser statistical tails.

---

## 9. License
CARspective is released under the MIT License.

# CARspective — Phase 10 Dataset Integrity & Quality Audit Report

**Dataset Path:** `data\raw\indian_used_cars_raw_57480.csv`  
**Nature:** Historical Indian used-car listing records / seller asking-price baseline  
**Legal & Governance Rule:** Must NEVER be cited as actual transaction or guaranteed resale value.  
**File SHA-256:** `a6a620dc6b8784acccacddc73754e070da9e48e8a2764c7c13e63d7c283941fe`  
**File Size:** 4,789,654 bytes  
**Raw Record Count:** 57,480  
**Total Columns:** 11  

---

## 1. Summary Accounting
| Metric | Value | Proportion |
|---|---|---|
| Total Raw Listing Rows | 57,480 | 100.0% |
| Cleaned / Usable Records | 57,400 | 99.86% |
| Filtered / Non-Standard Records | 80 | 0.14% |
| Exact Duplicate Rows | 0 | 0.0% |
| Listing Pattern Multi-Posts | 0 | 0.0% |

---

## 2. Missingness Analysis
| Column | Missing Count | Missing % | Status |
|---|---|---|---|
| `Unnamed: 0` | 0 | 0.0% | COMPLETE |
| `price` | 0 | 0.0% | COMPLETE |
| `manufacturing_year` | 0 | 0.0% | COMPLETE |
| `model` | 0 | 0.0% | COMPLETE |
| `km_driven` | 0 | 0.0% | COMPLETE |
| `fuel_type` | 28 | 0.0487% | PARTIAL |
| `transmission_type` | 0 | 0.0% | COMPLETE |
| `brand` | 0 | 0.0% | COMPLETE |
| `city` | 0 | 0.0% | COMPLETE |
| `bodytype` | 0 | 0.0% | COMPLETE |
| `number_of_owners` | 0 | 0.0% | COMPLETE |

---

## 3. Target Distribution: Historical Asking Price (INR)
- **Min:** ₹15,000
- **P05:** ₹140,000
- **P25 (Q1):** ₹340,000
- **Median (P50):** ₹550,000
- **Mean:** ₹996,083
- **P75 (Q3):** ₹988,916
- **P95:** ₹3,450,000
- **Max:** ₹200,000,000
- **Std Dev:** ₹1,832,278
- **Skewness:** 28.37 (Right-skewed, typical of luxury listing distribution)
- **Kurtosis:** 2541.88

---

## 4. Anomalies & Outlier Boundaries
- **Negative or Zero Price:** 0
- **Sub-₹10,000 Price:** 0
- **Hyper Luxury (> ₹1 Crore):** 282
- **Negative km:** 0
- **Extreme Mileage (> 1,000,000 km):** 72
- **Pre-1980 Manufacturing Year:** 0
- **Future Manufacturing Year (> 2026):** 0
- **Malformed Body Types Identified:** 1 (`['15']`)

---

## 5. Verified Data Cleaning Transformations
- **Price target validation**:
  - Rule: `Filter price > INR 20,000 and <= INR 5,00,00,000 (0.2L to 500L)`
  - Rationale: Remove invalid zero/scrap entries and unrealistic extreme outliers
  - Affected Rows: 4
  - Behavior: Prevents catastrophic distortion of root mean squared error baseline

- **Manufacturing year boundary**:
  - Rule: `Restrict manufacturing_year between 1995 and 2026`
  - Rationale: Used car pricing models evaluate modern registration era (< 30 years old)
  - Affected Rows: 4
  - Behavior: Excludes pre-OBD antique records with non-standard market pricing

- **Odometer km sanity check**:
  - Rule: `km_driven between 0 and 1,000,000 km`
  - Rationale: Odometer fraud or typo values exceeding 1 million km represent recording glitches
  - Affected Rows: 72
  - Behavior: Maintains linear and monotonic depreciation curve

- **Canonical text normalization**:
  - Rule: `Lower-case and strip brand, model, fuel_type, transmission_type, bodytype`
  - Rationale: Harmonize inconsistent casing and trailing whitespace across aggregator sources
  - Affected Rows: 57,480
  - Behavior: Consistent mapping to Phase 2 Canonical Vehicle Taxonomy

---
*Report certified by CARspective Phase 10 Production Audit Engine. Raw dataset remains 100% immutable.*

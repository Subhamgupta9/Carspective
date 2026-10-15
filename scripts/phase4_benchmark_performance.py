"""
CARspective — Phase 4 Performance Benchmark Script
Measures:
- Cold request latency
- Warm request latency
- Percentiles: p50, p95, p99
- Breakdown: Taxonomy Resolution vs ML Valuation vs Deal Logic
"""

import time
import json
import numpy as np
from server.app import create_app
from server.domain.deal_analyzer.models import DealAnalysisRequest
from server.domain.deal_analyzer.service import DealAnalyzerService
from server.domain.valuation.models import ValuationRequest
from server.schemas.taxonomy import CanonicalResolutionRequest

def run_performance_benchmarks():
    print("Initializing Flask test client and DealAnalyzerService...")
    app = create_app({"TESTING": True})
    client = app.test_client()
    deal_service = DealAnalyzerService()
    
    sample_payload = {
        "brand": "Hyundai",
        "model": "Creta",
        "manufacturing_year": 2019,
        "km_driven": 45000,
        "fuel_type": "Diesel",
        "transmission_type": "Manual",
        "city": "Delhi",
        "asking_price": 950000
    }
    
    # 1. Cold Request Measurement (first API hit)
    t_cold_start = time.perf_counter()
    resp_cold = client.post("/api/v1/deal-analysis", json=sample_payload)
    cold_latency_ms = (time.perf_counter() - t_cold_start) * 1000.0
    assert resp_cold.status_code == 200, f"Cold request failed: {resp_cold.status_code}"
    
    # 2. Warm Runs across multiple vehicle queries (100 iterations)
    queries = [
        {"brand": "Hyundai", "model": "Creta", "manufacturing_year": 2019, "km_driven": 45000, "asking_price": 950000},
        {"brand": "Maruti", "model": "Swift", "manufacturing_year": 2018, "km_driven": 50000, "asking_price": 520000},
        {"brand": "Tata", "model": "Nexon", "manufacturing_year": 2021, "km_driven": 30000, "asking_price": 850000},
        {"brand": "Mahindra", "model": "Thar", "manufacturing_year": 2021, "km_driven": 25000, "asking_price": 1400000},
        {"brand": "Kia", "model": "Seltos", "manufacturing_year": 2022, "km_driven": 20000, "asking_price": 1350000}
    ]
    
    # 5 warm-up iterations
    for q in queries:
        client.post("/api/v1/deal-analysis", json=q)
        
    api_latencies = []
    taxonomy_latencies = []
    valuation_latencies = []
    deal_logic_latencies = []
    
    for i in range(100):
        q = queries[i % len(queries)]
        
        # Breakdown measurements
        # Component A: Taxonomy Resolution
        tax_req = CanonicalResolutionRequest(brand=q["brand"], model=q["model"], year=q["manufacturing_year"])
        t0 = time.perf_counter()
        deal_service.valuation_service.taxonomy_resolver.resolve(tax_req)
        t_tax = (time.perf_counter() - t0) * 1000.0
        taxonomy_latencies.append(t_tax)
        
        # Component B: Direct ML Valuation (excluding taxonomy)
        val_req = ValuationRequest(
            brand=q["brand"],
            model=q["model"],
            manufacturing_year=q["manufacturing_year"],
            km_driven=q["km_driven"]
        )
        t0 = time.perf_counter()
        deal_service.valuation_service.evaluate_valuation(val_req)
        t_val = (time.perf_counter() - t0) * 1000.0
        valuation_latencies.append(t_val)
        
        # Component C: Complete API Endpoint
        t0 = time.perf_counter()
        res = client.post("/api/v1/deal-analysis", json=q)
        t_api = (time.perf_counter() - t0) * 1000.0
        api_latencies.append(t_api)
        assert res.status_code == 200

    results = {
        "cold_request_ms": round(cold_latency_ms, 2),
        "api_endpoint_percentiles": {
            "min_ms": round(float(np.min(api_latencies)), 2),
            "p50_ms": round(float(np.percentile(api_latencies, 50)), 2),
            "p90_ms": round(float(np.percentile(api_latencies, 90)), 2),
            "p95_ms": round(float(np.percentile(api_latencies, 95)), 2),
            "p99_ms": round(float(np.percentile(api_latencies, 99)), 2),
            "mean_ms": round(float(np.mean(api_latencies)), 2)
        },
        "component_breakdown_medians": {
            "taxonomy_resolution_p50_ms": round(float(np.percentile(taxonomy_latencies, 50)), 2),
            "ml_valuation_p50_ms": round(float(np.percentile(valuation_latencies, 50)), 2),
            "deal_logic_and_serialization_approx_ms": round(float(np.percentile(api_latencies, 50)) - float(np.percentile(valuation_latencies, 50)), 2)
        }
    }
    
    print("\n" + "="*60)
    print("PHASE 4 DEAL ANALYZER PERFORMANCE BENCHMARKS")
    print("="*60)
    print(json.dumps(results, indent=2))
    print("="*60 + "\n")
    
    with open("data/ml_benchmarks/phase4_performance_benchmarks.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_performance_benchmarks()

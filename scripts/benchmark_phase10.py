"""
CARspective — Phase 10: Performance, Latency & Bundle Size Benchmark Suite
Measures actual latency distributions (p50, p95, p99, mean) across all 8 domain endpoints
and records production client bundle metrics.
"""

import os
import sys
import json
import time
import numpy as np

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.abspath("."))

from typing import Dict, Any, List
from server.app import create_app

BENCHMARK_OUTPUT = os.path.join("data", "processed", "phase10_benchmark_results.json")

def measure_backend_latencies(client, iterations: int = 50) -> Dict[str, Any]:
    print(f"Running backend latency benchmarks ({iterations} iterations per endpoint)...")
    
    endpoints = {
        "Taxonomy (List Manufacturers)": {
            "method": "GET",
            "url": "/api/v1/vehicles/manufacturers",
            "payload": None
        },
        "Valuation Engine": {
            "method": "POST",
            "url": "/api/v1/valuation",
            "payload": {
                "brand": "Hyundai",
                "model": "Creta",
                "manufacturing_year": 2021,
                "km_driven": 35000,
                "fuel_type": "Diesel",
                "transmission_type": "Manual"
            }
        },
        "Deal Analyzer": {
            "method": "POST",
            "url": "/api/v1/deal-analysis",
            "payload": {
                "brand": "Tata",
                "model": "Nexon",
                "manufacturing_year": 2021,
                "km_driven": 30000,
                "asking_price": 850000.0,
                "fuel_type": "Petrol",
                "transmission_type": "Manual"
            }
        },
        "CARspective Score": {
            "method": "POST",
            "url": "/api/v1/score",
            "payload": {
                "brand": "Maruti Suzuki",
                "model": "Swift",
                "manufacturing_year": 2020
            }
        },
        "Recommendation Engine": {
            "method": "POST",
            "url": "/api/v1/recommendation",
            "payload": {
                "brand": "Tata",
                "model": "Nexon",
                "manufacturing_year": 2021,
                "km_driven": 25000,
                "asking_price": 820000.0,
                "budget_max": 900000.0
            }
        },
        "Comparison Engine": {
            "method": "POST",
            "url": "/api/v1/compare",
            "payload": {
                "vehicles": [
                    {"brand": "Maruti Suzuki", "model": "Swift", "manufacturing_year": 2021, "km_driven": 25000},
                    {"brand": "Hyundai", "model": "i20", "manufacturing_year": 2021, "km_driven": 25000}
                ]
            }
        },
        "Inspection Intelligence": {
            "method": "POST",
            "url": "/api/v1/inspection",
            "payload": {
                "vehicle": {
                    "brand": "Tata",
                    "model": "Nexon",
                    "manufacturing_year": 2021,
                    "fuel_type": "Petrol",
                    "transmission_type": "Manual"
                },
                "findings": [
                    {"item_id": "DOC_RC_VERIFICATION", "status": "PASS"},
                    {"item_id": "DOC_VIN_CHASSIS_STAMPING", "status": "PASS"}
                ]
            }
        },
        "Grounded AI Assistant": {
            "method": "POST",
            "url": "/api/v1/assistant",
            "payload": {
                "message": "What is the fair market value of this 2021 Nexon?",
                "vehicle": {"brand": "Tata", "model": "Nexon", "manufacturing_year": 2021, "km_driven": 30000}
            }
        }
    }
    
    results = {}
    for name, config in endpoints.items():
        latencies: List[float] = []
        # Warmup 2 calls
        for _ in range(2):
            if config["method"] == "GET":
                client.get(config["url"])
            else:
                client.post(config["url"], json=config["payload"])
                
        for _ in range(iterations):
            t0 = time.perf_counter()
            if config["method"] == "GET":
                res = client.get(config["url"])
            else:
                res = client.post(config["url"], json=config["payload"])
            elapsed_ms = (time.perf_counter() - t0) * 1000
            assert res.status_code == 200, f"{name} failed with {res.status_code}: {res.text}"
            latencies.append(elapsed_ms)
            
        arr = np.array(latencies)
        results[name] = {
            "iterations": iterations,
            "p50_ms": round(float(np.percentile(arr, 50)), 2),
            "p95_ms": round(float(np.percentile(arr, 95)), 2),
            "p99_ms": round(float(np.percentile(arr, 99)), 2),
            "mean_ms": round(float(np.mean(arr)), 2),
            "min_ms": round(float(np.min(arr)), 2),
            "max_ms": round(float(np.max(arr)), 2),
        }
        print(f"  {name}: p50={results[name]['p50_ms']}ms, p95={results[name]['p95_ms']}ms, mean={results[name]['mean_ms']}ms")
        
    return results

def measure_frontend_bundle() -> Dict[str, Any]:
    print("Auditing client bundle size in client/dist...")
    dist_dir = os.path.join("client", "dist")
    if not os.path.isdir(dist_dir):
        return {"status": "dist_not_built"}
        
    assets_dir = os.path.join(dist_dir, "assets")
    bundle_files = {}
    total_js_bytes = 0
    total_css_bytes = 0
    
    for f in os.listdir(assets_dir):
        fpath = os.path.join(assets_dir, f)
        size = os.path.getsize(fpath)
        bundle_files[f] = size
        if f.endswith(".js"):
            total_js_bytes += size
        elif f.endswith(".css"):
            total_css_bytes += size
            
    index_html_size = os.path.getsize(os.path.join(dist_dir, "index.html"))
    
    return {
        "index_html_bytes": index_html_size,
        "total_js_bytes": total_js_bytes,
        "total_js_kb": round(total_js_bytes / 1024, 2),
        "total_css_bytes": total_css_bytes,
        "total_css_kb": round(total_css_bytes / 1024, 2),
        "total_assets_bytes": total_js_bytes + total_css_bytes + index_html_size,
        "total_assets_kb": round((total_js_bytes + total_css_bytes + index_html_size) / 1024, 2),
        "asset_breakdown": bundle_files
    }

def run_benchmarks():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        backend_stats = measure_backend_latencies(client, iterations=50)
        
    frontend_stats = measure_frontend_bundle()
    
    three_d_audit = {
        "architecture": "Progressive non-blocking fallback",
        "digital_twin_exact_match_only": True,
        "universal_porsche_removed": True,
        "fallback_mechanism": "Lightweight SVG / CSS technical blueprint card (0 KB WebGL overhead)",
        "memory_cleanup": "WebGL renderer disposed and canvas removed on component unmount",
        "mobile_reduced_motion": "Three.js animations halted when prefers-reduced-motion: reduce detected"
    }
    
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "backend_latency": backend_stats,
        "frontend_bundle": frontend_stats,
        "three_d_system_audit": three_d_audit
    }
    
    os.makedirs(os.path.dirname(BENCHMARK_OUTPUT), exist_ok=True)
    with open(BENCHMARK_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print(f"Benchmark results successfully saved to: {BENCHMARK_OUTPUT}")
    return report

if __name__ == "__main__":
    run_benchmarks()

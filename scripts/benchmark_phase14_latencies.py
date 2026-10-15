"""
CARspective — Phase 14 Performance & SLA Benchmark Script
Measures p50 and p95 latency for Market API, Ownership API, TCO Calculation,
and End-to-End Vehicle Intelligence Workspace Synthesis.
"""

import time
import numpy as np
from server.app import create_app

app = create_app({"TESTING": True})
client = app.test_client()

VEHICLES = [
    "maruti-suzuki::swift",
    "hyundai::creta",
    "honda::city",
    "tata::nexon",
    "hyundai::verna",
]

N_ITER = 30

def benchmark_endpoint(name, method, url, json_payload=None):
    # Warm-up call
    if method == "GET":
        client.get(url)
    else:
        client.post(url, json=json_payload)

    latencies = []
    for _ in range(N_ITER):
        t0 = time.perf_counter()
        if method == "GET":
            res = client.get(url)
        else:
            res = client.post(url, json=json_payload)
        t1 = time.perf_counter()
        assert res.status_code == 200, f"{name} returned {res.status_code}"
        latencies.append((t1 - t0) * 1000.0)

    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    mean_lat = np.mean(latencies)
    print(f"{name:45s} | p50: {p50:6.2f} ms | p95: {p95:6.2f} ms | mean: {mean_lat:6.2f} ms")
    return p50, p95

print("================================================================================")
print("              CARSPECTIVE PHASE 14 LATENCY & SLA BENCHMARK                      ")
print("================================================================================")

for v in VEHICLES[:3]:
    benchmark_endpoint(f"GET /api/v1/market/{v}", "GET", f"/api/v1/market/{v}")

for v in VEHICLES[:3]:
    benchmark_endpoint(f"GET /api/v1/ownership/{v}", "GET", f"/api/v1/ownership/{v}")

tco_payload = {
    "canonical_vehicle_id": "hyundai::creta",
    "ownership_years": 5,
    "annual_km": 12000.0,
    "custom_purchase_price": 850000.0,
}
benchmark_endpoint("POST /api/v1/ownership/tco (5-Year)", "POST", "/api/v1/ownership/tco", tco_payload)

fuel_payload = {
    "mileage_kmpl": 16.5,
    "annual_km": 12000.0,
    "fuel_type": "Petrol",
}
benchmark_endpoint("POST /api/v1/ownership/cost", "POST", "/api/v1/ownership/cost", fuel_payload)

WORKSPACE_VEHICLES = [
    "maruti-suzuki::swift::gen-3-2018::2021::zxi",
    "hyundai::creta::gen-2-2020::2021::sx",
    "honda::city::gen-5-2020::2022::vx",
]

for v in WORKSPACE_VEHICLES:
    benchmark_endpoint(f"GET /api/v1/vehicles/workspace/{v}", "GET", f"/api/v1/vehicles/workspace/{v}")

print("================================================================================")

"""
CARspective — Phase 10: End-to-End (E2E) & Failure Recovery Test Suite
Validates complete user journeys across Flows A-G and verifies graceful degradation
under malformed payloads, unavailable entities, and service degradation.
"""

import pytest

class TestEndToEndResilienceFlows:

    # Flow A: Homepage -> Search -> Vehicle -> Valuation
    def test_flow_a_search_vehicle_valuation(self, app_client):
        # 1. Homepage / API status
        res_home = app_client.get("/api/v1")
        assert res_home.status_code == 200
        assert res_home.json["status"] == "OPERATIONAL"

        # 2. Search / List Manufacturers
        res_mfg = app_client.get("/api/v1/vehicles/manufacturers")
        assert res_mfg.status_code == 200
        assert any(m["slug"] == "hyundai" for m in res_mfg.json)

        # 3. Model Lookup
        res_models = app_client.get("/api/v1/vehicles/hyundai/models")
        assert res_models.status_code == 200
        assert any(mod["name"] == "Creta" for mod in res_models.json)

        # 4. Valuation Execution
        val_payload = {
            "brand": "Hyundai",
            "model": "Creta",
            "manufacturing_year": 2021,
            "km_driven": 35000,
            "fuel_type": "Diesel",
            "transmission_type": "Manual"
        }
        res_val = app_client.post("/api/v1/valuation", json=val_payload)
        assert res_val.status_code == 200
        val_data = res_val.json
        assert val_data["estimated_fair_market_value"] is not None
        assert val_data["expected_fair_market_range"] is not None
        assert val_data["expected_fair_market_range"]["lower_bound"] < val_data["estimated_fair_market_value"]
        assert val_data["expected_fair_market_range"]["upper_bound"] > val_data["estimated_fair_market_value"]

    # Flow B: Vehicle -> Enter asking price -> Deal analysis -> Negotiation context
    def test_flow_b_vehicle_asking_price_deal_analysis(self, app_client):
        deal_payload = {
            "brand": "Tata",
            "model": "Nexon",
            "manufacturing_year": 2021,
            "km_driven": 30000,
            "asking_price": 850000.0,
            "fuel_type": "Petrol",
            "transmission_type": "Manual"
        }
        res_deal = app_client.post("/api/v1/deal-analysis", json=deal_payload)
        assert res_deal.status_code == 200
        deal_data = res_deal.json
        assert deal_data["deal_quality"] in ["GREAT_DEAL", "FAIR_DEAL", "OVERPRICED", "UNUSUALLY_LOW_ASKING_PRICE"]
        assert deal_data["negotiation"]["negotiation_strength"] in ["STRONG", "MODERATE", "LIMITED"]
        assert deal_data["negotiation"]["safety_disclaimer"] is not None
        assert deal_data["asking_price_evidence_state"] == "UNVERIFIED"

    # Flow C: Vehicle -> Compare -> Second vehicle -> Comparison
    def test_flow_c_vehicle_comparison(self, app_client):
        compare_payload = {
            "vehicles": [
                {
                    "brand": "Maruti Suzuki",
                    "model": "Swift",
                    "manufacturing_year": 2021,
                    "km_driven": 25000,
                    "fuel_type": "Petrol",
                    "transmission_type": "Manual"
                },
                {
                    "brand": "Hyundai",
                    "model": "i20",
                    "manufacturing_year": 2021,
                    "km_driven": 25000,
                    "fuel_type": "Petrol",
                    "transmission_type": "Manual"
                }
            ]
        }
        res_comp = app_client.post("/api/v1/compare", json=compare_payload)
        assert res_comp.status_code == 200
        comp_data = res_comp.json
        assert len(comp_data["vehicles"]) == 2
        assert "best_for" in comp_data and "overall_result" in comp_data

    # Flow D: Vehicle -> Inspection -> Finding -> Risk -> Purchase readiness
    def test_flow_d_inspection_finding_readiness(self, app_client):
        insp_payload = {
            "vehicle": {
                "brand": "Tata",
                "model": "Nexon",
                "manufacturing_year": 2021,
                "fuel_type": "Petrol",
                "transmission_type": "Manual"
            },
            "findings": [
                {
                    "item_id": "DOC_RC_VERIFICATION",
                    "status": "PASS"
                },
                {
                    "item_id": "DOC_VIN_CHASSIS_STAMPING",
                    "status": "PASS"
                }
            ]
        }
        res_insp = app_client.post("/api/v1/inspection", json=insp_payload)
        assert res_insp.status_code == 200
        insp_data = res_insp.json
        assert insp_data["purchase_readiness"] is not None
        assert insp_data["summary"]["passed_items_count"] == 2
        assert len(insp_data["limitations"]) > 0

    # Flow E: Vehicle -> Ask CarSpective -> Valuation question -> Follow-up question
    def test_flow_e_assistant_valuation_and_followup(self, app_client):
        # Initial turn
        req_turn1 = {
            "message": "What is the fair market value of this 2020 Maruti Swift?",
            "vehicle": {
                "brand": "Maruti Suzuki",
                "model": "Swift",
                "manufacturing_year": 2020,
                "km_driven": 35000
            }
        }
        res_turn1 = app_client.post("/api/v1/assistant", json=req_turn1)
        assert res_turn1.status_code == 200
        turn1_data = res_turn1.json
        session_id = turn1_data["session_id"]
        assert len(turn1_data["evidence_bundle"]) > 0

        # Follow-up turn referencing same session
        req_turn2 = {
            "message": "What are the common risks with this car?",
            "session_id": session_id,
            "vehicle": {
                "brand": "Maruti Suzuki",
                "model": "Swift",
                "manufacturing_year": 2020,
                "km_driven": 35000
            }
        }
        res_turn2 = app_client.post("/api/v1/assistant", json=req_turn2)
        assert res_turn2.status_code == 200
        turn2_data = res_turn2.json
        assert turn2_data["session_id"] == session_id
        assert len(turn2_data["answer"]) > 0

    # Flow F: Vehicle -> Assistant -> Comparison context -> Follow-up
    def test_flow_f_assistant_comparison_context(self, app_client):
        req_comp = {
            "message": "Compare this Swift against the Tata Nexon.",
            "vehicle": {
                "brand": "Maruti Suzuki",
                "model": "Swift",
                "manufacturing_year": 2020
            },
            "compared_vehicles": [
                {
                    "brand": "Tata",
                    "model": "Nexon",
                    "manufacturing_year": 2020
                }
            ]
        }
        res_comp = app_client.post("/api/v1/assistant", json=req_comp)
        assert res_comp.status_code == 200
        data = res_comp.json
        assert data["intent"] in ["COMPARISON", "VEHICLE_OVERVIEW", "RECOMMENDATION"]
        assert len(data["answer"]) > 0

    # Flow G: Insufficient data -> Correct uncertainty UX
    def test_flow_g_insufficient_data_uncertainty(self, app_client):
        req_unsupported = {
            "brand": "McLaren",
            "model": "720S",
            "manufacturing_year": 1984,
            "km_driven": 950000
        }
        res_val = app_client.post("/api/v1/valuation", json=req_unsupported)
        assert res_val.status_code == 200
        val_data = res_val.json
        assert val_data["confidence_state"] == "INSUFFICIENT_DATA"
        assert val_data["estimated_fair_market_value"] is None
        assert any("insufficient" in lim.lower() for lim in val_data["limitations"])


class TestFailureRecoveryAndGracefulDegradation:

    def test_missing_vehicle_not_found_structured_error(self, app_client):
        res = app_client.get("/api/v1/vehicles/non-existent-manufacturer-xyz")
        assert res.status_code == 404
        assert res.headers.get("X-Request-ID") is not None
        assert res.json["title"] == "Manufacturer Not Found"
        assert res.json["status"] == 404

    def test_malformed_json_payload_rejection(self, app_client):
        # Empty body where JSON required
        res = app_client.post(
            "/api/v1/deal-analysis",
            data="not a json string",
            content_type="application/json"
        )
        assert res.status_code in [400, 422]
        assert res.headers.get("X-Request-ID") is not None

    def test_comparison_less_than_two_vehicles_rejected(self, app_client):
        # Comparison with only 1 vehicle must fail cleanly
        req = {
            "vehicles": [
                {"brand": "Tata", "model": "Nexon", "manufacturing_year": 2021}
            ]
        }
        res = app_client.post("/api/v1/compare", json=req)
        assert res.status_code in [400, 422]
        assert "at least" in str(res.json).lower() or "minimum" in str(res.json).lower() or res.status_code == 422

    def test_inspection_missing_required_vehicle_rejected(self, app_client):
        res = app_client.post("/api/v1/inspection", json={})
        assert res.status_code in [400, 422]
        assert res.headers.get("X-Request-ID") is not None

    def test_assistant_empty_message_rejected(self, app_client):
        res = app_client.post("/api/v1/assistant", json={"message": ""})
        assert res.status_code in [400, 422]
        assert res.headers.get("X-Request-ID") is not None

    def test_path_traversal_attack_blocked(self, app_client):
        # Attempt traversal attack on static or route
        res = app_client.get("/..%2f..%2fetc/passwd")
        assert res.status_code in [400, 404]

    def test_null_byte_path_blocked(self, app_client):
        res = app_client.get("/index.html%00.txt")
        assert res.status_code in [400, 404]

    def test_health_and_ready_probes_always_succeed(self, app_client):
        res_h = app_client.get("/health")
        assert res_h.status_code == 200
        assert res_h.json["status"] == "UP"

        res_r = app_client.get("/ready")
        assert res_r.status_code == 200
        assert res_r.json["status"] == "READY"
        assert res_r.json["checks"]["database"] == "CONNECTED"

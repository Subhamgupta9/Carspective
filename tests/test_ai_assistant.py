"""
SMARTCAR AI — PHASE 10: AI EXPLANATION ASSISTANT TESTS
======================================================
Validates:
1. The AI does NOT replace the ML model:
   - ML predicts. AI explains.
2. Grounded Explanation Generation:
   - All 5 required example questions:
     * Why is this price?
     * What reduced my car's value?
     * Is this a good selling price?
     * Explain depreciation.
     * What affects my valuation?
   - Mentions underlying dataset records and valuation dimensions.
   - Provides verified source citations.
3. Strict Anti-Hallucination Guardrails & Refusal:
   - Refuses unrecorded mechanical specs (horsepower, torque, 0-100, top speed).
   - Refuses unrecorded feature packages (sunroof, ventilated seats, sound system).
   - Refuses out-of-domain queries (crypto, real estate, unrelated vehicles).
   - Returns exact phrase: "I don't have enough data to answer that."
4. Configurable Provider & Local-Model Fallback:
   - Deterministic local-model fallback executes reliably with zero external dependencies.
5. Flask API Endpoint:
   - POST /api/ai/explain returns 200 with structured JSON.
   - Returns 400 when question is missing.
   - Supports Server-Sent Events (SSE) streaming when stream=True.
6. All 5 Benchmark Vehicles:
   - BMW 3 Series 2021
   - Hyundai Creta 2022
   - Toyota Fortuner 2021
   - Mercedes-Benz C-Class 2022
   - Porsche 911 2021
7. Frontend DOM, CSS, and JS API Contracts.
"""

import os
import json
import pytest
from app.app import app
from app.ai_assistant import AIAssistant, check_for_hallucination_triggers, REFUSAL_MESSAGE


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_bmw_context():
    vehicle_data = {
        "brand": "BMW",
        "model": "3 Series",
        "manufacturing_year": 2021,
        "km_driven": 40000,
        "fuel_type": "Diesel",
        "transmission_type": "Automatic",
        "city": "Delhi",
        "number_of_owners": 1
    }
    valuation_data = {
        "prediction": 3850000,
        "formatted_prediction": "₹38.50 Lakh",
        "price_range": {
            "formatted_min": "₹36.00 Lakh",
            "formatted_max": "₹41.00 Lakh",
            "formatted_margin": "₹2.50 Lakh",
            "confidence_level": "90% Empirical Interval"
        },
        "market_position": {
            "percentile": 55,
            "verdict": "Fair Market",
            "formatted_median_price": "₹37.90 Lakh",
            "delta_pct": 1.6
        },
        "depreciation": {
            "age_years": 5,
            "retained_value_pct": 74.5,
            "total_depreciation_pct": 25.5,
            "annual_depreciation_rate": 11.2
        },
        "usage_intensity": {
            "formatted_annual_km": "8,000 KM / Year",
            "benchmark_annual_km": 11000,
            "ratio": 0.73,
            "badge": "LOW MILEAGE"
        },
        "ownership_impact": {
            "number_of_owners": 1,
            "impact_label": "1st Owner (Single Owner)",
            "adjustment_pct": 0
        },
        "demand_level": {
            "liquidity_score": 80,
            "comparable_count": 54,
            "label": "Healthy Demand & Consistent Turnover"
        },
        "market_intelligence": {
            "sample_size": 54,
            "is_sparse": False,
            "depreciation_curve": {
                "has_sufficient_data": True,
                "cohort_count": 15,
                "newest_anchor_year": 2023,
                "formatted_newest_anchor_price": "₹48.00 Lakh",
                "points": [
                    {"year": 2023, "formatted_median_price": "₹48.00 Lakh", "depreciation_vs_newest_pct": 0},
                    {"year": 2021, "formatted_median_price": "₹38.50 Lakh", "depreciation_vs_newest_pct": 20}
                ]
            }
        },
        "comparables": [
            {
                "record_id": 1420,
                "brand": "BMW",
                "model": "3 Series",
                "manufacturing_year": 2021,
                "km_driven": 38000,
                "formatted_km": "38,000 KM",
                "fuel_type": "Diesel",
                "city": "Delhi",
                "actual_price": 3820000,
                "formatted_price": "₹38.20 Lakh",
                "similarity_score": 94
            }
        ]
    }
    return vehicle_data, valuation_data


# ============================================================
# 1. GROUNDED EXPLANATION TESTS FOR ALL 5 REQUIRED QUESTIONS
# ============================================================

def test_explain_why_is_this_price(sample_bmw_context):
    v_data, val_data = sample_bmw_context
    ai = AIAssistant(provider="local")
    res = ai.explain("Why is this price?", v_data, val_data)

    assert res["success"] is True
    assert res["is_refusal"] is False
    assert len(res["citations"]) >= 2
    # Must mention prediction and underlying data
    assert "₹38.50 Lakh" in res["answer"] or "38.50" in res["answer"]
    assert "54 comparable listings" in res["answer"] or "54" in res["answer"]
    assert "retained value" in res["answer"].lower() or "depreciation" in res["answer"].lower()


def test_explain_what_reduced_my_cars_value(sample_bmw_context):
    v_data, val_data = sample_bmw_context
    ai = AIAssistant(provider="local")
    res = ai.explain("What reduced my car's value?", v_data, val_data)

    assert res["success"] is True
    assert res["is_refusal"] is False
    assert "depreciation" in res["answer"].lower()
    assert "age" in res["answer"].lower()
    assert len(res["citations"]) >= 1


def test_explain_is_this_a_good_selling_price(sample_bmw_context):
    v_data, val_data = sample_bmw_context
    ai = AIAssistant(provider="local")
    res = ai.explain("Is this a good selling price?", v_data, val_data)

    assert res["success"] is True
    assert res["is_refusal"] is False
    assert "fair market" in res["answer"].lower() or "range" in res["answer"].lower()
    assert "₹36.00 Lakh" in res["answer"] or "36.00" in res["answer"]


def test_explain_depreciation(sample_bmw_context):
    v_data, val_data = sample_bmw_context
    ai = AIAssistant(provider="local")
    res = ai.explain("Explain depreciation.", v_data, val_data)

    assert res["success"] is True
    assert res["is_refusal"] is False
    assert "cohort" in res["answer"].lower() or "retained" in res["answer"].lower()
    assert "annual" in res["answer"].lower()


def test_explain_what_affects_my_valuation(sample_bmw_context):
    v_data, val_data = sample_bmw_context
    ai = AIAssistant(provider="local")
    res = ai.explain("What affects my valuation?", v_data, val_data)

    assert res["success"] is True
    assert res["is_refusal"] is False
    # Must mention drivers: age, mileage, fuel, ownership, city
    ans_lower = res["answer"].lower()
    assert "year" in ans_lower or "age" in ans_lower
    assert "km" in ans_lower or "mileage" in ans_lower
    assert "diesel" in ans_lower or "fuel" in ans_lower


# ============================================================
# 2. STRICT ANTI-HALLUCINATION & REFUSAL TESTS
# ============================================================

@pytest.mark.parametrize("hallucination_prompt", [
    "What is the horsepower of this car?",
    "How much brake horsepower (bhp) and torque does this have?",
    "What is the 0-100 acceleration and top speed?",
    "Does this car have a panoramic sunroof?",
    "Does it come with leather seats and apple carplay?",
    "Will Bitcoin reach 100k next year?",
    "What is the price of a Ferrari 488?",
    "How much will this car be worth in 2035?",
    "What is the boot space in liters and ground clearance?"
])
def test_hallucination_refusal(sample_bmw_context, hallucination_prompt):
    """Verify that unrecorded specs, features, out-of-domain, and speculative prompts are refused."""
    v_data, val_data = sample_bmw_context
    ai = AIAssistant(provider="local")
    res = ai.explain(hallucination_prompt, v_data, val_data)

    assert res["success"] is True
    assert res["is_refusal"] is True
    assert REFUSAL_MESSAGE in res["answer"]


def test_check_for_hallucination_triggers_direct():
    """Verify check_for_hallucination_triggers function directly."""
    veh = {"brand": "Hyundai", "model": "Creta"}
    val = {"prediction": 1200000}

    # Should trigger refusal
    refused, msg = check_for_hallucination_triggers("What is the top speed of this car?", veh, val)
    assert refused is True
    assert "I don't have enough data to answer that." in msg

    # Should not trigger refusal
    allowed, msg = check_for_hallucination_triggers("Why is this price?", veh, val)
    assert allowed is False
    assert msg == ""


# ============================================================
# 3. HTTP ENDPOINT TESTS (POST /api/ai/explain)
# ============================================================

def test_api_ai_explain_success(client, sample_bmw_context):
    v_data, val_data = sample_bmw_context
    payload = {
        "question": "Why is this price?",
        "vehicle_data": v_data,
        "valuation_data": val_data
    }
    response = client.post("/api/ai/explain", json=payload)
    assert response.status_code == 200
    data = response.get_json()

    assert data["success"] is True
    assert data["is_refusal"] is False
    assert "answer" in data
    assert len(data["citations"]) >= 1
    assert data["provider"] in ["local_grounded", "gemini"]


def test_api_ai_explain_missing_question(client):
    response = client.post("/api/ai/explain", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "question" in data["error"].lower()


def test_api_ai_explain_refusal_endpoint(client, sample_bmw_context):
    v_data, val_data = sample_bmw_context
    payload = {
        "question": "What is the horsepower of this engine?",
        "vehicle_data": v_data,
        "valuation_data": val_data
    }
    response = client.post("/api/ai/explain", json=payload)
    assert response.status_code == 200
    data = response.get_json()

    assert data["success"] is True
    assert data["is_refusal"] is True
    assert "I don't have enough data to answer that." in data["answer"]


def test_api_ai_explain_streaming_sse(client, sample_bmw_context):
    v_data, val_data = sample_bmw_context
    payload = {
        "question": "Why is this price?",
        "vehicle_data": v_data,
        "valuation_data": val_data,
        "stream": True
    }
    response = client.post("/api/ai/explain", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.content_type

    # Verify event stream structure
    stream_content = response.get_data(as_text=True)
    assert "data: " in stream_content
    assert '"done": true' in stream_content or '"done":true' in stream_content


# ============================================================
# 4. ALL FIVE BENCHMARK VEHICLES COVERAGE
# ============================================================

@pytest.mark.parametrize("brand,model,year,km,fuel,trans,city,owners", [
    ("BMW", "3 Series", 2021, 40000, "Diesel", "Automatic", "Delhi", 1),
    ("Hyundai", "Creta", 2022, 28000, "Petrol", "Manual", "Mumbai", 1),
    ("Toyota", "Fortuner", 2021, 55000, "Diesel", "Automatic", "Bangalore", 1),
    ("Mercedes-Benz", "C-Class", 2022, 24000, "Diesel", "Automatic", "Delhi", 1),
    ("Porsche", "911", 2021, 15000, "Petrol", "Automatic", "Mumbai", 1)
])
def test_all_five_benchmark_vehicles_ai_explanation(brand, model, year, km, fuel, trans, city, owners):
    """Verify AI explanation works reliably across all 5 benchmark models."""
    ai = AIAssistant(provider="local")
    v_data = {
        "brand": brand,
        "model": model,
        "manufacturing_year": year,
        "km_driven": km,
        "fuel_type": fuel,
        "transmission_type": trans,
        "city": city,
        "number_of_owners": owners
    }
    val_data = {
        "prediction": 2500000,
        "formatted_prediction": "₹25.00 Lakh",
        "market_position": {"percentile": 50, "verdict": "Fair Market"},
        "depreciation": {"age_years": 2026 - year, "retained_value_pct": 75}
    }

    res = ai.explain("What affects my valuation?", v_data, val_data)
    assert res["success"] is True
    assert res["is_refusal"] is False
    assert brand.lower() in res["answer"].lower()
    assert len(res["citations"]) >= 1


# ============================================================
# 5. FRONTEND DOM, CSS & JS API CONTRACTS
# ============================================================

def test_index_html_contains_phase10_assistant_elements():
    """Verify index.html contains the floating button, drawer, and chat elements."""
    index_path = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "aiAssistantContainer" in content
    assert "aiAssistantTrigger" in content
    assert "aiAssistantDrawer" in content
    assert "aiAssistantCloseBtn" in content
    assert "aiContextBanner" in content
    assert "aiChatMessages" in content
    assert "aiTypingIndicator" in content
    assert "aiSuggestedChips" in content
    assert "aiChatForm" in content
    assert "aiChatInput" in content


def test_ui_js_implements_ai_assistant_methods():
    """Verify ui.js includes setupAIAssistant, askAIAssistant, openAIAssistant."""
    ui_js_path = os.path.join(os.path.dirname(__file__), "..", "app", "static", "js", "experience", "ui.js")
    with open(ui_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "setupAIAssistant" in content
    assert "openAIAssistant" in content
    assert "closeAIAssistant" in content
    assert "askAIAssistant" in content
    assert "askAiValuationBtn" in content
    assert "/api/ai/explain" in content


def test_main_js_exposes_ai_methods():
    """Verify main.js exposes openAIAssistant and askAI on global objects."""
    main_js_path = os.path.join(os.path.dirname(__file__), "..", "app", "static", "js", "experience", "main.js")
    with open(main_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "openAIAssistant" in content
    assert "askAI" in content


def test_style_css_contains_phase10_rules():
    """Verify style.css contains Phase 10 AI Assistant styling rules."""
    style_css_path = os.path.join(os.path.dirname(__file__), "..", "app", "static", "css", "style.css")
    with open(style_css_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert ".ai-floating-btn" in content
    assert ".ai-drawer" in content
    assert ".ai-msg" in content
    assert ".ai-typing-indicator" in content
    assert ".ai-refusal-tag" in content
    assert ".ai-citations-box" in content
    assert ".ai-copy-btn" in content
    assert ".ai-share-btn" in content
    assert ".ai-valuation-quick-btn" in content

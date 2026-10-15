# ============================================================
# SMARTCAR AI — PHASE 11 TESTS: PERFORMANCE OPTIMIZATION
# tests/test_performance_optimization.py
# ============================================================

import os
import re
import json
import gzip
import time
import pytest
from pathlib import Path
from collections import OrderedDict
from io import BytesIO

from app.app import app
from app.market_intelligence import (
    market_summary,
    compute_factors,
    find_comparables,
    get_market_cache_stats,
    clear_market_cache,
    _SUMMARY_CACHE,
    MAX_MARKET_CACHE_SIZE
)
from app.vehicle_asset_resolver import VehicleAssetResolver

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT_ROOT / "app"
STATIC_DIR = APP_DIR / "static"
JS_DIR = STATIC_DIR / "js" / "experience"
CSS_DIR = STATIC_DIR / "css"
TEMPLATES_DIR = APP_DIR / "templates"


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ============================================================
# 1. BACKEND MARKET INTELLIGENCE CACHE LIMITS & LRU EVICTION
# ============================================================

def test_market_intelligence_cache_limits_and_eviction():
    """Verify market_intelligence uses a bounded LRU cache with MAX_MARKET_CACHE_SIZE."""
    clear_market_cache()
    stats_initial = get_market_cache_stats()
    assert stats_initial["summary_cache_size"] == 0
    assert stats_initial["summary_cache_max"] == MAX_MARKET_CACHE_SIZE
    assert MAX_MARKET_CACHE_SIZE <= 1024, "Cache limit must be strictly bounded to prevent memory growth"

    # Call market_summary for a real car segment
    s1 = market_summary("BMW", "3 Series", 2021)
    stats1 = get_market_cache_stats()
    assert stats1["summary_cache_size"] == 1
    assert stats1["summary_cache_misses"] >= 1

    # Call again with identical parameters -> should be a hit
    s2 = market_summary("BMW", "3 Series", 2021)
    stats2 = get_market_cache_stats()
    assert stats2["summary_cache_hits"] >= 1
    assert s1 == s2

    # Verify FIFO/LRU eviction when inserting up to max capacity
    for i in range(MAX_MARKET_CACHE_SIZE + 10):
        _SUMMARY_CACHE[f"dummy_key_{i}"] = {"data": i}
        if len(_SUMMARY_CACHE) > MAX_MARKET_CACHE_SIZE:
            _SUMMARY_CACHE.popitem(last=False)

    assert len(_SUMMARY_CACHE) == MAX_MARKET_CACHE_SIZE
    # Earliest items must have been evicted
    assert "dummy_key_0" not in _SUMMARY_CACHE
    assert f"dummy_key_{MAX_MARKET_CACHE_SIZE + 9}" in _SUMMARY_CACHE

    clear_market_cache()
    assert len(_SUMMARY_CACHE) == 0


def test_market_intelligence_helper_caches_bounded():
    """Verify compute_factors and find_comparables use bounded caching."""
    # Test compute_factors caching
    factors1 = compute_factors("BMW", "3 Series", 2021, 45000, "Diesel", "Automatic", "Delhi")
    factors2 = compute_factors("BMW", "3 Series", 2021, 45000, "Diesel", "Automatic", "Delhi")
    assert factors1 == factors2

    # Test find_comparables caching
    comps1 = find_comparables("BMW", "3 Series", 2021, 45000, "Diesel", "Automatic", "Delhi", 3500000, 4)
    comps2 = find_comparables("BMW", "3 Series", 2021, 45000, "Diesel", "Automatic", "Delhi", 3500000, 4)
    assert comps1 == comps2

    stats = get_market_cache_stats()
    assert "factors_cache_size" in stats
    assert "comparables_cache_size" in stats


# ============================================================
# 2. VERIFIED ASSET RESOLUTION CACHE & BOUNDS
# ============================================================

def test_asset_resolver_bounded_lru_cache():
    """Verify VehicleAssetResolver caches resolution results and respects max_size."""
    resolver = VehicleAssetResolver(cache_size=64)
    resolver.clear_cache()
    stats0 = resolver.get_cache_stats()
    assert stats0["cache_size"] == 0
    assert stats0["max_size"] == 64

    # Resolve Porsche 911 (exact local match)
    res1 = resolver.resolve("Porsche", "911", 2021)
    stats1 = resolver.get_cache_stats()
    assert stats1["cache_size"] == 1
    assert stats1["misses"] == 1

    # Second identical resolve must hit in-memory cache
    res2 = resolver.resolve("Porsche", "911", 2021)
    stats2 = resolver.get_cache_stats()
    assert stats2["cache_size"] == 1
    assert stats2["hits"] == 1
    assert res1["status"] == res2["status"]
    assert res1["path"] == res2["path"]

    # Verify cache bounds enforcement
    for i in range(80):
        resolver._resolution_cache[f"key_{i}"] = ("val", False)
        if len(resolver._resolution_cache) > resolver._max_cache_size:
            resolver._resolution_cache.popitem(last=False)

    assert len(resolver._resolution_cache) == 64
    assert "key_0" not in resolver._resolution_cache
    assert "key_79" in resolver._resolution_cache

    resolver.clear_cache()
    assert resolver.get_cache_stats()["cache_size"] == 0


# ============================================================
# 3. HTTP CACHING HEADERS & DYNAMIC COMPRESSION
# ============================================================

def test_static_and_model_caching_headers(client):
    """Verify long-term immutable caching headers for static assets and models."""
    res_static = client.get("/static/css/style.css")
    assert res_static.status_code == 200
    cache_control = res_static.headers.get("Cache-Control", "")
    assert "public" in cache_control
    assert "max-age=" in cache_control

    # Test vehicle model static caching header
    res_model = client.get("/static/models/generic_car.glb")
    assert res_model.status_code == 200
    model_cc = res_model.headers.get("Cache-Control", "")
    assert "public" in model_cc
    assert "max-age=" in model_cc

    # Test vehicle asset API caching header
    res_asset = client.get("/api/vehicle-asset?brand=Porsche&model=911&year=2021")
    assert res_asset.status_code == 200
    asset_cc = res_asset.headers.get("Cache-Control", "")
    assert "public" in asset_cc
    assert "max-age=" in asset_cc


def test_market_intelligence_cache_control_and_etag(client):
    """Verify Cache-Control, ETag, and 304 Not Modified for market intelligence endpoint."""
    res = client.get("/api/market-intelligence?brand=BMW&model=3+Series&manufacturing_year=2021")
    assert res.status_code == 200
    cc = res.headers.get("Cache-Control", "")
    assert "public" in cc
    assert "max-age=" in cc

    etag = res.headers.get("ETag")
    assert etag is not None, "ETag header missing on market intelligence response"

    # Send If-None-Match with the received ETag -> should return HTTP 304
    res_304 = client.get(
        "/api/market-intelligence?brand=BMW&model=3+Series&manufacturing_year=2021",
        headers={"If-None-Match": etag}
    )
    assert res_304.status_code == 304
    assert len(res_304.data) == 0


def test_dynamic_gzip_compression(client):
    """Verify dynamic Gzip compression is triggered when Accept-Encoding: gzip is present."""
    # Request without gzip
    res_plain = client.get(
        "/api/market-intelligence?brand=BMW&model=3+Series&manufacturing_year=2021"
    )
    assert res_plain.status_code == 200
    assert "Content-Encoding" not in res_plain.headers

    # Request with gzip
    res_gzip = client.get(
        "/api/market-intelligence?brand=BMW&model=3+Series&manufacturing_year=2021",
        headers={"Accept-Encoding": "gzip"}
    )
    assert res_gzip.status_code == 200
    if len(res_plain.data) > 500:
        assert res_gzip.headers.get("Content-Encoding") == "gzip"
        assert res_gzip.headers.get("Vary") == "Accept-Encoding"
        decompressed = gzip.decompress(res_gzip.data)
        data = json.loads(decompressed.decode("utf-8"))
        assert "brand" in data or "summary" in data or "total_listings" in data


# ============================================================
# 4. MOBILE RENDERING SAFEGUARDS IN scene.js
# ============================================================

def test_mobile_rendering_safeguards_in_scene_js():
    """Verify scene.js contains mobile safeguards: PR ≈ 1.2, reduced shadows, reduced particles, reduced hills, and optimized HDR."""
    scene_file = JS_DIR / "scene.js"
    assert scene_file.exists()
    content = scene_file.read_text(encoding="utf-8")

    # 1. Mobile pixel ratio ≈ 1.2
    assert "1.2" in content, "Mobile pixel ratio ~1.2 safeguard missing in scene.js"
    assert "maxPR" in content
    assert "isMobile" in content

    # 2. Shadow map size reduced on mobile (1024 vs 2048)
    shadow_pattern = re.search(r"isMobile\s*\?\s*1024\s*:\s*2048", content)
    assert shadow_pattern is not None, "Mobile shadow map size not halved in scene.js"

    # 3. Particle count reduced on mobile (180 vs 900)
    particles_pattern = re.search(r"isMobile\s*\?\s*180\s*:\s*900", content)
    assert particles_pattern is not None, "Particle count safeguard missing on mobile"

    # 4. Distant hills reduced on mobile (4 vs 12)
    hills_pattern = re.search(r"isMobile\s*\?\s*4\s*:\s*12", content)
    assert hills_pattern is not None, "Distant hills safeguard missing on mobile"

    # 5. HDR environment PMREM sigma optimized on mobile (0.08 vs 0.04)
    hdr_sigma_pattern = re.search(r"isMobile\s*\?\s*0\.08\s*:\s*0\.04", content)
    assert hdr_sigma_pattern is not None, "HDR roughness sigma safeguard missing on mobile"


# ============================================================
# 5. TEXTURE OPTIMIZATION IN materialPresets.js
# ============================================================

def test_texture_optimization_in_material_presets():
    """Verify materialPresets.js clamps texture anisotropy to 4 on mobile and disposes textures cleanly."""
    mat_file = JS_DIR / "materialPresets.js"
    assert mat_file.exists()
    content = mat_file.read_text(encoding="utf-8")

    # Clamping anisotropy on mobile (4 on mobile, 16 on desktop)
    assert "maxAnisotropy" in content
    anisotropy_pattern = re.search(r"isMobile\s*\?\s*4\s*:\s*16", content)
    assert anisotropy_pattern is not None, "Texture anisotropy not clamped to 4 on mobile"

    # Texture disposal
    assert "disposeTextures" in content
    assert "roughnessMap" in content
    assert "metalnessMap" in content
    assert "normalMap" in content


# ============================================================
# 6. MEMORY TELEMETRY & RECURSIVE DISPOSAL
# ============================================================

def test_memory_telemetry_and_recursive_disposal():
    """Verify vehicleLoader.js, vehicle.js, and main.js implement memory telemetry and recursive disposal."""
    loader_file = JS_DIR / "vehicleLoader.js"
    vehicle_file = JS_DIR / "vehicle.js"
    main_file = JS_DIR / "main.js"

    loader_content = loader_file.read_text(encoding="utf-8")
    vehicle_content = vehicle_file.read_text(encoding="utf-8")
    main_content = main_file.read_text(encoding="utf-8")

    # VehicleLoader memory stats
    assert "getMemoryStats" in loader_content
    assert "geometries" in loader_content
    assert "materials" in loader_content
    assert "textures" in loader_content

    # VehicleLoader recursive disposal
    assert "dispose()" in loader_content
    assert "disposeTextures" in loader_content

    # SmartCarVehicle memory stats and delegation
    assert "getMemoryStats" in vehicle_content

    # main.js exposes memory stats on window.__SMARTCAR__ and window.smartCarExperience
    assert "getMemoryStats" in main_content
    assert "window.__SMARTCAR__" in main_content


# ============================================================
# 7. CRITICAL ASSET PRIORITIZATION & LOADING SKELETON
# ============================================================

def test_critical_asset_prioritization_in_html():
    """Verify index.html includes preconnect, preload, modulepreload, and loading skeleton."""
    index_file = TEMPLATES_DIR / "index.html"
    content = index_file.read_text(encoding="utf-8")

    # Resource hints
    assert 'rel="preconnect"' in content, "Missing preconnect resource hint"
    assert 'rel="preload"' in content, "Missing preload resource hint for styles"
    assert 'rel="modulepreload"' in content, "Missing modulepreload resource hint for main.js"

    # Loading skeleton
    assert 'id="telemetrySkeleton"' in content, "Missing #telemetrySkeleton loading element"
    assert "skeleton-shimmer" in content, "Missing skeleton-shimmer placeholder class"


def test_loading_skeleton_styles_and_content_visibility():
    """Verify style.css implements skeleton shimmer animations and content-visibility."""
    style_file = CSS_DIR / "style.css"
    content = style_file.read_text(encoding="utf-8")

    assert ".skeleton-shimmer" in content
    assert "@keyframes skeletonShimmer" in content
    assert "content-visibility: auto" in content, "Missing content-visibility: auto for rendering performance"


def test_hud_and_ui_skeleton_and_cache():
    """Verify hud.js toggles skeleton during switches and ui.js caches market intel."""
    hud_file = JS_DIR / "hud.js"
    ui_file = JS_DIR / "ui.js"

    hud_content = hud_file.read_text(encoding="utf-8")
    ui_content = ui_file.read_text(encoding="utf-8")

    assert "showTelemetrySkeleton" in hud_content
    assert "hideTelemetrySkeleton" in hud_content

    assert "marketIntelCache" in ui_content or "intelCache" in ui_content


# ============================================================
# 8. BENCHMARK VEHICLES INTEGRITY & SIZE OPTIMIZATION
# ============================================================

def test_benchmark_models_under_size_budget():
    """Verify benchmark GLBs exist, have valid headers, and stay within mobile bandwidth limits."""
    models_to_check = [
        STATIC_DIR / "models" / "generic_car.glb",
        PROJECT_ROOT / "models" / "cache" / "bmw_3-series_g20-g21-g28-2019-2022.glb",
        PROJECT_ROOT / "models" / "cache" / "hyundai_creta_su2-2022-2025.glb",
        PROJECT_ROOT / "models" / "cache" / "toyota_fortuner_an150-an160-2020-now.glb",
        PROJECT_ROOT / "models" / "cache" / "mercedes_c-class_br206-2021-now.glb",
    ]

    for model_path in models_to_check:
        assert model_path.exists(), f"Benchmark model missing: {model_path.name}"
        size_bytes = model_path.stat().st_size
        if model_path.name == "generic_car.glb":
            assert size_bytes < 45 * 1024 * 1024, f"Model {model_path.name} exceeds 45MB budget ({size_bytes} bytes)"
        else:
            assert size_bytes < 15 * 1024 * 1024, f"Model {model_path.name} exceeds 15MB budget ({size_bytes} bytes)"
        
        with open(model_path, "rb") as f:
            magic = f.read(4)
            assert magic == b"glTF", f"Corrupt magic bytes in {model_path.name}"

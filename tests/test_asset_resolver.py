# ============================================================
# SMARTCAR AI — PHASE 2 UNIT TESTS
# tests/test_asset_resolver.py — Vehicle Identity & Asset Resolution Tests
# ============================================================
#
# Tests 9 required categories:
#   1. exact local
#   2. verified local
#   3. API sanitized
#   4. generation fallback
#   5. unavailable
#   6. wrong generation
#   7. invalid GLB
#   8. caching
#   9. secret leakage
# ============================================================

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.vehicle_asset_resolver import (
    VehicleAssetResolver,
    validate_glb,
    MIN_GLB_SIZE,
    GLB_MAGIC,
)
from app.carimages_service import get_api_credentials


def create_dummy_glb(filepath, size=1500, magic=b"glTF"):
    """Helper to create a dummy valid/invalid GLB file on disk."""
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    header = magic + b"\x02\x00\x00\x00" + (size).to_bytes(4, "little")
    padding = b"\x00" * max(0, size - len(header))
    with open(p, "wb") as f:
        f.write(header + padding)
    return p


# ─── 1. TEST: EXACT LOCAL ──────────────────────────────────

def test_exact_local_studio_hd(tmp_path):
    """Porsche 911 Studio HD showcase asset resolves as exact_local."""
    resolver = VehicleAssetResolver(assets_dir=tmp_path / "assets", cache_dir=tmp_path / "cache")
    result = resolver.resolve("Porsche", "911", 2021)

    assert result["status"] == "exact_local"
    assert result["path"] == "/static/models/generic_car.glb"
    assert result["asset"]["match_level"] == "EXACT_VARIANT"
    assert result["asset"]["source"] == "studio_hd"
    assert result["vehicle"]["brand"] == "Porsche"
    assert result["vehicle"]["model"] == "911"


def test_exact_local_curated_directory(tmp_path):
    """Curated GLB inside assets/vehicles/ resolves with exact_local priority."""
    assets_dir = tmp_path / "assets"
    # Create curated model in benchmark directory
    model_file = assets_dir / "BMW 3 Series 2021" / "model.glb"
    create_dummy_glb(model_file, size=2048)

    resolver = VehicleAssetResolver(assets_dir=assets_dir, cache_dir=tmp_path / "cache")
    result = resolver.resolve("BMW", "3 Series", 2021)

    assert result["status"] == "exact_local"
    assert result["path"].startswith("/api/vehicle-model/bmw/3-series/")
    assert result["asset"]["source"] == "exact_local"
    assert result["asset"]["match_level"] == "EXACT_VARIANT"


# ─── 2. TEST: VERIFIED LOCAL ────────────────────────────────

def test_verified_local_cache(tmp_path):
    """Existing verified GLB in local cache resolves with verified_local status."""
    cache_dir = tmp_path / "cache"
    # Create cached GLB for Mercedes C-Class br206
    cache_file = cache_dir / "mercedes_c-class_br206-2021-now.glb"
    create_dummy_glb(cache_file, size=2048)

    resolver = VehicleAssetResolver(assets_dir=tmp_path / "assets", cache_dir=cache_dir)
    
    with patch("app.vehicle_asset_resolver.resolveVehicleGeneration") as mock_gen:
        mock_gen.return_value = {
            "matched": True,
            "generation_slug": "br206-2021-now",
            "generation_name": "C-Class BR206",
            "year_start": 2021,
            "year_end": 2027,
            "match_level": "GENERATION_MATCH",
        }
        result = resolver.resolve("Mercedes-Benz", "C-Class", 2022)

    assert result["status"] == "verified_local"
    assert result["path"] == "/api/vehicle-model/mercedes/c-class/br206-2021-now"
    assert result["asset"]["source"] == "local_cache"
    assert result["asset"]["generation_slug"] == "br206-2021-now"


# ─── 3. TEST: API SANITIZED ─────────────────────────────────

def test_api_sanitized_download(tmp_path):
    """CarImages API match is downloaded, validated, and returned as api_sanitized."""
    cache_dir = tmp_path / "cache"
    resolver = VehicleAssetResolver(assets_dir=tmp_path / "assets", cache_dir=cache_dir)

    with patch("app.vehicle_asset_resolver.resolveVehicleGeneration") as mock_gen, \
         patch("app.vehicle_asset_resolver.fetch_vehicle_model") as mock_fetch, \
         patch("app.vehicle_asset_resolver.get_cached_or_download_glb") as mock_download:

        mock_gen.return_value = {
            "matched": True,
            "generation_slug": "su2-2022-2025",
            "generation_name": "Creta SU2",
            "year_start": 2022,
            "year_end": 2025,
            "match_level": "GENERATION_MATCH",
        }
        mock_fetch.return_value = (
            200,
            {"model": {"glb": "https://carimagesapi.com/models/creta.glb", "fallback": False}},
            None
        )
        # Mock download writing a valid GLB to cache
        def fake_download(make, model, gen, url):
            target = cache_dir / f"{make}_{model}_{gen}.glb"
            create_dummy_glb(target, size=2500)
            return target

        mock_download.side_effect = fake_download

        result = resolver.resolve("Hyundai", "Creta", 2022)

    assert result["status"] == "api_sanitized"
    assert result["path"] == "/api/vehicle-model/hyundai/creta/su2-2022-2025"
    assert result["asset"]["source"] == "carimagesapi"
    assert result["asset"]["fallback"] is False


# ─── 4. TEST: GENERATION FALLBACK ───────────────────────────

def test_generation_fallback(tmp_path):
    """API fallback response preserves identity and returns generation_fallback status."""
    cache_dir = tmp_path / "cache"
    resolver = VehicleAssetResolver(assets_dir=tmp_path / "assets", cache_dir=cache_dir)

    with patch("app.vehicle_asset_resolver.resolveVehicleGeneration") as mock_gen, \
         patch("app.vehicle_asset_resolver.fetch_vehicle_model") as mock_fetch, \
         patch("app.vehicle_asset_resolver.get_cached_or_download_glb") as mock_download:

        mock_gen.return_value = {
            "matched": True,
            "generation_slug": "an150-an160-2020-now",
            "generation_name": "Fortuner AN150",
            "year_start": 2020,
            "year_end": 2026,
            "match_level": "GENERATION_MATCH",
        }
        mock_fetch.return_value = (
            200,
            {"model": {"glb": "https://carimagesapi.com/models/fortuner.glb", "fallback": True}},
            None
        )
        def fake_download(make, model, gen, url):
            target = cache_dir / f"{make}_{model}_{gen}.glb"
            create_dummy_glb(target, size=2500)
            return target

        mock_download.side_effect = fake_download

        result = resolver.resolve("Toyota", "Fortuner", 2021)

    assert result["status"] == "generation_fallback"
    assert result["asset"]["fallback"] is True
    assert result["asset"]["match_level"] == "GENERATION_FALLBACK"
    assert len(result["warnings"]) > 0


# ─── 5. TEST: UNAVAILABLE ───────────────────────────────────

def test_unavailable_missing_parameters():
    """Missing brand or model immediately returns unavailable status."""
    resolver = VehicleAssetResolver()
    result = resolver.resolve("", "3 Series", 2021)
    assert result["status"] == "unavailable"
    assert result["path"] is None
    assert len(result["warnings"]) > 0

    result2 = resolver.resolve("BMW", "", 2021)
    assert result2["status"] == "unavailable"
    assert result2["path"] is None


def test_unavailable_nonexistent_vehicle(tmp_path):
    """Vehicle with no catalog generation returns unavailable without substitution."""
    resolver = VehicleAssetResolver(assets_dir=tmp_path / "assets", cache_dir=tmp_path / "cache")
    with patch("app.vehicle_asset_resolver.resolveVehicleGeneration") as mock_gen:
        mock_gen.return_value = {"matched": False}
        result = resolver.resolve("NonExistentBrand", "FakeModel", 2021)

    assert result["status"] == "unavailable"
    assert result["path"] is None
    assert result["asset"]["source"] == "none"


# ─── 6. TEST: WRONG GENERATION ──────────────────────────────

def test_wrong_generation_rejected(tmp_path):
    """Passing a wrong generation returns unavailable; never fuzzy matches or substitutes."""
    resolver = VehicleAssetResolver(assets_dir=tmp_path / "assets", cache_dir=tmp_path / "cache")

    with patch("app.vehicle_asset_resolver.fetch_catalog") as mock_cat:
        # Mock catalog returning real BMW 3 Series generations
        mock_cat.return_value = (
            200,
            {
                "generations": [
                    {"slug": "g20-g21-g28-2019-2022", "name": "G20", "year_start": 2019, "year_end": 2022},
                    {"slug": "f30-f31-f34-2012-2019", "name": "F30", "year_start": 2012, "year_end": 2019},
                ]
            },
            None
        )
        result = resolver.resolve("BMW", "3-Series", 2021, generation="wrong_gen")

    assert result["status"] == "unavailable"
    assert result["path"] is None
    assert any("wrong generation" in w.lower() or "invalid" in w.lower() for w in result["warnings"])


# ─── 7. TEST: INVALID GLB ───────────────────────────────────

def test_invalid_glb_magic_bytes_rejected(tmp_path):
    """GLB with invalid magic bytes is rejected by validator and resolver."""
    corrupt_file = tmp_path / "corrupt.glb"
    create_dummy_glb(corrupt_file, size=2048, magic=b"BAD!")
    valid, reason = validate_glb(corrupt_file)

    assert valid is False
    assert "invalid_magic_bytes" in reason


def test_invalid_glb_file_too_small_rejected(tmp_path):
    """GLB with size smaller than MIN_GLB_SIZE is rejected."""
    tiny_file = tmp_path / "tiny.glb"
    create_dummy_glb(tiny_file, size=100, magic=b"glTF")
    valid, reason = validate_glb(tiny_file)

    assert valid is False
    assert "file_too_small" in reason


def test_invalid_glb_in_cache_not_served(tmp_path):
    """Corrupted GLB in cache is rejected and not returned as verified_local."""
    cache_dir = tmp_path / "cache"
    bad_cache = cache_dir / "bmw_3-series_g20.glb"
    create_dummy_glb(bad_cache, size=50, magic=b"FAIL")

    resolver = VehicleAssetResolver(assets_dir=tmp_path / "assets", cache_dir=cache_dir)
    with patch("app.vehicle_asset_resolver.resolveVehicleGeneration") as mock_gen, \
         patch("app.vehicle_asset_resolver.fetch_vehicle_model") as mock_fetch:
        mock_gen.return_value = {
            "matched": True,
            "generation_slug": "g20",
            "generation_name": "G20",
            "year_start": 2019,
            "year_end": 2022,
        }
        mock_fetch.return_value = (404, None, "Not found")
        result = resolver.resolve("BMW", "3 Series", 2021)

    assert result["status"] != "verified_local"
    assert result["status"] == "unavailable"


# ─── 8. TEST: CACHING ───────────────────────────────────────

def test_caching_behavior(tmp_path):
    """Second resolution uses local cache instead of making repeated API calls."""
    cache_dir = tmp_path / "cache"
    resolver = VehicleAssetResolver(assets_dir=tmp_path / "assets", cache_dir=cache_dir)

    with patch("app.vehicle_asset_resolver.resolveVehicleGeneration") as mock_gen, \
         patch("app.vehicle_asset_resolver.fetch_vehicle_model") as mock_fetch, \
         patch("app.vehicle_asset_resolver.get_cached_or_download_glb") as mock_download:

        mock_gen.return_value = {
            "matched": True,
            "generation_slug": "su2-gen",
            "generation_name": "Creta SU2",
            "year_start": 2020,
            "year_end": 2025,
        }
        mock_fetch.return_value = (
            200,
            {"model": {"glb": "https://carimagesapi.com/creta.glb", "fallback": False}},
            None
        )
        def download_fn(make, model, gen, url):
            target = cache_dir / f"{make}_{model}_{gen}.glb"
            create_dummy_glb(target, size=2048)
            return target
        mock_download.side_effect = download_fn

        # Call 1: downloads and returns api_sanitized
        res1 = resolver.resolve("Hyundai", "Creta", 2022)
        assert res1["status"] == "api_sanitized"
        assert mock_fetch.call_count == 1

        # Call 2: cache file now exists and is valid -> verified_local immediately
        res2 = resolver.resolve("Hyundai", "Creta", 2022)
        assert res2["status"] == "verified_local"
        # fetch_vehicle_model should NOT be called again
        assert mock_fetch.call_count == 1


# ─── 9. TEST: SECRET LEAKAGE ────────────────────────────────

def test_zero_secret_leakage_in_resolver_output(tmp_path):
    """API key and secret must NEVER appear in resolver output or warnings."""
    resolver = VehicleAssetResolver(assets_dir=tmp_path / "assets", cache_dir=tmp_path / "cache")
    key, secret = get_api_credentials()

    # Even if environment credentials exist, ensure they never leak
    results = [
        resolver.resolve("Porsche", "911", 2021),
        resolver.resolve("BMW", "3-Series", 2021, generation="wrong_gen"),
        resolver.resolve("Invalid", "Model", 9999),
    ]

    for r in results:
        serialized = json.dumps(r)
        if key:
            assert key not in serialized, "SECURITY BREACH: CARIMAGES_API_KEY leaked in response!"
        if secret:
            assert secret not in serialized, "SECURITY BREACH: CARIMAGES_API_SECRET leaked in response!"
        path_str = r.get("path") or ""
        assert "api_key" not in path_str
        assert "api_secret" not in path_str


def test_zero_secret_leakage_in_flask_endpoint():
    """GET /api/vehicle-asset response JSON must never contain API credentials."""
    from app.app import app
    client = app.test_client()

    key, secret = get_api_credentials()

    # Test Porsche 911
    resp1 = client.get("/api/vehicle-asset?brand=porsche&model=911&year=2021&generation=992")
    data_str1 = resp1.get_data(as_text=True)
    if key:
        assert key not in data_str1, "API Key leaked in /api/vehicle-asset response"
    if secret:
        assert secret not in data_str1, "API Secret leaked in /api/vehicle-asset response"

    # Test wrong generation
    resp2 = client.get("/api/vehicle-asset?brand=bmw&model=3-series&year=2021&generation=wrong_gen")
    data_str2 = resp2.get_data(as_text=True)
    if key:
        assert key not in data_str2, "API Key leaked in /api/vehicle-asset wrong generation response"
    if secret:
        assert secret not in data_str2, "API Secret leaked in /api/vehicle-asset wrong generation response"

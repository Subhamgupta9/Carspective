# ============================================================
# SMARTCAR AI — PHASE 4 UNIT TESTS
# tests/test_manifest_and_ingestion.py — Local High-Quality Asset System Tests
# ============================================================
#
# Tests 5 required categories:
#   1. Manifest loading
#   2. Asset ingestion (valid, corrupted, metadata preservation, optimization)
#   3. Exact local resolution (manifest priority)
#   4. API fallback (when not in manifest)
#   5. Wrong generation rejection (strict verification)
# ============================================================

import os
import json
import struct
import math
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.vehicle_asset_resolver import VehicleAssetResolver, validate_glb
from scripts.ingest_asset import (
    ingest_asset,
    load_manifest,
    save_manifest,
    validate_full_glb,
    AssetValidationError,
    optimize_glb,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT_DIR / "assets" / "vehicles" / "manifest.json"
GENERIC_CAR_PATH = ROOT_DIR / "app" / "static" / "models" / "generic_car.glb"
CACHE_DIR = ROOT_DIR / "models" / "cache"


def create_mock_glb(
    filepath,
    num_meshes=1,
    vertex_count=48,
    dimensions=(4.5, 1.8, 1.4),  # (length, width, height)
    magic=b"glTF",
    corrupt_nan=False,
    corrupt_inf=False,
    materials=None,
):
    """
    Creates a syntactically and semantically valid GLB binary file on disk
    with custom vertex coordinates, meshes, and materials for testing.
    """
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)

    if materials is None:
        materials = [{"name": "CarPaint", "pbrMetallicRoughness": {"roughnessFactor": 0.2, "metallicFactor": 0.8}}]

    l, w, h = dimensions
    # Generate a simple 3D bounding box prism of vertices
    raw_vertices = [
        (-w / 2, 0.0, -l / 2),
        (w / 2, 0.0, -l / 2),
        (w / 2, h, -l / 2),
        (-w / 2, h, -l / 2),
        (-w / 2, 0.0, l / 2),
        (w / 2, 0.0, l / 2),
        (w / 2, h, l / 2),
        (-w / 2, h, l / 2),
    ]
    # Pad to vertex_count
    while len(raw_vertices) < vertex_count:
        raw_vertices.append((0.0, h / 2, 0.0))

    if corrupt_nan:
        raw_vertices[0] = (float("nan"), 0.0, 0.0)
    elif corrupt_inf:
        raw_vertices[0] = (float("inf"), 0.0, 0.0)

    # Pack binary vertex buffer
    bin_buffer = bytearray()
    for vx, vy, vz in raw_vertices:
        bin_buffer.extend(struct.pack("<fff", vx, vy, vz))

    # Pad bin_buffer to 4-byte alignment
    while len(bin_buffer) % 4 != 0:
        bin_buffer.append(0)

    min_x = min(v[0] for v in raw_vertices) if not (corrupt_nan or corrupt_inf) else 0.0
    max_x = max(v[0] for v in raw_vertices) if not (corrupt_nan or corrupt_inf) else 1.0
    min_y = min(v[1] for v in raw_vertices) if not (corrupt_nan or corrupt_inf) else 0.0
    max_y = max(v[1] for v in raw_vertices) if not (corrupt_nan or corrupt_inf) else 1.0
    min_z = min(v[2] for v in raw_vertices) if not (corrupt_nan or corrupt_inf) else 0.0
    max_z = max(v[2] for v in raw_vertices) if not (corrupt_nan or corrupt_inf) else 1.0

    gltf_dict = {
        "asset": {"version": "2.0", "generator": "SmartCar-Test-Builder"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [
            {
                "name": f"Mesh_{i}",
                "primitives": [
                    {
                        "attributes": {"POSITION": 0},
                        "material": 0,
                    }
                ],
            }
            for i in range(num_meshes)
        ],
        "materials": materials,
        "accessors": [
            {
                "bufferView": 0,
                "byteOffset": 0,
                "componentType": 5126,  # FLOAT
                "count": len(raw_vertices),
                "type": "VEC3",
                "max": [max_x, max_y, max_z],
                "min": [min_x, min_y, min_z],
            }
        ],
        "bufferViews": [
            {
                "buffer": 0,
                "byteOffset": 0,
                "byteLength": len(raw_vertices) * 12,
                "byteStride": 12,
            }
        ],
        "buffers": [{"byteLength": len(bin_buffer)}],
    }

    json_bytes = json.dumps(gltf_dict).encode("utf-8")
    # Pad JSON chunk to 4-byte alignment with spaces
    while len(json_bytes) % 4 != 0:
        json_bytes += b" "

    total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_buffer)

    header = magic + struct.pack("<II", 2, total_len)
    chunk0 = struct.pack("<I4s", len(json_bytes), b"JSON") + json_bytes
    chunk1 = struct.pack("<I4s", len(bin_buffer), b"BIN\x00") + bin_buffer

    with open(p, "wb") as f:
        f.write(header + chunk0 + chunk1)

    return p


# ─── 1. TEST SUITE: MANIFEST LOADING ─────────────────────────

def test_manifest_file_exists_and_contains_required_fields():
    """assets/vehicles/manifest.json must exist and contain required schema fields."""
    assert MANIFEST_PATH.exists(), f"Missing manifest: {MANIFEST_PATH}"
    manifest = load_manifest(MANIFEST_PATH)
    assert "vehicles" in manifest
    assert len(manifest["vehicles"]) > 0

    for entry in manifest["vehicles"]:
        # Required Phase 4 fields
        assert "path" in entry, "Manifest entry missing 'path'"
        assert "source" in entry, "Manifest entry missing 'source'"
        assert "verified" in entry, "Manifest entry missing 'verified'"
        assert "generation" in entry, "Manifest entry missing 'generation'"
        assert "variant" in entry, "Manifest entry missing 'variant'"
        assert entry["verified"] is True, "Expected initial manifest entry to be verified"


def test_flagship_asset_registered_in_manifest():
    """Flagship Porsche 911 Carrera 4S Studio HD asset must be registered and verified."""
    manifest = load_manifest(MANIFEST_PATH)
    flagship = next(
        (v for v in manifest["vehicles"] if v.get("make_slug") == "porsche" and v.get("model_slug") == "911"),
        None
    )
    assert flagship is not None, "Porsche 911 flagship missing from manifest.json"
    assert flagship["source"] == "studio_hd"
    assert flagship["verified"] is True
    assert "generic_car.glb" in flagship["path"]
    assert flagship["variant"] == "Carrera 4S"
    assert flagship["generation"] == "992-2019-2025"


def test_manifest_loader_caching_and_invalidation(tmp_path):
    """VehicleAssetResolver caches manifest and reloads when mtime changes."""
    m_path = tmp_path / "manifest.json"
    initial_data = {
        "vehicles": [
            {
                "brand": "Porsche",
                "model": "911",
                "make_slug": "porsche",
                "model_slug": "911",
                "generation": "992",
                "variant": "Turbo",
                "path": "test.glb",
                "source": "curated",
                "verified": True,
            }
        ]
    }
    save_manifest(initial_data, m_path)

    resolver = VehicleAssetResolver(assets_dir=tmp_path, manifest_path=m_path)
    entries1 = resolver.load_manifest()
    assert len(entries1) == 1
    assert entries1[0]["variant"] == "Turbo"

    # Modify manifest
    initial_data["vehicles"].append({
        "brand": "BMW",
        "model": "3 Series",
        "make_slug": "bmw",
        "model_slug": "3-series",
        "generation": "g20",
        "variant": "M340i",
        "path": "bmw.glb",
        "source": "curated",
        "verified": True,
    })
    save_manifest(initial_data, m_path)

    # Force reload or mtime reload
    entries2 = resolver.load_manifest(force_reload=True)
    assert len(entries2) == 2


# ─── 2. TEST SUITE: ASSET INGESTION ──────────────────────────

def test_ingest_valid_glb_success(tmp_path):
    """scripts/ingest_asset.py successfully validates and ingests a valid GLB."""
    src_glb = tmp_path / "raw_bmw.glb"
    create_mock_glb(src_glb, dimensions=(4.71, 1.83, 1.44))

    target_dir = tmp_path / "assets"
    manifest_file = target_dir / "manifest.json"

    result = ingest_asset(
        input_path=src_glb,
        brand="BMW",
        model="3 Series",
        generation="g20-g21-g28-2019-2022",
        year=2021,
        variant="330i M Sport",
        source="curated_local",
        manifest_path=manifest_file,
        target_dir=target_dir,
    )

    assert result["success"] is True
    assert Path(result["destination"]).exists()
    assert result["entry"]["verified"] is True
    assert result["entry"]["variant"] == "330i M Sport"
    assert result["entry"]["generation"] == "g20-g21-g28-2019-2022"

    # Check manifest updated on disk
    manifest = load_manifest(manifest_file)
    assert len(manifest["vehicles"]) == 1
    m_entry = manifest["vehicles"][0]
    assert m_entry["path"].endswith(".glb")
    assert m_entry["verified"] is True
    assert m_entry["generation"] == "g20-g21-g28-2019-2022"
    assert m_entry["variant"] == "330i M Sport"


def test_ingest_corrupted_glb_invalid_magic_rejected(tmp_path):
    """Ingestion rejects files with invalid GLB magic bytes."""
    corrupt_glb = tmp_path / "bad_magic.glb"
    create_mock_glb(corrupt_glb, magic=b"FAIL")

    target_dir = tmp_path / "assets"
    manifest_file = target_dir / "manifest.json"

    with pytest.raises(AssetValidationError, match="Invalid GLB magic bytes"):
        ingest_asset(
            input_path=corrupt_glb,
            brand="Toyota",
            model="Fortuner",
            year=2021,
            manifest_path=manifest_file,
            target_dir=target_dir,
        )

    # Manifest must NOT have been created or modified
    assert not manifest_file.exists()


def test_ingest_corrupted_glb_nan_vertices_rejected(tmp_path):
    """Ingestion rejects assets containing NaN vertex coordinates."""
    nan_glb = tmp_path / "nan_car.glb"
    create_mock_glb(nan_glb, corrupt_nan=True)

    with pytest.raises(AssetValidationError, match="NaN coordinate detected"):
        ingest_asset(
            input_path=nan_glb,
            brand="Hyundai",
            model="Creta",
            year=2022,
        )


def test_ingest_corrupted_glb_zero_meshes_rejected(tmp_path):
    """Ingestion rejects GLB models containing 0 meshes."""
    zero_mesh_glb = tmp_path / "zero_mesh.glb"
    create_mock_glb(zero_mesh_glb, num_meshes=0)

    with pytest.raises(AssetValidationError, match="0 meshes"):
        ingest_asset(
            input_path=zero_mesh_glb,
            brand="Mercedes-Benz",
            model="C-Class",
            year=2022,
        )


def test_ingest_corrupted_glb_degenerate_dimensions_rejected(tmp_path):
    """Ingestion rejects assets with unrealistic / degenerate non-automotive proportions."""
    # Flat sheet: length=0.001
    flat_glb = tmp_path / "flat_sheet.glb"
    create_mock_glb(flat_glb, dimensions=(0.001, 1.8, 1.4))

    with pytest.raises(AssetValidationError, match="Degenerate dimensions detected"):
        ingest_asset(
            input_path=flat_glb,
            brand="Audi",
            model="A4",
            year=2021,
        )


def test_ingest_preserves_canonical_generation_metadata(tmp_path):
    """Ingestion with manufacturing year resolves and stores generation metadata."""
    src_glb = tmp_path / "mercedes.glb"
    create_mock_glb(src_glb, dimensions=(4.75, 1.82, 1.44))

    target_dir = tmp_path / "assets"
    manifest_file = target_dir / "manifest.json"

    with patch("scripts.ingest_asset.resolveVehicleGeneration") as mock_gen:
        mock_gen.return_value = {
            "matched": True,
            "generation_slug": "br206-2021-now",
            "generation_name": "Mercedes-Benz C-Class BR206",
            "year_start": 2021,
            "year_end": 2027,
            "match_level": "GENERATION_MATCH",
        }
        res = ingest_asset(
            input_path=src_glb,
            brand="Mercedes-Benz",
            model="C-Class",
            year=2022,
            manifest_path=manifest_file,
            target_dir=target_dir,
        )

    assert res["entry"]["generation"] == "br206-2021-now"
    assert res["entry"]["generation_name"] == "Mercedes-Benz C-Class BR206"
    assert res["entry"]["year_start"] == 2021
    assert res["entry"]["year_end"] == 2027


def test_ingest_asset_optimization_flag(tmp_path):
    """Ingestion with --optimize reports optimization stats without breaking asset."""
    src_glb = tmp_path / "large_model.glb"
    create_mock_glb(src_glb, dimensions=(4.8, 1.85, 1.83))

    res = ingest_asset(
        input_path=src_glb,
        brand="Toyota",
        model="Fortuner",
        year=2021,
        optimize=True,
        dry_run=True,
    )
    assert "optimization" in res
    assert "initial_size" in res["optimization"]


# ─── 3. TEST SUITE: EXACT LOCAL RESOLUTION (MANIFEST PRIORITY) ─

def test_exact_local_manifest_priority(tmp_path):
    """Verified asset in manifest takes priority #1 over cached API assets."""
    assets_dir = tmp_path / "assets"
    cache_dir = tmp_path / "cache"
    manifest_file = assets_dir / "manifest.json"

    # Create local GLB
    local_glb = assets_dir / "bmw" / "3-series" / "g20" / "model.glb"
    create_mock_glb(local_glb, dimensions=(4.71, 1.83, 1.44))

    # Register in manifest
    manifest_data = {
        "vehicles": [
            {
                "brand": "BMW",
                "model": "3 Series",
                "make_slug": "bmw",
                "model_slug": "3-series",
                "generation": "g20-2019-2022",
                "generation_name": "BMW 3 Series G20",
                "variant": "M Sport",
                "year_start": 2019,
                "year_end": 2022,
                "path": str(local_glb),
                "source": "curated_local",
                "verified": True,
            }
        ]
    }
    save_manifest(manifest_data, manifest_file)

    # Also put a conflicting cached model in cache_dir
    cached_glb = cache_dir / "bmw_3-series_g20-2019-2022.glb"
    create_mock_glb(cached_glb, dimensions=(4.71, 1.83, 1.44))

    resolver = VehicleAssetResolver(assets_dir=assets_dir, cache_dir=cache_dir, manifest_path=manifest_file)
    result = resolver.resolve("BMW", "3 Series", 2021, variant="M Sport")

    assert result["status"] == "exact_local"
    assert result["asset"]["source"] == "curated_local"
    assert result["asset"]["verified"] is True
    assert result["asset"]["variant"] == "M Sport"


def test_unverified_manifest_entry_not_served(tmp_path):
    """Manifest entry with verified=False is skipped and not served as exact_local."""
    assets_dir = tmp_path / "assets"
    manifest_file = assets_dir / "manifest.json"

    local_glb = assets_dir / "unverified.glb"
    create_mock_glb(local_glb)

    manifest_data = {
        "vehicles": [
            {
                "brand": "BMW",
                "model": "3 Series",
                "make_slug": "bmw",
                "model_slug": "3-series",
                "generation": "g20",
                "variant": "",
                "path": str(local_glb),
                "source": "unverified_source",
                "verified": False,  # NOT verified!
            }
        ]
    }
    save_manifest(manifest_data, manifest_file)

    resolver = VehicleAssetResolver(assets_dir=assets_dir, cache_dir=tmp_path / "cache", manifest_path=manifest_file)
    with patch("app.vehicle_asset_resolver.resolveVehicleGeneration") as mock_gen:
        mock_gen.return_value = {"matched": False}
        result = resolver.resolve("BMW", "3 Series", 2021)

    assert result["status"] != "exact_local"


def test_missing_disk_file_in_manifest_skipped_with_warning(tmp_path):
    """Manifest entry referencing non-existent file on disk is safely skipped."""
    assets_dir = tmp_path / "assets"
    manifest_file = assets_dir / "manifest.json"

    manifest_data = {
        "vehicles": [
            {
                "brand": "Audi",
                "model": "A4",
                "make_slug": "audi",
                "model_slug": "a4",
                "generation": "b9",
                "variant": "",
                "year_start": 2016,
                "year_end": 2024,
                "path": "non_existent_file.glb",
                "source": "curated",
                "verified": True,
            }
        ]
    }
    save_manifest(manifest_data, manifest_file)

    resolver = VehicleAssetResolver(assets_dir=assets_dir, cache_dir=tmp_path / "cache", manifest_path=manifest_file)
    with patch("app.vehicle_asset_resolver.resolveVehicleGeneration") as mock_gen:
        mock_gen.return_value = {"matched": False}
        result = resolver.resolve("Audi", "A4", 2021)

    assert result["status"] == "unavailable"
    assert any("rejected" in w.lower() for w in result["warnings"])


# ─── 4. TEST SUITE: API FALLBACK ─────────────────────────────

def test_api_fallback_when_not_in_manifest(tmp_path):
    """When vehicle is not in manifest and not in cache, resolver falls back to API."""
    assets_dir = tmp_path / "assets"
    cache_dir = tmp_path / "cache"
    manifest_file = assets_dir / "manifest.json"
    save_manifest({"vehicles": []}, manifest_file)

    resolver = VehicleAssetResolver(assets_dir=assets_dir, cache_dir=cache_dir, manifest_path=manifest_file)

    with patch("app.vehicle_asset_resolver.resolveVehicleGeneration") as mock_gen, \
         patch("app.vehicle_asset_resolver.fetch_vehicle_model") as mock_fetch, \
         patch("app.vehicle_asset_resolver.get_cached_or_download_glb") as mock_dl:

        mock_gen.return_value = {
            "matched": True,
            "generation_slug": "su2-2022-2025",
            "generation_name": "Hyundai Creta SU2",
            "year_start": 2022,
            "year_end": 2025,
            "match_level": "GENERATION_MATCH",
        }
        mock_fetch.return_value = (
            200,
            {"model": {"glb": "https://api.carimages.com/creta.glb", "fallback": False}},
            None
        )

        def fake_download(make, model, gen, url):
            dest = cache_dir / f"{make}_{model}_{gen}.glb"
            create_mock_glb(dest, dimensions=(4.3, 1.79, 1.63))
            return dest

        mock_dl.side_effect = fake_download

        res = resolver.resolve("Hyundai", "Creta", 2022)

    assert res["status"] == "api_sanitized"
    assert res["asset"]["source"] == "carimagesapi"
    assert res["path"] == "/api/vehicle-model/hyundai/creta/su2-2022-2025"


# ─── 5. TEST SUITE: WRONG GENERATION REJECTION ───────────────

def test_wrong_generation_rejected_even_with_manifest(tmp_path):
    """Querying an explicit wrong generation returns unavailable without substitution."""
    assets_dir = tmp_path / "assets"
    manifest_file = assets_dir / "manifest.json"

    # Register real generation in manifest
    valid_glb = assets_dir / "fortuner.glb"
    create_mock_glb(valid_glb, dimensions=(4.8, 1.85, 1.83))
    manifest_data = {
        "vehicles": [
            {
                "brand": "Toyota",
                "model": "Fortuner",
                "make_slug": "toyota",
                "model_slug": "fortuner",
                "generation": "an150-an160-2020-now",
                "path": str(valid_glb),
                "source": "curated",
                "verified": True,
            }
        ]
    }
    save_manifest(manifest_data, manifest_file)

    resolver = VehicleAssetResolver(assets_dir=assets_dir, cache_dir=tmp_path / "cache", manifest_path=manifest_file)

    with patch("app.vehicle_asset_resolver.fetch_catalog") as mock_cat:
        mock_cat.return_value = (
            200,
            {
                "generations": [
                    {"slug": "an150-an160-2020-now", "name": "AN150", "year_start": 2020, "year_end": 2026}
                ]
            },
            None
        )
        res = resolver.resolve("Toyota", "Fortuner", 2021, generation="bogus_generation_xyz")

    assert res["status"] == "unavailable"
    assert res["path"] is None
    assert any("wrong generation" in w.lower() or "invalid" in w.lower() for w in res["warnings"])

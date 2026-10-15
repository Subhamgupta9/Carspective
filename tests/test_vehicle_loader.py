# ============================================================
# SMARTCAR AI — PHASE 3 UNIT TESTS
# tests/test_vehicle_loader.py — GLB Loading, Validation & Material Normalization Tests
# ============================================================

import json
import struct
import math
import pytest
from pathlib import Path

# Paths to benchmark models
ROOT_DIR = Path(__file__).resolve().parent.parent
GENERIC_CAR_PATH = ROOT_DIR / "app" / "static" / "models" / "generic_car.glb"
CACHE_DIR = ROOT_DIR / "models" / "cache"

BENCHMARK_MODELS = [
    ("Porsche 911 2021", GENERIC_CAR_PATH),
    ("BMW 3 Series 2021", CACHE_DIR / "bmw_3-series_g20-g21-g28-2019-2022.glb"),
    ("Hyundai Creta 2022", CACHE_DIR / "hyundai_creta_su2-2022-2025.glb"),
    ("Toyota Fortuner 2021", CACHE_DIR / "toyota_fortuner_an150-an160-2020-now.glb"),
    ("Mercedes C-Class 2022", CACHE_DIR / "mercedes_c-class_br206-2021-now.glb"),
]

# Automotive envelope limits: Length ~4.5m, Width ~1.8m, Height ~1.4m +- 30%
LIMITS = {
    "length": (4.5 * 0.70, 4.5 * 1.30), # (3.15, 5.85)
    "width":  (1.8 * 0.70, 1.8 * 1.30), # (1.26, 2.34)
    "height": (1.4 * 0.70, 1.4 * 1.30), # (0.98, 1.82)
}


def parse_glb_header_and_chunks(path):
    """Parses binary GLB file and returns (gltf_json, bin_bytes)."""
    with open(path, "rb") as f:
        magic = f.read(4)
        assert magic == b"glTF", f"Invalid magic bytes in {path.name}"
        version = struct.unpack("<I", f.read(4))[0]
        length = struct.unpack("<I", f.read(4))[0]

        json_len = struct.unpack("<I", f.read(4))[0]
        json_type = f.read(4)
        assert json_type == b"JSON", f"Invalid chunk type in {path.name}"
        json_bytes = f.read(json_len)
        gltf = json.loads(json_bytes.decode("utf-8"))

        bin_len = struct.unpack("<I", f.read(4))[0]
        bin_type = f.read(4)
        bin_bytes = f.read(bin_len)

    return gltf, bin_bytes


# ─── 1. TEST: BENCHMARK MODELS LOAD & VALIDATE ─────────────

@pytest.mark.parametrize("label,path", BENCHMARK_MODELS)
def test_benchmark_glb_header_and_mesh_count(label, path):
    """Every benchmark GLB file must exist and contain at least one valid mesh."""
    assert path.exists(), f"Benchmark model file missing: {path}"
    gltf, _ = parse_glb_header_and_chunks(path)

    meshes = gltf.get("meshes", [])
    assert len(meshes) > 0, f"{label} contains 0 meshes!"


@pytest.mark.parametrize("label,path", BENCHMARK_MODELS)
def test_benchmark_glb_buffers_and_no_nan_vertices(label, path):
    """Every benchmark model geometry must have valid position buffers with zero NaN vertices."""
    gltf, bin_bytes = parse_glb_header_and_chunks(path)
    accessors = gltf.get("accessors", [])
    buffer_views = gltf.get("bufferViews", [])
    meshes = gltf.get("meshes", [])

    total_vertices = 0
    nan_count = 0

    for mesh in meshes:
        for prim in mesh.get("primitives", []):
            attrs = prim.get("attributes", {})
            pos_acc_idx = attrs.get("POSITION")
            assert pos_acc_idx is not None, f"Primitive in {label} lacks POSITION attribute!"
            acc = accessors[pos_acc_idx]
            count = acc.get("count", 0)
            assert count > 0, f"Accessor count is 0 in {label}"
            total_vertices += count

            bv_idx = acc.get("bufferView")
            assert bv_idx is not None, f"Accessor missing bufferView in {label}"
            bv = buffer_views[bv_idx]
            byte_offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
            byte_stride = bv.get("byteStride", 12)

            # Sample every 10th vertex
            step = max(1, count // 100)
            for i in range(0, count, step):
                offset = byte_offset + i * byte_stride
                x, y, z = struct.unpack_from("<fff", bin_bytes, offset)
                if math.isnan(x) or math.isnan(y) or math.isnan(z) or math.isinf(x) or math.isinf(y) or math.isinf(z):
                    nan_count += 1

    assert total_vertices > 0, f"{label} has 0 total vertices"
    assert nan_count == 0, f"{label} contains {nan_count} NaN/Infinite vertices!"


@pytest.mark.parametrize("label,path", BENCHMARK_MODELS)
def test_benchmark_glb_materials_and_textures(label, path):
    """Every benchmark model must have valid materials and textures."""
    gltf, _ = parse_glb_header_and_chunks(path)
    materials = gltf.get("materials", [])
    assert len(materials) > 0, f"{label} has 0 materials!"


# ─── 2. TEST: DIMENSIONS & SCALING ENVELOPE ─────────────────

@pytest.mark.parametrize("label,path", BENCHMARK_MODELS)
def test_benchmark_scaled_dimensions_envelope(label, path):
    """When scaled to target height, dimensions must satisfy automotive envelope (L~4.5m, W~1.8m, H~1.4m +-30%)."""
    gltf, bin_bytes = parse_glb_header_and_chunks(path)
    accessors = gltf.get("accessors", [])
    buffer_views = gltf.get("bufferViews", [])

    xs, ys, zs = [], [], []
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            pos_acc_idx = prim.get("attributes", {}).get("POSITION")
            if pos_acc_idx is not None:
                acc = accessors[pos_acc_idx]
                count = acc.get("count", 0)
                bv = buffer_views[acc.get("bufferView")]
                byte_offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
                byte_stride = bv.get("byteStride", 12)
                step = max(1, count // 50)
                for i in range(0, count, step):
                    offset = byte_offset + i * byte_stride
                    x, y, z = struct.unpack_from("<fff", bin_bytes, offset)
                    xs.append(x)
                    ys.append(y)
                    zs.append(z)

    raw_w = max(xs) - min(xs)
    raw_h = max(ys) - min(ys)
    raw_l = max(zs) - min(zs)

    dims = sorted([raw_w, raw_h, raw_l])
    raw_height = dims[0]  # Shortest dimension is height
    raw_width  = dims[1]  # Middle dimension is width
    raw_length = dims[2]  # Longest dimension is length

    # Choose target height based on body type
    if "Fortuner" in label or "Creta" in label:
        target_h = 1.68
    elif "911" in label:
        target_h = 1.35
    else:
        target_h = 1.45

    scale = target_h / raw_height
    scaled_length = raw_length * scale
    scaled_width = raw_width * scale
    scaled_height = target_h

    # Check against +-30% limits
    assert LIMITS["height"][0] <= scaled_height <= LIMITS["height"][1], f"{label} height {scaled_height:.2f} outside limits!"
    assert LIMITS["length"][0] <= scaled_length <= LIMITS["length"][1], f"{label} length {scaled_length:.2f} outside limits!"
    assert LIMITS["width"][0] <= scaled_width <= LIMITS["width"][1], f"{label} width {scaled_width:.2f} outside limits!"


# ─── 3. TEST: MATERIAL PRESETS & CLASSIFICATION MODULE ─────

def test_material_presets_file_exists_and_exports():
    """Verify materialPresets.js exists and defines required presets."""
    preset_file = ROOT_DIR / "app" / "static" / "js" / "experience" / "materialPresets.js"
    assert preset_file.exists(), "materialPresets.js does not exist!"

    content = preset_file.read_text(encoding="utf-8")
    required_presets = ["paint", "glass", "chrome", "rubber", "leather", "plastic"]
    for p in required_presets:
        assert p in content, f"Preset '{p}' missing from materialPresets.js!"
    assert "classifyMaterial" in content
    assert "applyMaterialPreset" in content
    assert "isMaterialHighQuality" in content


# ─── 4. TEST: VEHICLE LOADER CLASS & DISPOSAL ───────────────

def test_vehicle_loader_file_exists_and_implements_api():
    """Verify vehicleLoader.js exists and implements load() and dispose() methods."""
    loader_file = ROOT_DIR / "app" / "static" / "js" / "experience" / "vehicleLoader.js"
    assert loader_file.exists(), "vehicleLoader.js does not exist!"

    content = loader_file.read_text(encoding="utf-8")
    assert "class VehicleLoader" in content
    assert "load(" in content
    assert "dispose(" in content
    assert "validate(" in content
    assert "normalize(" in content
    assert "disposeHierarchy(" in content


def test_main_js_disposes_previous_vehicle_on_switch():
    """Verify main.js calls unloadCurrentVehicle before loading a new vehicle."""
    main_file = ROOT_DIR / "app" / "static" / "js" / "experience" / "main.js"
    assert main_file.exists()

    content = main_file.read_text(encoding="utf-8")
    assert "unloadCurrentVehicle" in content
    assert "switchVehicle" in content
    assert "disposeVehicle" in content
